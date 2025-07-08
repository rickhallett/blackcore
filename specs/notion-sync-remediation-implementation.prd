# Notion Sync Engine Remediation Implementation PRD

**Product**: Blackcore Notion Sync Engine  
**Document Type**: Implementation PRD  
**Date**: 2025-07-08  
**Version**: 1.0  
**Status**: APPROVED FOR IMPLEMENTATION  
**Implementation Timeline**: 4 weeks  
**Risk Level**: HIGH - Production deployment blocked until completion

## Executive Summary

Following the comprehensive peer review, this PRD outlines the implementation plan to address 15 blockers and 23 major issues identified in the Notion sync engine. The implementation follows a phased approach prioritizing security, stability, and scalability.

**Key Objectives**:
1. Eliminate all security vulnerabilities (4 critical, 3 high severity)
2. Achieve 85%+ test coverage with comprehensive edge case handling
3. Implement production-grade architecture with proper abstractions
4. Enable full observability and monitoring
5. Ensure thread-safety and horizontal scalability

## Current State vs Target State

### Current State (High Risk)
```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  NotionClient   │────▶│ notion-client│────▶│  Notion API  │
│  (monolithic)   │     │     SDK      │     │              │
└─────────────────┘     └──────────────┘     └──────────────┘
        │
        ├─ No abstraction layer
        ├─ Thread-unsafe
        ├─ No monitoring
        └─ Security vulnerabilities
```

### Target State (Production Ready)
```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│ Service Layer   │────▶│  Repository  │────▶│   Adapters   │
│  (business)     │     │  Interface   │     │  (Notion)    │
└─────────────────┘     └──────────────┘     └──────────────┘
        │                      │                      │
        │                      │                      ├─ Rate Limiter
        │                      │                      ├─ Retry Logic
        │                      │                      └─ Monitoring
        │                      │
        │                      ├─ NotionRepository
        │                      ├─ CachedRepository
        │                      └─ MockRepository
        │
        ├─ Thread-safe
        ├─ Fully monitored
        └─ Secure
```

## Implementation Phases

### Phase 1: Critical Security & Stability (Week 1)

#### 1.1 Security Hardening (Days 1-2)

**Objective**: Eliminate all security vulnerabilities

**Implementation Tasks**:

1. **Secure API Key Management**
```python
# Current (vulnerable)
api_key = os.getenv("NOTION_API_KEY")

# Target implementation
from blackcore.security import SecretsManager

class NotionClient:
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets_manager = secrets_manager
        self._api_key_cache = None
        self._key_rotation_interval = timedelta(days=30)
    
    @property
    def api_key(self) -> str:
        if self._should_rotate_key():
            self._api_key_cache = self.secrets_manager.get_secret(
                "notion/api_key",
                version="latest"
            )
        return self._api_key_cache
```

2. **SSRF Prevention**
```python
# security/validators.py
from urllib.parse import urlparse
import ipaddress

class URLValidator:
    ALLOWED_SCHEMES = ['https']
    BLOCKED_NETWORKS = [
        ipaddress.ip_network('10.0.0.0/8'),      # Private
        ipaddress.ip_network('172.16.0.0/12'),   # Private
        ipaddress.ip_network('192.168.0.0/16'),  # Private
        ipaddress.ip_network('169.254.0.0/16'),  # Link-local
        ipaddress.ip_network('127.0.0.0/8'),     # Loopback
    ]
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in cls.ALLOWED_SCHEMES:
            raise ValueError(f"Only HTTPS URLs allowed, got: {parsed.scheme}")
        
        # Resolve hostname and check IP
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
            for network in cls.BLOCKED_NETWORKS:
                if ip in network:
                    raise ValueError(f"URL points to blocked network: {network}")
        except socket.gaierror:
            raise ValueError(f"Cannot resolve hostname: {parsed.hostname}")
        
        return True
```

3. **Audit Logging**
```python
# security/audit.py
import structlog
from datetime import datetime
from typing import Any, Dict

class AuditLogger:
    def __init__(self):
        self.logger = structlog.get_logger("audit")
    
    def log_api_call(self, method: str, **kwargs):
        self.logger.info(
            "api_call",
            method=method,
            timestamp=datetime.utcnow().isoformat(),
            user_id=self._get_current_user(),
            **self._sanitize_params(kwargs)
        )
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from logs"""
        sanitized = params.copy()
        for key in ['api_key', 'password', 'token']:
            if key in sanitized:
                sanitized[key] = "***REDACTED***"
        return sanitized
```

#### 1.2 Thread Safety Implementation (Day 3)

**Objective**: Make rate limiter thread-safe for production deployments

