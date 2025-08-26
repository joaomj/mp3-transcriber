# Technical Context

This document provides an overview of the architecture, components, and technical decisions for the Vercel Whisper Transcriber project.

## Project Overview

A serverless web application designed for easy deployment on Vercel. This tool provides a simple user interface to upload multiple MP3 audio files, transcribe them using OpenAI's Whisper API, and download the results as a single .zip archive.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Frontend UI   │────│  FastAPI Server  │────│  OpenAI Whisper  │
│   (Static HTML) │    │ (Serverless API) │    │     API          │
└─────────────────┘    └──────────────────┘    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   File Storage   │
                    │   (/tmp on Vercel)│
                    └──────────────────┘
```

### Components

1. **Frontend UI** (`static/`): Simple HTML/CSS/JavaScript interface for file uploads
2. **API Layer** (`api/index.py`): FastAPI application entry point with serverless deployment configuration
3. **Core Logic** (`src/app/`): Modular Python package containing:
   - Transcription processing (`transcription.py`)
   - Security/rate limiting (`security.py`)
   - Background tasks (`tasks.py`)
4. **Temporary Storage**: Uses Vercel's `/tmp` directory for file processing

## Key Technical Decisions

### 1. Security Improvements

- **API Key Handling**: API keys are sent in the Authorization header instead of form data to prevent logging
- **File Validation**: Enhanced validation including MIME type, file extension, and size limits (100MB max)
- **Rate Limiting**: IP-based rate limiting (10 requests/minute) to prevent abuse
- **Automatic Cleanup**: Files automatically deleted after 5 minutes

### 2. Architecture Patterns

- **Serverless-First Design**: Optimized for Vercel's serverless environment
- **Modular Structure**: Clean separation of concerns using Python packages
- **Asynchronous Processing**: Concurrent transcription processing for better performance
- **Resource Management**: Proper cleanup of temporary files and resources

### 3. Error Handling

- Comprehensive error handling for various failure scenarios
- Proper logging for debugging and monitoring
- Graceful degradation when individual transcriptions fail
- Validation error collection rather than immediate failure

## Dependencies

### Core Dependencies
- **FastAPI**: Web framework for API development
- **OpenAI**: Official Python client for Whisper API
- **SlowAPI**: Rate limiting implementation
- **APScheduler**: Background task scheduling

### Development Dependencies
- **PDM**: Package and dependency management
- **Pytest**: Testing framework
- **Ruff**: Code linting and formatting
- **MyPy**: Static type checking
- **Bandit**: Security scanning

## Deployment

### Vercel Configuration
- Python 3.12 runtime
- Serverless functions deployment
- Automatic scaling
- Edge network distribution

### Environment
- No persistent storage (uses `/tmp` for temporary files)
- Cold start optimization
- 5-minute execution timeout

## Testing Strategy

### Test Coverage
- Unit tests for all modules
- API endpoint testing
- Security validation
- Error condition testing

### Quality Assurance
- Code linting (Ruff)
- Type checking (MyPy)
- Security scanning (Bandit)
- Automated formatting

## File Structure

```
/
├── api/
│   └── index.py              # Vercel serverless entry point
├── src/
│   └── app/
│       ├── __init__.py
│       ├── security.py       # Rate limiting configuration
│       ├── tasks.py          # Background cleanup tasks
│       └── transcription.py  # Core transcription logic
├── static/
│   ├── index.html            # Frontend UI
│   ├── script.js             # Client-side JavaScript
│   └── style.css             # Styling
├── tests/                    # Test suite
│   ├── test_api.py
│   ├── test_security.py
│   ├── test_tasks.py
│   └── test_transcription.py
├── pyproject.toml            # Project configuration
├── vercel.json               # Deployment configuration
└── README.md                 # User documentation
```

## API Endpoints

### Main Endpoint
```
POST /transcribe
```

Parameters:
- `language` (form): Audio language (en or pt)
- `Authorization` (header): Bearer token with OpenAI API key
- `files` (form): Multiple MP3 files to transcribe

Response:
- ZIP file containing text transcriptions for each audio file

## Performance Considerations

- Asynchronous file processing for concurrent transcriptions
- Chunked file reading to avoid memory issues
- Temporary file cleanup to prevent storage overflow
- Rate limiting to ensure fair usage

## Security Considerations

- API keys never stored on server
- File type and size validation
- IP-based rate limiting
- Temporary file isolation
- Automatic cleanup after processing

## Future Improvements

- Additional language support
- Support for more audio formats
- Enhanced error reporting
- Progress tracking for long transcriptions
- Batch processing optimizations