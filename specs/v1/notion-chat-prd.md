# Product Requirements Document: Agentic Implementation of Notion Chat System

## Executive Summary

### Product Vision
Create an AI-powered coding agent that autonomously implements a complete WhatsApp-like chat system within Notion, following Test-Driven Development principles and best practices.

### Project Scope
The agent will:
- Design and implement Notion database schemas
- Create Python automation scripts
- Build real-time synchronization features
- Generate comprehensive test suites
- Document the entire system

### Success Criteria
- Fully functional 2-user chat system in Notion
- 95%+ test coverage
- Zero manual intervention required post-deployment
- Complete implementation in under 4 hours

## System Overview

### What the Agent Must Build

```
┌─────────────────────────────────────────────────┐
│             Notion Chat System                   │
├─────────────────────────────────────────────────┤
│  Components:                                    │
│  • 2 Notion Databases (Users, Messages)        │
│  • Python Setup Script                          │
│  • Background Monitor Service                   │
│  • Read/Unread Status Tracking                  │
│  • Automated Test Suite                         │
└─────────────────────────────────────────────────┘
```

### Agent Capabilities Required
1. **Notion API Mastery**: Full understanding of Notion's API capabilities and limitations
2. **TDD Implementation**: Write tests before code
3. **Python Development**: Clean, maintainable Python code
4. **System Design**: Architect scalable solutions
5. **Error Handling**: Robust failure recovery

## Detailed Requirements

### Phase 1: Test-Driven Database Design

#### 1.1 User Database Requirements

```python
# The agent should generate these tests first:

# test_notion_schema.py
class TestUserDatabaseSchema:
    def test_user_database_has_required_properties(self):
        """Test that user database has all required properties"""
        schema = NotionSchemaValidator()
        user_db_schema = {
            "title": "Chat Users",
            "properties": {
                "Name": {"type": "title"},
                "Status": {"type": "select", "options": ["🟢 Online", "⚫ Offline"]},
                "Last Seen": {"type": "date"},
                "Email": {"type": "email"}
            }
        }
        assert schema.validate_database_schema(user_db_schema) == True
    
    def test_user_database_supports_two_users(self):
        """Test that exactly 2 users can be created"""
        db = MockNotionDatabase()
        user1 = db.create_user("User 1", "user1@example.com")
        user2 = db.create_user("User 2", "user2@example.com")
        
        assert db.user_count() == 2
        assert db.get_user(user1.id).name == "User 1"
        assert db.get_user(user2.id).name == "User 2"
```

#### 1.2 Message Database Requirements

```python
# test_message_database.py
class TestMessageDatabaseSchema:
    def test_message_database_schema(self):
        """Test message database has required properties"""
        schema = NotionSchemaValidator()
        message_db_schema = {
            "title": "Chat Messages",
            "properties": {
                "Message": {"type": "title"},
                "Sender": {"type": "relation", "database_id": "users_db"},
                "Timestamp": {"type": "date"},
                "User 1 Read": {"type": "checkbox"},
                "User 2 Read": {"type": "checkbox"},
                "Read Status": {"type": "select"}
            }
        }
        assert schema.validate_database_schema(message_db_schema) == True
    
    def test_message_timestamp_auto_generation(self):
        """Test that messages get automatic timestamps"""
        db = MockNotionDatabase()
        message = db.create_message("Hello", sender_id="user1")
        
        assert message.timestamp is not None
        assert (datetime.now() - message.timestamp).seconds < 1
```

### Phase 2: Core Functionality Tests

#### 2.1 Message Sending Tests

