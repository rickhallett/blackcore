"""High-ROI test infrastructure for comprehensive validation.

Provides practical utilities for testing with minimal complexity and maximum value.
"""

import json
import time
import random
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Callable
from unittest.mock import Mock, patch, MagicMock

from blackcore.minimal.models import (
    TranscriptInput, Config, NotionConfig, AIConfig, 
    ProcessingConfig, DatabaseConfig, EntityType
)
from blackcore.minimal.transcript_processor import TranscriptProcessor


@dataclass
class TestMetrics:
    """Simple performance metrics collection."""
    start_time: float
    end_time: Optional[float] = None
    memory_peak: Optional[int] = None
    operations_count: int = 0
    errors_count: int = 0
    
    @property
    def duration(self) -> float:
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        if self.operations_count == 0:
            return 1.0
        return (self.operations_count - self.errors_count) / self.operations_count


class RealisticDataGenerator:
    """Generates realistic test data for high-value testing."""
    
    def __init__(self):
        self.names = [
            "Sarah Johnson", "Mike Chen", "Dr. Elizabeth Smith", "Robert Martinez",
            "Jennifer Wong", "David Kim", "Lisa Rodriguez", "James Wilson",
            "Maria Garcia", "Kevin O'Brien", "Amanda Taylor", "Brian Davis"
        ]
        
        self.organizations = [
            "TechCorp Industries", "Green Valley Hospital", "City Planning Commission",
            "DataFlow Solutions", "Riverside Community Center", "Metro Construction",
            "Blue Mountain Consulting", "Central Bank", "Westside Medical Group"
        ]
        
        self.places = [
            "Main Conference Room", "City Hall", "Building A - Floor 3", 
            "Remote via Zoom", "Client Office", "Project Site", "Board Room"
        ]
        
        self.transcript_templates = [
            self._meeting_template,
            self._interview_template,
            self._planning_session_template,
            self._status_update_template,
        ]
    
    def generate_transcript(self, complexity: str = "medium") -> TranscriptInput:
        """Generate a realistic transcript with controlled complexity."""
        template = random.choice(self.transcript_templates)
        
        complexity_params = {
            "simple": {"entities": 2, "relationships": 1, "length": "short"},
            "medium": {"entities": 5, "relationships": 3, "length": "medium"},
            "complex": {"entities": 8, "relationships": 6, "length": "long"},
        }
        
        params = complexity_params.get(complexity, complexity_params["medium"])
        return template(params)
    
    def generate_batch(self, count: int, complexity: str = "medium") -> List[TranscriptInput]:
        """Generate a batch of realistic transcripts."""
        return [self.generate_transcript(complexity) for _ in range(count)]
    
    def _meeting_template(self, params: Dict[str, Any]) -> TranscriptInput:
        """Generate a realistic meeting transcript."""
        attendees = random.sample(self.names, min(params["entities"], len(self.names)))
        organization = random.choice(self.organizations)
        location = random.choice(self.places)
        
        # Create realistic meeting content
        content_parts = [
            f"Meeting held at {location}",
            f"Attendees: {', '.join(attendees)}",
            "",
            "Discussion Topics:",
        ]
        
        # Add discussion points based on complexity
        discussion_points = [
            f"Budget review led by {attendees[0]}",
            f"Project timeline discussed with {attendees[1] if len(attendees) > 1 else attendees[0]}",
            f"Risk assessment requested from {organization}",
            f"Next steps assigned to {attendees[-1]}",
        ]
        
        content_parts.extend(discussion_points[:params["entities"]])
        
        # Add action items
        if params["relationships"] > 0:
            content_parts.extend([
                "",
                "Action Items:", 
                f"- {attendees[0]} to complete analysis by next Friday",
                f"- Follow up meeting scheduled with {organization}",
            ])
        
        return TranscriptInput(
            title=f"Meeting - {organization} Planning Session",
            content="\n".join(content_parts),
            date=datetime.now() - timedelta(days=random.randint(0, 30)),
            metadata={
                "source": "google_meet",
                "duration": "45 minutes",
                "location": location,
                "complexity": params
            }
        )
    
    def _interview_template(self, params: Dict[str, Any]) -> TranscriptInput:
        """Generate a realistic interview transcript."""
        interviewer = random.choice(self.names)
        interviewee = random.choice([n for n in self.names if n != interviewer])
        organization = random.choice(self.organizations)
        
        content = f"""Interview conducted by {interviewer} with {interviewee}
Organization: {organization}

Q: Can you tell us about the current project status?
A: We've made significant progress. The main deliverables are on track.

Q: What are the main challenges you're facing?
A: Resource allocation and timeline coordination with {organization}.

Q: Who else is involved in this project?
A: We're working closely with the team at {organization}.

Action Items:
- Follow up on resource requirements
- Schedule coordination meeting
- Review project timeline
"""
        
        return TranscriptInput(
            title=f"Interview - {interviewee} Project Update",
            content=content,
            date=datetime.now() - timedelta(days=random.randint(0, 15)),
            metadata={
                "source": "personal_note",
                "type": "interview",
                "participants": [interviewer, interviewee],
                "complexity": params
            }
        )
    
    def _planning_session_template(self, params: Dict[str, Any]) -> TranscriptInput:
        """Generate a realistic planning session transcript."""
        participants = random.sample(self.names, min(3, len(self.names)))
        organization = random.choice(self.organizations)
        
        content = f"""Planning Session - {organization}
Participants: {', '.join(participants)}

Current Status:
- Project is 60% complete
- Budget is on track
- Timeline needs adjustment

Key Discussion Points:
1. Resource allocation for Q2
2. Risk mitigation strategies
3. Stakeholder communication plan

Decisions Made:
- {participants[0]} will lead the next phase
- Weekly check-ins scheduled
- Budget review in 2 weeks

Next Steps:
- Prepare detailed timeline by {participants[1]}
- Risk assessment due next Monday
- Stakeholder update meeting scheduled
"""
        
        return TranscriptInput(
            title=f"Planning Session - {organization}",
            content=content,
            date=datetime.now() - timedelta(days=random.randint(0, 7)),
            metadata={
                "source": "voice_memo",
                "type": "planning",
                "organization": organization,
                "complexity": params
            }
        )
    
    def _status_update_template(self, params: Dict[str, Any]) -> TranscriptInput:
        """Generate a realistic status update transcript."""
        presenter = random.choice(self.names)
        organization = random.choice(self.organizations)
        
        content = f"""Status Update by {presenter}
Organization: {organization}

Weekly Progress Report:

Completed This Week:
- Milestone 3 delivered on schedule
- Testing phase completed
- Documentation updated

Upcoming Tasks:
- Integration testing with {organization}
- User acceptance testing
- Deployment preparation

Blockers:
- Waiting for approval from stakeholders
- External dependency delay

Next Week's Goals:
- Complete integration testing
- Address feedback from {organization}
- Prepare for go-live
"""
        
        return TranscriptInput(
            title=f"Status Update - {presenter}",
            content=content,
            date=datetime.now() - timedelta(days=random.randint(0, 5)),
            metadata={
                "source": "personal_note",
                "type": "status_update",
                "presenter": presenter,
                "complexity": params
            }
        )


