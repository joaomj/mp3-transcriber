import os
import uuid
import asyncio
import zipfile
import logging
from pathlib import Path
from fastapi import (
    APIRouter, Request, Form, UploadFile, File, HTTPException, status, Header
)
from fastapi.responses import FileResponse
from openai import OpenAI, AuthenticationError, APIError, APIConnectionError
from typing import List, Optional

from .security import limiter
from .tasks import TEMP_DIR

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()
# Supported languages are now limited to English and Portuguese
SUPPORTED_LANGUAGES = {"en": "English", "pt": "Portuguese"}
# Defines the maximum file limit
MAX_FILES_LIMIT = 5
# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

async def transcribe_file(client: OpenAI, file_path: str, language: str) -> str:
    """
    Sends an audio file to the OpenAI Whisper API for transcription.
    Uses asyncio.to_thread to run the blocking I/O operation in a separate thread.
    """
    with open(file_path, "rb") as audio_file:
        transcription = await asyncio.to_thread(
            client.audio.transcriptions.create,
            model="whisper-1",
            file=audio_file,
            language=language
        )
    return transcription.text

@router.post("/transcribe")
@limiter.limit("5/minute")
async def handle_transcription(
    request: Request,
    language: str = Form(...),
    authorization: Optional[str] = Header(None),
    files: List[UploadFile] = File(...)
):
    """
    Handles the file upload, transcription, and zipping process.
    API key should be provided in the Authorization header as "Bearer <api_key>"
    """
    # Validate the file count limit
    if len(files) > MAX_FILES_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A maximum of {MAX_FILES_LIMIT} files can be processed at once."
        )

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language selected."
        )
    
    # Extract API key from Authorization header
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key must be provided in the Authorization header as 'Bearer <api_key>'"
        )
    
    api_key = authorization[7:]  # Remove "Bearer " prefix
    
    run_id = str(uuid.uuid4())
    run_path = os.path.join(TEMP_DIR, run_id)
    os.makedirs(run_path, exist_ok=True)
    
    # Initialize cleanup flag
    cleanup_needed = True
    
    client_creation_error = None
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        client_creation_error = str(e)
    
    if client_creation_error:
        logger.error(f"Invalid OpenAI API Key format: {client_creation_error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OpenAI API Key format."
        )

    transcription_tasks = []
    output_filenames = {}
    saved_files = []

    # Track any validation errors
    validation_errors = []
    
    try:
        for index, file in enumerate(files):
            # Validate file type
            if file.content_type not in ["audio/mpeg", "audio/mp3"]:
                validation_errors.append(f"File {file.filename} has invalid MIME type: {file.content_type}")
                continue

            # Validate file extension
            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in [".mp3", ".mpeg"]:
                validation_errors.append(f"File {file.filename} has invalid extension: {file_extension}")
                continue

            # Check file size
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                validation_errors.append(f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE / (1024*1024)} MB")
                continue

            file_path = os.path.join(run_path, file.filename)
            with open(file_path, "wb") as buffer:
                # Copy file in chunks to avoid memory issues
                while True:
                    chunk = await file.read(64 * 1024)  # 64KB chunks
                    if not chunk:
                        break
                    buffer.write(chunk)
            
            saved_files.append(file_path)
            transcription_tasks.append(transcribe_file(client, file_path, language))
            
            base_name = os.path.splitext(file.filename)[0]
            output_filenames[index] = f"{base_name}.txt"

        # If we have validation errors and no valid files, return the errors
        if validation_errors and not transcription_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid MP3 files were provided. Errors: " + "; ".join(validation_errors)
            )

        results = await asyncio.gather(*transcription_tasks, return_exceptions=True)

        zip_path = os.path.join(run_path, "transcriptions.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Transcription failed for file {i}: {result}")
                    # Add error information to the zip file
                    error_filename = f"error_{output_filenames.get(i, f'file_{i}.txt')}"
                    zipf.writestr(error_filename, f"Transcription failed: {str(result)}")
                elif isinstance(result, str) and i in output_filenames:
                    txt_filename = output_filenames[i]
                    zipf.writestr(txt_filename, result.strip())

        # Set cleanup flag to False so the finally block doesn't delete files before response
        cleanup_needed = False
        
        # Return the response
        return FileResponse(
            path=zip_path,
            media_type='application/zip',
            filename='transcriptions.zip'
        )
    except (AuthenticationError, APIError, APIConnectionError) as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OpenAI API Error: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during transcription process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )
    finally:
        # Clean up files if an error occurred before sending response
        if cleanup_needed:
            try:
                # Clean up the run directory
                import shutil
                shutil.rmtree(run_path, ignore_errors=True)
                logger.info(f"Cleaned up directory after error: {run_path}")
            except Exception as e:
                logger.error(f"Failed to clean up directory {run_path}: {e}")