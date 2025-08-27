import asyncio
import logging
import os
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from fastapi import (
    APIRouter,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from openai import APIConnectionError, APIError, AuthenticationError, OpenAI

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
    logger.info(f"Starting transcription for file: {file_path}")
    
    # Check if file exists and has content
    if not os.path.exists(file_path):
        error_msg = f"File does not exist: {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
        
    file_size = os.path.getsize(file_path)
    logger.info(f"File size: {file_size} bytes")
    
    if file_size == 0:
        error_msg = f"File is empty: {file_path}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        with open(file_path, "rb") as audio_file:
            # Check if audio file has content
            audio_file.seek(0, os.SEEK_END)
            audio_size = audio_file.tell()
            audio_file.seek(0)
            
            if audio_size == 0:
                error_msg = f"Audio file is empty: {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"Sending {audio_size} bytes to OpenAI API")
            
            transcription = await asyncio.to_thread(
                client.audio.transcriptions.create,
                model="whisper-1",
                file=audio_file,
                language=language,
            )
            
        # Check transcription result
        if transcription is None:
            error_msg = "Received None transcription result from OpenAI API"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not hasattr(transcription, 'text'):
            error_msg = "Transcription result missing 'text' attribute"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        transcription_text = transcription.text
        logger.info(f"Transcription completed for file: {file_path}, length: {len(transcription_text)}")
        
        if len(transcription_text) == 0:
            logger.warning(f"Transcription result is empty for file: {file_path}")
            
        return transcription_text
        
    except Exception as e:
        logger.error(f"Error during transcription of {file_path}: {e}")
        raise


def validate_file(file: UploadFile) -> Optional[str]:
    """Validate a single uploaded file and return an error message if invalid."""
    logger.info(f"Validating file: {file.filename}")
    
    # Validate file extension first
    if file.filename is not None:
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in [".mp3", ".mpeg"]:
            error_msg = f"File {file.filename} has invalid extension: {file_extension}"
            logger.warning(error_msg)
            return error_msg
    else:
        error_msg = "File has no filename"
        logger.warning(error_msg)
        return error_msg

    # Validate file type (be more permissive with MIME types for MP3 files)
    if file.content_type not in ["audio/mpeg", "audio/mp3"]:
        # If MIME type is not what we expect but extension is .mp3, we'll allow it
        if file.filename and Path(file.filename).suffix.lower() == ".mp3":
            logger.info(f"Accepting file with .mp3 extension despite MIME type: {file.content_type}")
        else:
            error_msg = f"File {file.filename} has invalid MIME type: {file.content_type}"
            logger.warning(error_msg)
            return error_msg

    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        error_msg = f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE / (1024 * 1024)} MB"
        logger.warning(error_msg)
        return error_msg

    if file.filename is None:
        error_msg = "File has no filename"
        logger.warning(error_msg)
        return error_msg

    logger.info(f"File {file.filename} passed validation")
    return None


def create_client(api_key: str) -> Tuple[Optional[OpenAI], Optional[str]]:
    """Create OpenAI client and return it with any error message."""
    client_creation_error = None
    client = None
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        client_creation_error = str(e)

    return client, client_creation_error


async def save_file(
    file: UploadFile, run_path: str, index: int
) -> Tuple[Optional[str], Optional[Tuple[int, str]]]:
    """Save a single uploaded file to disk and return file path and output filename."""
    logger.info(f"Saving file {index}: {file.filename}")
    
    if file.filename is None:
        logger.error("File has no filename")
        return None, None

    file_path = os.path.join(run_path, file.filename)
    logger.info(f"Saving file to: {file_path}")
    
    try:
        with open(file_path, "wb") as buffer:
            # Copy file in chunks to avoid memory issues
            total_bytes = 0
            while True:
                chunk = await file.read(64 * 1024)  # 64KB chunks
                if not chunk:
                    break
                buffer.write(chunk)
                total_bytes += len(chunk)
        
        logger.info(f"File saved successfully: {file_path}, size: {total_bytes} bytes")
        
        if total_bytes == 0:
            logger.error("Saved file is empty")
            return None, None
            
        base_name = os.path.splitext(file.filename)[0]
        output_filename = f"{base_name}.txt"

        return file_path, (index, output_filename)
    except Exception as e:
        logger.error(f"Failed to save file {file.filename}: {e}")
        return None, None


def create_zip_response(
    results: List[Union[str, Exception]],
    output_filenames: Dict[int, str],
    run_path: str,
) -> str:
    """Create a zip file with transcription results and return its path."""
    logger.info(f"Creating ZIP response with {len(results)} results")
    zip_path = os.path.join(run_path, "transcriptions.zip")
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for i, result in enumerate(results):
            logger.info(f"Processing result {i}: {type(result)}")
            if isinstance(result, Exception):
                logger.error(f"Transcription failed for file {i}: {result}")
                # Add error information to the zip file
                error_filename = f"error_{output_filenames.get(i, f'file_{i}.txt')}"
                zipf.writestr(error_filename, f"Transcription failed: {str(result)}")
            elif isinstance(result, str) and i in output_filenames:
                txt_filename = output_filenames[i]
                logger.info(f"Adding transcription for {txt_filename}: {len(result)} characters")
                zipf.writestr(txt_filename, result.strip())
            else:
                logger.warning(f"Unexpected result type or missing filename for result {i}")

    logger.info(f"ZIP file created at {zip_path}")
    return zip_path