```python
# test_message_operations.py
class TestMessageOperations:
    def test_send_simple_message(self):
        """Test sending a basic text message"""
        chat = NotionChat(test_mode=True)
        user1_id = "test_user_1"
        
        message_id = chat.send_message(
            content="Hello, World!",
            sender_id=user1_id
        )
        
        assert message_id is not None
        message = chat.get_message(message_id)
        assert message.content == "Hello, World!"
        assert message.sender_id == user1_id
    
    def test_message_appears_in_both_user_views(self):
        """Test that sent messages are visible to both users"""
        chat = NotionChat(test_mode=True)
        user1_id, user2_id = chat.get_user_ids()
        
        message_id = chat.send_message("Test message", user1_id)
        
        user1_messages = chat.get_messages(user1_id)
        user2_messages = chat.get_messages(user2_id)
        
        assert any(m.id == message_id for m in user1_messages)
        assert any(m.id == message_id for m in user2_messages)
    
    def test_message_ordering(self):
        """Test messages appear in chronological order"""
        chat = NotionChat(test_mode=True)
        user1_id, user2_id = chat.get_user_ids()
        
        # Send messages with delays
        msg1 = chat.send_message("First", user1_id)
        time.sleep(0.1)
        msg2 = chat.send_message("Second", user2_id)
        time.sleep(0.1)
        msg3 = chat.send_message("Third", user1_id)
        
        messages = chat.get_messages()
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"
```

#### 2.2 Read Status Tests

```python
# test_read_status.py
class TestReadStatus:
    def test_message_initially_unread(self):
        """Test new messages are unread by default"""
        chat = NotionChat(test_mode=True)
        user1_id, user2_id = chat.get_user_ids()
        
        message_id = chat.send_message("New message", user1_id)
        message = chat.get_message(message_id)
        
        assert message.is_read_by(user1_id) == True  # Sender has read
        assert message.is_read_by(user2_id) == False  # Recipient hasn't
    
    def test_mark_message_as_read(self):
        """Test marking messages as read"""
        chat = NotionChat(test_mode=True)
        user1_id, user2_id = chat.get_user_ids()
        
        message_id = chat.send_message("Test", user1_id)
        chat.mark_as_read(message_id, user2_id)
        
        message = chat.get_message(message_id)
        assert message.is_read_by(user2_id) == True
        assert message.read_status == "✓✓ Read"
    
    def test_unread_message_count(self):
        """Test counting unread messages for each user"""
        chat = NotionChat(test_mode=True)
        user1_id, user2_id = chat.get_user_ids()
        
        # User 1 sends 3 messages
        for i in range(3):
            chat.send_message(f"Message {i}", user1_id)
        
        assert chat.get_unread_count(user2_id) == 3
        assert chat.get_unread_count(user1_id) == 0
```

### Phase 3: Integration Tests

#### 3.1 Notion API Integration Tests

```python
# test_notion_integration.py
class TestNotionIntegration:
    @pytest.mark.integration
    def test_create_actual_notion_database(self):
        """Test creating real Notion database"""
        setup = NotionChatSetup(
            token=os.getenv("NOTION_TEST_TOKEN"),
            parent_page_id=os.getenv("NOTION_TEST_PAGE")
        )
        
        result = setup.create_users_database()
        assert result.database_id is not None
        assert result.database_url.startswith("https://notion.so")
    
    @pytest.mark.integration
    def test_rate_limiting_compliance(self):
        """Test that we stay within Notion's rate limits"""
        chat = NotionChat()
        start_time = time.time()
        request_count = 0
        
        # Attempt 10 rapid requests
        for _ in range(10):
            chat.send_message("Test", "user1")
            request_count += 1
        
        elapsed = time.time() - start_time
        requests_per_second = request_count / elapsed
        
        assert requests_per_second < 3.0  # Notion limit
```

#### 3.2 Background Monitor Tests

