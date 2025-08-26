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
    with open(file_path, "rb") as audio_file:
        transcription = await asyncio.to_thread(
            client.audio.transcriptions.create,
            model="whisper-1",
            file=audio_file,
            language=language,
        )
    return transcription.text


def validate_file(file: UploadFile) -> Optional[str]:
    """Validate a single uploaded file and return an error message if invalid."""
    # Validate file type
    if file.content_type not in ["audio/mpeg", "audio/mp3"]:
        return f"File {file.filename} has invalid MIME type: {file.content_type}"

    # Validate file extension
    if file.filename is not None:
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in [".mp3", ".mpeg"]:
            return f"File {file.filename} has invalid extension: {file_extension}"
    else:
        return "File has no filename"

    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE / (1024 * 1024)} MB"

    if file.filename is None:
        return "File has no filename"

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
    if file.filename is None:
        return None, None

    file_path = os.path.join(run_path, file.filename)
    with open(file_path, "wb") as buffer:
        # Copy file in chunks to avoid memory issues
        while True:
            chunk = await file.read(64 * 1024)  # 64KB chunks
            if not chunk:
                break
            buffer.write(chunk)

    base_name = os.path.splitext(file.filename)[0]
    output_filename = f"{base_name}.txt"

    return file_path, (index, output_filename)


def create_zip_response(
    results: List[Union[str, Exception]],
    output_filenames: Dict[int, str],
    run_path: str,
) -> str:
    """Create a zip file with transcription results and return its path."""
    zip_path = os.path.join(run_path, "transcriptions.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Transcription failed for file {i}: {result}")
                # Add error information to the zip file
                error_filename = f"error_{output_filenames.get(i, f'file_{i}.txt')}"
                zipf.writestr(error_filename, f"Transcription failed: {str(result)}")
            elif isinstance(result, str) and i in output_filenames:
                txt_filename = output_filenames[i]
                zipf.writestr(txt_filename, result.strip())

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


def process_files(
    files: List[UploadFile], run_path: str
) -> Tuple[List[str], Dict[int, str], List[str]]:
    """Process uploaded files and return saved files, output filenames, and validation errors."""
    validation_errors: List[str] = []
    save_tasks = []

    for index, file in enumerate(files):
        # Validate file
        error = validate_file(file)
        if error:
            validation_errors.append(error)
            continue

        # Create save task
        save_tasks.append(save_file(file, run_path, index))

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
    ] = asyncio.run(asyncio.gather(*save_tasks, return_exceptions=True))  # type: ignore

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

    # Validate request data
    api_key = validate_request_data(files, language, authorization)

    run_id = str(uuid.uuid4())
    run_path = os.path.join(TEMP_DIR, run_id)
    os.makedirs(run_path, exist_ok=True)

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
        saved_files, output_filenames, validation_errors = process_files(
            files or [], run_path
        )

        # Create transcription tasks for valid files
        transcription_tasks = [
            transcribe_file(client, file_path, language) for file_path in saved_files
        ]

        # Process transcriptions
        results = await asyncio.gather(*transcription_tasks, return_exceptions=True)

        # Create zip file with results
        zip_path = create_zip_response(list(results), output_filenames, run_path)  # type: ignore

        # Set cleanup flag to False so the finally block doesn't delete files before response
        cleanup_needed = False

        # Return the response
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