```python
# rate_limiting/thread_safe.py
import threading
import time
from typing import Optional
import redis

class ThreadSafeRateLimiter:
    """Thread-safe rate limiter with distributed support"""
    
    def __init__(self, 
                 requests_per_second: float = 3,
                 redis_client: Optional[redis.Redis] = None):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self._local_lock = threading.Lock()
        self._last_request_time = 0.0
        self.redis_client = redis_client
        self.instance_id = f"limiter:{os.getpid()}"
    
    def wait_if_needed(self) -> None:
        if self.redis_client:
            self._distributed_wait()
        else:
            self._local_wait()
    
    def _local_wait(self) -> None:
        """Thread-safe local rate limiting"""
        with self._local_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    def _distributed_wait(self) -> None:
        """Distributed rate limiting using Redis"""
        key = "notion:rate_limit"
        current_time = time.time()
        
        # Sliding window rate limiting
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, current_time - 1)  # Remove old entries
        pipe.zadd(key, {self.instance_id: current_time})
        pipe.zcount(key, current_time - 1, current_time)
        pipe.expire(key, 2)
        
        _, _, request_count, _ = pipe.execute()
        
        if request_count > self.requests_per_second:
            sleep_time = self.min_interval
            time.sleep(sleep_time)
```

#### 1.3 Error Context Preservation (Day 4)

```python
# errors/handlers.py
import traceback
from typing import Optional, Type
from dataclasses import dataclass

@dataclass
class APIError:
    """Structured error information"""
    error_type: str
    message: str
    context: dict
    stack_trace: str
    retry_able: bool
    user_message: str

class ErrorHandler:
    """Centralized error handling with context preservation"""
    
    USER_MESSAGES = {
        "rate_limited": "The system is busy. Please try again in a moment.",
        "invalid_request": "Invalid request. Please check your input.",
        "unauthorized": "Authentication failed. Please check your credentials.",
        "network_error": "Network error. Please check your connection.",
        "unknown": "An unexpected error occurred. Please try again."
    }
    
    @classmethod
    def handle_api_error(cls, e: Exception, context: dict) -> APIError:
        error_type = cls._classify_error(e)
        
        return APIError(
            error_type=error_type,
            message=str(e),
            context=context,
            stack_trace=traceback.format_exc(),
            retry_able=cls._is_retryable(error_type),
            user_message=cls.USER_MESSAGES.get(error_type, cls.USER_MESSAGES["unknown"])
        )
    
    @staticmethod
    def _classify_error(e: Exception) -> str:
        if hasattr(e, 'code'):
            return e.code
        elif isinstance(e, ConnectionError):
            return "network_error"
        else:
            return "unknown"
```

#### 1.4 Response Validation (Day 5)

```python
# validation/schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class NotionResponse(BaseModel):
    """Base response model for Notion API"""
    object: str
    
    @validator('object')
    def validate_object_type(cls, v):
        valid_types = ['database', 'page', 'list', 'error']
        if v not in valid_types:
            raise ValueError(f"Invalid object type: {v}")
        return v

class PageResponse(NotionResponse):
    """Validated page response"""
    id: str = Field(..., regex=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
    created_time: datetime
    last_edited_time: datetime
    created_by: Dict[str, Any]
    last_edited_by: Dict[str, Any]
    parent: Dict[str, Any]
    archived: bool
    properties: Dict[str, Any]
    
class DatabaseQueryResponse(NotionResponse):
    """Validated database query response"""
    results: List[PageResponse]
    has_more: bool
    next_cursor: Optional[str]
    
    @validator('results')
    def validate_results(cls, v):
        if not isinstance(v, list):
            raise ValueError("Results must be a list")
        return v

# validation/validator.py
class ResponseValidator:
    """Validates API responses against schemas"""
    
    @staticmethod
    def validate_page(response: dict) -> PageResponse:
        try:
            return PageResponse(**response)
        except Exception as e:
            raise ValueError(f"Invalid page response: {e}")
    
    @staticmethod
    def validate_query_response(response: dict) -> DatabaseQueryResponse:
        try:
            return DatabaseQueryResponse(**response)
        except Exception as e:
            raise ValueError(f"Invalid query response: {e}")
```

### Phase 2: Architecture Refactoring (Week 2)

#### 2.1 Property Handler Strategy Pattern (Days 1-2)

