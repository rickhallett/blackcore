"""Main orchestrator for transcript processing pipeline."""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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
from .simple_scorer import SimpleScorer
from .llm_scorer import LLMScorerWithFallback


class TranscriptProcessor:
    """Main class for processing transcripts through the pipeline."""

    def __init__(
        self, config: Optional[Config] = None, config_path: Optional[str] = None
    ):
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

        self.cache = SimpleCache(
            cache_dir=self.config.processing.cache_dir,
            ttl=self.config.processing.cache_ttl,
        )

        # Initialize scorer for deduplication based on config
        self._init_scorer()

        # Track database schemas
        self._schemas: Dict[str, Dict[str, str]] = {}

    def _init_scorer(self):
        """Initialize the appropriate scorer based on configuration."""
        scorer_type = getattr(self.config.processing, "deduplication_scorer", "simple")

        if scorer_type == "llm":
            # Use LLM scorer with fallback
            try:
                # Get LLM config
                llm_config = getattr(self.config.processing, "llm_scorer_config", {})
                model = llm_config.get("model", "claude-3-5-haiku-20241022")
                temperature = llm_config.get("temperature", 0.1)
                cache_ttl = llm_config.get("cache_ttl", 3600)

                # Create simple scorer as fallback
                simple_scorer = SimpleScorer()

                # Create LLM scorer with fallback
                self.scorer = LLMScorerWithFallback(
                    api_key=self.config.ai.api_key,
                    model=model,
                    temperature=temperature,
                    cache_ttl=cache_ttl,
                    fallback_scorer=simple_scorer,
                )

                if self.config.processing.verbose:
                    print(
                        "Using LLM scorer (Claude 3.5 Haiku) with simple scorer fallback"
                    )

            except Exception as e:
                print(f"Failed to initialize LLM scorer: {e}")
                print("Falling back to simple scorer")
                self.scorer = SimpleScorer()
        else:
            # Use simple scorer
            self.scorer = SimpleScorer()
            if self.config.processing.verbose:
                print("Using simple rule-based scorer")

    def process_transcript(self, transcript: TranscriptInput) -> ProcessingResult:
        """Process a single transcript through the entire pipeline.

        Args:
            transcript: Input transcript to process

        Returns:
            ProcessingResult with details of created/updated entities
        """
        start_time = time.time()
        result = ProcessingResult()

        # Store transcript title for context
        self._current_transcript_title = transcript.title

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
            result.add_error(
                stage="processing", error_type=type(e).__name__, message=str(e)
            )

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
        batch_result = BatchResult(
            total_transcripts=len(transcripts), successful=0, failed=0
        )

        for i, transcript in enumerate(transcripts):
            if self.config.processing.verbose:
                print(
                    f"\nProcessing transcript {i + 1}/{len(transcripts)}: {transcript.title}"
                )

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

    def _find_existing_entity(
        self, entity: Entity, database_id: str, entity_type: str
    ) -> Optional[NotionPage]:
        """Find an existing entity with high confidence match.

        Args:
            entity: Entity to match
            database_id: Database to search
            entity_type: Type of entity (person, organization)

        Returns:
            Existing NotionPage if high-confidence match found, None otherwise
        """
        # Get deduplication threshold from config, default to 90.0
        threshold = getattr(self.config.processing, "deduplication_threshold", 90.0)

        # Search for potential matches by name
        search_results = self.notion_updater.search_database(
            database_id=database_id,
            query=entity.name,
            limit=10,  # Check top 10 potential matches
        )

        if not search_results:
            return None

        # Score each potential match
        best_match = None
        best_score = 0.0
        best_reason = ""

        for page in search_results:
            # Build entity dict from page properties
            page_properties = page.properties
            if isinstance(page_properties, Mock):
                page_properties = page.properties.return_value

            existing_entity = {
                "name": page_properties.get(
                    "Full Name", page_properties.get("Organization Name", "")
                ),
                "email": page_properties.get("Email", ""),
                "phone": page_properties.get("Phone", ""),
                "organization": page_properties.get("Organization", ""),
                "website": page_properties.get("Website", ""),
            }

            # Build new entity dict
            new_entity = {
                "name": entity.name,
                "email": entity.properties.get("email", ""),
                "phone": entity.properties.get("phone", ""),
                "organization": entity.properties.get("organization", ""),
                "website": entity.properties.get("website", ""),
            }

            # Calculate similarity score
            # Check if scorer supports context (LLM scorer)
            if (
                hasattr(self.scorer, "score_entities")
                and "context" in self.scorer.score_entities.__code__.co_varnames
            ):
                # LLM scorer with context
                score_result = self.scorer.score_entities(
                    existing_entity,
                    new_entity,
                    entity_type,
                    context={
                        "source_documents": [
                            f"Transcript: {getattr(self, '_current_transcript_title', 'Unknown')}"
                        ]
                    },
                )
                # Handle both tuple formats
                if len(score_result) == 3:
                    score, reason, _ = score_result
                else:
                    score, reason = score_result
            else:
                # Simple scorer
                score, reason = self.scorer.score_entities(
                    existing_entity, new_entity, entity_type
                )

            if score > best_score:
                best_score = score
                best_match = page
                best_reason = reason

        # Return match if above threshold
        if best_score >= threshold:
            if self.config.processing.verbose:
                print(
                    f"  Found duplicate: '{entity.name}' matches existing entity (score: {best_score:.1f}, reason: {best_reason})"
                )
            return best_match

        return None

    def _process_person(self, person: Entity) -> Tuple[Optional[NotionPage], bool]:
        """Process a person entity."""
        db_config = self.config.notion.databases.get("people")
        if not db_config or not db_config.id:
            return None, False

        # Check for existing entity with deduplication
        if getattr(self.config.processing, "enable_deduplication", True):
            existing = self._find_existing_entity(person, db_config.id, "person")
            if existing:
                # Update existing entity
                properties = {}

                # Only update properties that have values
                if "role" in person.properties and person.properties["role"]:
                    properties[db_config.mappings.get("role", "Role")] = (
                        person.properties["role"]
                    )

                if (
                    "organization" in person.properties
                    and person.properties["organization"]
                ):
                    properties[
                        db_config.mappings.get("organization", "Organization")
                    ] = person.properties["organization"]

                if "email" in person.properties and person.properties["email"]:
                    properties[db_config.mappings.get("email", "Email")] = (
                        person.properties["email"]
                    )

                if "phone" in person.properties and person.properties["phone"]:
                    properties[db_config.mappings.get("phone", "Phone")] = (
                        person.properties["phone"]
                    )

                if person.context:
                    # Append context to existing notes
                    existing_notes = existing.properties.get(
                        db_config.mappings.get("notes", "Notes"), ""
                    )
                    if existing_notes:
                        properties[db_config.mappings.get("notes", "Notes")] = (
                            f"{existing_notes}\n\n{person.context}"
                        )
                    else:
                        properties[db_config.mappings.get("notes", "Notes")] = (
                            person.context
                        )

                # Update if we have new properties
                if properties:
                    updated_page = self.notion_updater.update_page(
                        existing.id, properties
                    )
                    return updated_page, False  # False = not created, was updated
                else:
                    return existing, False  # No updates needed

        # No existing entity found or deduplication disabled - create new
        properties = {db_config.mappings.get("name", "Full Name"): person.name}

        # Add additional properties
        if "role" in person.properties:
            properties[db_config.mappings.get("role", "Role")] = person.properties[
                "role"
            ]

        if "organization" in person.properties:
            properties[db_config.mappings.get("organization", "Organization")] = (
                person.properties["organization"]
            )

        if "email" in person.properties:
            properties[db_config.mappings.get("email", "Email")] = person.properties[
                "email"
            ]

        if "phone" in person.properties:
            properties[db_config.mappings.get("phone", "Phone")] = person.properties[
                "phone"
            ]

        if person.context:
            properties[db_config.mappings.get("notes", "Notes")] = person.context

        # Create new page
        page = self.notion_updater.create_page(db_config.id, properties)
        return page, True  # True = created new

    def _process_organization(self, org: Entity) -> Tuple[Optional[NotionPage], bool]:
        """Process an organization entity."""
        db_config = self.config.notion.databases.get("organizations")
        if not db_config or not db_config.id:
            return None, False

        # Check for existing entity with deduplication
        if getattr(self.config.processing, "enable_deduplication", True):
            existing = self._find_existing_entity(org, db_config.id, "organization")
            if existing:
                # Update existing entity
                properties = {}

                # Only update properties that have values
                if "category" in org.properties and org.properties["category"]:
                    properties[db_config.mappings.get("category", "Category")] = (
                        org.properties["category"]
                    )

                if "website" in org.properties and org.properties["website"]:
                    properties[db_config.mappings.get("website", "Website")] = (
                        org.properties["website"]
                    )

                if org.context:
                    # Append context to existing notes
                    existing_notes = existing.properties.get(
                        db_config.mappings.get("notes", "Notes"), ""
                    )
                    if existing_notes:
                        properties[db_config.mappings.get("notes", "Notes")] = (
                            f"{existing_notes}\n\n{org.context}"
                        )
                    else:
                        properties[db_config.mappings.get("notes", "Notes")] = (
                            org.context
                        )

                # Update if we have new properties
                if properties:
                    updated_page = self.notion_updater.update_page(
                        existing.id, properties
                    )
                    return updated_page, False  # False = not created, was updated
                else:
                    return existing, False  # No updates needed

        # No existing entity found or deduplication disabled - create new
        properties = {db_config.mappings.get("name", "Organization Name"): org.name}

        if "category" in org.properties:
            properties[db_config.mappings.get("category", "Category")] = org.properties[
                "category"
            ]

        if "website" in org.properties:
            properties[db_config.mappings.get("website", "Website")] = org.properties[
                "website"
            ]

        # Create new page
        page = self.notion_updater.create_page(db_config.id, properties)
        return page, True  # True = created new

    def _process_task(self, task: Entity) -> Tuple[Optional[NotionPage], bool]:
        """Process a task entity."""
        db_config = self.config.notion.databases.get("tasks")
        if not db_config or not db_config.id:
            return None, False

        properties = {
            db_config.mappings.get("name", "Task Name"): task.name,
            db_config.mappings.get("status", "Status"): task.properties.get(
                "status", "To-Do"
            ),
        }

        if "assignee" in task.properties:
            properties[db_config.mappings.get("assignee", "Assignee")] = (
                task.properties["assignee"]
            )

        if "due_date" in task.properties:
            properties[db_config.mappings.get("due_date", "Due Date")] = (
                task.properties["due_date"]
            )

        if "priority" in task.properties:
            properties[db_config.mappings.get("priority", "Priority")] = (
                task.properties["priority"]
            )

        return self.notion_updater.create_page(db_config.id, properties), True

    def _process_transgression(
        self, transgression: Entity, entity_map: Dict[str, str]
    ) -> Tuple[Optional[NotionPage], bool]:
        """Process a transgression entity."""
        db_config = self.config.notion.databases.get("transgressions")
        if not db_config or not db_config.id:
            return None, False

        properties = {
            db_config.mappings.get(
                "summary", "Transgression Summary"
            ): transgression.name
        }

        # Link perpetrators if they exist
        if "perpetrator_person" in transgression.properties:
            person_name = transgression.properties["perpetrator_person"]
            if person_name in entity_map:
                properties[
                    db_config.mappings.get("perpetrator_person", "Perpetrator (Person)")
                ] = [entity_map[person_name]]

        if "perpetrator_org" in transgression.properties:
            org_name = transgression.properties["perpetrator_org"]
            if org_name in entity_map:
                properties[
                    db_config.mappings.get("perpetrator_org", "Perpetrator (Org)")
                ] = [entity_map[org_name]]

        if "date" in transgression.properties:
            properties[db_config.mappings.get("date", "Date of Transgression")] = (
                transgression.properties["date"]
            )

        if "severity" in transgression.properties:
            properties[db_config.mappings.get("severity", "Severity")] = (
                transgression.properties["severity"]
            )

        return self.notion_updater.create_page(db_config.id, properties), True

    def _update_transcript(
        self,
        transcript: TranscriptInput,
        extracted: ExtractedEntities,
        entity_map: Dict[str, str],
    ) -> Optional[NotionPage]:
        """Update the transcript in Notion with extracted information."""
        db_config = self.config.notion.databases.get("transcripts")
        if not db_config or not db_config.id:
            return None

        # Collect all entity IDs
        entity_ids = list(entity_map.values())

        properties = {
            db_config.mappings.get("title", "Entry Title"): transcript.title,
            db_config.mappings.get(
                "content", "Raw Transcript/Note"
            ): transcript.content[
                :2000
            ],  # Notion text limit
            db_config.mappings.get("status", "Processing Status"): "Processed",
        }

        if transcript.date:
            properties[db_config.mappings.get("date", "Date Recorded")] = (
                transcript.date.isoformat()
            )

        if transcript.source:
            properties[db_config.mappings.get("source", "Source")] = (
                transcript.source.value
            )

        if extracted.summary:
            properties[db_config.mappings.get("summary", "AI Summary")] = (
                extracted.summary
            )

        if entity_ids:
            properties[db_config.mappings.get("entities", "Tagged Entities")] = (
                entity_ids
            )

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
        print("\nBatch processing complete:")
        print(f"  Total: {batch_result.total_transcripts} transcripts")
        print(f"  Successful: {batch_result.successful}")
        print(f"  Failed: {batch_result.failed}")
        print(f"  Success rate: {batch_result.success_rate:.1%}")

        if batch_result.processing_time:
            print(f"  Total time: {batch_result.processing_time:.2f}s")
            avg_time = batch_result.processing_time / batch_result.total_transcripts
            print(f"  Average time: {avg_time:.2f}s per transcript")
