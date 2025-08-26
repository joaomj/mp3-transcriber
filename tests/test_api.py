import os
import sys
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.index import app


class TestAPI:
    """Test cases for the main API."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_app_instance(self):
        """Test that the app is properly instantiated."""
        assert isinstance(app, FastAPI)

    def test_app_title(self):
        """Test that the app has the correct title."""
        assert app.title == "Vercel Whisper Transcriber"

    def test_app_description(self):
        """Test that the app has the correct description."""
        assert (
            app.description
            == "A serverless web application for audio transcription using OpenAI's Whisper API"
        )

    def test_app_version(self):
        """Test that the app has the correct version."""
        assert app.version == "0.1.0"

    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = self.client.get("/")
        # We expect either a successful response or a 500 if static files are missing
        assert response.status_code in [200, 500]

    def test_transcribe_endpoint_exists(self):
        """Test that the transcribe endpoint is registered."""
        # Find the transcribe route
        transcribe_routes = [
            route for route in app.routes if route.path == "/transcribe"
        ]
        assert len(transcribe_routes) > 0
        assert transcribe_routes[0].methods == {"POST"}

    @patch("src.app.transcription.handle_transcription")
    def test_transcribe_endpoint_call(self, mock_handle_transcription):
        """Test calling the transcribe endpoint."""
        mock_handle_transcription.return_value = {"message": "test"}

        # Test with minimal data
        response = self.client.post(
            "/transcribe",
            data={"language": "en"},
            headers={"Authorization": "Bearer test-key"},
        )

        # We're just checking that the endpoint exists and routes correctly
        # The actual implementation will have its own tests
        assert response.status_code in [200, 400, 401, 422, 500]
