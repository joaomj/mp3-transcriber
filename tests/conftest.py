import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))


def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


def mock_audio_file(temp_dir):
    """Create a mock audio file for tests."""
    file_path = temp_dir / "test.mp3"
    file_path.write_bytes(b"fake mp3 content")
    return file_path