```python
# properties/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class PropertyHandler(ABC):
    """Base class for property handlers"""
    
    @abstractmethod
    def can_handle(self, property_type: str) -> bool:
        """Check if this handler can process the property type"""
        pass
    
    @abstractmethod
    def simplify(self, property_data: Dict[str, Any]) -> Any:
        """Convert Notion property to simple Python value"""
        pass
    
    @abstractmethod
    def build_payload(self, value: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python value to Notion API payload"""
        pass
    
    @abstractmethod
    def validate(self, value: Any) -> bool:
        """Validate the property value"""
        pass

# properties/text.py
class TextPropertyHandler(PropertyHandler):
    """Handles title and rich_text properties"""
    
    SUPPORTED_TYPES = ['title', 'rich_text']
    MAX_LENGTH = 2000
    
    def can_handle(self, property_type: str) -> bool:
        return property_type in self.SUPPORTED_TYPES
    
    def simplify(self, property_data: Dict[str, Any]) -> Optional[str]:
        prop_type = property_data.get('type')
        if not prop_type or not property_data.get(prop_type):
            return None
        
        text_array = property_data[prop_type]
        if text_array and len(text_array) > 0:
            return text_array[0].get('plain_text')
        return None
    
    def build_payload(self, value: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        if not self.validate(value):
            raise ValueError(f"Invalid text value: {value}")
        
        prop_type = schema['type']
        text = str(value)[:self.MAX_LENGTH]
        
        return {
            prop_type: [{
                "text": {"content": text}
            }]
        }
    
    def validate(self, value: Any) -> bool:
        return value is not None and len(str(value)) <= self.MAX_LENGTH

# properties/registry.py
class PropertyHandlerRegistry:
    """Registry for property handlers"""
    
    def __init__(self):
        self._handlers: List[PropertyHandler] = []
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register all default property handlers"""
        from .text import TextPropertyHandler
        from .date import DatePropertyHandler
        from .select import SelectPropertyHandler
        from .number import NumberPropertyHandler
        from .checkbox import CheckboxPropertyHandler
        from .url import URLPropertyHandler
        from .email import EmailPropertyHandler
        from .relation import RelationPropertyHandler
        from .people import PeoplePropertyHandler
        from .files import FilesPropertyHandler
        
        self.register(TextPropertyHandler())
        self.register(DatePropertyHandler())
        self.register(SelectPropertyHandler())
        self.register(NumberPropertyHandler())
        self.register(CheckboxPropertyHandler())
        self.register(URLPropertyHandler())
        self.register(EmailPropertyHandler())
        self.register(RelationPropertyHandler())
        self.register(PeoplePropertyHandler())
        self.register(FilesPropertyHandler())
    
    def register(self, handler: PropertyHandler):
        """Register a new property handler"""
        self._handlers.append(handler)
    
    def get_handler(self, property_type: str) -> PropertyHandler:
        """Get handler for property type"""
        for handler in self._handlers:
            if handler.can_handle(property_type):
                return handler
        raise ValueError(f"No handler found for property type: {property_type}")
```

#### 2.2 Repository Pattern Implementation (Days 3-4)

```python
# repositories/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Page:
    """Domain model for Notion page"""
    id: str
    database_id: str
    properties: Dict[str, Any]
    created_time: datetime
    last_edited_time: datetime

class NotionRepository(ABC):
    """Abstract repository for Notion operations"""
    
    @abstractmethod
    async def get_page(self, page_id: str) -> Optional[Page]:
        """Get a single page by ID"""
        pass
    
    @abstractmethod
    async def get_all_pages(self, database_id: str) -> List[Page]:
        """Get all pages from a database"""
        pass
    
    @abstractmethod
    async def create_page(self, database_id: str, properties: Dict[str, Any]) -> Page:
        """Create a new page"""
        pass
    
    @abstractmethod
    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Page:
        """Update an existing page"""
        pass
    
    @abstractmethod
    async def delete_page(self, page_id: str) -> bool:
        """Delete a page"""
        pass

# repositories/notion.py
class NotionAPIRepository(NotionRepository):
    """Concrete repository using Notion API"""
    
    def __init__(self, 
                 client: NotionClient,
                 property_registry: PropertyHandlerRegistry,
                 validator: ResponseValidator):
        self.client = client
        self.property_registry = property_registry
        self.validator = validator
    
    async def get_all_pages(self, database_id: str) -> List[Page]:
        """Get all pages with proper pagination"""
        pages = []
        has_more = True
        start_cursor = None
        
        while has_more:
            response = await self.client.query_database(
                database_id=database_id,
                start_cursor=start_cursor
            )
            
            # Validate response
            validated = self.validator.validate_query_response(response)
            
            # Convert to domain models
            for page_data in validated.results:
                page = self._to_domain_model(page_data)
                pages.append(page)
            
            has_more = validated.has_more
            start_cursor = validated.next_cursor
        
        return pages
    
    def _to_domain_model(self, page_response: PageResponse) -> Page:
        """Convert API response to domain model"""
        simplified_props = {}
        
        for prop_name, prop_data in page_response.properties.items():
            prop_type = prop_data.get('type')
            handler = self.property_registry.get_handler(prop_type)
            simplified_props[prop_name] = handler.simplify(prop_data)
        
        return Page(
            id=page_response.id,
            database_id=page_response.parent['database_id'],
            properties=simplified_props,
            created_time=page_response.created_time,
            last_edited_time=page_response.last_edited_time
        )

# repositories/cached.py
class CachedNotionRepository(NotionRepository):
    """Repository with caching layer"""
    
    def __init__(self, 
                 base_repository: NotionRepository,
                 cache: Cache,
                 ttl: int = 300):
        self.base = base_repository
        self.cache = cache
        self.ttl = ttl
    
    async def get_page(self, page_id: str) -> Optional[Page]:
        cache_key = f"page:{page_id}"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return Page(**cached)
        
        # Fall back to base repository
        page = await self.base.get_page(page_id)
        if page:
            await self.cache.set(cache_key, page.__dict__, ttl=self.ttl)
        
        return page
```

#### 2.3 Service Layer (Day 5)

