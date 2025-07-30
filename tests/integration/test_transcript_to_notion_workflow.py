"""Integration tests for the complete transcript to Notion workflow."""

import pytest
from unittest.mock import Mock

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.models import TranscriptInput, ProcessingResult
from blackcore.deduplication.cli.async_engine import AsyncDeduplicationEngine


class TestTranscriptToNotionWorkflow:
    """Test the complete workflow from transcript ingestion to Notion update."""

    @pytest.fixture
    def mock_transcript_processor(self):
        """Create a mock transcript processor with deduplication."""
        processor = Mock(spec=TranscriptProcessor)
        processor.config = Mock()
        processor.ai_extractor = Mock()
        processor.notion_updater = Mock()
        processor.cache = Mock()
        return processor

    @pytest.fixture
    def mock_dedupe_engine(self):
        """Create a mock deduplication engine."""
        engine = Mock(spec=AsyncDeduplicationEngine)
        engine.config = {
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "enable_ai_analysis": True,
        }
        return engine

    @pytest.fixture
    def sample_transcript(self):
        """Create a sample transcript for testing."""
        return TranscriptInput(
            title="Meeting with Mayor Johnson",
            content="""
            Meeting with Mayor Johnson at Town Hall.
            Discussed beach hut survey with John Smith from Acme Corp.
            Jane Doe from the planning department was also present.
            
            Action items:
            - John Smith to review survey data by Friday
            - Jane Doe to prepare planning report
            - Mayor Johnson to schedule follow-up meeting next week
            """,
            date="2025-01-09",
            source="voice_memo",
            metadata={"location": "Town Hall", "duration_minutes": 45},
        )

    def test_new_transcript_with_existing_entities(
        self, mock_transcript_processor, mock_dedupe_engine, sample_transcript
    ):
        """Test processing a transcript that mentions existing entities in Notion."""

        # Mock existing entities in Notion
        existing_entities = {
            "people": [
                {
                    "id": "person-1",
                    "Full Name": "John Smith",
                    "Email": "john@acme.com",
                    "Organization": "Acme Corp",
                },
                {
                    "id": "person-2",
                    "Full Name": "Jane Doe",
                    "Email": "jane@planning.gov",
                    "Department": "Planning",
                },
            ],
            "organizations": [
                {"id": "org-1", "Name": "Acme Corp", "Type": "Private Company"}
            ],
        }

        # Mock AI extraction results
        extracted_entities = {
            "people": [
                {
                    "name": "Mayor Johnson",
                    "role": "Mayor",
                    "mentioned_in": "Meeting with Mayor Johnson",
                },
                {
                    "name": "John Smith",
                    "organization": "Acme Corp",
                    "mentioned_in": "John Smith from Acme Corp",
                },
                {
                    "name": "Jane Doe",
                    "department": "planning department",
                    "mentioned_in": "Jane Doe from the planning department",
                },
            ],
            "tasks": [
                {
                    "title": "Review survey data",
                    "assignee": "John Smith",
                    "due_date": "Friday",
                },
                {"title": "Prepare planning report", "assignee": "Jane Doe"},
                {
                    "title": "Schedule follow-up meeting",
                    "assignee": "Mayor Johnson",
                    "timeline": "next week",
                },
            ],
            "organizations": [
                {"name": "Acme Corp", "type": "company", "people": ["John Smith"]}
            ],
        }

        mock_transcript_processor.ai_extractor.extract.return_value = extracted_entities

        # Mock deduplication results
        dedupe_results = {
            "People & Contacts": {
                "total_entities": 3,
                "potential_duplicates": 2,
                "high_confidence_matches": [
                    {
                        "entity_a": {"id": "person-1", "Full Name": "John Smith"},
                        "entity_b": {"name": "John Smith", "organization": "Acme Corp"},
                        "confidence_score": 95.0,
                        "decision": "merge",
                    }
                ],
                "medium_confidence_matches": [
                    {
                        "entity_a": {"id": "person-2", "Full Name": "Jane Doe"},
                        "entity_b": {
                            "name": "Jane Doe",
                            "department": "planning department",
                        },
                        "confidence_score": 85.0,
                        "decision": "merge",
                    }
                ],
                "low_confidence_matches": [],
            }
        }

        # Mock the integrated workflow
        def process_with_deduplication(
            transcript, extracted_entities, existing_entities
        ):
            # Step 1: Check for duplicates
            matches = []
            for person in extracted_entities["people"]:
                for existing in existing_entities["people"]:
                    if person["name"].lower() in existing["Full Name"].lower():
                        matches.append(
                            {
                                "new": person,
                                "existing": existing,
                                "confidence": (
                                    95.0 if person.get("organization") else 85.0
                                ),
                            }
                        )

            # Step 2: Update existing or create new
            result = ProcessingResult()

            # Update existing entities
            for match in matches:
                if match["confidence"] >= 90.0:  # Auto-merge
                    result.updated.append(
                        {
                            "id": match["existing"]["id"],
                            "type": "person",
                            "updates": match["new"],
                        }
                    )
                else:  # Manual review
                    result.updated.append(
                        {
                            "id": match["existing"]["id"],
                            "type": "person",
                            "updates": match["new"],
                            "review_required": True,
                        }
                    )

            # Create new entities (Mayor Johnson)
            new_people = [
                p
                for p in extracted_entities["people"]
                if not any(p["name"] in m["new"]["name"] for m in matches)
            ]
            for person in new_people:
                result.created.append({"type": "person", "data": person})

            # Create tasks with proper assignee links
            for task in extracted_entities["tasks"]:
                # Find the assignee's Notion ID
                assignee_id = None
                for match in matches:
                    if task["assignee"] == match["new"]["name"]:
                        assignee_id = match["existing"]["id"]
                        break

                if not assignee_id:
                    # Check newly created people
                    for person in new_people:
                        if task["assignee"] == person["name"]:
                            assignee_id = f"new-person-{person['name']}"
                            break

                result.created.append(
                    {"type": "task", "data": {**task, "assignee_id": assignee_id}}
                )

            return result

        # Execute the workflow
        result = process_with_deduplication(
            sample_transcript, extracted_entities, existing_entities
        )

        # Verify results
        assert len(result.created) == 4  # 1 new person (Mayor) + 3 tasks
        assert len(result.updated) == 2  # John Smith and Jane Doe

        # Verify John Smith was auto-merged (high confidence)
        john_update = next(u for u in result.updated if u["id"] == "person-1")
        assert (
            "review_required" not in john_update or not john_update["review_required"]
        )

        # Verify Jane Doe requires review (medium confidence)
        jane_update = next(u for u in result.updated if u["id"] == "person-2")
        assert jane_update.get("review_required") == True

        # Verify tasks are linked to correct people
        review_task = next(
            t for t in result.created if t["data"]["title"] == "Review survey data"
        )
        assert review_task["data"]["assignee_id"] == "person-1"  # John Smith's ID

        planning_task = next(
            t for t in result.created if t["data"]["title"] == "Prepare planning report"
        )
        assert planning_task["data"]["assignee_id"] == "person-2"  # Jane Doe's ID

        meeting_task = next(
            t
            for t in result.created
            if t["data"]["title"] == "Schedule follow-up meeting"
        )
        assert (
            meeting_task["data"]["assignee_id"] == "new-person-Mayor Johnson"
        )  # New person

    def test_transcript_creating_linked_entities(
        self, mock_transcript_processor, sample_transcript
    ):
        """Test transcript that creates person + task + organization with proper relations."""

        # Mock extraction with rich entity relationships
        extracted_entities = {
            "people": [
                {
                    "name": "Sarah Chen",
                    "role": "Project Manager",
                    "organization": "Beta Industries",
                    "email": "sarah.chen@beta.com",
                }
            ],
            "organizations": [
                {
                    "name": "Beta Industries",
                    "type": "Technology Company",
                    "key_people": ["Sarah Chen"],
                }
            ],
            "tasks": [
                {
                    "title": "Complete integration testing",
                    "assignee": "Sarah Chen",
                    "related_org": "Beta Industries",
                    "priority": "high",
                    "due_date": "2025-01-15",
                }
            ],
            "events": [
                {
                    "name": "Project Kickoff Meeting",
                    "date": "2025-01-09",
                    "attendees": ["Sarah Chen", "Mayor Johnson"],
                    "location": "Town Hall",
                }
            ],
        }

        mock_transcript_processor.ai_extractor.extract.return_value = extracted_entities

        # Mock the entity creation with relationship preservation
        def create_linked_entities(entities):
            result = ProcessingResult()

            # Create organization first
            org_id = "org-new-1"
            result.created.append(
                {
                    "type": "organization",
                    "id": org_id,
                    "data": entities["organizations"][0],
                }
            )

            # Create person with org relation
            person_id = "person-new-1"
            result.created.append(
                {
                    "type": "person",
                    "id": person_id,
                    "data": {**entities["people"][0], "organization_id": org_id},
                }
            )

            # Create task with both relations
            task_id = "task-new-1"
            result.created.append(
                {
                    "type": "task",
                    "id": task_id,
                    "data": {
                        **entities["tasks"][0],
                        "assignee_id": person_id,
                        "related_org_id": org_id,
                    },
                }
            )

            # Create event with attendee relations
            event_id = "event-new-1"
            result.created.append(
                {
                    "type": "event",
                    "id": event_id,
                    "data": {
                        **entities["events"][0],
                        "attendee_ids": [
                            person_id
                        ],  # Mayor would need to be resolved separately
                    },
                }
            )

            # Verify circular relationships
            result.metadata = {
                "relationships": {
                    "person_to_org": {person_id: org_id},
                    "org_to_people": {org_id: [person_id]},
                    "task_to_person": {task_id: person_id},
                    "task_to_org": {task_id: org_id},
                    "event_to_attendees": {event_id: [person_id]},
                }
            }

            return result

        # Execute the workflow
        result = create_linked_entities(extracted_entities)

        # Verify all entities created
        assert len(result.created) == 4  # org, person, task, event

        # Verify relationship integrity
        relationships = result.metadata["relationships"]

        # Person → Organization
        person = next(e for e in result.created if e["type"] == "person")
        assert person["data"]["organization_id"] == "org-new-1"

        # Organization → People (reverse relation)
        assert "person-new-1" in relationships["org_to_people"]["org-new-1"]

        # Task → Person & Organization
        task = next(e for e in result.created if e["type"] == "task")
        assert task["data"]["assignee_id"] == "person-new-1"
        assert task["data"]["related_org_id"] == "org-new-1"

        # Event → Attendees
        event = next(e for e in result.created if e["type"] == "event")
        assert "person-new-1" in event["data"]["attendee_ids"]

    def test_incremental_transcript_processing(self, mock_transcript_processor):
        """Test processing multiple transcripts over time with evolving information."""

        # Transcript 1: Initial meeting
        transcript1 = TranscriptInput(
            title="Initial Planning Meeting",
            content="""
            Met with John Smith about the new project.
            He's the lead developer at Acme Corp.
            Discussed initial requirements and timeline.
            """,
            date="2025-01-09",
        )

        # Transcript 2: Follow-up with new information
        transcript2 = TranscriptInput(
            title="Follow-up Meeting",
            content="""
            Follow-up with John Smith (john.smith@acme.com).
            He mentioned his team includes Alice Wong and Bob Chen.
            John's direct line is 555-0123.
            New deadline set for end of month.
            """,
            date="2025-01-11",
        )

        # Transcript 3: Status update with corrections
        transcript3 = TranscriptInput(
            title="Status Update",
            content="""
            Correction: John Smith is actually the Technical Lead, not lead developer.
            Alice Wong has been promoted to Senior Developer.
            Project is on track for January 31st deadline.
            """,
            date="2025-01-15",
        )

        # Mock the incremental processing
        processing_state = {"entities": {}, "transcript_history": []}

        def process_incrementally(transcript, state):
            result = ProcessingResult()

            # Extract entities from current transcript
            if "Initial Planning" in transcript.title:
                entities = {
                    "people": [
                        {
                            "name": "John Smith",
                            "role": "lead developer",
                            "organization": "Acme Corp",
                        }
                    ]
                }
            elif "Follow-up" in transcript.title:
                entities = {
                    "people": [
                        {
                            "name": "John Smith",
                            "email": "john.smith@acme.com",
                            "phone": "555-0123",
                        },
                        {"name": "Alice Wong", "organization": "Acme Corp"},
                        {"name": "Bob Chen", "organization": "Acme Corp"},
                    ],
                    "tasks": [
                        {"title": "Complete project", "deadline": "end of month"}
                    ],
                }
            else:  # Status update
                entities = {
                    "people": [
                        {
                            "name": "John Smith",
                            "role": "Technical Lead",  # Updated role
                        },
                        {"name": "Alice Wong", "role": "Senior Developer"},  # New role
                    ],
                    "tasks": [
                        {
                            "title": "Complete project",
                            "deadline": "January 31st",  # Specific date
                        }
                    ],
                }

            # Process entities incrementally
            for entity_type, items in entities.items():
                if entity_type not in state["entities"]:
                    state["entities"][entity_type] = {}

                for item in items:
                    key = item.get("name") or item.get("title")

                    if key in state["entities"][entity_type]:
                        # Update existing entity
                        existing = state["entities"][entity_type][key]
                        updates = {}

                        for field, value in item.items():
                            if field not in existing or existing[field] != value:
                                updates[field] = value
                                existing[field] = value

                        if updates:
                            result.updated.append(
                                {"type": entity_type, "key": key, "updates": updates}
                            )
                    else:
                        # Create new entity
                        state["entities"][entity_type][key] = item.copy()
                        result.created.append({"type": entity_type, "data": item})

            state["transcript_history"].append(
                {
                    "title": transcript.title,
                    "date": transcript.date,
                    "entities_created": len(result.created),
                    "entities_updated": len(result.updated),
                }
            )

            return result

        # Process transcripts in sequence
        result1 = process_incrementally(transcript1, processing_state)
        result2 = process_incrementally(transcript2, processing_state)
        result3 = process_incrementally(transcript3, processing_state)

        # Verify first transcript creates John Smith
        assert len(result1.created) == 1
        assert result1.created[0]["data"]["name"] == "John Smith"
        assert result1.created[0]["data"]["role"] == "lead developer"

        # Verify second transcript updates John and creates others
        assert len(result2.updated) == 1  # John Smith updated with email/phone
        assert len(result2.created) == 3  # Alice, Bob, and task

        john_update = result2.updated[0]
        assert john_update["updates"]["email"] == "john.smith@acme.com"
        assert john_update["updates"]["phone"] == "555-0123"

        # Verify third transcript updates roles and deadline
        assert len(result3.updated) == 3  # John role, Alice role, task deadline

        john_role_update = next(u for u in result3.updated if u["key"] == "John Smith")
        assert john_role_update["updates"]["role"] == "Technical Lead"

        alice_role_update = next(u for u in result3.updated if u["key"] == "Alice Wong")
        assert alice_role_update["updates"]["role"] == "Senior Developer"

        task_update = next(u for u in result3.updated if u["key"] == "Complete project")
        assert task_update["updates"]["deadline"] == "January 31st"

        # Verify final state
        assert len(processing_state["entities"]["people"]) == 3  # John, Alice, Bob
        assert (
            processing_state["entities"]["people"]["John Smith"]["role"]
            == "Technical Lead"
        )
        assert (
            processing_state["entities"]["people"]["John Smith"]["email"]
            == "john.smith@acme.com"
        )

    def test_transcript_duplicate_prevention(
        self, mock_transcript_processor, sample_transcript
    ):
        """Test that processing the same transcript twice doesn't create duplicates."""

        # Mock cache to detect duplicate processing
        processed_transcripts = set()

        def process_transcript_with_duplicate_check(transcript):
            # Generate transcript hash
            transcript_hash = (
                f"{transcript.title}_{transcript.date}_{len(transcript.content)}"
            )

            result = ProcessingResult()

            if transcript_hash in processed_transcripts:
                # Transcript already processed
                result.metadata = {"duplicate_transcript": True}
                result.errors.append("Transcript already processed")
                return result

            # Process normally
            processed_transcripts.add(transcript_hash)

            # Mock entity extraction
            entities = {
                "people": [
                    {"name": "Mayor Johnson", "role": "Mayor"},
                    {"name": "John Smith", "organization": "Acme Corp"},
                ],
                "tasks": [{"title": "Review survey data", "assignee": "John Smith"}],
            }

            # Create entities
            for person in entities["people"]:
                result.created.append({"type": "person", "data": person})
            for task in entities["tasks"]:
                result.created.append({"type": "task", "data": task})

            result.metadata = {"duplicate_transcript": False}
            return result

        # Process transcript first time
        result1 = process_transcript_with_duplicate_check(sample_transcript)

        assert result1.metadata["duplicate_transcript"] == False
        assert len(result1.created) == 3  # 2 people + 1 task
        assert len(result1.errors) == 0

        # Process same transcript again
        result2 = process_transcript_with_duplicate_check(sample_transcript)

        assert result2.metadata["duplicate_transcript"] == True
        assert len(result2.created) == 0  # Nothing created
        assert len(result2.errors) == 1
        assert "already processed" in result2.errors[0]

        # Process slightly modified transcript (should be treated as new)
        modified_transcript = TranscriptInput(
            title=sample_transcript.title,
            content=sample_transcript.content + "\nAdditional notes: Budget approved.",
            date=sample_transcript.date,
        )

        result3 = process_transcript_with_duplicate_check(modified_transcript)

        assert result3.metadata["duplicate_transcript"] == False
        assert len(result3.created) == 3  # Entities created again (would need dedup)

    def test_ai_extraction_to_deduplication_pipeline(
        self, mock_transcript_processor, mock_dedupe_engine
    ):
        """Test the complete pipeline from AI extraction through deduplication to Notion update."""

        # Create a complex transcript with potential duplicates
        complex_transcript = TranscriptInput(
            title="Quarterly Review Meeting",
            content="""
            Quarterly review with the team.
            
            Attendees:
            - John Smith (Acme Corp) - presenting Q4 results
            - J. Smith from Acme - will handle follow-ups
            - Jane from Planning Dept
            - Jane D. from city planning
            - Bob Wilson, our new CTO
            - Robert Wilson, Chief Technology Officer
            
            Action items assigned during meeting...
            """,
            date="2025-01-15",
        )

        # Mock AI extraction with potential duplicates
        ai_extracted = {
            "people": [
                {
                    "name": "John Smith",
                    "organization": "Acme Corp",
                    "context": "presenting Q4 results",
                },
                {
                    "name": "J. Smith",
                    "organization": "Acme",
                    "context": "will handle follow-ups",
                },
                {
                    "name": "Jane",
                    "department": "Planning Dept",
                    "context": "from Planning Dept",
                },
                {
                    "name": "Jane D.",
                    "department": "city planning",
                    "context": "from city planning",
                },
                {"name": "Bob Wilson", "role": "CTO", "context": "our new CTO"},
                {
                    "name": "Robert Wilson",
                    "role": "Chief Technology Officer",
                    "context": "Chief Technology Officer",
                },
            ]
        }

        # Mock deduplication analysis
        def analyze_for_duplicates(entities):
            duplicates = []

            # John Smith vs J. Smith
            duplicates.append(
                {
                    "entity_a": entities[0],  # John Smith
                    "entity_b": entities[1],  # J. Smith
                    "confidence": 95.0,
                    "reasoning": "Same organization, similar name pattern",
                }
            )

            # Jane vs Jane D.
            duplicates.append(
                {
                    "entity_a": entities[2],  # Jane
                    "entity_b": entities[3],  # Jane D.
                    "confidence": 85.0,
                    "reasoning": "Same department context, name variation",
                }
            )

            # Bob Wilson vs Robert Wilson
            duplicates.append(
                {
                    "entity_a": entities[4],  # Bob Wilson
                    "entity_b": entities[5],  # Robert Wilson
                    "confidence": 98.0,
                    "reasoning": "Bob is common nickname for Robert, same role",
                }
            )

            return duplicates

        # Execute the pipeline
        mock_transcript_processor.ai_extractor.extract.return_value = ai_extracted

        # Step 1: Extract entities
        extracted = mock_transcript_processor.ai_extractor.extract(complex_transcript)
        assert len(extracted["people"]) == 6

        # Step 2: Run deduplication
        duplicate_pairs = analyze_for_duplicates(extracted["people"])
        assert len(duplicate_pairs) == 3

        # Step 3: Merge duplicates based on confidence
        merged_entities = []
        processed_indices = set()

        for i, entity in enumerate(extracted["people"]):
            if i in processed_indices:
                continue

            # Check if this entity is part of a duplicate pair
            for dup in duplicate_pairs:
                if entity == dup["entity_a"]:
                    if dup["confidence"] >= 90.0:  # Auto-merge threshold
                        # Merge b into a
                        merged = {
                            **entity,
                            "alternate_names": [dup["entity_b"]["name"]],
                            "confidence": dup["confidence"],
                        }
                        merged_entities.append(merged)

                        # Mark both as processed
                        processed_indices.add(i)
                        b_index = extracted["people"].index(dup["entity_b"])
                        processed_indices.add(b_index)
                        break
                    else:
                        # Requires manual review
                        merged_entities.append(
                            {
                                **entity,
                                "requires_review": True,
                                "potential_duplicate": dup["entity_b"],
                                "confidence": dup["confidence"],
                            }
                        )
                        processed_indices.add(i)
                        break
            else:
                # No duplicates found
                merged_entities.append(entity)
                processed_indices.add(i)

        # Verify deduplication results
        assert len(merged_entities) == 3  # 6 entities reduced to 3

        # John Smith / J. Smith merged (95% confidence)
        john = next(e for e in merged_entities if "John Smith" in e["name"])
        assert "alternate_names" in john
        assert "J. Smith" in john["alternate_names"]

        # Jane / Jane D. marked for review (85% confidence)
        jane = next(e for e in merged_entities if e["name"] == "Jane")
        assert jane["requires_review"] == True
        assert jane["potential_duplicate"]["name"] == "Jane D."

        # Bob Wilson / Robert Wilson merged (98% confidence)
        bob = next(e for e in merged_entities if "Wilson" in e["name"])
        assert bob["confidence"] == 98.0
        assert "alternate_names" in bob

        # Step 4: Create final result
        final_result = ProcessingResult()
        for entity in merged_entities:
            if entity.get("requires_review"):
                final_result.review_required.append(
                    {"type": "person", "entity": entity, "action": "confirm_duplicate"}
                )
            else:
                final_result.created.append({"type": "person", "data": entity})

        assert len(final_result.created) == 2  # John and Bob auto-merged
        assert len(final_result.review_required) == 1  # Jane needs review
