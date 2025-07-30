"""Transcript test fixtures."""

from datetime import datetime
from blackcore.minimal.models import TranscriptInput, TranscriptSource

# Simple transcript with basic entities
SIMPLE_TRANSCRIPT = TranscriptInput(
    title="Meeting with John Doe",
    content="""Had a meeting with John Doe from ACME Corp today. 
    He mentioned they're working on a new project called Project Phoenix.
    We should follow up next week about the contract details.""",
    source=TranscriptSource.VOICE_MEMO,
    date=datetime(2025, 1, 9, 14, 30),
)

# Complex transcript with many entities and relationships
COMPLEX_TRANSCRIPT = TranscriptInput(
    title="Board Meeting - Q1 Planning",
    content="""Board meeting attendees: John Smith (CEO), Jane Doe (CFO), 
    Bob Johnson (CTO) from TechCorp Inc.
    
    Key decisions:
    1. Approved budget for Project Alpha ($2M)
    2. Jane will lead the financial review by March 15
    3. Bob mentioned security breach at competitor DataSoft last week
    4. Meeting scheduled at NYC headquarters on Jan 20
    
    Action items:
    - John to review contracts with Legal team
    - Jane to prepare Q1 forecast
    - Bob to conduct security audit
    
    Note: Concerns raised about competitor's unethical practices regarding 
    customer data handling. Need to ensure our compliance is bulletproof.""",
    source=TranscriptSource.GOOGLE_MEET,
    date=datetime(2025, 1, 8, 10, 0),
)

# Edge case transcript - empty content
EMPTY_TRANSCRIPT = TranscriptInput(
    title="Empty Note",
    content="",
    source=TranscriptSource.PERSONAL_NOTE,
    date=datetime(2025, 1, 9),
)

# Edge case transcript - very long content
LARGE_TRANSCRIPT = TranscriptInput(
    title="Annual Report Summary",
    content="This is a very long transcript. " * 1000,  # ~30KB of text
    source=TranscriptSource.EXTERNAL_SOURCE,
    date=datetime(2025, 1, 1),
)

# Edge case transcript - special characters and unicode
SPECIAL_CHARS_TRANSCRIPT = TranscriptInput(
    title="International Meeting 🌍",
    content="""Meeting with François Müller from Zürich.
    Discussed €1M investment opportunity.
    他说中文很好。(He speaks Chinese well)
    Email: françois@example.com
    Phone: +41-76-123-4567
    
    Special chars test: <script>alert('test')</script>
    SQL test: '; DROP TABLE users; --
    Path test: ../../../etc/passwd""",
    source=TranscriptSource.VOICE_MEMO,
    date=datetime(2025, 1, 10),
)

# Transcript that should trigger errors
ERROR_TRANSCRIPT = TranscriptInput(
    title="A" * 300,  # Title too long
    content="Content with null bytes: \x00\x01\x02",
    source=TranscriptSource.PERSONAL_NOTE,
    date=datetime(2025, 1, 11),
)

# List of all test transcripts
TEST_TRANSCRIPTS = [
    SIMPLE_TRANSCRIPT,
    COMPLEX_TRANSCRIPT,
    EMPTY_TRANSCRIPT,
    SPECIAL_CHARS_TRANSCRIPT,
]

# Batch processing test data
BATCH_TRANSCRIPTS = [
    TranscriptInput(
        title=f"Transcript {i}",
        content=f"This is test transcript number {i} with person Person{i} from Org{i}",
        source=TranscriptSource.VOICE_MEMO,
        date=datetime(2025, 1, i % 28 + 1),
    )
    for i in range(1, 11)
]
