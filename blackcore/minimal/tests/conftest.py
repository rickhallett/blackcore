"""Global test configuration and fixtures."""

import pytest
import tempfile
import glob
import os
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_files():
    """Auto-cleanup fixture that runs after all tests."""
    yield
    
    # Clean up any remaining temporary files created during tests
    base_dir = Path(__file__).parent.parent.parent.parent.parent  # Go up to project root
    
    # Clean up temporary files with test prefixes
    for pattern in ["test_*.txt", "test_*.json", "test_*.tmp"]:
        for file_path in glob.glob(str(base_dir / pattern)):
            try:
                os.unlink(file_path)
            except OSError:
                pass  # Ignore errors
    
    # Clean up temporary directories with test prefixes
    temp_base = Path(tempfile.gettempdir())
    for dir_path in temp_base.glob("test_*"):
        try:
            if dir_path.is_dir():
                import shutil
                shutil.rmtree(dir_path, ignore_errors=True)
        except OSError:
            pass  # Ignore errors


@pytest.fixture
def isolated_test_env(tmp_path):
    """Provide an isolated test environment with temporary directory."""
    return {
        "temp_dir": tmp_path,
        "original_cwd": os.getcwd(),
    }