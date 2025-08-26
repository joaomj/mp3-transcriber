import os
import shutil
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Use Vercel's recommended temporary directory for serverless functions
TEMP_DIR = "/tmp/transcriber_runs"
# Files and directories older than 5 minutes will be deleted
MAX_AGE_SECONDS = 5 * 60

scheduler = AsyncIOScheduler()

def cleanup_old_files():
    """Finds and deletes processing directories that are older than MAX_AGE_SECONDS."""
    if not os.path.exists(TEMP_DIR):
        return

    now = time.time()
    for dirname in os.listdir(TEMP_DIR):
        dirpath = os.path.join(TEMP_DIR, dirname)
        try:
            if os.stat(dirpath).st_mtime < now - MAX_AGE_SECONDS:
                shutil.rmtree(dirpath, ignore_errors=True)
                print(f"Cleaned up old directory: {dirpath}")
        except FileNotFoundError:
            # This can happen if another process cleans the file between listdir and stat
            continue

def start_scheduler():
    """Initializes the temporary directory and starts the cleanup scheduler."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    scheduler.add_job(cleanup_old_files, 'interval', minutes=1)
    scheduler.start()
    print("Cleanup scheduler started.")

def shutdown_scheduler():
    """Shuts down the cleanup scheduler gracefully."""
    scheduler.shutdown()
    print("Cleanup scheduler stopped.")