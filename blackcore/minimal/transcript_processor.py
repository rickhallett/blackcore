"""Main orchestrator for transcript processing pipeline."""

import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from .models import (
    TranscriptInput,
    ProcessingResult,
    BatchResult,
    ExtractedEntities,
    EntityType,
    NotionPage,
    Entity,
)
from .config import ConfigManager, Config
from .ai_extractor import AIExtractor
from .notion_updater import NotionUpdater
from .cache import SimpleCache


class TranscriptProcessor:
    """Main class for processing transcripts through the pipeline."""

    def __init__(self, config: Optional[Config] = None, config_path: Optional[str] = None):
        """Initialize transcript processor.

        Args:
            config: Config object (takes precedence)
            config_path: Path to config file
        """
        # Load configuration
        if config:
            self.config = config
        else:
            config_manager = ConfigManager(config_path)
            self.config = config_manager.load()

        # Validate configuration
        self._validate_config()

        # Initialize components
        self.ai_extractor = AIExtractor(
            provider=self.config.ai.provider,
            api_key=self.config.ai.api_key,
            model=self.config.ai.model,
        )

        self.notion_updater = NotionUpdater(
            api_key=self.config.notion.api_key,
            rate_limit=self.config.notion.rate_limit,
            retry_attempts=self.config.notion.retry_attempts,
        )

        self.cache = SimpleCache(ttl=self.config.processing.cache_ttl)

        # Track database schemas
        self._schemas: Dict[str, Dict[str, str]] = {}

    def process_transcript(self, transcript: TranscriptInput) -> ProcessingResult:
        """Process a single transcript through the entire pipeline.

        Args:
            transcript: Input transcript to process

        Returns:
            ProcessingResult with details of created/updated entities
        """
        start_time = time.time()
        result = ProcessingResult()

        try:
            # Step 1: Extract entities using AI
            if self.config.processing.verbose:
                print(f"Extracting entities from '{transcript.title}'...")

            extracted = self._extract_entities(transcript)

            # Step 2: Create/update entities in Notion
            if self.config.processing.dry_run:
                print("DRY RUN: Would create/update the following entities:")
                self._print_dry_run_summary(extracted)
                result.success = True
                return result

            # Process each entity type
            entity_map = {}  # Map entity names to their Notion IDs

            # People
            people = extracted.get_entities_by_type(EntityType.PERSON)
            for person in people:
                page, created = self._process_person(person)
                if page:
                    entity_map[person.name] = page.id
                    if created:
                        result.created.append(page)
                    else:
                        result.updated.append(page)

            # Organizations
            orgs = extracted.get_entities_by_type(EntityType.ORGANIZATION)
            for org in orgs:
                page, created = self._process_organization(org)
                if page:
                    entity_map[org.name] = page.id
                    if created:
                        result.created.append(page)
                    else:
                        result.updated.append(page)

            # Tasks
            tasks = extracted.get_entities_by_type(EntityType.TASK)
            for task in tasks:
                page, created = self._process_task(task)
                if page:
                    entity_map[task.name] = page.id
                    if created:
                        result.created.append(page)
                    else:
                        result.updated.append(page)

            # Transgressions
            transgressions = extracted.get_entities_by_type(EntityType.TRANSGRESSION)
            for transgression in transgressions:
                page, created = self._process_transgression(transgression, entity_map)
                if page:
                    if created:
                        result.created.append(page)
                    else:
                        result.updated.append(page)

            # Step 3: Update transcript with summary and entities
            transcript_page = self._update_transcript(transcript, extracted, entity_map)
            if transcript_page:
                result.transcript_id = transcript_page.id
                result.updated.append(transcript_page)

            # Step 4: Create relationships
            relationships_created = self._create_relationships(extracted, entity_map)
            result.relationships_created = relationships_created

            result.success = True

        except Exception as e:
            result.add_error(stage="processing", error_type=type(e).__name__, message=str(e))

        result.processing_time = time.time() - start_time

        if self.config.processing.verbose:
            self._print_result_summary(result)

        return result

    def process_batch(self, transcripts: List[TranscriptInput]) -> BatchResult:
        """Process multiple transcripts.

        Args:
            transcripts: List of transcripts to process

        Returns:
            BatchResult with summary of all processing
        """
        batch_result = BatchResult(total_transcripts=len(transcripts), successful=0, failed=0)

        for i, transcript in enumerate(transcripts):
            if self.config.processing.verbose:
                print(f"\nProcessing transcript {i + 1}/{len(transcripts)}: {transcript.title}")

            result = self.process_transcript(transcript)
            batch_result.results.append(result)

            if result.success:
                batch_result.successful += 1
            else:
                batch_result.failed += 1

        batch_result.end_time = datetime.utcnow()

        if self.config.processing.verbose:
            self._print_batch_summary(batch_result)

        return batch_result

    def _validate_config(self):
        """Validate configuration has required values."""
        if not self.config.notion.api_key:
            raise ValueError("Notion API key not configured")

        if not self.config.ai.api_key:
            raise ValueError("AI API key not configured")

        # Warn about missing database IDs
        for db_name, db_config in self.config.notion.databases.items():
            if not db_config.id:
                print(
                    f"Warning: Database ID not configured for '{db_name}'. This entity type will be skipped."
                )

    def _extract_entities(self, transcript: TranscriptInput) -> ExtractedEntities:
        """Extract entities from transcript using AI."""
        # Check cache first
        cache_key = f"extract:{transcript.title}:{hash(transcript.content)}"
        cached = self.cache.get(cache_key)
        if cached:
            return ExtractedEntities(**cached)

        # Extract using AI
        extracted = self.ai_extractor.extract_entities(
            text=transcript.content, prompt=self.config.ai.extraction_prompt
        )

        # Cache result
        self.cache.set(cache_key, extracted.dict())

        return extracted

    def _process_person(self, person: Entity) -> Tuple[Optional[NotionPage], bool]:
        """Process a person entity."""
        db_config = self.config.notion.databases.get("people")
        if not db_config or not db_config.id:
            return None, False

        properties = {db_config.mappings.get("name", "Full Name"): person.name}

        # Add additional properties
        if "role" in person.properties:
            properties[db_config.mappings.get("role", "Role")] = person.properties["role"]

        if "organization" in person.properties:
            properties[db_config.mappings.get("organization", "Organization")] = person.properties[
                "organization"
            ]

        if "email" in person.properties:
            properties[db_config.mappings.get("email", "Email")] = person.properties["email"]

        if "phone" in person.properties:
            properties[db_config.mappings.get("phone", "Phone")] = person.properties["phone"]

        if person.context:
            properties[db_config.mappings.get("notes", "Notes")] = person.context

        # Find or create
        return self.notion_updater.find_or_create_page(
            database_id=db_config.id,
            properties=properties,
            match_property=db_config.mappings.get("name", "Full Name"),
        )

    def _process_organization(self, org: Entity) -> Tuple[Optional[NotionPage], bool]:
        """Process an organization entity."""
        db_config = self.config.notion.databases.get("organizations")
        if not db_config or not db_config.id:
            return None, False

        properties = {db_config.mappings.get("name", "Organization Name"): org.name}

        if "category" in org.properties:
            properties[db_config.mappings.get("category", "Category")] = org.properties["category"]

        if "website" in org.properties:
            properties[db_config.mappings.get("website", "Website")] = org.properties["website"]

        return self.notion_updater.find_or_create_page(
            database_id=db_config.id,
            properties=properties,
            match_property=db_config.mappings.get("name", "Organization Name"),
        )

    def _process_task(self, task: Entity) -> Tuple[Optional[NotionPage], bool]:
        """Process a task entity."""
        db_config = self.config.notion.databases.get("tasks")
        if not db_config or not db_config.id:
            return None, False

        properties = {
            db_config.mappings.get("name", "Task Name"): task.name,
            db_config.mappings.get("status", "Status"): task.properties.get("status", "To-Do"),
        }

        if "assignee" in task.properties:
            properties[db_config.mappings.get("assignee", "Assignee")] = task.properties["assignee"]

        if "due_date" in task.properties:
            properties[db_config.mappings.get("due_date", "Due Date")] = task.properties["due_date"]

        if "priority" in task.properties:
            properties[db_config.mappings.get("priority", "Priority")] = task.properties["priority"]

        return self.notion_updater.create_page(db_config.id, properties), True

    def _process_transgression(
        self, transgression: Entity, entity_map: Dict[str, str]
    ) -> Tuple[Optional[NotionPage], bool]:
        """Process a transgression entity."""
        db_config = self.config.notion.databases.get("transgressions")
        if not db_config or not db_config.id:
            return None, False

        properties = {
            db_config.mappings.get("summary", "Transgression Summary"): transgression.name
        }

        # Link perpetrators if they exist
        if "perpetrator_person" in transgression.properties:
            person_name = transgression.properties["perpetrator_person"]
            if person_name in entity_map:
                properties[db_config.mappings.get("perpetrator_person", "Perpetrator (Person)")] = [
                    entity_map[person_name]
                ]

        if "perpetrator_org" in transgression.properties:
            org_name = transgression.properties["perpetrator_org"]
            if org_name in entity_map:
                properties[db_config.mappings.get("perpetrator_org", "Perpetrator (Org)")] = [
                    entity_map[org_name]
                ]

        if "date" in transgression.properties:
            properties[db_config.mappings.get("date", "Date of Transgression")] = (
                transgression.properties["date"]
            )

        if "severity" in transgression.properties:
            properties[db_config.mappings.get("severity", "Severity")] = transgression.properties[
                "severity"
            ]

        return self.notion_updater.create_page(db_config.id, properties), True

    def _update_transcript(
        self, transcript: TranscriptInput, extracted: ExtractedEntities, entity_map: Dict[str, str]
    ) -> Optional[NotionPage]:
        """Update the transcript in Notion with extracted information."""
        db_config = self.config.notion.databases.get("transcripts")
        if not db_config or not db_config.id:
            return None

        # Collect all entity IDs
        entity_ids = list(entity_map.values())

        properties = {
            db_config.mappings.get("title", "Entry Title"): transcript.title,
            db_config.mappings.get("content", "Raw Transcript/Note"): transcript.content[
                :2000
            ],  # Notion text limit
            db_config.mappings.get("status", "Processing Status"): "Processed",
        }

        if transcript.date:
            properties[db_config.mappings.get("date", "Date Recorded")] = (
                transcript.date.isoformat()
            )

        if transcript.source:
            properties[db_config.mappings.get("source", "Source")] = transcript.source.value

        if extracted.summary:
            properties[db_config.mappings.get("summary", "AI Summary")] = extracted.summary

        if entity_ids:
            properties[db_config.mappings.get("entities", "Tagged Entities")] = entity_ids

        page, _ = self.notion_updater.find_or_create_page(
            database_id=db_config.id,
            properties=properties,
            match_property=db_config.mappings.get("title", "Entry Title"),
        )

        return page

    def _create_relationships(
        self, extracted: ExtractedEntities, entity_map: Dict[str, str]
    ) -> int:
        """Create relationships between entities."""
        count = 0

        for relationship in extracted.relationships:
            # Check if both entities exist
            source_id = entity_map.get(relationship.source_entity)
            target_id = entity_map.get(relationship.target_entity)

            if not source_id or not target_id:
                continue

            # For now, we'll skip relationship creation as it requires
            # more complex property mapping
            # TODO: Implement relationship creation based on relationship types

        return count

    def _print_dry_run_summary(self, extracted: ExtractedEntities):
        """Print summary for dry run mode."""
        print(f"\nExtracted {len(extracted.entities)} entities:")
        for entity_type in EntityType:
            entities = extracted.get_entities_by_type(entity_type)
            if entities:
                print(f"  {entity_type.value}: {len(entities)}")
                for entity in entities[:3]:  # Show first 3
                    print(f"    - {entity.name}")
                if len(entities) > 3:
                    print(f"    ... and {len(entities) - 3} more")

        if extracted.summary:
            print(f"\nSummary: {extracted.summary}")

        if extracted.key_points:
            print("\nKey Points:")
            for point in extracted.key_points:
                print(f"  • {point}")

    def _print_result_summary(self, result: ProcessingResult):
        """Print processing result summary."""
        print(f"\nProcessing complete in {result.processing_time:.2f}s:")
        print(f"  Created: {len(result.created)} entities")
        print(f"  Updated: {len(result.updated)} entities")
        print(f"  Relationships: {result.relationships_created}")

        if result.errors:
            print(f"  Errors: {len(result.errors)}")
            for error in result.errors:
                print(f"    - {error.error_type}: {error.message}")

    def _print_batch_summary(self, batch_result: BatchResult):
        """Print batch processing summary."""
        print(f"\nBatch processing complete:")
        print(f"  Total: {batch_result.total_transcripts} transcripts")
        print(f"  Successful: {batch_result.successful}")
        print(f"  Failed: {batch_result.failed}")
        print(f"  Success rate: {batch_result.success_rate:.1%}")

        if batch_result.processing_time:
            print(f"  Total time: {batch_result.processing_time:.2f}s")
            avg_time = batch_result.processing_time / batch_result.total_transcripts
            print(f"  Average time: {avg_time:.2f}s per transcript")