```python
# test_background_monitor.py
class TestBackgroundMonitor:
    def test_monitor_updates_read_status(self):
        """Test background monitor updates read status"""
        chat = NotionChat(test_mode=True)
        monitor = NotionChatMonitor(chat)
        
        # Send message
        user1_id, user2_id = chat.get_user_ids()
        msg_id = chat.send_message("Test", user1_id)
        
        # Simulate user 2 checking the box
        chat._simulate_checkbox_update(msg_id, "User 2 Read", True)
        
        # Run monitor cycle
        monitor.update_read_status()
        
        # Verify status updated
        message = chat.get_message(msg_id)
        assert message.read_status == "✓✓ Read"
    
    @pytest.mark.asyncio
    async def test_monitor_polling_interval(self):
        """Test monitor polls at correct intervals"""
        monitor = NotionChatMonitor(poll_interval=2)
        call_times = []
        
        def track_call():
            call_times.append(time.time())
        
        monitor.update_callback = track_call
        
        # Run for 6 seconds
        task = asyncio.create_task(monitor.start())
        await asyncio.sleep(6)
        monitor.stop()
        
        # Should have ~3 calls
        assert 2 <= len(call_times) <= 4
        
        # Check intervals
        intervals = [call_times[i+1] - call_times[i] 
                    for i in range(len(call_times)-1)]
        assert all(1.5 < interval < 2.5 for interval in intervals)
```

### Phase 4: Performance & Reliability Tests

#### 4.1 Performance Tests

```python
# test_performance.py
class TestPerformance:
    def test_message_retrieval_performance(self):
        """Test message retrieval stays fast with many messages"""
        chat = NotionChat(test_mode=True)
        user1_id, user2_id = chat.get_user_ids()
        
        # Create 100 messages
        for i in range(100):
            chat.send_message(f"Message {i}", 
                            user1_id if i % 2 == 0 else user2_id)
        
        # Time retrieval
        start = time.time()
        messages = chat.get_messages(limit=50)
        elapsed = time.time() - start
        
        assert len(messages) == 50
        assert elapsed < 1.0  # Should be under 1 second
    
    def test_caching_reduces_api_calls(self):
        """Test that caching effectively reduces API calls"""
        chat = NotionChat(test_mode=True, enable_cache=True)
        
        # First call - hits API
        api_calls_before = chat.get_api_call_count()
        messages1 = chat.get_messages()
        api_calls_after1 = chat.get_api_call_count()
        
        assert api_calls_after1 > api_calls_before
        
        # Second call - should use cache
        messages2 = chat.get_messages()
        api_calls_after2 = chat.get_api_call_count()
        
        assert api_calls_after2 == api_calls_after1
        assert messages1 == messages2
```

#### 4.2 Error Handling Tests

```python
# test_error_handling.py
class TestErrorHandling:
    def test_handle_notion_api_errors(self):
        """Test graceful handling of Notion API errors"""
        chat = NotionChat(test_mode=True)
        
        # Simulate API error
        with patch('notion_client.Client.pages.create') as mock_create:
            mock_create.side_effect = APIResponseError(
                "Rate limit exceeded"
            )
            
            result = chat.send_message("Test", "user1")
            assert result.success == False
            assert result.retry_after > 0
    
    def test_handle_network_failures(self):
        """Test handling of network failures"""
        chat = NotionChat(test_mode=True)
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = ConnectionError()
            
            # Should not crash
            result = chat.send_message("Test", "user1")
            assert result.success == False
            assert result.error_type == "network"
    
    def test_data_consistency_on_partial_failure(self):
        """Test data remains consistent during partial failures"""
        chat = NotionChat(test_mode=True)
        
        # Start a multi-step operation
        with chat.transaction() as tx:
            msg1 = tx.send_message("First", "user1")
            
            # Simulate failure
            with patch('notion_client.Client.pages.create') as mock:
                mock.side_effect = Exception("Failed")
                
                # This should rollback entire transaction
                with pytest.raises(TransactionError):
                    tx.send_message("Second", "user2")
        
        # Verify first message was rolled back
        messages = chat.get_messages()
        assert not any(m.content == "First" for m in messages)
```

## Implementation Specification for Agent

### Stage 1: Environment Setup (Generated by Agent)