```python
# services/sync.py
from typing import List, Dict, Any
import asyncio

class NotionSyncService:
    """High-level sync orchestration service"""
    
    def __init__(self,
                 repository: NotionRepository,
                 validator: DataValidator,
                 monitor: MetricsCollector):
        self.repository = repository
        self.validator = validator
        self.monitor = monitor
    
    async def sync_database(self, 
                          database_id: str,
                          local_data: List[Dict[str, Any]],
                          config: SyncConfig) -> SyncResult:
        """Orchestrate full database sync"""
        
        with self.monitor.timer("sync.duration"):
            try:
                # Fetch existing data
                existing_pages = await self.repository.get_all_pages(database_id)
                existing_map = {
                    page.properties[config.title_property]: page 
                    for page in existing_pages
                }
                
                # Plan sync operations
                plan = self._create_sync_plan(local_data, existing_map, config)
                
                # Execute plan with transaction semantics
                result = await self._execute_plan(plan, database_id)
                
                self.monitor.increment("sync.success")
                return result
                
            except Exception as e:
                self.monitor.increment("sync.failure")
                raise SyncError(f"Sync failed: {e}") from e
    
    def _create_sync_plan(self, 
                         local_data: List[Dict],
                         existing_map: Dict[str, Page],
                         config: SyncConfig) -> SyncPlan:
        """Create plan for sync operations"""
        plan = SyncPlan()
        
        for item in local_data:
            title = item.get(config.title_property)
            if not title:
                plan.add_skip(item, "Missing title")
                continue
            
            if title in existing_map:
                existing = existing_map[title]
                if self._needs_update(item, existing, config):
                    plan.add_update(existing.id, item)
                else:
                    plan.add_skip(item, "No changes")
            else:
                plan.add_create(item)
        
        # Handle deletions if configured
        if config.delete_missing:
            for title, page in existing_map.items():
                if not any(item.get(config.title_property) == title 
                          for item in local_data):
                    plan.add_delete(page.id)
        
        return plan
```

### Phase 3: Comprehensive Testing (Week 3)

#### 3.1 Test Infrastructure (Days 1-2)

```python
# tests/fixtures/notion.py
import pytest
from unittest.mock import AsyncMock, Mock
import asyncio
from typing import List, Dict, Any

@pytest.fixture
def mock_notion_client():
    """Create a mock Notion client with realistic behavior"""
    client = AsyncMock()
    
    # Set up realistic response delays
    async def delayed_response(response, delay=0.1):
        await asyncio.sleep(delay)
        return response
    
    # Mock query database with pagination
    query_responses = []
    
    def setup_paginated_response(pages: List[Dict], page_size: int = 100):
        nonlocal query_responses
        query_responses = []
        
        for i in range(0, len(pages), page_size):
            chunk = pages[i:i + page_size]
            has_more = i + page_size < len(pages)
            next_cursor = f"cursor_{i + page_size}" if has_more else None
            
            query_responses.append({
                "object": "list",
                "results": chunk,
                "has_more": has_more,
                "next_cursor": next_cursor
            })
    
    client.setup_paginated_response = setup_paginated_response
    return client

@pytest.fixture
def network_failure_simulator():
    """Simulate various network failures"""
    class NetworkFailureSimulator:
        def __init__(self):
            self.failure_count = 0
            self.max_failures = 2
        
        async def simulate_timeout(self, delay=5):
            await asyncio.sleep(delay)
            raise asyncio.TimeoutError("Request timed out")
        
        async def simulate_connection_error(self):
            raise ConnectionError("Connection refused")
        
        async def simulate_intermittent_failure(self, success_response):
            self.failure_count += 1
            if self.failure_count <= self.max_failures:
                raise ConnectionError("Temporary failure")
            return success_response
    
    return NetworkFailureSimulator()

# tests/property_handlers/test_edge_cases.py
import pytest
from blackcore.properties import PropertyHandlerRegistry

class TestPropertyEdgeCases:
    """Test property handlers with edge cases"""
    
    @pytest.fixture
    def registry(self):
        return PropertyHandlerRegistry()
    
    def test_unicode_handling(self, registry):
        """Test various Unicode scenarios"""
        test_cases = [
            # Emoji
            ("🚀 Rocket Launch", "title"),
            # RTL text
            ("مرحبا بك في نوشن", "rich_text"),
            # Mixed scripts
            ("Hello 你好 مرحبا", "title"),
            # Zero-width characters
            ("Test\u200bString", "rich_text"),
            # Surrogate pairs
            ("𝓗𝓮𝓵𝓵𝓸 𝓦𝓸𝓻𝓵𝓭", "title"),
        ]
        
        for text, prop_type in test_cases:
            handler = registry.get_handler(prop_type)
            
            # Test simplify
            prop_data = {
                "type": prop_type,
                prop_type: [{"plain_text": text}]
            }
            simplified = handler.simplify(prop_data)
            assert simplified == text
            
            # Test payload building
            payload = handler.build_payload(text, {"type": prop_type})
            assert payload[prop_type][0]["text"]["content"] == text
    
    def test_malformed_data_handling(self, registry):
        """Test handling of malformed data"""
        malformed_cases = [
            # Missing type
            ({"title": [{"plain_text": "Test"}]}, None),
            # Wrong structure
            ({"type": "title", "title": "Not an array"}, None),
            # Empty array
            ({"type": "title", "title": []}, None),
            # Missing plain_text
            ({"type": "title", "title": [{"text": "Wrong key"}]}, None),
        ]
        
        for prop_data, expected in malformed_cases:
            handler = registry.get_handler("title")
            result = handler.simplify(prop_data)
            assert result == expected

# tests/integration/test_network_resilience.py
class TestNetworkResilience:
    """Test behavior under various network conditions"""
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_notion_client, network_failure_simulator):
        """Test handling of network timeouts"""
        repository = NotionAPIRepository(mock_notion_client)
        
        # Simulate timeout
        mock_notion_client.query_database.side_effect = network_failure_simulator.simulate_timeout
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                repository.get_all_pages("test-db"),
                timeout=1.0
            )
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, mock_notion_client, network_failure_simulator):
        """Test retry logic for transient failures"""
        repository = NotionAPIRepository(mock_notion_client)
        
        # Set up intermittent failure
        success_response = {
            "object": "list",
            "results": [{"id": "test-page"}],
            "has_more": False,
            "next_cursor": None
        }
        
        mock_notion_client.query_database.side_effect = lambda **kwargs: \
            network_failure_simulator.simulate_intermittent_failure(success_response)
        
        # Should succeed after retries
        pages = await repository.get_all_pages("test-db")
        assert len(pages) == 1
```

