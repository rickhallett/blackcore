"""Protocol adapters for Agent A (Data Foundation) integration.

This module provides adapters that bridge between the orchestrator's
expected interfaces and Agent A's data loading and filtering implementations.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Protocol
from pathlib import Path
import logging

from ..core.orchestrator import DataLoader, FilterEngine
from ..models import QueryFilter, QueryOperator

logger = logging.getLogger(__name__)


class BlackcoreDataLoader:
    """Adapter for Blackcore's JSON data loading functionality."""
    
    def __init__(self, json_data_path: Optional[str] = None):
        """Initialize with path to JSON data files."""
        if json_data_path is None:
            # Default to Blackcore's standard JSON data path
            json_data_path = os.path.join(
                os.path.dirname(__file__), 
                '..', '..', '..', 'models', 'json'
            )
        
        self.json_data_path = Path(json_data_path).resolve()
        self._cache = {}
        self._cache_timestamps = {}
        
        logger.info(f"Initialized DataLoader with path: {self.json_data_path}")
    
    def load_database(self, database_name: str) -> List[Dict[str, Any]]:
        """Load database from JSON file."""
        # Map database names to JSON files
        filename_map = {
            'People & Contacts': 'people_contacts.json',
            'Organizations & Bodies': 'organizations_bodies.json',
            'Actionable Tasks': 'actionable_tasks.json',
            'Key Places & Events': 'key_places_events.json',
            'Intelligence & Transcripts': 'intelligence_transcripts.json',
            'Documents & Evidence': 'documents_evidence.json',
            'Agendas & Epics': 'agendas_epics.json',
            'Identified Transgressions': 'identified_transgressions.json'
        }
        
        # Use exact name if not in map
        filename = filename_map.get(database_name, f"{database_name.lower().replace(' & ', '_').replace(' ', '_')}.json")
        file_path = self.json_data_path / filename
        
        # Check cache first
        if self._is_cache_valid(database_name, file_path):
            logger.debug(f"Loading {database_name} from cache")
            return self._cache[database_name]
        
        # Load from file
        try:
            if not file_path.exists():
                logger.warning(f"Database file not found: {file_path}")
                return []
            
            logger.info(f"Loading {database_name} from {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, dict):
                if 'results' in data:
                    data = data['results']
                elif 'data' in data:
                    data = data['data']
                else:
                    # Convert dict to list of records
                    data = [data]
            
            # Ensure all records have an ID
            for i, record in enumerate(data):
                if 'id' not in record:
                    record['id'] = f"{database_name}_{i}"
            
            # Cache the result
            self._cache[database_name] = data
            self._cache_timestamps[database_name] = file_path.stat().st_mtime
            
            logger.info(f"Loaded {len(data)} records from {database_name}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading {database_name}: {e}")
            return []
    
    def get_available_databases(self) -> List[str]:
        """Get list of available databases."""
        if not self.json_data_path.exists():
            logger.warning(f"JSON data path does not exist: {self.json_data_path}")
            return []
        
        databases = []
        
        # Standard Blackcore databases
        standard_databases = [
            'People & Contacts',
            'Organizations & Bodies',
            'Actionable Tasks',
            'Key Places & Events',
            'Intelligence & Transcripts',
            'Documents & Evidence',
            'Agendas & Epics',
            'Identified Transgressions'
        ]
        
        for db in standard_databases:
            filename_map = {
                'People & Contacts': 'people_contacts.json',
                'Organizations & Bodies': 'organizations_bodies.json',
                'Actionable Tasks': 'actionable_tasks.json',
                'Key Places & Events': 'key_places_events.json',
                'Intelligence & Transcripts': 'intelligence_transcripts.json',
                'Documents & Evidence': 'documents_evidence.json',
                'Agendas & Epics': 'agendas_epics.json',
                'Identified Transgressions': 'identified_transgressions.json'
            }
            
            filename = filename_map.get(db, f"{db.lower().replace(' & ', '_').replace(' ', '_')}.json")
            if (self.json_data_path / filename).exists():
                databases.append(db)
        
        # Also scan for any other JSON files
        for json_file in self.json_data_path.glob('*.json'):
            db_name = json_file.stem.replace('_', ' ').title()
            if db_name not in databases:
                databases.append(db_name)
        
        logger.debug(f"Available databases: {databases}")
        return databases
    
    def refresh_cache(self, database_name: Optional[str] = None) -> None:
        """Refresh cache for specific database or all databases."""
        if database_name:
            if database_name in self._cache:
                del self._cache[database_name]
                del self._cache_timestamps[database_name]
                logger.info(f"Refreshed cache for {database_name}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Refreshed all caches")
    
    def _is_cache_valid(self, database_name: str, file_path: Path) -> bool:
        """Check if cached data is still valid."""
        if database_name not in self._cache:
            return False
        
        if not file_path.exists():
            return False
        
        # Check if file has been modified since cache
        cached_timestamp = self._cache_timestamps.get(database_name, 0)
        file_timestamp = file_path.stat().st_mtime
        
        return file_timestamp <= cached_timestamp


class BlackcoreFilterEngine:
    """Adapter for Blackcore's filtering functionality."""
    
    def __init__(self):
        """Initialize filter engine."""
        self._operator_map = {
            QueryOperator.EQUALS: self._equals,
            QueryOperator.NOT_EQUALS: self._not_equals,
            QueryOperator.CONTAINS: self._contains,
            QueryOperator.NOT_CONTAINS: self._not_contains,
            QueryOperator.STARTS_WITH: self._starts_with,
            QueryOperator.ENDS_WITH: self._ends_with,
            QueryOperator.GT: self._greater_than,
            QueryOperator.GTE: self._greater_than_equal,
            QueryOperator.LT: self._less_than,
            QueryOperator.LTE: self._less_than_equal,
            QueryOperator.BETWEEN: self._between,
            QueryOperator.IN: self._in,
            QueryOperator.NOT_IN: self._not_in,
            QueryOperator.IS_NULL: self._is_null,
            QueryOperator.IS_NOT_NULL: self._is_not_null,
        }
    
    def apply_filters(self, data: List[Dict[str, Any]], filters: List[QueryFilter]) -> List[Dict[str, Any]]:
        """Apply all filters to the data."""
        if not filters:
            return data
        
        result = data
        for filter_obj in filters:
            result = self._apply_single_filter(result, filter_obj)
            logger.debug(f"After filter {filter_obj.field} {filter_obj.operator.value}: {len(result)} records")
        
        return result
    
    def _apply_single_filter(self, data: List[Dict[str, Any]], filter_obj: QueryFilter) -> List[Dict[str, Any]]:
        """Apply a single filter to the data."""
        if filter_obj.operator not in self._operator_map:
            logger.warning(f"Unsupported operator: {filter_obj.operator}")
            return data
        
        filter_func = self._operator_map[filter_obj.operator]
        
        result = []
        for item in data:
            try:
                field_value = self._get_nested_field(item, filter_obj.field)
                if filter_func(field_value, filter_obj.value):
                    result.append(item)
            except Exception as e:
                logger.debug(f"Filter error for item {item.get('id', 'unknown')}: {e}")
                continue
        
        return result
    
    def _get_nested_field(self, item: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation."""
        parts = field_path.split('.')
        value = item
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                index = int(part)
                value = value[index] if 0 <= index < len(value) else None
            else:
                return None
        
        return value
    
    # Filter implementation methods
    def _equals(self, field_value: Any, filter_value: Any) -> bool:
        """Equals filter."""
        if field_value is None:
            return filter_value is None
        
        # Handle case-insensitive string comparison
        if isinstance(field_value, str) and isinstance(filter_value, str):
            return field_value.lower() == filter_value.lower()
        
        return field_value == filter_value
    
    def _not_equals(self, field_value: Any, filter_value: Any) -> bool:
        """Not equals filter."""
        return not self._equals(field_value, filter_value)
    
    def _contains(self, field_value: Any, filter_value: Any) -> bool:
        """Contains filter."""
        if field_value is None:
            return False
        
        field_str = str(field_value).lower()
        filter_str = str(filter_value).lower()
        return filter_str in field_str
    
    def _not_contains(self, field_value: Any, filter_value: Any) -> bool:
        """Not contains filter."""
        return not self._contains(field_value, filter_value)
    
    def _starts_with(self, field_value: Any, filter_value: Any) -> bool:
        """Starts with filter."""
        if field_value is None:
            return False
        
        field_str = str(field_value).lower()
        filter_str = str(filter_value).lower()
        return field_str.startswith(filter_str)
    
    def _ends_with(self, field_value: Any, filter_value: Any) -> bool:
        """Ends with filter."""
        if field_value is None:
            return False
        
        field_str = str(field_value).lower()
        filter_str = str(filter_value).lower()
        return field_str.endswith(filter_str)
    
    def _greater_than(self, field_value: Any, filter_value: Any) -> bool:
        """Greater than filter."""
        try:
            return float(field_value) > float(filter_value)
        except (ValueError, TypeError):
            return str(field_value) > str(filter_value)
    
    def _greater_than_equal(self, field_value: Any, filter_value: Any) -> bool:
        """Greater than or equal filter."""
        try:
            return float(field_value) >= float(filter_value)
        except (ValueError, TypeError):
            return str(field_value) >= str(filter_value)
    
    def _less_than(self, field_value: Any, filter_value: Any) -> bool:
        """Less than filter."""
        try:
            return float(field_value) < float(filter_value)
        except (ValueError, TypeError):
            return str(field_value) < str(filter_value)
    
    def _less_than_equal(self, field_value: Any, filter_value: Any) -> bool:
        """Less than or equal filter."""
        try:
            return float(field_value) <= float(filter_value)
        except (ValueError, TypeError):
            return str(field_value) <= str(filter_value)
    
    def _between(self, field_value: Any, filter_value: Any) -> bool:
        """Between filter - expects filter_value to be [min, max]."""
        if not isinstance(filter_value, (list, tuple)) or len(filter_value) != 2:
            return False
        
        min_val, max_val = filter_value
        try:
            field_num = float(field_value)
            return float(min_val) <= field_num <= float(max_val)
        except (ValueError, TypeError):
            field_str = str(field_value)
            return str(min_val) <= field_str <= str(max_val)
    
    def _in(self, field_value: Any, filter_value: Any) -> bool:
        """In filter - expects filter_value to be a list."""
        if not isinstance(filter_value, (list, tuple)):
            return self._equals(field_value, filter_value)
        
        for value in filter_value:
            if self._equals(field_value, value):
                return True
        return False
    
    def _not_in(self, field_value: Any, filter_value: Any) -> bool:
        """Not in filter."""
        return not self._in(field_value, filter_value)
    
    def _is_null(self, field_value: Any, filter_value: Any) -> bool:
        """Is null filter."""
        return field_value is None or field_value == '' or field_value == []
    
    def _is_not_null(self, field_value: Any, filter_value: Any) -> bool:
        """Is not null filter."""
        return not self._is_null(field_value, filter_value)


# Factory functions for easy instantiation
def create_blackcore_data_loader(json_data_path: Optional[str] = None) -> BlackcoreDataLoader:
    """Create a Blackcore data loader adapter."""
    return BlackcoreDataLoader(json_data_path)


def create_blackcore_filter_engine() -> BlackcoreFilterEngine:
    """Create a Blackcore filter engine adapter."""
    return BlackcoreFilterEngine()


# Integration helper
def integrate_agent_a(json_data_path: Optional[str] = None) -> Dict[str, Any]:
    """Create all Agent A components for integration."""
    return {
        'data_loader': create_blackcore_data_loader(json_data_path),
        'filter_engine': create_blackcore_filter_engine()
    }