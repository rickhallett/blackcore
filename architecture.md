# Blackcore Architecture

> **Technical deep-dive into the Blackcore intelligence processing system**

This document provides comprehensive technical documentation for the Blackcore architecture, covering system design, component interactions, data flows, and implementation patterns.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Principles](#architectural-principles)
3. [Component Architecture](#component-architecture)
4. [Minimal Module Deep Dive](#minimal-module-deep-dive)
5. [Repository Pattern Implementation](#repository-pattern-implementation)
6. [AI Integration Architecture](#ai-integration-architecture)
7. [Security Architecture](#security-architecture)
8. [Test Infrastructure](#test-infrastructure)
9. [Data Flow Diagrams](#data-flow-diagrams)
10. [Performance Considerations](#performance-considerations)
11. [Deployment Architecture](#deployment-architecture)

## System Overview

Blackcore is designed as a multi-layered, security-first intelligence processing system that transforms unstructured data into structured knowledge graphs. The system follows Domain-Driven Design (DDD) principles with clear boundaries between contexts.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT INTERFACES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  CLI Tools        │  Web UI           │  API Endpoints   │  Batch Scripts   │
│  ├─ Minimal CLI   │  ├─ Admin Panel   │  ├─ REST API     │  ├─ Setup        │
│  ├─ Dedupe CLI    │  ├─ Review UI     │  ├─ GraphQL      │  ├─ Sync         │
│  └─ Debug Tools   │  └─ Analytics     │  └─ Webhooks     │  └─ Maintenance  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                         ORCHESTRATION SERVICES                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ Transcript      │  │ Deduplication   │  │ Synchronization │           │
│  │ Processor       │  │ Engine          │  │ Service         │           │
│  │                 │  │                 │  │                 │           │
│  │ • Entity Extr.  │  │ • Similarity    │  │ • Notion Sync   │           │
│  │ • Relationship  │  │ • AI Analysis   │  │ • JSON Export   │           │
│  │ • Notion Update │  │ • Merge Logic   │  │ • Diff Detection│           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DOMAIN LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                          BUSINESS SERVICES                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ Intelligence    │  │ Entity          │  │ Relationship    │           │
│  │ Service         │  │ Service         │  │ Service         │           │
│  │                 │  │                 │  │                 │           │
│  │ • Validation    │  │ • Normalization │  │ • Graph Ops     │           │
│  │ • Enrichment    │  │ • Deduplication │  │ • Consistency   │           │
│  │ • Classification│  │ • Merging       │  │ • Validation    │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
│                                                                           │
│                           DOMAIN MODELS                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ Person │ Organization │ Task │ Event │ Document │ Transgression  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                       INFRASTRUCTURE LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                         REPOSITORY LAYER                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ Page            │  │ Database        │  │ Search          │           │
│  │ Repository      │  │ Repository      │  │ Repository      │           │
│  │                 │  │                 │  │                 │           │
│  │ • CRUD Ops      │  │ • Schema Mgmt   │  │ • Query Builder │           │
│  │ • Batch Ops     │  │ • Validation    │  │ • Filtering     │           │
│  │ • Caching       │  │ • Migration     │  │ • Pagination    │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
│                                                                           │
│                      INTEGRATION ADAPTERS                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ Notion          │  │ AI              │  │ Property        │           │
│  │ Client          │  │ Extractor       │  │ Handlers        │           │
│  │                 │  │                 │  │                 │           │
│  │ • Rate Limiting │  │ • Claude API    │  │ • Type System   │           │
│  │ • Retry Logic   │  │ • OpenAI API    │  │ • Validation    │           │
│  │ • Response Mgmt │  │ • Prompt Mgmt   │  │ • Conversion    │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
│                                                                           │
│                     CROSS-CUTTING CONCERNS                               │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ Security │ Caching │ Rate Limiting │ Error Handling │ Logging     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Architectural Principles

### 1. **Separation of Concerns**
- **Clear Layer Boundaries**: Each layer has distinct responsibilities
- **Single Responsibility**: Components focus on one aspect of the system
- **Dependency Inversion**: High-level modules don't depend on low-level modules

### 2. **Security First**
- **Defense in Depth**: Multiple security layers
- **Principle of Least Privilege**: Minimal required permissions
- **Fail Secure**: System defaults to secure state on failure

### 3. **Reliability & Resilience**
- **Graceful Degradation**: Partial functionality during failures
- **Circuit Breaker Pattern**: Prevent cascade failures
- **Comprehensive Testing**: 686 tests with 100% pass rate

### 4. **Performance & Scalability**
- **Caching Strategy**: Multi-level caching (file, memory, Redis)
- **Async Operations**: Non-blocking I/O for external services
- **Batch Processing**: Efficient bulk operations

### 5. **Maintainability**
- **Clean Architecture**: Testable, flexible, maintainable
- **Type Safety**: Comprehensive type hints with Pydantic
- **Documentation**: Code self-documents through clear naming

## Component Architecture

### CLI Layer
**Responsibility**: User interaction and command orchestration

```python
# Entry points for different user interfaces
├── blackcore/minimal/cli.py          # Main CLI for minimal module
├── scripts/deduplication/dedupe_cli.py  # Interactive deduplication
├── scripts/setup/setup_databases.py     # Database initialization
└── scripts/sync/notion_sync.py          # Data synchronization
```

**Key Components:**
- **Command Parsers**: Argument parsing and validation
- **Progress Indicators**: Rich terminal UI with progress tracking
- **Error Presentation**: User-friendly error messages
- **Configuration Wizards**: Interactive setup and configuration

### Application Layer
**Responsibility**: Orchestrate business processes and coordinate between layers

#### Transcript Processor
```python
class TranscriptProcessor:
    """Main orchestrator for intelligence processing workflow."""
    
    def __init__(self, config: Config):
        self.ai_extractor = AIExtractor(config.ai)
        self.notion_updater = NotionUpdater(config.notion)
        self.cache = Cache(config.processing.cache_dir)
    
    async def process_transcript(self, transcript: TranscriptInput) -> ProcessingResult:
        """Process a single transcript through the full pipeline."""
        # 1. Extract entities using AI
        extracted = await self.ai_extractor.extract_entities(transcript)
        
        # 2. Create/update entities in Notion
        result = await self.notion_updater.update_entities(extracted)
        
        # 3. Cache results for performance
        await self.cache.store(transcript.id, result)
        
        return result
```

#### Deduplication Engine
```python
class DeduplicationEngine:
    """AI-powered duplicate detection and merging system."""
    
    def __init__(self, config: Config):
        self.similarity_scorer = SimilarityScorer(config)
        self.llm_analyzer = LLMAnalyzer(config.ai)
        self.graph_analyzer = GraphAnalyzer()
    
    async def find_duplicates(self, database_id: str) -> List[DuplicateMatch]:
        """Find potential duplicates using multiple strategies."""
        # 1. Similarity scoring based on content
        # 2. Graph analysis for relationship patterns
        # 3. AI analysis for semantic similarity
```

### Domain Layer
**Responsibility**: Business logic and domain rules

#### Entity Services
```python
# Core domain services implementing business rules
├── blackcore/services/entity_service.py      # Entity lifecycle management
├── blackcore/services/intelligence_service.py # Intelligence processing rules
├── blackcore/services/relationship_service.py # Relationship management
└── blackcore/services/validation_service.py   # Business validation rules
```

#### Domain Models
```python
# Pydantic models representing core business entities
class Person(BaseModel):
    """Domain model for a person entity."""
    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    relationships: List[Relationship] = Field(default_factory=list)
    
    class Config:
        validate_assignment = True
        use_enum_values = True
```

### Infrastructure Layer
**Responsibility**: Technical capabilities and external integrations

#### Repository Pattern Implementation
```python
class BaseRepository(ABC):
    """Abstract base for all repositories."""
    
    def __init__(self, client: NotionClient):
        self.client = client
        self.cache = RepositoryCache()
    
    @abstractmethod
    async def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing entity."""
        pass
    
    async def batch_create(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple entities efficiently."""
        results = []
        for batch in self._chunk_requests(entities, batch_size=10):
            batch_results = await asyncio.gather(*[
                self.create(entity) for entity in batch
            ])
            results.extend(batch_results)
        return results
```

## Minimal Module Deep Dive

The minimal module (`blackcore/minimal/`) represents a self-contained, production-ready implementation designed for ease of adoption and deployment.

### Minimal Module Architecture

```
blackcore/minimal/
├── models.py                    # Pydantic data models
├── config.py                    # Configuration management
├── transcript_processor.py      # Main orchestrator
├── ai_extractor.py             # AI integration layer
├── notion_updater.py           # Notion API wrapper
├── property_handlers.py        # Type-specific property handling
├── cache.py                    # Simple file-based caching
├── cli.py                      # Command-line interface
├── utils.py                    # Helper functions
└── tests/                      # 686 comprehensive tests
    ├── test_transcript_processor.py
    ├── comprehensive/
    │   ├── infrastructure.py   # Test utilities and fixtures
    │   ├── test_realistic_workflows.py      # 16 workflow tests
    │   ├── test_network_resilience.py       # 22+ resilience tests
    │   └── test_performance_regression.py   # Performance benchmarks
    └── ...
```

### Key Design Decisions

#### 1. **Self-Contained Dependencies**
- No dependency on main blackcore modules
- All required functionality included within minimal/
- Clean separation allows independent deployment

#### 2. **Simple Caching Strategy**
```python
class FileCache:
    """Simple file-based cache with TTL support."""
    
    def __init__(self, cache_dir: str, default_ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if not expired."""
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            return None
            
        # Check TTL and return data if valid
        metadata = self._read_metadata(cache_file)
        if time.time() > metadata['expires_at']:
            cache_file.unlink()  # Remove expired cache
            return None
            
        return self._read_data(cache_file)
```

#### 3. **Property Handler System**
```python
class PropertyHandlerRegistry:
    """Registry for all Notion property type handlers."""
    
    def __init__(self):
        self._handlers = {}
        self._register_default_handlers()
    
    def register(self, property_type: str, handler: PropertyHandler):
        """Register a property handler for a specific type."""
        self._handlers[property_type] = handler
    
    def get_handler(self, property_type: str) -> PropertyHandler:
        """Get the appropriate handler for a property type."""
        return self._handlers.get(property_type, self._handlers['default'])
    
    def _register_default_handlers(self):
        """Register all built-in property handlers."""
        self.register('title', TitlePropertyHandler())
        self.register('rich_text', RichTextPropertyHandler())
        self.register('select', SelectPropertyHandler())
        self.register('multi_select', MultiSelectPropertyHandler())
        self.register('relation', RelationPropertyHandler())
        # ... all other Notion property types
```

## Repository Pattern Implementation

The repository pattern provides a clean abstraction over data access, making the system testable and maintainable.

### Repository Hierarchy

```python
BaseRepository (Abstract)
├── PageRepository           # Notion page operations
├── DatabaseRepository       # Notion database operations
└── SearchRepository        # Query and search operations
```

### Implementation Details

#### Page Repository
```python
class PageRepository(BaseRepository):
    """Repository for Notion page operations."""
    
    async def create(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new page in Notion."""
        try:
            response = await self._make_api_call('pages.create', **page_data)
            await self.cache.store(response['id'], response)
            return response
        except Exception as e:
            self._handle_api_error(e, 'create_page', page_data)
    
    async def find_by_title(self, database_id: str, title: str) -> Optional[Dict[str, Any]]:
        """Find a page by title in a specific database."""
        # Try cache first
        cache_key = f"page:{database_id}:{title}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Query Notion API
        query_result = await self._make_api_call(
            'databases.query',
            database_id=database_id,
            filter={
                "property": "Name",  # Assuming title property is "Name"
                "title": {"equals": title}
            }
        )
        
        pages = query_result.get('results', [])
        if pages:
            page = pages[0]
            await self.cache.store(cache_key, page)
            return page
        
        return None
    
    async def batch_update(self, updates: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Update multiple pages efficiently."""
        results = []
        
        # Process in batches to respect rate limits
        for batch in self._chunk_requests(updates, batch_size=3):
            batch_tasks = [
                self.update(page_id, update_data) 
                for page_id, update_data in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle any errors in the batch
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    page_id, update_data = batch[i]
                    self._log_error(f"Failed to update page {page_id}: {result}")
                    results.append(None)
                else:
                    results.append(result)
        
        return results
```

#### Database Repository
```python
class DatabaseRepository(BaseRepository):
    """Repository for Notion database operations."""
    
    async def get_schema(self, database_id: str) -> Dict[str, Any]:
        """Get database schema with property definitions."""
        # Check cache first
        cache_key = f"schema:{database_id}"
        cached_schema = await self.cache.get(cache_key)
        if cached_schema:
            return cached_schema
        
        # Fetch from Notion
        database = await self._make_api_call('databases.retrieve', database_id=database_id)
        schema = database.get('properties', {})
        
        # Cache for 1 hour (schema changes infrequently)
        await self.cache.store(cache_key, schema, ttl=3600)
        return schema
    
    async def validate_properties(self, database_id: str, properties: Dict[str, Any]) -> List[str]:
        """Validate properties against database schema."""
        schema = await self.get_schema(database_id)
        errors = []
        
        for prop_name, prop_value in properties.items():
            if prop_name not in schema:
                errors.append(f"Property '{prop_name}' does not exist in database schema")
                continue
            
            expected_type = schema[prop_name]['type']
            if not self._validate_property_type(prop_value, expected_type):
                errors.append(f"Property '{prop_name}' has invalid type. Expected: {expected_type}")
        
        return errors
```

## AI Integration Architecture

The AI integration layer provides a unified interface for multiple AI providers while handling provider-specific implementations.

### AI Provider Architecture

```python
class AIExtractor:
    """Unified AI extraction interface supporting multiple providers."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.provider = self._create_provider(config.provider)
        self.prompt_manager = PromptManager()
    
    def _create_provider(self, provider_name: str) -> AIProvider:
        """Factory method for AI providers."""
        if provider_name == 'claude':
            return ClaudeProvider(self.config)
        elif provider_name == 'openai':
            return OpenAIProvider(self.config)
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")
    
    async def extract_entities(self, transcript: TranscriptInput) -> ExtractedEntities:
        """Extract entities from transcript using configured AI provider."""
        # Build extraction prompt
        prompt = self.prompt_manager.build_extraction_prompt(
            content=transcript.content,
            context=transcript.metadata
        )
        
        # Get AI response with retry logic
        response = await self._get_ai_response_with_retry(prompt)
        
        # Parse and validate response
        extracted = self._parse_extraction_response(response)
        
        # Apply post-processing rules
        return self._post_process_entities(extracted)
```

### Prompt Management System

```python
class PromptManager:
    """Manages AI prompts with templates and versioning."""
    
    def __init__(self, prompt_dir: Optional[str] = None):
        self.prompt_dir = Path(prompt_dir or 'prompts')
        self.templates = self._load_templates()
    
    def build_extraction_prompt(self, content: str, context: Dict[str, Any]) -> str:
        """Build entity extraction prompt from template."""
        template = self.templates['entity_extraction']
        
        return template.render(
            content=content,
            context=context,
            schema=ENTITY_SCHEMA,
            examples=EXTRACTION_EXAMPLES
        )
    
    def _load_templates(self) -> Dict[str, Template]:
        """Load all prompt templates from files."""
        templates = {}
        
        for template_file in self.prompt_dir.glob('*.j2'):
            template_name = template_file.stem
            with open(template_file, encoding='utf-8') as f:
                templates[template_name] = Template(f.read())
        
        return templates
```

### Entity Extraction Schema

```python
ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"enum": ["person", "organization", "task", "event", "document", "transgression"]},
                    "properties": {"type": "object"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "target": {"type": "string"},
                                "type": {"type": "string"},
                                "confidence": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["name", "type", "confidence"]
            }
        }
    }
}
```

## Security Architecture

Blackcore implements a comprehensive security framework based on defense-in-depth principles.

### Security Layers

#### 1. **Input Validation & Sanitization**
```python
class SecurityValidator:
    """Comprehensive input validation and sanitization."""
    
    def __init__(self):
        self.sql_injection_detector = SQLInjectionDetector()
        self.xss_detector = XSSDetector()
        self.file_path_validator = FilePathValidator()
    
    def validate_transcript_input(self, transcript: TranscriptInput) -> List[SecurityIssue]:
        """Validate transcript input for security issues."""
        issues = []
        
        # Check for SQL injection patterns
        if self.sql_injection_detector.detect(transcript.content):
            issues.append(SecurityIssue("SQL_INJECTION", "Potential SQL injection detected"))
        
        # Check for XSS patterns
        if self.xss_detector.detect(transcript.content):
            issues.append(SecurityIssue("XSS", "Potential XSS payload detected"))
        
        # Validate file paths in metadata
        if 'file_path' in transcript.metadata:
            if not self.file_path_validator.is_safe(transcript.metadata['file_path']):
                issues.append(SecurityIssue("PATH_TRAVERSAL", "Unsafe file path detected"))
        
        return issues
```

#### 2. **Secrets Management**
```python
class SecretsManager:
    """Encrypted secrets management with rotation support."""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self.cipher = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))
        self.secrets_file = Path('.secrets.enc')
    
    def store_secret(self, key: str, value: str) -> None:
        """Store an encrypted secret."""
        secrets = self._load_secrets()
        
        encrypted_value = self.cipher.encrypt(value.encode())
        secrets[key] = {
            'value': encrypted_value.decode(),
            'created_at': datetime.utcnow().isoformat(),
            'version': secrets.get(key, {}).get('version', 0) + 1
        }
        
        self._save_secrets(secrets)
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a secret."""
        secrets = self._load_secrets()
        
        if key not in secrets:
            return None
        
        encrypted_value = secrets[key]['value'].encode()
        decrypted_value = self.cipher.decrypt(encrypted_value)
        return decrypted_value.decode()
    
    def rotate_secret(self, key: str, new_value: str) -> None:
        """Rotate a secret with versioning."""
        # Keep old version for rollback capability
        self._archive_secret_version(key)
        self.store_secret(key, new_value)
```

#### 3. **Network Security**
```python
class NetworkSecurityFilter:
    """SSRF protection and network request filtering."""
    
    PRIVATE_IP_RANGES = [
        ipaddress.IPv4Network('10.0.0.0/8'),
        ipaddress.IPv4Network('172.16.0.0/12'),
        ipaddress.IPv4Network('192.168.0.0/16'),
        ipaddress.IPv4Network('127.0.0.0/8'),
        ipaddress.IPv4Network('169.254.0.0/16'),
    ]
    
    def is_request_allowed(self, url: str) -> bool:
        """Check if network request is allowed."""
        try:
            parsed = urlparse(url)
            ip_address = ipaddress.IPv4Address(socket.gethostbyname(parsed.hostname))
            
            # Block private IP ranges
            for private_range in self.PRIVATE_IP_RANGES:
                if ip_address in private_range:
                    return False
            
            # Block localhost variations
            if ip_address.is_loopback:
                return False
            
            return True
            
        except Exception:
            # If we can't resolve/validate, block the request
            return False
```

## Test Infrastructure

The comprehensive test infrastructure is a core component of Blackcore's reliability strategy.

### Test Architecture Overview

```
blackcore/minimal/tests/
├── test_transcript_processor.py         # Unit tests (7 tests)
├── conftest.py                         # Shared fixtures and configuration
├── comprehensive/
│   ├── infrastructure.py               # Test utilities and realistic data generation
│   ├── test_realistic_workflows.py     # End-to-end workflow tests (16 tests)
│   ├── test_network_resilience.py      # Network failure simulation (22+ tests)
│   └── test_performance_regression.py  # Performance benchmarking
└── ...additional test modules
```

### Test Infrastructure Components

#### 1. **Realistic Data Generation**
```python
class RealisticDataGenerator:
    """Generates authentic test data for high-value testing."""
    
    def __init__(self):
        self.names = ["Sarah Johnson", "Mike Chen", "Dr. Elizabeth Smith", ...]
        self.organizations = ["TechCorp Industries", "Green Valley Hospital", ...]
        self.places = ["Main Conference Room", "City Hall", ...]
        
    def generate_transcript(self, complexity: str = "medium") -> TranscriptInput:
        """Generate realistic transcript with controlled complexity."""
        template = random.choice(self.transcript_templates)
        
        complexity_params = {
            "simple": {"entities": 2, "relationships": 1, "length": "short"},
            "medium": {"entities": 5, "relationships": 3, "length": "medium"},
            "complex": {"entities": 8, "relationships": 6, "length": "long"},
        }
        
        return template(complexity_params[complexity])
```

#### 2. **Network Failure Simulation**
```python
class FailureSimulator:
    """Simulates realistic network failures for resilience testing."""
    
    @contextmanager
    def network_failure(self, failure_rate: float = 1.0):
        """Simulate network failures with specified rate."""
        def mock_request(*args, **kwargs):
            if random.random() < failure_rate:
                raise requests.exceptions.ConnectionError("Simulated network failure")
            return MagicMock(status_code=200, json=lambda: {"results": []})
        
        with patch('requests.request', side_effect=mock_request):
            yield
    
    @contextmanager
    def partial_api_failure(self, success_rate: float = 0.5):
        """Simulate partial API failures for resilience testing."""
        def mock_notion_query(*args, **kwargs):
            if random.random() < success_rate:
                return {"results": [], "has_more": False}
            else:
                raise Exception("Simulated partial API failure")
        
        with patch('notion_client.Client') as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.databases.query.side_effect = mock_notion_query
            yield mock_instance
```

#### 3. **Performance Profiling**
```python
class PerformanceProfiler:
    """Performance profiling for regression detection."""
    
    def __init__(self):
        self.benchmarks: Dict[str, List[float]] = {}
    
    @contextmanager
    def profile(self, operation_name: str):
        """Profile an operation and record timing."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation_name not in self.benchmarks:
                self.benchmarks[operation_name] = []
            self.benchmarks[operation_name].append(duration)
    
    def check_regression(self, operation_name: str, threshold_percent: float = 20.0) -> bool:
        """Check if recent performance is within threshold of baseline."""
        if operation_name not in self.benchmarks or len(self.benchmarks[operation_name]) < 2:
            return True
        
        baseline = sum(self.benchmarks[operation_name][:-1]) / (len(self.benchmarks[operation_name]) - 1)
        recent = self.benchmarks[operation_name][-1]
        
        regression_threshold = baseline * (1 + threshold_percent / 100)
        return recent <= regression_threshold
```

### Test Categories Detail

#### Unit Tests (7 tests)
- **Core Functionality**: Basic transcript processing workflows
- **Model Validation**: Pydantic model integrity and validation
- **Configuration**: Config loading and validation
- **Error Handling**: Exception handling and error recovery

#### Realistic Workflows (16 tests)
- **Meeting Transcripts**: Typical business meeting scenarios
- **Interview Processing**: One-on-one interview transcripts
- **Planning Sessions**: Strategic planning and decision-making
- **Status Updates**: Progress reports and updates
- **Batch Processing**: Multiple transcript handling
- **Dry Run Validation**: No-side-effect testing

#### Network Resilience (22+ tests)
- **Complete Network Failure**: Total connectivity loss
- **Intermittent Failures**: Partial success scenarios (50% failure rate)
- **API Timeouts**: Request timeout handling
- **HTTP Error Responses**: 4xx/5xx status code handling
- **Rate Limiting**: 429 responses with retry-after headers
- **Connection Drops**: Mid-request failures
- **DNS Failures**: Name resolution errors
- **High Latency**: Slow response simulation

#### Performance Regression Tests
- **Baseline Establishment**: Single transcript processing benchmarks
- **Scalability Testing**: Batch sizes (5, 10, 25, 50 transcripts)
- **Memory Usage**: Peak usage and cleanup verification
- **Cache Performance**: Hit ratios and efficiency metrics
- **Concurrent Processing**: Thread safety validation

## Data Flow Diagrams

### Intelligence Processing Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raw Input     │    │   Validation    │    │   AI Analysis   │
│                 │    │                 │    │                 │
│ • Transcripts   │───▶│ • Schema Check  │───▶│ • Entity Extr.  │
│ • Documents     │    │ • Security Scan │    │ • Relationship  │
│ • Audio Files   │    │ • Format Valid. │    │ • Confidence    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Notion Update  │    │  Deduplication  │    │  Entity Norm.   │
│                 │    │                 │    │                 │
│ • Create Pages  │◀───│ • Similarity    │◀───│ • Name Standard │
│ • Update Props  │    │ • AI Analysis   │    │ • Type Valid.   │
│ • Link Relations│    │ • Merge Decision│    │ • Confidence    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Repository Data Access Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service       │    │   Repository    │    │     Cache       │
│   Layer         │    │     Layer       │    │                 │
│                 │    │                 │    │                 │
│ • Business      │───▶│ • Data Access   │───▶│ • File Cache    │
│   Logic         │    │ • Validation    │    │ • Memory Cache  │
│ • Orchestration │    │ • Transformation│    │ • TTL Mgmt      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        │
                    ┌─────────────────┐                  │
                    │  Notion API     │                  │
                    │                 │                  │
                    │ • Rate Limited  │                  │
                    │ • Retry Logic   │                  │
                    │ • Error Handling│                  │
                    └─────────────────┘                  │
                                │                        │
                                ▼                        │
                    ┌─────────────────┐                  │
                    │   Response      │──────────────────┘
                    │   Processing    │
                    │                 │
                    │ • Validation    │
                    │ • Caching       │
                    │ • Transformation│
                    └─────────────────┘
```

## Performance Considerations

### Caching Strategy

#### Multi-Level Caching
```python
class CacheManager:
    """Multi-level caching with different strategies per layer."""
    
    def __init__(self, config: CacheConfig):
        self.l1_cache = MemoryCache(max_size=config.memory_cache_size)  # Fast access
        self.l2_cache = FileCache(config.file_cache_dir)                # Persistent
        self.l3_cache = RedisCache(config.redis_url) if config.redis_url else None  # Distributed
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache with fallback strategy."""
        # Try L1 (memory) first
        value = await self.l1_cache.get(key)
        if value is not None:
            return value
        
        # Try L2 (file) cache
        value = await self.l2_cache.get(key)
        if value is not None:
            # Promote to L1
            await self.l1_cache.set(key, value)
            return value
        
        # Try L3 (Redis) if available
        if self.l3_cache:
            value = await self.l3_cache.get(key)
            if value is not None:
                # Promote to L1 and L2
                await self.l1_cache.set(key, value)
                await self.l2_cache.set(key, value)
                return value
        
        return None
```

### Rate Limiting Strategy

```python
class RateLimiter:
    """Thread-safe rate limiter with sliding window."""
    
    def __init__(self, requests_per_second: float = 3.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire rate limit permission."""
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                await asyncio.sleep(sleep_time)
            
            self.last_request_time = time.time()
```

### Batch Processing Optimization

```python
class BatchProcessor:
    """Optimized batch processing with configurable strategies."""
    
    def __init__(self, batch_size: int = 10, max_concurrency: int = 3):
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_batch(self, items: List[Any], processor: Callable) -> List[Any]:
        """Process items in batches with concurrency control."""
        results = []
        
        for batch in self._chunk_items(items, self.batch_size):
            async with self.semaphore:
                batch_results = await asyncio.gather(*[
                    processor(item) for item in batch
                ], return_exceptions=True)
                
                results.extend(batch_results)
        
        return results
```

## Deployment Architecture

### Docker Configuration

```dockerfile
# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

FROM python:3.11-slim as runtime

# Copy virtual environment from builder
COPY --from=builder /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Copy application code
COPY blackcore/ /app/blackcore/
COPY scripts/ /app/scripts/

WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m blackcore.minimal --help || exit 1

# Default command
CMD ["python", "-m", "blackcore.minimal"]
```

### Environment Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  blackcore:
    build: .
    environment:
      - BLACKCORE_MASTER_KEY=${BLACKCORE_MASTER_KEY}
      - NOTION_API_KEY=${NOTION_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

### Monitoring & Observability

```python
# Structured logging configuration
import structlog

logger = structlog.get_logger()

class ProcessingMetrics:
    """Metrics collection for monitoring."""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self.gauges = defaultdict(float)
    
    def increment(self, metric: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        key = self._make_key(metric, labels or {})
        self.counters[key] += value
    
    def observe(self, metric: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation."""
        key = self._make_key(metric, labels or {})
        self.histograms[key].append(value)
    
    def set_gauge(self, metric: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value."""
        key = self._make_key(metric, labels or {})
        self.gauges[key] = value
```

## Conclusion

The Blackcore architecture represents a comprehensive, production-ready system for intelligence processing and knowledge graph creation. Key architectural strengths include:

1. **Layered Architecture**: Clear separation of concerns with well-defined boundaries
2. **Security First**: Defense-in-depth with comprehensive protection mechanisms
3. **Test-Driven Design**: 686 comprehensive tests ensuring reliability
4. **Performance Optimized**: Multi-level caching and efficient batch processing
5. **Scalable Design**: Repository pattern and async operations for scalability
6. **Maintainable Code**: Type safety, clean abstractions, and comprehensive documentation

The minimal module provides a streamlined entry point while maintaining all the architectural benefits of the larger system. This design enables both rapid adoption and enterprise-grade deployment scenarios.

For implementation details and usage examples, refer to the [CLAUDE.md](CLAUDE.md) development guide and the comprehensive test suite in `blackcore/minimal/tests/`.