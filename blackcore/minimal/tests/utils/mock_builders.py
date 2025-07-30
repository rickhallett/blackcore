"""Mock builders for complex test scenarios."""

from typing import Dict, Any, List
from unittest.mock import MagicMock
import json
from datetime import datetime

from blackcore.minimal.models import (
    Entity,
    ExtractedEntities,
    Relationship,
    NotionPage,
)


class MockNotionClientBuilder:
    """Builder for creating configured mock Notion clients."""

    def __init__(self):
        self.client = MagicMock()
        self._query_results = {}
        self._create_responses = {}
        self._update_responses = {}
        self._retrieve_responses = {}
        self._errors = {}

    def with_query_results(self, database_id: str, results: List[Dict[str, Any]]):
        """Configure query results for a database."""
        self._query_results[database_id] = {"results": results, "has_more": False}
        return self

    def with_create_response(self, database_id: str, response: Dict[str, Any]):
        """Configure create response for a database."""
        self._create_responses[database_id] = response
        return self

    def with_update_response(self, page_id: str, response: Dict[str, Any]):
        """Configure update response for a page."""
        self._update_responses[page_id] = response
        return self

    def with_retrieve_response(self, database_id: str, response: Dict[str, Any]):
        """Configure retrieve response for a database."""
        self._retrieve_responses[database_id] = response
        return self

    def with_error(self, operation: str, error: Exception):
        """Configure an error for an operation."""
        self._errors[operation] = error
        return self

    def build(self) -> MagicMock:
        """Build the configured mock client."""

        # Configure query
        def query_side_effect(database_id, **kwargs):
            if "query" in self._errors:
                raise self._errors["query"]
            return self._query_results.get(
                database_id, {"results": [], "has_more": False}
            )

        self.client.databases.query.side_effect = query_side_effect

        # Configure create
        def create_side_effect(parent, properties):
            if "create" in self._errors:
                raise self._errors["create"]
            db_id = parent.get("database_id")
            return self._create_responses.get(
                db_id,
                {"id": f"page-{datetime.now().timestamp()}", "properties": properties},
            )

        self.client.pages.create.side_effect = create_side_effect

        # Configure update
        def update_side_effect(page_id, properties):
            if "update" in self._errors:
                raise self._errors["update"]
            return self._update_responses.get(
                page_id, {"id": page_id, "properties": properties}
            )

        self.client.pages.update.side_effect = update_side_effect

        # Configure retrieve
        def retrieve_side_effect(database_id):
            if "retrieve" in self._errors:
                raise self._errors["retrieve"]
            return self._retrieve_responses.get(
                database_id, {"id": database_id, "properties": {}}
            )

        self.client.databases.retrieve.side_effect = retrieve_side_effect

        return self.client


class MockAIProviderBuilder:
    """Builder for creating configured mock AI providers."""

    def __init__(self, provider: str = "claude"):
        self.provider = provider
        self._responses = []
        self._error = None

    def with_extraction(
        self, entities: List[Entity], relationships: List[Relationship] = None
    ):
        """Add an extraction response."""
        extracted = ExtractedEntities(
            entities=entities, relationships=relationships or []
        )

        response_text = json.dumps(extracted.dict())

        if self.provider == "claude":
            response = MagicMock()
            response.content = [MagicMock(text=response_text)]
        else:  # openai
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content=response_text))]

        self._responses.append(response)
        return self

    def with_error(self, error: Exception):
        """Configure an error response."""
        self._error = error
        return self

    def build(self) -> MagicMock:
        """Build the configured mock provider."""
        mock = MagicMock()

        if self._error:
            if self.provider == "claude":
                mock.messages.create.side_effect = self._error
            else:
                mock.chat.completions.create.side_effect = self._error
        else:
            if self.provider == "claude":
                mock.messages.create.side_effect = self._responses
            else:
                mock.chat.completions.create.side_effect = self._responses

        return mock


class ProcessingScenarioBuilder:
    """Builder for creating complete processing scenarios."""

    def __init__(self):
        self.transcripts = []
        self.expected_entities = {}
        self.expected_pages = {}
        self.expected_errors = []

    def add_transcript(
        self, transcript, entities: List[Entity], notion_pages: List[NotionPage]
    ):
        """Add a transcript with expected results."""
        self.transcripts.append(transcript)
        self.expected_entities[transcript.title] = entities
        self.expected_pages[transcript.title] = notion_pages
        return self

    def add_error_case(self, transcript, error_message: str):
        """Add a transcript that should produce an error."""
        self.transcripts.append(transcript)
        self.expected_errors.append((transcript.title, error_message))
        return self

    def build_mocks(self) -> tuple:
        """Build all necessary mocks for the scenario."""
        # Build AI mock
        ai_builder = MockAIProviderBuilder()
        for transcript in self.transcripts:
            if transcript.title in self.expected_entities:
                ai_builder.with_extraction(self.expected_entities[transcript.title])

        # Build Notion mock
        notion_builder = MockNotionClientBuilder()
        for transcript in self.transcripts:
            if transcript.title in self.expected_pages:
                for page in self.expected_pages[transcript.title]:
                    notion_builder.with_create_response(
                        "db-123",  # Simplified - would need proper mapping
                        page.dict(),
                    )

        return ai_builder.build(), notion_builder.build()


def create_rate_limit_scenario(requests_before_limit: int = 3):
    """Create a mock that triggers rate limiting after N requests."""
    mock = MagicMock()
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > requests_before_limit:
            error = Exception("Rate limited")
            error.status = 429
            raise error
        return {"id": f"page-{call_count}"}

    mock.pages.create.side_effect = side_effect
    return mock


def create_flaky_api_mock(success_rate: float = 0.5):
    """Create a mock that randomly fails."""
    import random

    mock = MagicMock()

    def side_effect(*args, **kwargs):
        if random.random() > success_rate:
            raise Exception("Random API failure")
        return {"id": "page-success"}

    mock.pages.create.side_effect = side_effect
    return mock
