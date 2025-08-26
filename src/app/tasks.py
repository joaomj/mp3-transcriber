import logging
import os
import shutil
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configure logging
logger = logging.getLogger(__name__)

# Use Vercel's recommended temporary directory for serverless functions
# This is intentional for Vercel's serverless functions environment
TEMP_DIR = "/tmp/transcriber_runs"  # nosec B108
# Files and directories older than 5 minutes will be deleted
MAX_AGE_SECONDS = 5 * 60

scheduler = AsyncIOScheduler()


def cleanup_old_files() -> None:
    """Finds and deletes processing directories that are older than MAX_AGE_SECONDS."""
    if not os.path.exists(TEMP_DIR):
        return

    now = time.time()
    for dirname in os.listdir(TEMP_DIR):
        dirpath = os.path.join(TEMP_DIR, dirname)
        try:
            # Check if it's a directory and get its modification time
            if os.path.isdir(dirpath):
                if os.stat(dirpath).st_mtime < now - MAX_AGE_SECONDS:
                    shutil.rmtree(dirpath, ignore_errors=True)
                    logger.info(f"Cleaned up old directory: {dirpath}")
        except FileNotFoundError:
            # This can happen if another process cleans the file between listdir and stat
            continue
        except PermissionError as e:
            logger.warning(f"Permission error when cleaning up {dirpath}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error when cleaning up {dirpath}: {e}")


def start_scheduler() -> None:
    """Initializes the temporary directory and starts the cleanup scheduler."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    scheduler.add_job(cleanup_old_files, "interval", minutes=1)
    scheduler.start()
    logger.info("Cleanup scheduler started.")


def shutdown_scheduler() -> None:
    """Shuts down the cleanup scheduler gracefully."""
    try:
        scheduler.shutdown()
        logger.info("Cleanup scheduler stopped.")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")