#### 3.2 Property Type Coverage (Day 3)

```python
# tests/property_handlers/test_all_types.py
import pytest
from datetime import datetime, timezone
from blackcore.properties import *

class TestAllPropertyTypes:
    """Comprehensive tests for all Notion property types"""
    
    @pytest.fixture
    def test_data(self):
        """Generate test data for all property types"""
        return {
            "title": ["", "a", "Normal Title", "x" * 2000, "x" * 2001],
            "rich_text": ["", "Simple text", "Multi\nline\ntext", "🎉 Unicode"],
            "number": [0, -1, 3.14159, float('inf'), float('-inf')],
            "select": ["", "Option 1", "New Option", None],
            "multi_select": [[], ["Tag1"], ["Tag1", "Tag2", "Tag3"]],
            "date": [
                "2025-01-01",
                "2025-01-01T10:00:00Z",
                "2025-01-01T10:00:00+05:00",
                {"start": "2025-01-01", "end": "2025-01-31"}
            ],
            "checkbox": [True, False, None],
            "url": [
                "https://example.com",
                "https://sub.example.com/path?query=1",
                "https://例え.jp",  # IDN
            ],
            "email": [
                "user@example.com",
                "user+tag@example.co.uk",
                "test.email@sub.domain.com"
            ],
            "phone_number": [
                "+1234567890",
                "+1 (234) 567-8900",
                "+44 20 7123 4567"
            ],
            "people": [
                [{"object": "user", "id": "123", "name": "John Doe"}],
                [{"object": "user", "id": "456", "person": {"email": "jane@example.com"}}],
                []
            ],
            "files": [
                [{"type": "external", "name": "doc.pdf", "external": {"url": "https://example.com/doc.pdf"}}],
                [{"type": "file", "name": "image.png", "file": {"url": "https://notion.so/image.png"}}],
                []
            ],
            "formula": [
                {"type": "string", "string": "Calculated Value"},
                {"type": "number", "number": 42},
                {"type": "boolean", "boolean": True},
                {"type": "date", "date": {"start": "2025-01-01"}}
            ],
            "rollup": [
                {"type": "number", "number": 100},
                {"type": "array", "array": [1, 2, 3]}
            ]
        }
    
    @pytest.mark.parametrize("prop_type", [
        "title", "rich_text", "number", "select", "multi_select",
        "date", "checkbox", "url", "email", "phone_number",
        "people", "files", "formula", "rollup"
    ])
    def test_property_type_round_trip(self, prop_type, test_data):
        """Test each property type can be simplified and rebuilt"""
        registry = PropertyHandlerRegistry()
        handler = registry.get_handler(prop_type)
        
        for test_value in test_data.get(prop_type, []):
            # Skip invalid values
            if not handler.validate(test_value):
                continue
            
            # Build payload
            payload = handler.build_payload(test_value, {"type": prop_type})
            
            # Simulate API response
            api_response = {"type": prop_type, **payload}
            
            # Simplify back
            simplified = handler.simplify(api_response)
            
            # Compare (accounting for transformations)
            if prop_type in ["title", "rich_text"] and isinstance(test_value, str):
                # Text might be truncated
                assert simplified == test_value[:2000]
            else:
                assert simplified == test_value
```

#### 3.3 Performance & Load Testing (Day 4)

