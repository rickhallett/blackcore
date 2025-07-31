"""Test cache directory permissions."""

import os
import tempfile
import shutil
import stat
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

from blackcore.minimal.cache import SimpleCache


class TestCachePermissions:
    """Test suite for cache directory permissions."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_cache_directory_created_with_permissions(self, temp_cache_dir):
        """Test that cache directory is created with restricted permissions."""
        cache_path = Path(temp_cache_dir) / "test_cache"
        
        # Ensure directory doesn't exist
        if cache_path.exists():
            shutil.rmtree(cache_path)
        
        # Create cache
        cache = SimpleCache(cache_dir=str(cache_path))
        
        # Directory should be created
        assert cache_path.exists()
        assert cache_path.is_dir()
        
        # Check permissions (0o700 = drwx------)
        stat_info = cache_path.stat()
        mode = stat_info.st_mode & 0o777
        assert mode == 0o700, f"Expected 0o700, got 0o{mode:o}"
    
    def test_existing_directory_permissions_updated(self, temp_cache_dir):
        """Test that existing directory permissions are updated."""
        cache_path = Path(temp_cache_dir) / "existing_cache"
        
        # Create directory with open permissions
        cache_path.mkdir(exist_ok=True)
        cache_path.chmod(0o777)
        
        # Verify it has open permissions
        mode = cache_path.stat().st_mode & 0o777
        assert mode == 0o777
        
        # Create cache
        cache = SimpleCache(cache_dir=str(cache_path))
        
        # Permissions should be restricted
        mode = cache_path.stat().st_mode & 0o777
        assert mode == 0o700, f"Expected 0o700, got 0o{mode:o}"
    
    def test_cache_files_created_with_permissions(self, temp_cache_dir):
        """Test that cache files are created with restricted permissions."""
        cache = SimpleCache(cache_dir=temp_cache_dir)
        
        # Save some data
        test_data = {"entities": [], "summary": "Test"}
        test_key = "test_key"
        cache.set(test_key, test_data)
        
        # Get the hash of the key to find the file
        import hashlib
        key_hash = hashlib.md5(test_key.encode()).hexdigest()
        cache_file = Path(temp_cache_dir) / f"{key_hash}.json"
        assert cache_file.exists()
        
        # Check file permissions (0o600 = -rw-------)
        stat_info = cache_file.stat()
        mode = stat_info.st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got 0o{mode:o}"
    
    def test_cache_permissions_on_windows(self, temp_cache_dir):
        """Test cache permissions handling on Windows."""
        # Mock platform detection
        with patch('platform.system', return_value='Windows'):
            cache = SimpleCache(cache_dir=temp_cache_dir)
            
            # On Windows, permissions setting should not raise errors
            # Just verify the cache works
            test_data = {"test": "data"}
            cache.set("test", test_data)
            assert cache.get("test") == test_data
    
    def test_permission_error_handling(self, temp_cache_dir):
        """Test handling of permission errors."""
        cache_path = Path(temp_cache_dir) / "protected_cache"
        
        # Mock os.chmod to raise PermissionError
        with patch('os.chmod', side_effect=PermissionError("Permission denied")):
            # Should log warning but not crash
            with patch('blackcore.minimal.cache.logger') as mock_logger:
                cache = SimpleCache(cache_dir=str(cache_path))
                
                # Verify warning was logged
                mock_logger.warning.assert_called()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "Failed to set cache directory permissions" in warning_msg
    
    def test_cache_directory_in_home(self, temp_cache_dir):
        """Test default cache directory permissions in user home."""
        with patch('pathlib.Path.home', return_value=Path(temp_cache_dir)):
            # Create cache with default directory
            cache = SimpleCache()
            
            # Should use .blackcore_cache in home
            expected_path = Path(temp_cache_dir) / ".blackcore_cache"
            assert Path(cache.cache_dir) == expected_path
            
            # Check permissions
            mode = expected_path.stat().st_mode & 0o777
            assert mode == 0o700
    
    def test_subdirectory_permissions(self, temp_cache_dir):
        """Test that subdirectories inherit proper permissions."""
        cache = SimpleCache(cache_dir=temp_cache_dir)
        
        # Create a subdirectory
        subdir = Path(temp_cache_dir) / "subdir"
        subdir.mkdir()
        
        # Set permissions on subdirectory
        cache._set_directory_permissions(str(subdir))
        
        # Check permissions
        mode = subdir.stat().st_mode & 0o777
        assert mode == 0o700
    
    def test_umask_respected(self, temp_cache_dir):
        """Test that umask is properly handled."""
        # Save current umask
        old_umask = os.umask(0o022)
        try:
            cache_path = Path(temp_cache_dir) / "umask_test"
            cache = SimpleCache(cache_dir=str(cache_path))
            
            # Even with umask, should have restricted permissions
            mode = cache_path.stat().st_mode & 0o777
            assert mode == 0o700
        finally:
            # Restore umask
            os.umask(old_umask)
    
    def test_concurrent_permission_setting(self, temp_cache_dir):
        """Test thread-safe permission setting."""
        import threading
        
        cache_path = Path(temp_cache_dir) / "concurrent_test"
        results = []
        
        def create_cache():
            try:
                cache = SimpleCache(cache_dir=str(cache_path))
                mode = cache_path.stat().st_mode & 0o777
                results.append(mode)
            except Exception as e:
                results.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=create_cache) for _ in range(5)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # All should have correct permissions
        for result in results:
            if isinstance(result, int):
                assert result == 0o700
            else:
                # Should not have exceptions
                pytest.fail(f"Unexpected exception: {result}")