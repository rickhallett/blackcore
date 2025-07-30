"""AI provider response fixtures."""

import json
from typing import Dict, Any

# Claude successful response
CLAUDE_RESPONSE_SUCCESS = {
    "content": [
        {
            "type": "text",
            "text": json.dumps(
                {
                    "entities": [
                        {
                            "name": "John Doe",
                            "type": "person",
                            "properties": {"role": "CEO", "company": "ACME Corp"},
                            "context": "Meeting attendee",
                            "confidence": 0.95,
                        },
                        {
                            "name": "ACME Corp",
                            "type": "organization",
                            "properties": {"industry": "Technology"},
                            "context": "John Doe's company",
                            "confidence": 0.9,
                        },
                        {
                            "name": "Project Phoenix",
                            "type": "task",
                            "properties": {
                                "status": "In Progress",
                                "owner": "John Doe",
                            },
                            "context": "New project mentioned",
                            "confidence": 0.85,
                        },
                    ],
                    "relationships": [
                        {
                            "source_entity": "John Doe",
                            "source_type": "person",
                            "target_entity": "ACME Corp",
                            "target_type": "organization",
                            "relationship_type": "works_for",
                            "context": "CEO of the company",
                        }
                    ],
                }
            ),
        }
    ]
}

# OpenAI successful response
OPENAI_RESPONSE_SUCCESS = {
    "choices": [
        {
            "message": {
                "content": json.dumps(
                    {
                        "entities": [
                            {
                                "name": "Jane Smith",
                                "type": "person",
                                "properties": {"role": "CFO"},
                                "confidence": 0.92,
                            },
                            {
                                "name": "TechCorp Inc",
                                "type": "organization",
                                "properties": {"type": "Corporation"},
                                "confidence": 0.88,
                            },
                        ],
                        "relationships": [],
                    }
                )
            }
        }
    ]
}

# Malformed JSON response
MALFORMED_JSON_RESPONSE = {
    "content": [
        {"type": "text", "text": "Here are the entities I found: {invalid json"}
    ]
}

# Response with markdown formatting
MARKDOWN_RESPONSE = {
    "content": [
        {
            "type": "text",
            "text": """I'll extract the entities from the transcript.

```json
{
    "entities": [
        {
            "name": "Bob Johnson",
            "type": "person",
            "properties": {"title": "CTO"},
            "confidence": 0.9
        }
    ],
    "relationships": []
}
```

The main entity found was Bob Johnson who serves as CTO.""",
        }
    ]
}

# Empty extraction response
EMPTY_EXTRACTION_RESPONSE = {
    "content": [
        {"type": "text", "text": json.dumps({"entities": [], "relationships": []})}
    ]
}

# Rate limit error from AI provider
AI_RATE_LIMIT_ERROR = {
    "error": {
        "type": "rate_limit_error",
        "message": "Rate limit exceeded. Please try again later.",
    }
}

# Token limit exceeded error
TOKEN_LIMIT_ERROR = {
    "error": {
        "type": "invalid_request_error",
        "message": "This model's maximum context length is 100000 tokens.",
    }
}

# Complex extraction with all entity types
COMPLEX_EXTRACTION_RESPONSE = {
    "content": [
        {
            "type": "text",
            "text": json.dumps(
                {
                    "entities": [
                        {
                            "name": "John Smith",
                            "type": "person",
                            "properties": {
                                "role": "CEO",
                                "email": "john@techcorp.com",
                                "phone": "+1-555-0001",
                            },
                            "confidence": 0.95,
                        },
                        {
                            "name": "TechCorp Inc",
                            "type": "organization",
                            "properties": {"type": "Corporation", "location": "NYC"},
                            "confidence": 0.93,
                        },
                        {
                            "name": "Q1 Board Meeting",
                            "type": "event",
                            "properties": {
                                "date": "2025-01-20",
                                "location": "NYC headquarters",
                            },
                            "confidence": 0.88,
                        },
                        {
                            "name": "Financial Review",
                            "type": "task",
                            "properties": {
                                "assignee": "Jane Doe",
                                "due_date": "2025-03-15",
                            },
                            "confidence": 0.9,
                        },
                        {
                            "name": "Data Privacy Violation",
                            "type": "transgression",
                            "properties": {
                                "severity": "High",
                                "organization": "DataSoft",
                            },
                            "confidence": 0.85,
                        },
                        {
                            "name": "Q1 Forecast Document",
                            "type": "document",
                            "properties": {
                                "type": "Financial Report",
                                "owner": "Jane Doe",
                            },
                            "confidence": 0.82,
                        },
                        {
                            "name": "NYC headquarters",
                            "type": "place",
                            "properties": {
                                "address": "123 Tech Avenue, NYC",
                                "type": "Office",
                            },
                            "confidence": 0.87,
                        },
                    ],
                    "relationships": [
                        {
                            "source_entity": "John Smith",
                            "source_type": "person",
                            "target_entity": "TechCorp Inc",
                            "target_type": "organization",
                            "relationship_type": "ceo_of",
                        },
                        {
                            "source_entity": "Financial Review",
                            "source_type": "task",
                            "target_entity": "Jane Doe",
                            "target_type": "person",
                            "relationship_type": "assigned_to",
                        },
                        {
                            "source_entity": "Q1 Board Meeting",
                            "source_type": "event",
                            "target_entity": "NYC headquarters",
                            "target_type": "place",
                            "relationship_type": "located_at",
                        },
                    ],
                }
            ),
        }
    ]
}


def create_mock_ai_response(
    entities: list, relationships: list = None
) -> Dict[str, Any]:
    """Create a mock AI response with custom entities."""
    content = {"entities": entities, "relationships": relationships or []}

    return {"content": [{"type": "text", "text": json.dumps(content)}]}


def create_mock_error_response(error_type: str, message: str) -> Dict[str, Any]:
    """Create a mock AI error response."""
    return {"error": {"type": error_type, "message": message}}