```python
# tests/performance/test_load.py
import pytest
import asyncio
import time
from memory_profiler import profile
import psutil
import os

class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_dataset_memory_usage(self):
        """Test memory usage with large datasets"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create repository with 10k pages
        repository = MockNotionRepository()
        pages = [self._create_test_page(i) for i in range(10000)]
        repository.set_pages(pages)
        
        # Process all pages
        service = NotionSyncService(repository)
        start_time = time.time()
        
        all_pages = await service.get_all_pages_as_generator("test-db")
        processed_count = 0
        
        async for page in all_pages:
            processed_count += 1
            # Simulate processing
            await asyncio.sleep(0.001)
        
        end_time = time.time()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Assertions
        assert processed_count == 10000
        memory_increase = final_memory - initial_memory
        assert memory_increase < 100  # Should not exceed 100MB for 10k pages
        
        processing_time = end_time - start_time
        assert processing_time < 30  # Should complete within 30 seconds
    
    @pytest.mark.performance
    def test_rate_limit_compliance_under_load(self):
        """Test rate limiter maintains limits under concurrent load"""
        limiter = ThreadSafeRateLimiter(requests_per_second=10)
        request_times = []
        
        def make_request():
            limiter.wait_if_needed()
            request_times.append(time.time())
        
        # Simulate 100 concurrent requests
        threads = []
        for _ in range(100):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Analyze request distribution
        request_times.sort()
        
        # Check that no more than 10 requests happen per second
        for i in range(len(request_times) - 10):
            time_window = request_times[i + 10] - request_times[i]
            assert time_window >= 0.95  # Allow 5% tolerance
    
    @profile
    def test_property_handler_memory_efficiency(self):
        """Profile memory usage of property handlers"""
        registry = PropertyHandlerRegistry()
        
        # Process 1000 pages with all property types
        for i in range(1000):
            page_data = self._create_complex_page_data(i)
            
            for prop_name, prop_data in page_data.items():
                prop_type = prop_data.get('type')
                handler = registry.get_handler(prop_type)
                simplified = handler.simplify(prop_data)
                
                # Ensure no memory leaks
                del simplified
```

#### 3.4 Security Testing (Day 5)

```python
# tests/security/test_vulnerabilities.py
import pytest
from blackcore.security import URLValidator, InputSanitizer

class TestSecurityVulnerabilities:
    """Test for security vulnerabilities"""
    
    def test_ssrf_prevention(self):
        """Test SSRF attack prevention"""
        validator = URLValidator()
        
        # Test blocked URLs
        blocked_urls = [
            "http://localhost/admin",
            "http://127.0.0.1:8080",
            "http://169.254.169.254/latest/meta-data",  # AWS metadata
            "http://192.168.1.1/",  # Private network
            "http://10.0.0.1/",  # Private network
            "file:///etc/passwd",  # File protocol
            "ftp://internal-server/",  # Non-HTTPS
            "https://[::1]/",  # IPv6 localhost
        ]
        
        for url in blocked_urls:
            with pytest.raises(ValueError):
                validator.validate_url(url)
        
        # Test allowed URLs
        allowed_urls = [
            "https://api.notion.com/v1/pages",
            "https://example.com/webhook",
            "https://cdn.example.com/image.png",
        ]
        
        for url in allowed_urls:
            assert validator.validate_url(url) is True
    
    def test_xss_prevention(self):
        """Test XSS attack prevention"""
        sanitizer = InputSanitizer()
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
        ]
        
        for payload in xss_payloads:
            sanitized = sanitizer.sanitize_text(payload)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "onerror=" not in sanitized
            assert "onload=" not in sanitized
    
    def test_api_key_protection(self):
        """Test API key is never exposed"""
        from blackcore.security import SecretsManager
        
        secrets = SecretsManager()
        api_key = "secret-api-key-12345"
        
        # Store key
        secrets.store_secret("test_key", api_key)
        
        # Ensure it's not in string representation
        assert api_key not in str(secrets)
        assert api_key not in repr(secrets)
        
        # Ensure it's not in error messages
        try:
            secrets.get_secret("non_existent")
        except KeyError as e:
            assert api_key not in str(e)
```

### Phase 4: Production Readiness (Week 4)

#### 4.1 Observability Implementation (Days 1-2)

```python
# monitoring/metrics.py
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import structlog

class ObservabilitySetup:
    """Configure comprehensive observability"""
    
    @classmethod
    def initialize(cls):
        # Configure structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Configure OpenTelemetry
        tracer = trace.get_tracer(__name__)
        meter = metrics.get_meter(__name__)
        
        # Create metrics
        cls.api_call_counter = meter.create_counter(
            "notion_api_calls_total",
            description="Total number of Notion API calls",
            unit="1"
        )
        
        cls.api_call_duration = meter.create_histogram(
            "notion_api_call_duration_seconds",
            description="Duration of Notion API calls",
            unit="s"
        )
        
        cls.rate_limit_hits = meter.create_counter(
            "notion_rate_limit_hits_total",
            description="Number of rate limit hits",
            unit="1"
        )
        
        cls.sync_operations = meter.create_counter(
            "notion_sync_operations_total",
            description="Number of sync operations",
            unit="1"
        )
        
        return cls

# monitoring/instrumentation.py
from functools import wraps
from opentelemetry import trace
import time

def instrument_api_call(operation: str):
    """Decorator to instrument API calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(f"notion.api.{operation}") as span:
                span.set_attribute("operation", operation)
                span.set_attribute("database_id", kwargs.get("database_id", "unknown"))
                
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    
                    # Record metrics
                    ObservabilitySetup.api_call_counter.add(
                        1, {"operation": operation, "status": "success"}
                    )
                    
                    return result
                    
                except Exception as e:
                    span.set_status(
                        trace.Status(trace.StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    
                    # Record metrics
                    ObservabilitySetup.api_call_counter.add(
                        1, {"operation": operation, "status": "error"}
                    )
                    
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    ObservabilitySetup.api_call_duration.record(
                        duration, {"operation": operation}
                    )
        
        return wrapper
    return decorator
```