class TestEnvironmentManager:
    """Manages isolated test environments with controlled conditions."""
    
    def __init__(self):
        self.temp_dirs: List[Path] = []
        self.active_patches: List[Any] = []
        self.metrics = TestMetrics(start_time=time.time())
    
    @contextmanager
    def isolated_environment(self, config_overrides: Optional[Dict[str, Any]] = None):
        """Create an isolated test environment with mocked dependencies."""
        temp_dir = Path(tempfile.mkdtemp(prefix="comprehensive_test_"))
        self.temp_dirs.append(temp_dir)
        
        try:
            # Create test configuration
            config = self._create_test_config(temp_dir, config_overrides or {})
            
            # Set up mocked dependencies
            with self._mock_external_dependencies() as mocks:
                yield {
                    'config': config,
                    'temp_dir': temp_dir,
                    'mocks': mocks,
                    'metrics': self.metrics
                }
        finally:
            self._cleanup_temp_dir(temp_dir)
    
    def _create_test_config(self, temp_dir: Path, overrides: Dict[str, Any]) -> Config:
        """Create a test configuration with realistic defaults."""
        base_config = {
            'notion': NotionConfig(
                api_key="test-notion-key",
                databases={
                    "people": DatabaseConfig(
                        id="test-people-db",
                        name="People & Contacts",
                        mappings={
                            "name": "Full Name",
                            "email": "Email",
                            "role": "Role",
                            "company": "Organization"
                        }
                    ),
                    "organizations": DatabaseConfig(
                        id="test-org-db", 
                        name="Organizations",
                        mappings={
                            "name": "Name",
                            "type": "Type",
                            "location": "Location"
                        }
                    ),
                    "tasks": DatabaseConfig(
                        id="test-tasks-db",
                        name="Tasks", 
                        mappings={
                            "name": "Title",
                            "status": "Status",
                            "assignee": "Assigned To",
                            "due_date": "Due Date"
                        }
                    )
                }
            ),
            'ai': AIConfig(
                provider="claude",
                api_key="test-ai-key",
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.3
            ),
            'processing': ProcessingConfig(
                batch_size=10,
                cache_dir=str(temp_dir / "cache"),
                cache_ttl=3600,
                dry_run=False,
                verbose=False
            )
        }
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(base_config, key):
                setattr(base_config, key, value)
        
        return Config(**base_config)
    
    @contextmanager
    def _mock_external_dependencies(self):
        """Mock external API dependencies for controlled testing."""
        # Mock Notion client
        notion_mock = MagicMock()
        notion_mock.databases.query.return_value = {"results": [], "has_more": False}
        notion_mock.pages.create.return_value = {"id": "test-page-123", "properties": {}}
        notion_mock.pages.update.return_value = {"id": "test-page-123", "properties": {}}
        
        # Mock AI client
        ai_mock = MagicMock()
        ai_mock.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "entities": [
                    {
                        "name": "Test Person",
                        "type": "person",
                        "properties": {"role": "Test Role"},
                        "confidence": 0.9
                    }
                ],
                "relationships": []
            }))]
        )
        
        patches = [
            patch('blackcore.minimal.notion_updater.Client', return_value=notion_mock),
            patch('blackcore.minimal.ai_extractor.Anthropic', return_value=ai_mock),
        ]
        
        try:
            for p in patches:
                p.start()
                self.active_patches.append(p)
            
            yield {
                'notion_client': notion_mock,
                'ai_client': ai_mock
            }
        finally:
            for p in patches:
                try:
                    p.stop()
                except Exception:
                    pass  # Ignore cleanup errors
    
    def _cleanup_temp_dir(self, temp_dir: Path):
        """Clean up temporary directory."""
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors
    
    def cleanup_all(self):
        """Clean up all test resources."""
        # Stop all patches
        for patch in self.active_patches:
            try:
                patch.stop()
            except Exception:
                pass
        
        # Clean up temp directories
        for temp_dir in self.temp_dirs:
            self._cleanup_temp_dir(temp_dir)
        
        self.temp_dirs.clear()
        self.active_patches.clear()


