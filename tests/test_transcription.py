import os
import tempfile
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.app.transcription import (
    MAX_FILE_SIZE,
    MAX_FILES_LIMIT,
    SUPPORTED_LANGUAGES,
    handle_transcription,
    transcribe_file,
)


class TestTranscription:
    """Test cases for the transcription module."""

    def test_supported_languages(self):
        """Test that supported languages are correctly defined."""
        assert "en" in SUPPORTED_LANGUAGES
        assert "pt" in SUPPORTED_LANGUAGES
        assert SUPPORTED_LANGUAGES["en"] == "English"
        assert SUPPORTED_LANGUAGES["pt"] == "Portuguese"

    def test_max_files_limit(self):
        """Test that the maximum files limit is set."""
        assert MAX_FILES_LIMIT == 5

    def test_max_file_size(self):
        """Test that the maximum file size is set correctly (100MB)."""
        assert MAX_FILE_SIZE == 100 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_transcribe_file(self):
        """Test the transcribe_file function."""
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_transcription = Mock()
        mock_transcription.text = "Test transcription"
        mock_client.audio.transcriptions.create.return_value = mock_transcription

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_file.write(b"test audio content")
            tmp_file_path = tmp_file.name

        try:
            result = await transcribe_file(mock_client, tmp_file_path, "en")
            assert result == "Test transcription"
            mock_client.audio.transcriptions.create.assert_called_once()
        finally:
            os.unlink(tmp_file_path)

    @pytest.mark.asyncio
    async def test_handle_transcription_invalid_language(self):
        """Test handle_transcription with an invalid language."""
        # Create a proper Request object
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/transcribe",
            "query_string": b"",
            "headers": [],
        }
        mock_request = Request(mock_scope)
        mock_files = []

        with pytest.raises(HTTPException) as exc_info:
            await handle_transcription(
                request=mock_request,
                language="es",  # Spanish is not supported
                authorization="Bearer test-key",
                files=mock_files,
            )

        assert exc_info.value.status_code == 400
        assert "Unsupported language" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_transcription_missing_auth_header(self):
        """Test handle_transcription without authorization header."""
        # Create a proper Request object
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/transcribe",
            "query_string": b"",
            "headers": [],
        }
        mock_request = Request(mock_scope)
        mock_files = []

        with pytest.raises(HTTPException) as exc_info:
            await handle_transcription(
                request=mock_request,
                language="en",
                authorization=None,  # Missing auth header
                files=mock_files,
            )

        assert exc_info.value.status_code == 400
        assert "API key must be provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_transcription_invalid_auth_header(self):
        """Test handle_transcription with invalid authorization header format."""
        # Create a proper Request object
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/transcribe",
            "query_string": b"",
            "headers": [],
        }
        mock_request = Request(mock_scope)
        mock_files = []

        with pytest.raises(HTTPException) as exc_info:
            await handle_transcription(
                request=mock_request,
                language="en",
                authorization="InvalidFormat",  # Should be "Bearer <key>"
                files=mock_files,
            )

        assert exc_info.value.status_code == 400
        assert "API key must be provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_transcription_too_many_files(self):
        """Test handle_transcription with too many files."""
        # Create a proper Request object
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/transcribe",
            "query_string": b"",
            "headers": [],
        }
        mock_request = Request(mock_scope)
        # Create more files than the limit
        mock_files = [Mock() for _ in range(MAX_FILES_LIMIT + 1)]

        with pytest.raises(HTTPException) as exc_info:
            await handle_transcription(
                request=mock_request,
                language="en",
                authorization="Bearer test-key",
                files=mock_files,
            )

        assert exc_info.value.status_code == 400
        assert f"A maximum of {MAX_FILES_LIMIT} files" in str(exc_info.value.detail)
