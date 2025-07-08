"""Notion synchronization service."""

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from ..repositories import PageRepository, DatabaseRepository, SearchRepository
from ..models.responses import NotionPage, NotionDatabase
from ..errors.handlers import SyncError, ErrorContext
from .base import BaseService, ServiceError


class SyncMode(str, Enum):
    """Synchronization modes."""
    FULL = "full"  # Full sync, all data
    INCREMENTAL = "incremental"  # Only changes since last sync
    SELECTIVE = "selective"  # Specific items only


@dataclass
class SyncResult:
    """Result of a sync operation."""
    mode: SyncMode
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_items: int = 0
    synced_items: int = 0
    failed_items: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_items == 0:
            return 0.0
        return (self.synced_items / self.total_items) * 100
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mode": self.mode.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items": self.total_items,
            "synced_items": self.synced_items,
            "failed_items": self.failed_items,
            "success_rate": self.success_rate,
            "duration": self.duration,
            "errors": self.errors,
            "summary": self.summary,
        }


class NotionSyncService(BaseService):
    """Service for synchronizing Notion data."""
    
    def __init__(self, *args, sync_state_file: Optional[Path] = None, **kwargs):
        """Initialize sync service.
        
        Args:
            sync_state_file: Optional file to store sync state
        """
        super().__init__(*args, **kwargs)
        self.sync_state_file = sync_state_file or Path("sync_state.json")
        self._sync_state = self._load_sync_state()
    
    def _init_repositories(self) -> None:
        """Initialize required repositories."""
        self.page_repo = self._create_repository(PageRepository)
        self.database_repo = self._create_repository(DatabaseRepository)
        self.search_repo = self._create_repository(SearchRepository)
    
    def sync_database(
        self,
        database_id: str,
        mode: SyncMode = SyncMode.FULL,
        output_file: Optional[Path] = None,
    ) -> SyncResult:
        """Sync a database and its pages.
        
        Args:
            database_id: Database ID to sync
            mode: Sync mode
            output_file: Optional file to save data
            
        Returns:
            Sync result
        """
        result = SyncResult(
            mode=mode,
            started_at=datetime.utcnow(),
        )
        
        with self.error_handler.error_context(
            operation="sync_database",
            resource_id=database_id,
        ):
            try:
                # Get database metadata
                database = self.database_repo.get_by_id(database_id)
                result.summary["database"] = {
                    "id": database.id,
                    "title": "".join(t.plain_text for t in database.title),
                    "properties": list(database.properties.keys()),
                }
                
                # Determine pages to sync
                if mode == SyncMode.FULL:
                    pages = self.database_repo.get_all_pages(database_id)
                elif mode == SyncMode.INCREMENTAL:
                    pages = self._get_incremental_pages(database_id)
                else:
                    # Selective mode would need specific page IDs
                    pages = []
                
                result.total_items = len(pages)
                
                # Sync each page
                synced_data = {
                    "database": database.dict(),
                    "pages": [],
                }
                
                for page in pages:
                    try:
                        page_data = self._sync_page(page)
                        synced_data["pages"].append(page_data)
                        result.synced_items += 1
                    except Exception as e:
                        result.failed_items += 1
                        result.errors.append({
                            "page_id": page.id,
                            "error": str(e),
                        })
                        self.logger.error(f"Failed to sync page {page.id}: {e}")
                
                # Save to file if specified
                if output_file:
                    self._save_sync_data(synced_data, output_file)
                
                # Update sync state
                self._update_sync_state(database_id, datetime.utcnow())
                
                result.completed_at = datetime.utcnow()
                result.summary["synced_pages"] = result.synced_items
                
                self.log_operation(
                    "sync_database",
                    database_id=database_id,
                    mode=mode.value,
                    result=result.to_dict(),
                )
                
                return result
                
            except Exception as e:
                raise SyncError(
                    f"Database sync failed: {str(e)}",
                    phase="sync",
                    context=ErrorContext(
                        operation="sync_database",
                        resource_id=database_id,
                        metadata={"mode": mode.value},
                    ),
                )
    
    def sync_from_json(
        self,
        json_file: Path,
        database_id: str,
        update_existing: bool = True,
        create_missing: bool = True,
    ) -> SyncResult:
        """Sync data from JSON file to Notion.
        
        Args:
            json_file: JSON file with data
            database_id: Target database ID
            update_existing: Whether to update existing pages
            create_missing: Whether to create missing pages
            
        Returns:
            Sync result
        """
        result = SyncResult(
            mode=SyncMode.FULL,
            started_at=datetime.utcnow(),
        )
        
        with self.error_handler.error_context(
            operation="sync_from_json",
            resource_id=database_id,
        ):
            try:
                # Load JSON data
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                if "pages" not in data:
                    raise ServiceError("JSON file must contain 'pages' array")
                
                pages_data = data["pages"]
                result.total_items = len(pages_data)
                
                # Get existing pages for comparison
                existing_pages = {
                    self._get_page_key(page): page
                    for page in self.database_repo.get_all_pages(database_id)
                }
                
                # Sync each page
                for page_data in pages_data:
                    try:
                        # Determine if page exists
                        page_key = self._get_page_key_from_data(page_data)
                        exists = page_key in existing_pages
                        
                        if exists and update_existing:
                            # Update existing page
                            page = existing_pages[page_key]
                            self.page_repo.update(page.id, page_data)
                            result.synced_items += 1
                        elif not exists and create_missing:
                            # Create new page
                            page_data["parent"] = {
                                "type": "database_id",
                                "database_id": database_id
                            }
                            self.page_repo.create(page_data)
                            result.synced_items += 1
                        else:
                            # Skip
                            pass
                            
                    except Exception as e:
                        result.failed_items += 1
                        result.errors.append({
                            "page_data": page_data,
                            "error": str(e),
                        })
                        self.logger.error(f"Failed to sync page: {e}")
                
                result.completed_at = datetime.utcnow()
                result.summary["updated"] = sum(
                    1 for e in result.errors if "update" in str(e)
                )
                result.summary["created"] = result.synced_items - result.summary["updated"]
                
                self.log_operation(
                    "sync_from_json",
                    database_id=database_id,
                    json_file=str(json_file),
                    result=result.to_dict(),
                )
                
                return result
                
            except Exception as e:
                raise SyncError(
                    f"JSON sync failed: {str(e)}",
                    phase="sync",
                    context=ErrorContext(
                        operation="sync_from_json",
                        resource_id=database_id,
                        metadata={"json_file": str(json_file)},
                    ),
                )
    
    def sync_workspace(
        self,
        include_databases: bool = True,
        include_pages: bool = True,
        output_dir: Optional[Path] = None,
    ) -> SyncResult:
        """Sync entire workspace.
        
        Args:
            include_databases: Whether to sync databases
            include_pages: Whether to sync standalone pages
            output_dir: Optional directory to save data
            
        Returns:
            Sync result
        """
        result = SyncResult(
            mode=SyncMode.FULL,
            started_at=datetime.utcnow(),
        )
        
        try:
            synced_data = {
                "databases": [],
                "pages": [],
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Sync databases
            if include_databases:
                databases = self.search_repo.search_databases("")
                result.total_items += len(databases)
                
                for database in databases:
                    try:
                        # Sync database and its pages
                        db_result = self.sync_database(
                            database.id,
                            mode=SyncMode.FULL,
                        )
                        
                        synced_data["databases"].append({
                            "database": database.dict(),
                            "sync_result": db_result.to_dict(),
                        })
                        
                        result.synced_items += 1
                        result.summary[f"database_{database.id}"] = db_result.to_dict()
                        
                    except Exception as e:
                        result.failed_items += 1
                        result.errors.append({
                            "database_id": database.id,
                            "error": str(e),
                        })
            
            # Sync standalone pages
            if include_pages:
                pages = self.search_repo.search_pages("")
                # Filter out pages that belong to databases
                standalone_pages = [
                    p for p in pages
                    if p.parent.get("type") != "database_id"
                ]
                result.total_items += len(standalone_pages)
                
                for page in standalone_pages:
                    try:
                        page_data = self._sync_page(page)
                        synced_data["pages"].append(page_data)
                        result.synced_items += 1
                    except Exception as e:
                        result.failed_items += 1
                        result.errors.append({
                            "page_id": page.id,
                            "error": str(e),
                        })
            
            # Save to directory if specified
            if output_dir:
                output_dir.mkdir(exist_ok=True)
                
                # Save main data
                with open(output_dir / "workspace_sync.json", 'w') as f:
                    json.dump(synced_data, f, indent=2)
                
                # Save individual database files
                for db_data in synced_data["databases"]:
                    db_id = db_data["database"]["id"]
                    with open(output_dir / f"database_{db_id}.json", 'w') as f:
                        json.dump(db_data, f, indent=2)
            
            result.completed_at = datetime.utcnow()
            
            self.log_operation(
                "sync_workspace",
                result=result.to_dict(),
            )
            
            return result
            
        except Exception as e:
            raise SyncError(
                f"Workspace sync failed: {str(e)}",
                phase="sync",
                context=ErrorContext(operation="sync_workspace"),
            )
    
    def _sync_page(self, page: NotionPage) -> Dict[str, Any]:
        """Sync a single page.
        
        Args:
            page: Page to sync
            
        Returns:
            Page data
        """
        # Get full page data
        full_page = self.page_repo.get_by_id(page.id)
        
        # Convert to dict and process
        page_data = full_page.dict()
        
        # Extract plain values for properties
        plain_properties = {}
        for name, prop_data in full_page.properties.items():
            # This is simplified - would need property type info
            plain_properties[name] = prop_data
        
        page_data["properties_plain"] = plain_properties
        
        return page_data
    
    def _get_incremental_pages(self, database_id: str) -> List[NotionPage]:
        """Get pages changed since last sync.
        
        Args:
            database_id: Database ID
            
        Returns:
            List of changed pages
        """
        last_sync = self._sync_state.get(database_id, {}).get("last_sync")
        
        if not last_sync:
            # No previous sync, do full sync
            return self.database_repo.get_all_pages(database_id)
        
        # Query for pages modified after last sync
        # This is simplified - would need proper date filtering
        all_pages = self.database_repo.get_all_pages(database_id)
        
        changed_pages = []
        for page in all_pages:
            if page.last_edited_time > datetime.fromisoformat(last_sync):
                changed_pages.append(page)
        
        return changed_pages
    
    def _get_page_key(self, page: NotionPage) -> str:
        """Get unique key for page (for matching)."""
        # Use title if available, otherwise ID
        if "title" in page.properties:
            # This is simplified - would need to extract actual title
            return f"title:{page.id[:8]}"
        return f"id:{page.id}"
    
    def _get_page_key_from_data(self, page_data: Dict[str, Any]) -> str:
        """Get unique key from page data."""
        # This is simplified - would need to match the above logic
        if "id" in page_data:
            return f"id:{page_data['id']}"
        return f"title:unknown"
    
    def _save_sync_data(self, data: Dict[str, Any], file: Path) -> None:
        """Save sync data to file."""
        with open(file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_sync_state(self) -> Dict[str, Any]:
        """Load sync state from file."""
        if self.sync_state_file.exists():
            with open(self.sync_state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _update_sync_state(self, database_id: str, timestamp: datetime) -> None:
        """Update sync state."""
        self._sync_state[database_id] = {
            "last_sync": timestamp.isoformat(),
        }
        
        with open(self.sync_state_file, 'w') as f:
            json.dump(self._sync_state, f, indent=2)
    
    def _save_sync_state(self) -> None:
        """Save sync state to file."""
        with open(self.sync_state_file, 'w') as f:
            json.dump(self._sync_state, f, indent=2)