def validate_request_data(
    files: List[UploadFile], language: str, authorization: Optional[str]
) -> str:
    """Validate request data and return API key if valid."""
    # Validate the file count limit
    if len(files) > MAX_FILES_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A maximum of {MAX_FILES_LIMIT} files can be processed at once.",
        )

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language selected.",
        )

    # Extract API key from Authorization header
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key must be provided in the Authorization header as 'Bearer <api_key>'",
        )

    return authorization[7:]  # Remove "Bearer " prefix


async def process_files(
    files: List[UploadFile], run_path: str
) -> Tuple[List[str], Dict[int, str], List[str]]:
    """Process uploaded files and return saved files, output filenames, and validation errors."""
    logger.info(f"Processing {len(files)} files")
    validation_errors: List[str] = []
    save_tasks = []

    for index, file in enumerate(files):
        logger.info(f"Processing file {index}: {file.filename}")
        # Validate file
        error = validate_file(file)
        if error:
            logger.warning(f"File validation error for {file.filename}: {error}")
            validation_errors.append(error)
            continue

        # Create save task
        save_tasks.append(save_file(file, run_path, index))

    logger.info(f"Validation errors: {len(validation_errors)}")
    logger.info(f"Save tasks created: {len(save_tasks)}")

    # If all files have validation errors, raise an exception
    if validation_errors and len(validation_errors) == len(files):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid MP3 files were provided. Errors: "
            + "; ".join(validation_errors),
        )

    # Save files concurrently
    save_results: List[
        Union[Tuple[Optional[str], Optional[Tuple[int, str]]], BaseException]
    ] = await asyncio.gather(*save_tasks, return_exceptions=True)  # type: ignore

    # Process save results
    saved_files: List[str] = []
    output_filenames: Dict[int, str] = {}
    for result in save_results:
        if isinstance(result, Exception):
            logger.error(f"Failed to save file: {result}")
            continue
        elif isinstance(result, tuple) and len(result) == 2:
            file_path, output_info = result
            if file_path and output_info:
                index, filename = output_info
                saved_files.append(file_path)
                output_filenames[index] = filename

    logger.info(f"Saved files: {len(saved_files)}")
    logger.info(f"Output filenames: {output_filenames}")
    return saved_files, output_filenames, validation_errors


@router.post("/transcribe")
@limiter.limit("5/minute")
async def handle_transcription(
    request: Request,
    language: str = Form(...),
    authorization: Optional[str] = Header(None),
    files: Optional[List[UploadFile]] = None,
) -> FileResponse:
    # Handle the case where files is None
    if files is None:
        files = []

    logger.info(f"Received transcription request with {len(files)} files, language: {language}")
    
    # Validate request data
    api_key = validate_request_data(files, language, authorization)

    run_id = str(uuid.uuid4())
    run_path = os.path.join(TEMP_DIR, run_id)
    os.makedirs(run_path, exist_ok=True)
    logger.info(f"Created run directory: {run_path}")

    # Initialize cleanup flag
    cleanup_needed = True

    # Create OpenAI client
    client, client_creation_error = create_client(api_key)
    if client_creation_error:
        logger.error(f"Invalid OpenAI API Key format: {client_creation_error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OpenAI API Key format.",
        )

    # This should never happen, but mypy needs assurance
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OpenAI client.",
        )

    try:
        # Process files
        saved_files, output_filenames, validation_errors = await process_files(
            files or [], run_path
        )
        
        logger.info(f"Processed files - saved: {len(saved_files)}, output filenames: {len(output_filenames)}")

        # Create transcription tasks for valid files
        transcription_tasks = [
            transcribe_file(client, file_path, language) for file_path in saved_files
        ]
        
        logger.info(f"Created {len(transcription_tasks)} transcription tasks")

        # Process transcriptions
        results = await asyncio.gather(*transcription_tasks, return_exceptions=True)
        logger.info(f"Received {len(results)} transcription results")
        
        # Log details about results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Transcription task {i} failed: {result}")
            else:
                logger.info(f"Transcription task {i} succeeded, length: {len(result) if result else 0}")

        # Create zip file with results
        zip_path = create_zip_response(list(results), output_filenames, run_path)  # type: ignore

        # Set cleanup flag to False so the finally block doesn't delete files before response
        cleanup_needed = False

        # Return the response
        logger.info(f"Returning ZIP file: {zip_path}")
        return FileResponse(
            path=zip_path, media_type="application/zip", filename="transcriptions.zip"
        )
    except (AuthenticationError, APIError, APIConnectionError) as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OpenAI API Error: {str(e)}",
        ) from e
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during transcription process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        ) from e
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
