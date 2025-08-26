# **Vercel Whisper Transcriber**

A serverless web application designed for easy deployment on Vercel. This tool provides a simple user interface to upload multiple MP3 audio files, transcribe them using OpenAI's Whisper API, and download the results as a single .zip archive.

## **Features**

* **Simple Web UI**: Clean and straightforward interface for uploading files.
* **User-Provided API Key**: Requires users to provide their own OpenAI API key for each session, ensuring keys are not stored on the server. The API key is now sent securely in the Authorization header.
* **Multi-File Processing**: Upload and transcribe multiple MP3 files in a single batch.
* **Concurrent Transcriptions**: Processes all uploaded files asynchronously for faster results.
* **Language Selection**: Users must specify the audio language from a supported list (English or Portuguese).
* **Zipped Results**: All text transcriptions are conveniently packaged into a single .zip file for download.
* **Automatic File Cleanup**: All user-uploaded files and generated transcriptions are automatically deleted from the server after 5 minutes to ensure privacy.
* **Security**: Includes IP-based rate limiting to prevent abuse of the service.
* **Enhanced Error Handling**: Comprehensive error handling for file validation, API errors, and server issues.
* **File Size Limits**: Maximum file size limit of 100MB per file to prevent abuse.

## **Tech Stack**

* **Backend**: FastAPI
* **Dependency Management**: PDM
* **Transcription Service**: OpenAI API (Whisper)
* **Deployment**: Vercel
* **Background Tasks**: APScheduler

## **Project Structure**

The project uses the src layout to separate the application's source code from project configuration files.

```
/
|-- pyproject.toml         # Project definition and dependencies
|-- vercel.json            # Vercel deployment configuration
|-- Makefile               # Commands for running tests and checks
|-- run-checks.sh          # Script to run all tests and quality checks
|-- docs/
|   |-- tech-context.md    # Technical documentation and architecture
|-- api/
|   |-- index.py           # Vercel's serverless entry point
|-- src/
|   |-- app/
|       |-- __init__.py
|       |-- security.py    # Rate limiting configuration
|       |-- tasks.py       # Background tasks for file cleanup
|       |-- transcription.py # Main transcription logic
|-- static/
|   |-- index.html         # Frontend UI
|   |-- script.js          # Frontend JavaScript
|   |-- style.css          # Frontend Styles
|-- tests/
|   |-- conftest.py        # Pytest configuration
|   |-- test_api.py        # Tests for the main API
|   |-- test_security.py   # Tests for the security module
|   |-- test_tasks.py      # Tests for the tasks module
|   |-- test_transcription.py # Tests for the transcription module
```

## **Security Improvements**

1. **API Key Handling**: API keys are now sent in the Authorization header instead of form data, preventing them from being logged in server logs.
2. **File Validation**: Enhanced file validation including MIME type, file extension, and size limits.
3. **Rate Limiting**: IP-based rate limiting to prevent abuse.
4. **Automatic Cleanup**: Files are automatically deleted after 5 minutes.

## **Setup and Local Development**

Follow these steps to run the application on your local machine.

### **1. Prerequisites**

* Python 3.12+
* [PDM](https://pdm-project.org/latest/) installed on your system.

### **2. Clone the Repository**

```bash
git clone <your-repository-url>
cd audio-to-text
```

### **3. Install Dependencies**

PDM will read the pyproject.toml file and install all required packages into a virtual environment.

```bash
pdm install
```

### **4. Run the Development Server**

Use the PDM script defined in pyproject.toml to start the local server.

```bash
pdm run dev
```

The application will now be available at http://127.0.0.1:8000.

## **Testing and Quality Assurance**

This project includes a comprehensive test suite and quality assurance system:

### **Running Tests**

You can run tests using either the Makefile or directly with PDM:

```bash
# Using Makefile
make test

# Using PDM directly
pdm run test
```

### **Running Quality Checks**

The project includes several quality checks:

```bash
# Run all checks at once
make all-checks

# Or run individual checks
make lint        # Code linting (Ruff)
make format      # Code formatting (Ruff)
make type-check  # Type checking (MyPy)
make security    # Security checks (Bandit)
```

### **Test Suite Overview**

The test suite includes:
* 23 unit tests covering all modules
* API endpoint tests
* Security validation
* Error condition testing
* Code quality checks (linting, formatting, type checking, security scanning)

### **Quality Assurance Tools**
* **Linting**: Ruff for code style and error checking
* **Formatting**: Automatic code formatting with Ruff
* **Type Checking**: MyPy for static type checking
* **Security Scanning**: Bandit for security vulnerability detection

## **Deployment to Vercel**

This project is configured for seamless deployment to Vercel.

1. **Push to a Git Repository**: Push your project code to a GitHub, GitLab, or Bitbucket repository.
2. **Create a Vercel Project**: In your Vercel dashboard, create a new project and link it to your Git repository.
3. **Deploy**: Vercel will automatically detect the vercel.json file and deploy the application. Any push to the main branch will trigger a new deployment.

Note: This application does not require any environment variables to be set on Vercel. Each user provides their own OpenAI API key through the UI.

## **API Usage**

The application exposes a single endpoint for transcription:

```
POST /transcribe
```

Parameters:
* `language` (form): The language of the audio files (en or pt)
* `Authorization` (header): Bearer token with the OpenAI API key
* `files` (form): Multiple MP3 files to transcribe

The response will be a ZIP file containing text transcriptions for each audio file.