```python
# setup_project.py - Generated by agent
"""
Project setup script for Notion Chat implementation
Generated by: AgenticCoder v1.0
"""

import os
import subprocess
from pathlib import Path

class ProjectSetup:
    def __init__(self):
        self.project_root = Path.cwd() / "notion-chat"
        
    def create_structure(self):
        """Create project directory structure"""
        directories = [
            "src",
            "tests/unit",
            "tests/integration", 
            "tests/e2e",
            "config",
            "docs"
        ]
        
        for directory in directories:
            (self.project_root / directory).mkdir(parents=True, exist_ok=True)
    
    def create_requirements(self):
        """Generate requirements.txt"""
        requirements = """
notion-client==2.2.1
pytest==7.4.0
pytest-asyncio==0.21.0
pytest-mock==3.11.1
python-dotenv==1.0.0
tenacity==8.2.2
pydantic==2.0.0
        """.strip()
        
        (self.project_root / "requirements.txt").write_text(requirements)
    
    def create_env_template(self):
        """Create .env.template file"""
        template = """
# Notion API Configuration
NOTION_TOKEN=your_notion_integration_token
NOTION_PARENT_PAGE_ID=your_parent_page_id

# Test Configuration
NOTION_TEST_TOKEN=your_test_token
NOTION_TEST_PAGE_ID=your_test_page_id

# Generated IDs (filled by setup script)
USERS_DB_ID=
MESSAGES_DB_ID=
USER1_ID=
USER2_ID=
        """.strip()
        
        (self.project_root / ".env.template").write_text(template)
```

### Stage 2: Core Implementation Plan

```yaml
# implementation_plan.yaml - Generated by agent
implementation_phases:
  phase_1:
    name: "Test Infrastructure"
    duration: "30 minutes"
    tasks:
      - Create base test fixtures
      - Implement mock Notion client
      - Set up test database schemas
      - Create assertion helpers
    
  phase_2:
    name: "Database Layer"
    duration: "45 minutes"
    tasks:
      - Implement NotionDatabaseManager
      - Create schema validation
      - Build CRUD operations
      - Add relationship handling
    
  phase_3:
    name: "Chat Logic"
    duration: "60 minutes"
    tasks:
      - Implement message sending
      - Build read status tracking
      - Create user management
      - Add message retrieval
    
  phase_4:
    name: "Background Services"
    duration: "45 minutes"
    tasks:
      - Build monitor service
      - Implement status updater
      - Add polling mechanism
      - Create health checks
    
  phase_5:
    name: "Integration & Polish"
    duration: "60 minutes"
    tasks:
      - Connect all components
      - Add error handling
      - Implement caching
      - Create CLI interface
```

### Stage 3: Test Generation Strategy

```python
# test_generation_strategy.py
class TestGenerationStrategy:
    """Strategy for generating comprehensive test suite"""
    
    def __init__(self, agent):
        self.agent = agent
        self.test_categories = [
            "schema_validation",
            "crud_operations",
            "message_flow",
            "read_status",
            "error_handling",
            "performance",
            "integration"
        ]
    
    def generate_test_file(self, category: str) -> str:
        """Generate test file for a category"""
        template = f"""
# test_{category}.py
# Generated by AgenticCoder
# Category: {category}
# Coverage Target: 95%

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.notion_chat import NotionChat
from src.models import Message, User
from src.exceptions import *

class Test{category.title().replace('_', '')}:
    '''Comprehensive tests for {category.replace('_', ' ')}'''
    
    @pytest.fixture
    def chat_instance(self):
        '''Fixture providing clean chat instance'''
        return NotionChat(test_mode=True)
    
    # Agent will generate specific tests here based on category
    {self._generate_category_tests(category)}
"""
        return template
```

## Agent Execution Workflow

### 1. Pre-Implementation Analysis
```python
# The agent should execute this workflow:

def analyze_requirements():
    """Agent analyzes PRD and creates implementation plan"""
    steps = [
        "Parse PRD requirements",
        "Identify Notion API constraints",
        "Design optimal architecture",
        "Create test scenarios",
        "Generate implementation timeline"
    ]
    return ImplementationPlan(steps)
```

