# **Vercel Whisper Transcriber**

A serverless web application designed for easy deployment on Vercel. This tool provides a simple user interface to upload multiple MP3 audio files, transcribe them using OpenAI's Whisper API, and download the results as a single .zip archive.

## **Features**

* **Simple Web UI**: Clean and straightforward interface for uploading files.  
* **User-Provided API Key**: Requires users to provide their own OpenAI API key for each session, ensuring keys are not stored on the server.  
* **Multi-File Processing**: Upload and transcribe multiple MP3 files in a single batch.  
* **Concurrent Transcriptions**: Processes all uploaded files asynchronously for faster results.  
* **Language Selection**: Users must specify the audio language from a supported list.  
* **Zipped Results**: All text transcriptions are conveniently packaged into a single .zip file for download.  
* **Automatic File Cleanup**: All user-uploaded files and generated transcriptions are automatically deleted from the server after 5 minutes to ensure privacy.  
* **Security**: Includes IP-based rate limiting to prevent abuse of the service.

## **Tech Stack**

* **Backend**: FastAPI  
* **Dependency Management**: PDM  
* **Transcription Service**: OpenAI API (Whisper)  
* **Deployment**: Vercel  
* **Background Tasks**: APScheduler

## **Project Structure**

The project uses the src layout to separate the application's source code from project configuration files.

/  
|-- pyproject.toml         \# Project definition and dependencies  
|-- vercel.json            \# Vercel deployment configuration  
|-- api/  
|   |-- index.py           \# Vercel's serverless entry point  
|-- src/  
|   |-- app/               \# Main application source code  
|-- static/  
|   |-- index.html         \# Frontend UI and assets

## **Setup and Local Development**

Follow these steps to run the application on your local machine.

### **1\. Prerequisites**

* Python 3.9+  
* [PDM](https://pdm-project.org/latest/) installed on your system.

### **2\. Clone the Repository**

git clone \<your-repository-url\>  
cd vercel-transcriber

### **3\. Install Dependencies**

PDM will read the pyproject.toml file and install all required packages into a virtual environment.

pdm install

### **4\. Set Environment Variable**

The application requires an OpenAI API key. Set it as an environment variable.

**On macOS/Linux:**

export OPENAI\_API\_KEY="sk-YourSecretKeyHere"

**On Windows (Command Prompt):**

$env:OPENAI\_API\_KEY="sk-YourSecretKeyHere"

### **5\. Run the Development Server**

Use the PDM script defined in pyproject.toml to start the local server.

pdm run dev

The application will now be available at http://127.0.0.1:8000.

## **Deployment to Vercel**

This project is configured for seamless deployment to Vercel.

1. **Push to a Git Repository**: Push your project code to a GitHub, GitLab, or Bitbucket repository.  
2. **Create a Vercel Project**: In your Vercel dashboard, create a new project and link it to your Git repository.  
3. **Configure Environment Variables**: In the Vercel project settings, navigate to "Environment Variables" and add your OPENAI\_API\_KEY. This is a critical step.  
4. **Deploy**: Vercel will automatically detect the vercel.json file and deploy the application. Any push to the main branch will trigger a new deployment.