#### 4.2 Deployment Configuration (Day 3)

```python
# deployment/config.py
from pydantic import BaseSettings, Field, validator
from typing import Optional, List
import os

class NotionSyncConfig(BaseSettings):
    """Production configuration with validation"""
    
    # API Configuration
    notion_api_key: str = Field(..., env="NOTION_API_KEY")
    api_version: str = Field("2022-06-28", env="NOTION_API_VERSION")
    
    # Rate Limiting
    rate_limit_rps: float = Field(3.0, env="RATE_LIMIT_RPS", ge=0.1, le=10)
    rate_limit_burst: int = Field(5, env="RATE_LIMIT_BURST", ge=1, le=20)
    
    # Retry Configuration
    max_retry_attempts: int = Field(3, env="MAX_RETRY_ATTEMPTS", ge=1, le=5)
    retry_backoff_base: float = Field(2.0, env="RETRY_BACKOFF_BASE", ge=1.5, le=3.0)
    
    # Security
    secrets_provider: str = Field("env", env="SECRETS_PROVIDER")
    allowed_domains: List[str] = Field(
        ["api.notion.com", "notion.so"],
        env="ALLOWED_DOMAINS"
    )
    
    # Performance
    page_size: int = Field(100, env="PAGE_SIZE", ge=1, le=100)
    sync_timeout: int = Field(300, env="SYNC_TIMEOUT", ge=60, le=3600)
    
    # Monitoring
    enable_tracing: bool = Field(True, env="ENABLE_TRACING")
    trace_endpoint: Optional[str] = Field(None, env="TRACE_ENDPOINT")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    
    # Cache Configuration
    cache_enabled: bool = Field(True, env="CACHE_ENABLED")
    cache_ttl: int = Field(300, env="CACHE_TTL", ge=0, le=3600)
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator("notion_api_key")
    def validate_api_key(cls, v):
        if not v.startswith(("secret_", "ntn_")):
            raise ValueError("Invalid Notion API key format")
        return v
    
    @validator("redis_url")
    def validate_redis_url(cls, v, values):
        if values.get("cache_enabled") and not v:
            raise ValueError("Redis URL required when cache is enabled")
        return v

# deployment/health.py
from typing import Dict, Any
import asyncio
from datetime import datetime

class HealthChecker:
    """Production health checks"""
    
    def __init__(self, 
                 notion_client: NotionClient,
                 redis_client: Optional[Redis],
                 config: NotionSyncConfig):
        self.notion = notion_client
        self.redis = redis_client
        self.config = config
    
    async def check_health(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        checks = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": {}
        }
        
        # Check Notion API
        try:
            await asyncio.wait_for(
                self.notion.get_current_user(),
                timeout=5.0
            )
            checks["checks"]["notion_api"] = {"status": "healthy"}
        except Exception as e:
            checks["checks"]["notion_api"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            checks["status"] = "unhealthy"
        
        # Check Redis if enabled
        if self.config.cache_enabled and self.redis:
            try:
                await self.redis.ping()
                checks["checks"]["redis"] = {"status": "healthy"}
            except Exception as e:
                checks["checks"]["redis"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                checks["status"] = "degraded"
        
        # Check rate limiter
        checks["checks"]["rate_limiter"] = {
            "status": "healthy",
            "current_rps": self.config.rate_limit_rps,
            "burst": self.config.rate_limit_burst
        }
        
        return checks
```

#### 4.3 Deployment Scripts (Day 4)

```yaml
# docker/Dockerfile
FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 notion && \
    mkdir -p /app && \
    chown -R notion:notion /app

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=notion:notion . .

# Security: Drop privileges
USER notion

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m blackcore.health || exit 1

# Metrics port
EXPOSE 9090

# Start application
CMD ["python", "-m", "blackcore.main"]

# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notion-sync
  labels:
    app: notion-sync
spec:
  replicas: 3
  selector:
    matchLabels:
      app: notion-sync
  template:
    metadata:
      labels:
        app: notion-sync
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: notion-sync
        image: notion-sync:latest
        ports:
        - containerPort: 9090
          name: metrics
        env:
        - name: NOTION_API_KEY
          valueFrom:
            secretKeyRef:
              name: notion-secrets
              key: api-key
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secrets
              key: connection-string
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 4.4 Documentation & Runbook (Day 5)

```markdown
# Production Runbook: Notion Sync Engine

