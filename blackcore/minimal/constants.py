"""Constants for the minimal module."""

# Rate limiting constants
DEFAULT_RATE_LIMIT = 3.0  # requests per second

# Notion client constants
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_POOL_CONNECTIONS = 10
DEFAULT_POOL_MAXSIZE = 10
CONNECT_TIMEOUT = 10.0  # seconds
READ_TIMEOUT = 60.0  # seconds
NOTION_API_VERSION = "2022-06-28"

# Cache constants
DEFAULT_CACHE_TTL = 3600  # 1 hour in seconds
CACHE_FILE_PERMISSIONS = 0o600  # -rw-------
CACHE_DIR_PERMISSIONS = 0o700   # drwx------

# AI provider constants
CLAUDE_DEFAULT_MODEL = "claude-3-sonnet-20240229"
OPENAI_DEFAULT_MODEL = "gpt-4"
AI_MAX_TOKENS = 4000
AI_TEMPERATURE = 0.3

# Configuration constants
DEFAULT_BATCH_SIZE = 10
DEDUPLICATION_THRESHOLD = 90.0
LLM_SCORER_TEMPERATURE = 0.1
LLM_SCORER_BATCH_SIZE = 5

# API key validation constants
NOTION_KEY_PREFIX = "secret_"
NOTION_KEY_LENGTH = 43
ANTHROPIC_KEY_PREFIX = "sk-ant-"
ANTHROPIC_KEY_LENGTH = 95
OPENAI_KEY_PREFIX = "sk-"
OPENAI_KEY_LENGTH = 48

# HTTP status codes
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIMEOUT = 504

# Retry strategy constants
RETRY_TOTAL_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 1
RETRY_STATUS_FORCELIST = [
    HTTP_TOO_MANY_REQUESTS,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_GATEWAY_TIMEOUT,
]

# Prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    "\n\nHuman:",
    "\n\nAssistant:",
    "\n\nSystem:",
    "\n\nUser:",
    "\n\nAI:",
]

# Notion API limits
NOTION_TEXT_LIMIT = 2000
NOTION_ARRAY_LIMIT = 100
NOTION_PAGE_SIZE_LIMIT = 100