class FailureSimulator:
    """Simple, practical failure simulation for high-ROI testing."""
    
    @contextmanager
    def network_failure(self, failure_rate: float = 1.0):
        """Simulate network failures with specified rate."""
        def mock_request(*args, **kwargs):
            if random.random() < failure_rate:
                import requests
                raise requests.exceptions.ConnectionError("Simulated network failure")
            return MagicMock(status_code=200, json=lambda: {"results": []})
        
        with patch('requests.request', side_effect=mock_request):
            yield
    
    @contextmanager
    def api_timeout(self, timeout_seconds: float = 1.0):
        """Simulate API timeouts."""
        def mock_request(*args, **kwargs):
            time.sleep(timeout_seconds + 0.1)  # Slightly longer than timeout
            import requests
            raise requests.exceptions.Timeout("Simulated API timeout")
        
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
        
        with patch('blackcore.minimal.notion_updater.Client') as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.databases.query.side_effect = mock_notion_query
            yield mock_instance


class PerformanceProfiler:
    """Simple performance profiling for regression detection."""
    
    def __init__(self):
        self.benchmarks: Dict[str, List[float]] = {}
    
    @contextmanager
    def profile(self, operation_name: str):
        """Profile an operation and record the timing."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation_name not in self.benchmarks:
                self.benchmarks[operation_name] = []
            self.benchmarks[operation_name].append(duration)
    
    def get_baseline(self, operation_name: str) -> Optional[float]:
        """Get the average baseline for an operation."""
        if operation_name not in self.benchmarks:
            return None
        return sum(self.benchmarks[operation_name]) / len(self.benchmarks[operation_name])
    
    def check_regression(self, operation_name: str, threshold_percent: float = 20.0) -> bool:
        """Check if recent performance is within threshold of baseline."""
        if operation_name not in self.benchmarks or len(self.benchmarks[operation_name]) < 2:
            return True  # Not enough data to check regression
        
        baseline = self.get_baseline(operation_name)
        recent = self.benchmarks[operation_name][-1]
        
        if baseline is None:
            return True
        
        regression_threshold = baseline * (1 + threshold_percent / 100)
        return recent <= regression_threshold


# Convenience functions for easy test usage
def create_realistic_transcript(complexity: str = "medium") -> TranscriptInput:
    """Create a single realistic transcript for testing."""
    return RealisticDataGenerator().generate_transcript(complexity)


def create_test_batch(size: int = 5, complexity: str = "medium") -> List[TranscriptInput]:
    """Create a batch of realistic transcripts for testing."""
    return RealisticDataGenerator().generate_batch(size, complexity)


@contextmanager
def test_environment(config_overrides: Optional[Dict[str, Any]] = None):
    """Create a complete test environment with cleanup."""
    env_manager = TestEnvironmentManager()
    try:
        with env_manager.isolated_environment(config_overrides) as env:
            yield env
    finally:
        env_manager.cleanup_all()