### 2. TDD Implementation Loop
```python
def tdd_implementation_loop():
    """Agent's TDD implementation process"""
    while not all_requirements_met():
        # 1. Write failing test
        test = generate_next_test()
        run_test(test)  # Verify it fails
        
        # 2. Write minimal code to pass
        implementation = generate_implementation(test)
        
        # 3. Run test again
        result = run_test(test)
        assert result.passed
        
        # 4. Refactor if needed
        if needs_refactoring(implementation):
            refactored = refactor_code(implementation)
            assert run_test(test).passed
        
        # 5. Commit progress
        commit_changes(test, implementation)
```

### 3. Integration Testing
```python
def integration_testing_phase():
    """Agent performs integration testing"""
    # Test with real Notion API
    # Verify all components work together
    # Performance testing
    # Error scenario testing
```

## Success Metrics for Agent

### Code Quality Metrics
- **Test Coverage**: >= 95%
- **Code Complexity**: Cyclomatic complexity < 10
- **Documentation**: 100% of public methods documented
- **Type Hints**: 100% type coverage

### Functional Metrics
- **All Tests Pass**: 100% pass rate
- **API Compliance**: No rate limit violations
- **Error Handling**: All edge cases covered
- **Performance**: < 100ms average response time

### Implementation Metrics
- **Time to Complete**: < 4 hours
- **Human Interventions**: 0
- **Bugs Found Post-Implementation**: < 2

## Agent Constraints & Guidelines

### Must Follow
1. **TDD Strictly**: Never write code without a test
2. **Notion API Limits**: Stay within rate limits
3. **Python Best Practices**: PEP 8, type hints
4. **Error Handling**: Never let exceptions bubble up
5. **Documentation**: Docstrings for all functions

### Must Avoid
1. **Over-Engineering**: Keep it simple for 2 users
2. **Premature Optimization**: Focus on working first
3. **Complex Dependencies**: Use standard library when possible
4. **Tight Coupling**: Keep components modular
5. **Security Risks**: No hardcoded credentials

## Deliverables Expected from Agent

### 1. Complete Codebase
```
notion-chat/
├── src/
│   ├── __init__.py
│   ├── notion_chat.py
│   ├── models.py
│   ├── database.py
│   ├── monitor.py
│   └── utils.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── config/
│   └── settings.py
├── docs/
│   ├── setup.md
│   ├── usage.md
│   └── api.md
├── requirements.txt
├── setup.py
├── README.md
└── .env.template
```

### 2. Documentation
- Setup instructions
- API documentation
- Architecture diagrams
- Test coverage reports

### 3. Deployment Scripts
- One-click setup script
- Database initialization
- Monitor service setup
- Health check endpoints

## Agent Learning Objectives

Through implementing this project, the agent should:

1. **Master Notion API**: Understand capabilities and limitations
2. **Practice TDD**: Write tests first, always
3. **Handle Real-world Constraints**: Rate limits, API quirks
4. **Build Maintainable Code**: Clean, documented, tested
5. **Create User-Friendly Systems**: Easy setup and usage

## Appendix: Sample Test Output

```bash
# Expected test output from agent's implementation
$ pytest -v

tests/unit/test_schema_validation.py::test_user_database_schema PASSED
tests/unit/test_schema_validation.py::test_message_database_schema PASSED
tests/unit/test_message_operations.py::test_send_simple_message PASSED
tests/unit/test_message_operations.py::test_message_ordering PASSED
tests/unit/test_read_status.py::test_message_initially_unread PASSED
tests/unit/test_read_status.py::test_mark_message_as_read PASSED
tests/integration/test_notion_integration.py::test_create_database PASSED
tests/integration/test_notion_integration.py::test_rate_limiting PASSED
tests/e2e/test_full_chat_flow.py::test_complete_conversation PASSED

========================= 45 passed in 12.34s ==========================

Coverage report:
Name                     Stmts   Miss  Cover
--------------------------------------------
src/notion_chat.py         234      8    97%
src/models.py               56      0   100%
src/database.py            123      4    97%
src/monitor.py              89      3    97%
src/utils.py                34      0   100%
--------------------------------------------
TOTAL                      536     15    97%
```

This PRD provides a comprehensive guide for an agentic coding tool to implement the Notion Chat system using TDD principles, with clear requirements, test scenarios, and success metrics.
