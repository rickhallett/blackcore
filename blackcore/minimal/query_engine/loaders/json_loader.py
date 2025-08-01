"""High-performance JSON data loader with memory-mapped file support."""

import json
import mmap
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from ..interfaces import DataLoader
from ..models import QueryError

logger = logging.getLogger(__name__)


class JSONDataLoader:
    """High-performance JSON data loader with optimized file reading.
    
    Performance characteristics:
    - O(1) database name lookup
    - O(n) data loading where n is file size
    - Memory-mapped reading for large files
    - Concurrent loading support
    - <100ms loading for 10K records target
    """
    
    def __init__(
        self, 
        cache_dir: str = "blackcore/models/json",
        enable_mmap: bool = True,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """Initialize JSON data loader.
        
        Args:
            cache_dir: Directory containing JSON database files
            enable_mmap: Use memory-mapped file reading for performance
            max_workers: Maximum concurrent file loading workers
            progress_callback: Callback for long operations (database_name, progress_percent)
        """
        self.cache_dir = Path(cache_dir)
        self.enable_mmap = enable_mmap
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._file_stats: Dict[str, Dict[str, Any]] = {}
        
        if not self.cache_dir.exists():
            raise QueryError(f"Cache directory does not exist: {cache_dir}")
    
    def load_database(self, database_name: str) -> List[Dict[str, Any]]:
        """Load a database by name with optimized reading.
        
        Performance: O(n) where n is file size
        Memory: ~1.2x file size during loading
        
        Args:
            database_name: Name of the database to load
            
        Returns:
            List of database records
            
        Raises:
            QueryError: If database cannot be loaded
        """
        if database_name in self._cache:
            logger.debug(f"Returning cached data for {database_name}")
            return self._cache[database_name]
        
        file_path = self._find_database_file(database_name)
        if not file_path:
            raise QueryError(f"Database not found: {database_name}")
        
        try:
            data = self._load_json_file(file_path, database_name)
            self._cache[database_name] = data
            return data
        except Exception as e:
            raise QueryError(f"Failed to load database {database_name}: {str(e)}")
    
    def get_available_databases(self) -> List[str]:
        """Get list of available databases.
        
        Performance: O(n) where n is number of files
        
        Returns:
            List of database names
        """
        databases = []
        
        for file_path in self.cache_dir.glob("*.json"):
            if file_path.is_file():
                db_name = file_path.stem
                if db_name not in self._file_stats:
                    self._file_stats[db_name] = {
                        "path": file_path,
                        "size": file_path.stat().st_size,
                        "modified": file_path.stat().st_mtime
                    }
                databases.append(db_name)
        
        return sorted(databases)
    
    def refresh_cache(self, database_name: Optional[str] = None) -> None:
        """Refresh cached data by reloading from disk.
        
        Args:
            database_name: Specific database to refresh, or None for all
        """
        if database_name:
            if database_name in self._cache:
                del self._cache[database_name]
            if database_name in self._file_stats:
                del self._file_stats[database_name]
            logger.info(f"Cleared cache for database: {database_name}")
        else:
            self._cache.clear()
            self._file_stats.clear()
            logger.info("Cleared all cached data")
    
    def load_multiple_databases(self, database_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Load multiple databases concurrently for performance.
        
        Performance: O(n) with concurrent loading
        
        Args:
            database_names: List of databases to load
            
        Returns:
            Dict mapping database name to data
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_db = {
                executor.submit(self.load_database, db_name): db_name 
                for db_name in database_names
            }
            
            for future in as_completed(future_to_db):
                db_name = future_to_db[future]
                try:
                    results[db_name] = future.result()
                except Exception as e:
                    logger.error(f"Failed to load {db_name}: {e}")
                    results[db_name] = []
        
        return results
    
    def _find_database_file(self, database_name: str) -> Optional[Path]:
        """Find database file by name."""
        json_file = self.cache_dir / f"{database_name}.json"
        if json_file.exists():
            return json_file
        
        # Try case-insensitive search
        for file_path in self.cache_dir.glob("*.json"):
            if file_path.stem.lower() == database_name.lower():
                return file_path
        
        return None
    
    def _load_json_file(self, file_path: Path, database_name: str) -> List[Dict[str, Any]]:
        """Load JSON file with optimized reading strategy.
        
        Uses memory mapping for files >10MB for better performance.
        """
        file_size = file_path.stat().st_size
        
        # Report progress for large files
        if self.progress_callback and file_size > 1_000_000:  # 1MB
            self.progress_callback(database_name, 0.0)
        
        # Use memory mapping for large files
        if self.enable_mmap and file_size > 10_000_000:  # 10MB
            return self._load_with_mmap(file_path, database_name)
        else:
            return self._load_standard(file_path, database_name)
    
    def _load_standard(self, file_path: Path, database_name: str) -> List[Dict[str, Any]]:
        """Standard JSON loading for smaller files."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if self.progress_callback:
            self.progress_callback(database_name, 100.0)
        
        # Validate data structure
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        elif isinstance(data, list):
            return data
        else:
            raise QueryError(f"Invalid JSON structure in {database_name}")
    
    def _load_with_mmap(self, file_path: Path, database_name: str) -> List[Dict[str, Any]]:
        """Memory-mapped loading for large files."""
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                # Read in chunks for progress reporting
                chunk_size = 1024 * 1024  # 1MB chunks
                chunks = []
                bytes_read = 0
                total_size = len(mmapped_file)
                
                while bytes_read < total_size:
                    chunk = mmapped_file.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    bytes_read += len(chunk)
                    
                    if self.progress_callback:
                        progress = (bytes_read / total_size) * 100
                        self.progress_callback(database_name, progress)
                
                # Decode and parse JSON
                json_str = b''.join(chunks).decode('utf-8')
                data = json.loads(json_str)
                
                if self.progress_callback:
                    self.progress_callback(database_name, 100.0)
                
                # Validate data structure
                if isinstance(data, dict) and "items" in data:
                    return data["items"]
                elif isinstance(data, list):
                    return data
                else:
                    raise QueryError(f"Invalid JSON structure in {database_name}")
    
    def get_database_stats(self, database_name: str) -> Dict[str, Any]:
        """Get statistics about a database file.
        
        Returns:
            Dict with path, size, modified time, record count
        """
        if database_name not in self._file_stats:
            file_path = self._find_database_file(database_name)
            if not file_path:
                raise QueryError(f"Database not found: {database_name}")
            
            self._file_stats[database_name] = {
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            }
        
        stats = self._file_stats[database_name].copy()
        
        # Add record count if data is cached
        if database_name in self._cache:
            stats["record_count"] = len(self._cache[database_name])
        
        return stats
    
    def preload_databases(self, database_names: Optional[List[str]] = None) -> None:
        """Preload databases into cache for better performance.
        
        Args:
            database_names: Specific databases to preload, or None for all
        """
        if database_names is None:
            database_names = self.get_available_databases()
        
        logger.info(f"Preloading {len(database_names)} databases...")
        self.load_multiple_databases(database_names)
        logger.info("Preloading complete")
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get estimated memory usage of cached data.
        
        Returns:
            Dict mapping database name to approximate memory usage in bytes
        """
        import sys
        
        memory_usage = {}
        for db_name, data in self._cache.items():
            # Rough estimation of memory usage
            memory_usage[db_name] = sys.getsizeof(data) + sum(
                sys.getsizeof(record) for record in data[:100]
            ) * (len(data) / 100)
        
        return memory_usage