import os
import uuid
import asyncio
import zipfile
from fastapi import (
    APIRouter, Request, Form, UploadFile, File, HTTPException, status
)
from fastapi.responses import FileResponse
from openai import OpenAI, AuthenticationError, APIError
from typing import List

from .security import limiter
from .tasks import TEMP_DIR

router = APIRouter()
SUPPORTED_LANGUAGES = {"en": "English", "pt": "Portuguese"}

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
    api_key: str = Form(...),
    language: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Handles the file upload, transcription, and zipping process.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language selected."
        )
    
    # Create a unique directory for this request to avoid file collisions
    run_id = str(uuid.uuid4())
    run_path = os.path.join(TEMP_DIR, run_id)
    os.makedirs(run_path)
    
    try:
        client = OpenAI(api_key=api_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OpenAI API Key format."
        )

    transcription_tasks = []
    output_filenames = {}

    for index, file in enumerate(files):
        if file.content_type not in ["audio/mpeg", "audio/mp3"]:
            # Silently skip non-MP3 files
            continue

        # Save the uploaded file to the unique request directory
        file_path = os.path.join(run_path, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        transcription_tasks.append(transcribe_file(client, file_path, language))
        
        # Store the desired output filename for the corresponding task
        base_name = os.path.splitext(file.filename)[0]
        output_filenames[index] = f"{base_name}.txt"

    if not transcription_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid MP3 files were provided."
        )

    try:
        # Run all transcription tasks concurrently
        results = await asyncio.gather(*transcription_tasks, return_exceptions=True)
    except (AuthenticationError, APIError) as e:
        # Handle API-level errors from OpenAI
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OpenAI API Error: {e}"
        )

    zip_path = os.path.join(run_path, "transcriptions.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for i, result in enumerate(results):
            if isinstance(result, str) and i in output_filenames:
                txt_filename = output_filenames[i]
                zipf.writestr(txt_filename, result.strip())

    # Return the zip file for download
    return FileResponse(
        path=zip_path,
        media_type='application/zip',
        filename='transcriptions.zip'
    )
