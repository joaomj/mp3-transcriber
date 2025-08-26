document.getElementById('transcription-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData();
    const statusDiv = document.getElementById('status');
    const submitBtn = document.getElementById('submit-btn');

    formData.append('api_key', document.getElementById('api-key').value);
    formData.append('language', document.getElementById('language').value);

    const files = document.getElementById('files').files;
    if (files.length === 0) {
        statusDiv.textContent = 'Please select at least one MP3 file.';
        statusDiv.style.color = 'red';
        return;
    }
    for (const file of files) {
        formData.append('files', file);
    }

    statusDiv.textContent = 'Uploading and processing... This may take a moment.';
    statusDiv.style.color = 'blue';
    submitBtn.disabled = true;

    try {
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData,
        });

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
        }
    } catch (error) {
        statusDiv.textContent = 'A network error occurred. Please try again.';
        statusDiv.style.color = 'red';
    } finally {
        submitBtn.disabled = false;
    }
});
