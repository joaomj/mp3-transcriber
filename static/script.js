document.getElementById('transcription-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData();
    const statusDiv = document.getElementById('status');
    const submitBtn = document.getElementById('submit-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const apiKey = document.getElementById('api-key').value;

    // Reset UI elements
    statusDiv.textContent = '';
    progressContainer.style.display = 'none';
    progressBar.style.width = '0%';
    
    // Validate API key
    if (!apiKey.startsWith('sk-')) {
        statusDiv.textContent = 'Error: Please provide a valid OpenAI API key (should start with "sk-").';
        statusDiv.style.color = 'red';
        return;
    }
    
    formData.append('language', document.getElementById('language').value);

    const files = document.getElementById('files').files;
    
    // Client-side validation for the file limit
    if (files.length > 5) {
        statusDiv.textContent = 'Error: You can only upload a maximum of 5 files at a time.';
        statusDiv.style.color = 'red';
        return;
    }
    
    if (files.length === 0) {
        statusDiv.textContent = 'Please select at least one MP3 file.';
        statusDiv.style.color = 'red';
        return;
    }

    // Check file sizes (Vercel has a 100MB limit)
    for (const file of files) {
        if (file.size > 100 * 1024 * 1024) {  // 100MB in bytes
            statusDiv.textContent = `Error: File ${file.name} exceeds the 100MB limit. Please select a smaller file.`;
            statusDiv.style.color = 'red';
            return;
        }
        formData.append('files', file);
    }

    statusDiv.textContent = 'Uploading and processing... This may take a moment.';
    statusDiv.style.color = 'blue';
    submitBtn.disabled = true;
    
    // Display and animate the progress bar
    progressContainer.style.display = 'block';
    progressBar.style.width = '50%'; // Initial animation to show activity

    // Timeout implementation (3 minutes)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
        controller.abort();
    }, 180000); // 3 minutes

    try {
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData,
            headers: {
                'Authorization': `Bearer ${apiKey}`
            },
            signal: controller.signal // Associate the AbortController with the request
        });

        // Clear the timeout if the request completes in time
        clearTimeout(timeoutId);

        progressBar.style.width = '100%';

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'transcriptions.zip';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            
            statusDiv.textContent = 'Success! Your download has started.';
            statusDiv.style.color = 'green';
        } else {
            const error = await response.json();
            statusDiv.textContent = `Error: ${error.detail || 'An unknown error occurred.'}`;
            statusDiv.style.color = 'red';
            progressContainer.style.display = 'none';
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            statusDiv.textContent = 'Error: The request timed out after 3 minutes. Please try again with smaller files.';
        } else {
            statusDiv.textContent = 'A network error occurred. Please try again.';
            console.error('Network error:', error);
        }
        statusDiv.style.color = 'red';
        progressContainer.style.display = 'none';
    } finally {
        submitBtn.disabled = false;
    }
});