## Quick Start

### Local Development
```bash
# Clone repository
git clone https://github.com/org/blackcore.git
cd blackcore

# Set up environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run tests
pytest

# Start development server
python -m blackcore.main --dev
```

### Production Deployment
```bash
# Build Docker image
docker build -t notion-sync:latest .

# Run with Docker Compose
docker-compose up -d

# Or deploy to Kubernetes
kubectl apply -f kubernetes/
```

## Monitoring & Alerts

### Key Metrics
1. **API Call Rate**: `notion_api_calls_total`
   - Alert if rate > 2.5 req/sec (approaching limit)
   
2. **Error Rate**: `notion_api_calls_total{status="error"}`
   - Alert if error rate > 1% over 5 minutes
   
3. **Response Time**: `notion_api_call_duration_seconds`
   - Alert if p99 > 2 seconds

### Dashboards
- Grafana: http://monitoring.internal/d/notion-sync
- Logs: http://kibana.internal/app/logs

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**
   ```
   Symptom: HTTP 429 errors
   Check: Current RPS in metrics
   Fix: Reduce rate_limit_rps in config
   ```

2. **Memory Issues**
   ```
   Symptom: OOM kills
   Check: Memory usage in container
   Fix: Increase memory limit or optimize batch size
   ```

3. **Connection Timeouts**
   ```
   Symptom: Timeout errors in logs
   Check: Network connectivity to Notion API
   Fix: Check firewall rules, DNS resolution
   ```

### Emergency Procedures

1. **Complete Service Failure**
   ```bash
   # Rollback to previous version
   kubectl rollout undo deployment/notion-sync
   
   # Check logs
   kubectl logs -l app=notion-sync --tail=100
   ```

2. **Data Corruption**
   ```bash
   # Stop all sync operations
   kubectl scale deployment/notion-sync --replicas=0
   
   # Restore from backup
   python -m blackcore.restore --timestamp=2025-01-01T00:00:00Z
   ```

## Security

### API Key Rotation
```bash
# Generate new key in Notion
# Update in secrets manager
kubectl create secret generic notion-secrets \
  --from-literal=api-key=NEW_KEY \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods
kubectl rollout restart deployment/notion-sync
```

### Audit Logs
All API operations are logged with:
- User ID
- Operation type
- Timestamp
- Result

Access audit logs: http://kibana.internal/app/logs?query=audit

## Performance Tuning

### Batch Size Optimization
```python
# For small datasets (<1000 items)
PAGE_SIZE=100
SYNC_BATCH_SIZE=50

# For large datasets (>10000 items)
PAGE_SIZE=50
SYNC_BATCH_SIZE=20
```

### Cache Configuration
```python
# High read, low write
CACHE_TTL=3600  # 1 hour

# High write frequency
CACHE_TTL=300   # 5 minutes
```

## Contact

- **On-Call**: notion-sync-oncall@company.com
- **Team Chat**: #notion-sync-support
- **Escalation**: Engineering Manager
```

## Success Criteria

### Technical Success Metrics
- [ ] All security vulnerabilities resolved (0 high/critical findings)
- [ ] Test coverage > 85% with all edge cases covered
- [ ] API error rate < 0.1% in production
- [ ] p99 latency < 500ms for all operations
- [ ] Memory usage < 100MB per 1000 pages processed
- [ ] Zero data loss or corruption incidents
- [ ] 99.9% uptime SLA achieved

### Operational Success Metrics
- [ ] Mean time to detection < 5 minutes
- [ ] Mean time to recovery < 15 minutes
- [ ] Deployment frequency >= daily
- [ ] Change failure rate < 5%
- [ ] All team members can debug issues independently

### Business Success Metrics
- [ ] Sync operations 10x faster than manual process
- [ ] Support ticket volume reduced by 80%
- [ ] Zero compliance violations
- [ ] Customer satisfaction score > 4.5/5

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|---------|------------|-------|
| API rate limit changes | Low | High | Monitor Notion changelog, implement adaptive rate limiting | DevOps |
| Security breach | Low | Critical | Security scanning, key rotation, audit logs | Security |
| Data corruption | Medium | High | Validation, backups, dry-run mode | Backend |
| Performance degradation | Medium | Medium | Monitoring, auto-scaling, caching | DevOps |
| Team knowledge loss | Medium | Medium | Documentation, pair programming, runbooks | Tech Lead |

## Implementation Sign-off

- [ ] Security Engineer: Security review complete
- [ ] QA Engineer: Test plan approved and executed
- [ ] DevOps Engineer: Deployment pipeline ready
- [ ] Tech Lead: Architecture approved
- [ ] Product Manager: Requirements met
- [ ] Engineering Manager: Resources allocated

---
**Document Version**: 1.0  
**Next Review**: Post-implementation retrospective  
**Approval Date**: 2025-07-08