from unittest.mock import Mock, patch

from src.app.tasks import (
    MAX_AGE_SECONDS,
    TEMP_DIR,
    cleanup_old_files,
    shutdown_scheduler,
    start_scheduler,
)


class TestTasks:
    """Test cases for the tasks module."""

    def test_temp_dir_constant(self):
        """Test that the TEMP_DIR constant is correctly set."""
        assert TEMP_DIR == "/tmp/transcriber_runs"

    def test_max_age_seconds(self):
        """Test that MAX_AGE_SECONDS is set to 5 minutes."""
        assert MAX_AGE_SECONDS == 5 * 60

    @patch("src.app.tasks.os.path.exists")
    @patch("src.app.tasks.os.listdir")
    @patch("src.app.tasks.os.stat")
    @patch("src.app.tasks.shutil.rmtree")
    def test_cleanup_old_files(self, mock_rmtree, mock_stat, mock_listdir, mock_exists):
        """Test the cleanup_old_files function."""
        # Setup mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ["dir1", "dir2"]

        # Create a mock stat result with a modification time that's older than MAX_AGE_SECONDS
        old_time = Mock()
        old_time.st_mtime = 0  # Very old timestamp
        mock_stat.return_value = old_time

        # Mock os.path.isdir to return True
        with patch("src.app.tasks.os.path.isdir", return_value=True):
            # Run the function
            cleanup_old_files()

            # Assertions
            assert mock_exists.called
            assert mock_listdir.called
            assert mock_stat.call_count == 2  # Called for each directory
            assert mock_rmtree.call_count == 2  # Called for each directory

    @patch("src.app.tasks.os.makedirs")
    @patch("src.app.tasks.scheduler")
    def test_start_scheduler(self, mock_scheduler, mock_makedirs):
        """Test the start_scheduler function."""
        start_scheduler()

        # Assertions
        mock_makedirs.assert_called_once_with(TEMP_DIR, exist_ok=True)
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()

    @patch("src.app.tasks.scheduler")
    def test_shutdown_scheduler(self, mock_scheduler):
        """Test the shutdown_scheduler function."""
        shutdown_scheduler()

        # Assertions
        mock_scheduler.shutdown.assert_called_once()
