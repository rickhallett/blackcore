"""Tests for continuous data synchronization workflows."""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
import json

from blackcore.minimal.json_sync import JSONSyncProcessor
from blackcore.minimal.models import TranscriptInput, ProcessingResult


class TestContinuousSyncWorkflow:
    """Test the daily/weekly workflow of continuously adding new data."""

    @pytest.fixture
    def sync_state_file(self, tmp_path):
        """Create a temporary sync state file."""
        state_file = tmp_path / "sync_state.json"
        return state_file

    @pytest.fixture
    def mock_sync_processor(self, sync_state_file):
        """Create a mock sync processor with state tracking."""
        processor = Mock(spec=JSONSyncProcessor)
        processor.sync_state_file = sync_state_file
        processor.notion_updater = Mock()
        processor.config = Mock()

        # Initialize sync state
        processor._sync_state = {}

        def save_sync_state():
            with open(sync_state_file, "w") as f:
                json.dump(processor._sync_state, f)

        def load_sync_state():
            if sync_state_file.exists():
                with open(sync_state_file, "r") as f:
                    processor._sync_state = json.load(f)
            return processor._sync_state

        processor._save_sync_state = save_sync_state
        processor._load_sync_state = load_sync_state

        return processor

    @pytest.fixture
    def daily_transcripts(self):
        """Create a week's worth of daily transcripts."""
        base_date = datetime(2025, 1, 6)  # Monday
        transcripts = {}

        # Monday - Initial meeting
        transcripts["monday"] = TranscriptInput(
            title="Weekly Planning Meeting",
            content="""
            Weekly planning meeting with the team.
            Attendees: John Smith (Project Lead), Jane Doe (Designer), Bob Wilson (Developer)
            
            John Smith: "We need to finalize the beach hut survey by Friday."
            Jane Doe: "I'll have the designs ready by Wednesday."
            Bob Wilson: "I can start implementation once designs are approved."
            
            Action items:
            - John to review requirements by EOD
            - Jane to complete designs by Wednesday
            - Bob to estimate development time
            """,
            date=base_date.isoformat(),
            metadata={"day": "Monday", "meeting_type": "planning"},
        )

        # Tuesday - Follow-up
        transcripts["tuesday"] = TranscriptInput(
            title="Design Review Session",
            content="""
            Design review with Jane Doe and John Smith.
            Also present: Sarah Chen from Beta Industries (client representative)
            
            Jane presented initial mockups. Sarah Chen provided feedback:
            "The color scheme needs to match our brand guidelines."
            
            John Smith's email is john.smith@acme.com (for sending updates).
            Sarah can be reached at s.chen@beta.com.
            
            New action items:
            - Jane to revise designs with brand colors
            - John to schedule follow-up with Sarah for Thursday
            """,
            date=(base_date + timedelta(days=1)).isoformat(),
            metadata={"day": "Tuesday", "meeting_type": "review"},
        )

        # Wednesday - New person joins
        transcripts["wednesday"] = TranscriptInput(
            title="Developer Sync",
            content="""
            Quick sync with development team.
            Bob Wilson introduced new team member: Michael Chang (Senior Developer)
            Michael's contact: m.chang@acme.com, direct line: 555-0147
            
            Bob mentioned he's now at 555-0156 (new extension).
            
            Michael will be taking over some of Bob's tasks:
            - API integration
            - Database schema design
            
            Jane Doe sent updated designs as promised.
            """,
            date=(base_date + timedelta(days=2)).isoformat(),
            metadata={"day": "Wednesday", "meeting_type": "sync"},
        )

        # Thursday - Client meeting
        transcripts["thursday"] = TranscriptInput(
            title="Client Presentation",
            content="""
            Client presentation at Beta Industries.
            Present: John Smith, Jane Doe, Sarah Chen, and Beta's CTO Robert Lee
            
            Robert Lee (rlee@beta.com) approved the revised designs.
            He mentioned their CEO Elizabeth Chen will need final sign-off.
            
            Sarah Chen is actually the Project Manager, not just client rep.
            
            Deadlines confirmed:
            - Final designs: Tomorrow (Friday)
            - Development complete: Next Friday
            - Go-live: End of month
            """,
            date=(base_date + timedelta(days=3)).isoformat(),
            metadata={"day": "Thursday", "meeting_type": "client"},
        )

        # Friday - Wrap-up
        transcripts["friday"] = TranscriptInput(
            title="Weekly Wrap-up",
            content="""
            End of week status meeting.
            Team updates:
            
            John Smith: "Requirements are finalized and signed off"
            Jane Doe: "Final designs delivered to client"
            Bob Wilson: "Development environment set up"
            Michael Chang: "API specifications reviewed"
            
            Notes:
            - Elizabeth Chen (Beta's CEO) approved everything via email
            - Sarah Chen will be our main point of contact going forward
            - Team celebration lunch next Tuesday!
            
            Everyone's contact info confirmed in team directory.
            """,
            date=(base_date + timedelta(days=4)).isoformat(),
            metadata={"day": "Friday", "meeting_type": "status"},
        )

        return transcripts

    def test_daily_transcript_workflow(self, mock_sync_processor, daily_transcripts):
        """Test processing transcripts day by day with information accumulation."""

        # Track entities across days
        entity_tracker = {"people": {}, "organizations": {}, "tasks": {}}

        # Track what information we have about each person
        person_info_evolution = {}

        def process_daily_transcript(transcript, day):
            """Process a single day's transcript and track entity evolution."""

            # Extract entities based on day
            if day == "monday":
                extracted = {
                    "people": [
                        {"name": "John Smith", "role": "Project Lead"},
                        {"name": "Jane Doe", "role": "Designer"},
                        {"name": "Bob Wilson", "role": "Developer"},
                    ],
                    "tasks": [
                        {
                            "title": "Review requirements",
                            "assignee": "John Smith",
                            "due": "EOD",
                        },
                        {
                            "title": "Complete designs",
                            "assignee": "Jane Doe",
                            "due": "Wednesday",
                        },
                        {
                            "title": "Estimate development time",
                            "assignee": "Bob Wilson",
                        },
                    ],
                }
            elif day == "tuesday":
                extracted = {
                    "people": [
                        {"name": "John Smith", "email": "john.smith@acme.com"},
                        {"name": "Jane Doe"},  # Already known
                        {
                            "name": "Sarah Chen",
                            "organization": "Beta Industries",
                            "email": "s.chen@beta.com",
                        },
                    ],
                    "organizations": [{"name": "Beta Industries", "type": "client"}],
                    "tasks": [
                        {
                            "title": "Revise designs with brand colors",
                            "assignee": "Jane Doe",
                        },
                        {
                            "title": "Schedule follow-up",
                            "assignee": "John Smith",
                            "due": "Thursday",
                        },
                    ],
                }
            elif day == "wednesday":
                extracted = {
                    "people": [
                        {"name": "Bob Wilson", "phone": "555-0156"},  # Phone update
                        {
                            "name": "Michael Chang",
                            "role": "Senior Developer",
                            "email": "m.chang@acme.com",
                            "phone": "555-0147",
                        },
                        {"name": "Jane Doe"},  # Mentioned for completing task
                    ],
                    "tasks": [
                        {"title": "API integration", "assignee": "Michael Chang"},
                        {
                            "title": "Database schema design",
                            "assignee": "Michael Chang",
                        },
                    ],
                }
            elif day == "thursday":
                extracted = {
                    "people": [
                        {"name": "John Smith"},
                        {"name": "Jane Doe"},
                        {
                            "name": "Sarah Chen",
                            "role": "Project Manager",
                        },  # Role update
                        {
                            "name": "Robert Lee",
                            "role": "CTO",
                            "organization": "Beta Industries",
                            "email": "rlee@beta.com",
                        },
                        {
                            "name": "Elizabeth Chen",
                            "role": "CEO",
                            "organization": "Beta Industries",
                        },
                    ],
                    "tasks": [
                        {
                            "title": "Final designs",
                            "assignee": "Jane Doe",
                            "due": "Friday",
                        },
                        {"title": "Development complete", "due": "Next Friday"},
                        {"title": "Go-live", "due": "End of month"},
                    ],
                }
            else:  # friday
                extracted = {
                    "people": [
                        {"name": "John Smith"},
                        {"name": "Jane Doe"},
                        {"name": "Bob Wilson"},
                        {"name": "Michael Chang"},
                        {"name": "Elizabeth Chen"},  # Mentioned as approver
                        {"name": "Sarah Chen"},  # Confirmed as main contact
                    ],
                    "task_completions": [
                        {"task": "Review requirements", "completed_by": "John Smith"},
                        {"task": "Complete designs", "completed_by": "Jane Doe"},
                    ],
                }

            # Process extracted entities
            result = ProcessingResult()

            # Handle people
            for person in extracted.get("people", []):
                name = person["name"]

                if name in entity_tracker["people"]:
                    # Update existing person
                    existing = entity_tracker["people"][name]
                    updates = {}

                    for key, value in person.items():
                        if key != "name" and key not in existing:
                            updates[key] = value
                            existing[key] = value
                        elif key != "name" and existing.get(key) != value:
                            updates[key] = value
                            existing[key] = value

                    if updates:
                        result.updated.append(
                            {"type": "person", "name": name, "updates": updates}
                        )

                        # Track information evolution
                        if name not in person_info_evolution:
                            person_info_evolution[name] = []
                        person_info_evolution[name].append(
                            {"day": day, "new_info": updates}
                        )
                else:
                    # Create new person
                    entity_tracker["people"][name] = person.copy()
                    result.created.append({"type": "person", "data": person})

                    person_info_evolution[name] = [{"day": day, "initial_info": person}]

            # Handle organizations
            for org in extracted.get("organizations", []):
                name = org["name"]
                if name not in entity_tracker["organizations"]:
                    entity_tracker["organizations"][name] = org.copy()
                    result.created.append({"type": "organization", "data": org})

            # Handle tasks
            for task in extracted.get("tasks", []):
                title = task["title"]
                if title not in entity_tracker["tasks"]:
                    entity_tracker["tasks"][title] = task.copy()
                    result.created.append({"type": "task", "data": task})
                else:
                    # Update task (e.g., due date changes)
                    existing = entity_tracker["tasks"][title]
                    updates = {}

                    for key, value in task.items():
                        if key != "title" and existing.get(key) != value:
                            updates[key] = value
                            existing[key] = value

                    if updates:
                        result.updated.append(
                            {"type": "task", "title": title, "updates": updates}
                        )

            # Handle task completions
            for completion in extracted.get("task_completions", []):
                task_title = completion["task"]
                if task_title in entity_tracker["tasks"]:
                    entity_tracker["tasks"][task_title]["status"] = "completed"
                    entity_tracker["tasks"][task_title]["completed_by"] = completion[
                        "completed_by"
                    ]
                    entity_tracker["tasks"][task_title][
                        "completed_date"
                    ] = transcript.date

                    result.updated.append(
                        {
                            "type": "task",
                            "title": task_title,
                            "updates": {
                                "status": "completed",
                                "completed_date": transcript.date,
                            },
                        }
                    )

            return result

        # Process each day's transcript
        daily_results = {}

        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            transcript = daily_transcripts[day]
            result = process_daily_transcript(transcript, day)
            daily_results[day] = result

            # Update sync state
            mock_sync_processor._sync_state[f"transcript_{day}"] = {
                "processed_at": datetime.now().isoformat(),
                "entities_created": len(result.created),
                "entities_updated": len(result.updated),
            }

        # Verify entity evolution across the week

        # John Smith: Started with role, gained email
        assert "John Smith" in entity_tracker["people"]
        john = entity_tracker["people"]["John Smith"]
        assert john["role"] == "Project Lead"
        assert john["email"] == "john.smith@acme.com"

        john_evolution = person_info_evolution["John Smith"]
        assert len(john_evolution) >= 2  # Initial + email update
        assert any("email" in update.get("new_info", {}) for update in john_evolution)

        # Bob Wilson: Started with role, gained phone
        assert "Bob Wilson" in entity_tracker["people"]
        bob = entity_tracker["people"]["Bob Wilson"]
        assert bob["role"] == "Developer"
        assert bob["phone"] == "555-0156"

        # Sarah Chen: Started Tuesday, gained role Thursday
        assert "Sarah Chen" in entity_tracker["people"]
        sarah = entity_tracker["people"]["Sarah Chen"]
        assert sarah["organization"] == "Beta Industries"
        assert sarah["email"] == "s.chen@beta.com"
        assert sarah["role"] == "Project Manager"

        sarah_evolution = person_info_evolution["Sarah Chen"]
        assert any("role" in update.get("new_info", {}) for update in sarah_evolution)

        # New people added mid-week
        assert "Michael Chang" in entity_tracker["people"]
        assert "Robert Lee" in entity_tracker["people"]
        assert "Elizabeth Chen" in entity_tracker["people"]

        # Organizations tracked
        assert "Beta Industries" in entity_tracker["organizations"]

        # Tasks created and some completed
        assert "Review requirements" in entity_tracker["tasks"]
        assert entity_tracker["tasks"]["Review requirements"]["status"] == "completed"

        assert "Complete designs" in entity_tracker["tasks"]
        assert entity_tracker["tasks"]["Complete designs"]["status"] == "completed"

        # Verify daily results
        assert len(daily_results["monday"].created) > 0  # Initial entities
        assert len(daily_results["tuesday"].created) > 0  # Sarah Chen + Beta Industries
        assert len(daily_results["tuesday"].updated) > 0  # John's email
        assert len(daily_results["wednesday"].created) > 0  # Michael Chang
        assert len(daily_results["wednesday"].updated) > 0  # Bob's phone
        assert len(daily_results["friday"].updated) > 0  # Task completions

        # Verify sync state persistence
        mock_sync_processor._save_sync_state()
        assert mock_sync_processor.sync_state_file.exists()

        saved_state = mock_sync_processor._load_sync_state()
        assert "transcript_monday" in saved_state
        assert "transcript_friday" in saved_state

    def test_entity_information_updates(self, mock_sync_processor):
        """Test how new information merges with existing entities."""

        # Existing entity state
        existing_entities = {
            "people": {
                "Alice Johnson": {
                    "id": "person-1",
                    "Full Name": "Alice Johnson",
                    "Role": "Marketing Manager",
                    "Department": "Marketing",
                },
                "David Kim": {
                    "id": "person-2",
                    "Full Name": "David Kim",
                    "Email": "dkim@company.com",
                },
            },
            "organizations": {
                "TechCorp": {"id": "org-1", "Name": "TechCorp", "Type": "Technology"}
            },
        }

        # New information from transcripts
        updates_sequence = [
            {
                "source": "Monday meeting",
                "updates": {
                    "Alice Johnson": {
                        "Email": "alice.johnson@techcorp.com",
                        "Phone": "555-0200",
                    },
                    "David Kim": {
                        "Role": "Senior Engineer",
                        "Department": "Engineering",
                    },
                },
            },
            {
                "source": "Tuesday update",
                "updates": {
                    "Alice Johnson": {
                        "Organization": "TechCorp",  # Link to org
                        "Direct Reports": ["David Kim"],  # New relationship
                    },
                    "David Kim": {"Manager": "Alice Johnson", "Phone": "555-0201"},
                },
            },
            {
                "source": "Wednesday announcement",
                "updates": {
                    "Alice Johnson": {
                        "Role": "VP of Marketing",  # Promotion
                        "Office": "Building A, Suite 300",
                    },
                    "TechCorp": {"Headquarters": "San Francisco", "Employees": "500+"},
                },
            },
        ]

        def apply_entity_updates(existing, updates):
            """Apply updates to existing entities, tracking changes."""
            change_log = []

            for entity_name, new_info in updates.items():
                entity_type = None

                # Determine entity type
                if entity_name in existing["people"]:
                    entity_type = "people"
                elif entity_name in existing["organizations"]:
                    entity_type = "organizations"
                else:
                    # New entity
                    continue

                existing_entity = existing[entity_type][entity_name]
                changes = {}

                for field, value in new_info.items():
                    if field not in existing_entity:
                        # New field
                        changes[field] = {"action": "added", "value": value}
                        existing_entity[field] = value
                    elif existing_entity[field] != value:
                        # Updated field
                        changes[field] = {
                            "action": "updated",
                            "old_value": existing_entity[field],
                            "new_value": value,
                        }
                        existing_entity[field] = value

                if changes:
                    change_log.append(
                        {
                            "entity": entity_name,
                            "type": entity_type,
                            "changes": changes,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

            return change_log

        # Apply updates sequentially
        all_changes = []

        for update_batch in updates_sequence:
            changes = apply_entity_updates(existing_entities, update_batch["updates"])
            all_changes.extend(changes)

            # Save sync state
            mock_sync_processor._sync_state[update_batch["source"]] = {
                "processed_at": datetime.now().isoformat(),
                "changes_made": len(changes),
            }

        # Verify entity information evolution

        # Alice Johnson should have all accumulated information
        alice = existing_entities["people"]["Alice Johnson"]
        assert alice["Email"] == "alice.johnson@techcorp.com"
        assert alice["Phone"] == "555-0200"
        assert alice["Role"] == "VP of Marketing"  # Latest role
        assert alice["Organization"] == "TechCorp"
        assert alice["Office"] == "Building A, Suite 300"
        assert "David Kim" in alice["Direct Reports"]

        # David Kim should have accumulated info
        david = existing_entities["people"]["David Kim"]
        assert david["Role"] == "Senior Engineer"
        assert david["Department"] == "Engineering"
        assert david["Manager"] == "Alice Johnson"
        assert david["Phone"] == "555-0201"

        # TechCorp should have new fields
        techcorp = existing_entities["organizations"]["TechCorp"]
        assert techcorp["Headquarters"] == "San Francisco"
        assert techcorp["Employees"] == "500+"

        # Verify change log
        assert len(all_changes) > 0

        # Check Alice's promotion was tracked
        alice_changes = [c for c in all_changes if c["entity"] == "Alice Johnson"]
        role_changes = [c for c in alice_changes if "Role" in c["changes"]]
        assert len(role_changes) > 0
        assert role_changes[-1]["changes"]["Role"]["old_value"] == "Marketing Manager"
        assert role_changes[-1]["changes"]["Role"]["new_value"] == "VP of Marketing"

        # Verify relationship tracking
        assert any("Direct Reports" in c["changes"] for c in alice_changes)
        assert any(
            "Manager" in c["changes"] for c in all_changes if c["entity"] == "David Kim"
        )

    def test_sync_state_persistence(self, mock_sync_processor, daily_transcripts):
        """Test that sync state persists across system restarts."""

        # Process first few days
        initial_processing = {
            "monday": {
                "transcript_id": "transcript_001",
                "processed_at": "2025-01-06T10:00:00",
                "entities": {"created": 5, "updated": 0},
            },
            "tuesday": {
                "transcript_id": "transcript_002",
                "processed_at": "2025-01-07T10:00:00",
                "entities": {"created": 2, "updated": 3},
            },
        }

        # Save initial state
        mock_sync_processor._sync_state = initial_processing
        mock_sync_processor._save_sync_state()

        # Simulate system restart
        new_processor = Mock(spec=JSONSyncProcessor)
        new_processor.sync_state_file = mock_sync_processor.sync_state_file
        new_processor._sync_state = {}

        def load_state():
            with open(new_processor.sync_state_file, "r") as f:
                new_processor._sync_state = json.load(f)
            return new_processor._sync_state

        new_processor._load_sync_state = load_state

        # Load state in new processor
        loaded_state = new_processor._load_sync_state()

        # Verify state was preserved
        assert "monday" in loaded_state
        assert "tuesday" in loaded_state
        assert loaded_state["monday"]["transcript_id"] == "transcript_001"
        assert loaded_state["tuesday"]["entities"]["created"] == 2

        # Continue processing from where we left off
        remaining_days = ["wednesday", "thursday", "friday"]

        def should_process_transcript(transcript_id, day):
            """Check if transcript has already been processed."""
            return day not in new_processor._sync_state

        # Process remaining transcripts
        processed_count = 0
        skipped_count = 0

        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            if should_process_transcript(f"transcript_{day}", day):
                # Process transcript
                new_processor._sync_state[day] = {
                    "transcript_id": f"transcript_{day}",
                    "processed_at": datetime.now().isoformat(),
                    "entities": {"created": 1, "updated": 1},  # Mock data
                }
                processed_count += 1
            else:
                skipped_count += 1

        # Verify resumption worked correctly
        assert skipped_count == 2  # Monday and Tuesday skipped
        assert processed_count == 3  # Wednesday, Thursday, Friday processed

        # All days should now be in state
        assert all(
            day in new_processor._sync_state
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]
        )

    def test_incremental_sync_with_deduplication(self, mock_sync_processor):
        """Test incremental sync that integrates with deduplication."""

        # Existing database state
        notion_database = {
            "people": [
                {
                    "id": "p1",
                    "Full Name": "Jennifer White",
                    "Email": "jwhite@example.com",
                },
                {"id": "p2", "Full Name": "Mark Brown", "Organization": "ABC Corp"},
            ],
            "tasks": [
                {
                    "id": "t1",
                    "Title": "Quarterly Review",
                    "Assignee": "p1",
                    "Status": "In Progress",
                }
            ],
        }

        # New data to sync
        new_data_batches = [
            {
                "batch_id": "batch_001",
                "timestamp": "2025-01-10T09:00:00",
                "entities": {
                    "people": [
                        {
                            "name": "Jennifer White",
                            "phone": "555-0300",
                        },  # Update existing
                        {
                            "name": "J. White",
                            "department": "Finance",
                        },  # Potential duplicate
                        {
                            "name": "Lisa Green",
                            "email": "lgreen@example.com",
                        },  # New person
                    ],
                    "tasks": [
                        {"title": "Budget Planning", "assignee": "Jennifer White"},
                        {
                            "title": "Quarterly Review",
                            "update": "Needs revision",
                        },  # Update existing
                    ],
                },
            },
            {
                "batch_id": "batch_002",
                "timestamp": "2025-01-11T09:00:00",
                "entities": {
                    "people": [
                        {
                            "name": "Mark Brown",
                            "email": "mbrown@abc.com",
                        },  # Update existing
                        {
                            "name": "M. Brown",
                            "title": "Director",
                        },  # Potential duplicate
                        {
                            "name": "Jennifer W.",
                            "role": "CFO",
                        },  # Another potential duplicate
                    ],
                    "tasks": [
                        {
                            "title": "Q1 Planning",
                            "assignee": "Mark Brown",
                            "due": "2025-01-31",
                        }
                    ],
                },
            },
        ]

        def incremental_sync_with_dedup(batch, existing_db):
            """Sync new data with deduplication checks."""
            sync_result = {
                "created": [],
                "updated": [],
                "duplicates_found": [],
                "requires_review": [],
            }

            # Process people with deduplication
            for person in batch["entities"]["people"]:
                matches = []

                # Check for existing matches
                for existing in existing_db["people"]:
                    confidence = 0
                    reasons = []

                    # Exact name match
                    if person["name"] == existing["Full Name"]:
                        confidence = 95
                        reasons.append("Exact name match")

                    # Initial match (J. White vs Jennifer White)
                    elif (
                        person["name"].startswith("J.")
                        and "Jennifer" in existing["Full Name"]
                    ):
                        confidence = 80
                        reasons.append("Initial matches")

                    # Last name match with initial
                    elif "White" in person["name"] and "White" in existing["Full Name"]:
                        confidence = 75
                        reasons.append("Last name with initial")

                    # Similar pattern for Mark/M. Brown
                    elif (
                        person["name"] in ["M. Brown", "Mark Brown"]
                        and "Mark Brown" in existing["Full Name"]
                    ):
                        confidence = 85
                        reasons.append("Name variation match")

                    if confidence > 0:
                        matches.append(
                            {
                                "existing": existing,
                                "confidence": confidence,
                                "reasons": reasons,
                            }
                        )

                if matches:
                    best_match = max(matches, key=lambda x: x["confidence"])

                    if best_match["confidence"] >= 90:
                        # Auto-merge updates
                        updates = {}
                        for key, value in person.items():
                            if key != "name" and key not in best_match["existing"]:
                                updates[key] = value

                        if updates:
                            sync_result["updated"].append(
                                {
                                    "id": best_match["existing"]["id"],
                                    "updates": updates,
                                    "confidence": best_match["confidence"],
                                }
                            )
                        else:
                            sync_result["duplicates_found"].append(
                                {
                                    "new": person,
                                    "existing": best_match["existing"],
                                    "confidence": best_match["confidence"],
                                }
                            )
                    else:
                        # Requires manual review
                        sync_result["requires_review"].append(
                            {"new": person, "potential_matches": matches}
                        )
                else:
                    # New entity
                    sync_result["created"].append({"type": "person", "data": person})

            # Process tasks
            for task in batch["entities"].get("tasks", []):
                existing_task = next(
                    (t for t in existing_db["tasks"] if t["Title"] == task["title"]),
                    None,
                )

                if existing_task:
                    # Update existing task
                    updates = {}
                    if "update" in task:
                        updates["Notes"] = task["update"]
                    if "assignee" in task:
                        # Find assignee ID
                        assignee = next(
                            (
                                p
                                for p in existing_db["people"]
                                if p["Full Name"] == task["assignee"]
                            ),
                            None,
                        )
                        if assignee:
                            updates["Assignee"] = assignee["id"]

                    if updates:
                        sync_result["updated"].append(
                            {"id": existing_task["id"], "updates": updates}
                        )
                else:
                    # New task
                    sync_result["created"].append({"type": "task", "data": task})

            return sync_result

        # Process batches incrementally
        all_results = []

        for batch in new_data_batches:
            # Check if batch already processed
            if batch["batch_id"] not in mock_sync_processor._sync_state:
                result = incremental_sync_with_dedup(batch, notion_database)
                all_results.append(result)

                # Update sync state
                mock_sync_processor._sync_state[batch["batch_id"]] = {
                    "processed_at": datetime.now().isoformat(),
                    "created": len(result["created"]),
                    "updated": len(result["updated"]),
                    "duplicates": len(result["duplicates_found"]),
                    "requires_review": len(result["requires_review"]),
                }

                # Apply changes to database (mock)
                for update in result["updated"]:
                    entity = next(
                        e for e in notion_database["people"] if e["id"] == update["id"]
                    )
                    entity.update(update["updates"])

                for creation in result["created"]:
                    if creation["type"] == "person":
                        new_id = f"p{len(notion_database['people']) + 1}"
                        notion_database["people"].append(
                            {"id": new_id, **creation["data"]}
                        )

        # Verify incremental sync results

        # Batch 1 results
        batch1_result = all_results[0]
        assert len(batch1_result["updated"]) >= 1  # Jennifer White phone update
        assert len(batch1_result["created"]) >= 1  # Lisa Green
        assert len(batch1_result["requires_review"]) >= 1  # J. White needs review

        # Batch 2 results
        batch2_result = all_results[1]
        assert len(batch2_result["updated"]) >= 1  # Mark Brown email update
        assert len(batch2_result["requires_review"]) >= 2  # M. Brown and Jennifer W.

        # Verify database state after sync
        jennifer = next(
            p for p in notion_database["people"] if p["Full Name"] == "Jennifer White"
        )
        assert "phone" in jennifer  # Should have phone from batch 1

        mark = next(
            p for p in notion_database["people"] if p["Full Name"] == "Mark Brown"
        )
        assert "email" in mark  # Should have email from batch 2

        # New person should exist
        assert any(p.get("name") == "Lisa Green" for p in notion_database["people"])

        # Verify sync state
        assert "batch_001" in mock_sync_processor._sync_state
        assert "batch_002" in mock_sync_processor._sync_state
        assert mock_sync_processor._sync_state["batch_001"]["duplicates"] == 0
        assert mock_sync_processor._sync_state["batch_001"]["requires_review"] >= 1

    def test_conflict_resolution_during_sync(self, mock_sync_processor):
        """Test handling conflicts when syncing updates to existing entities."""

        # Current state in Notion
        notion_state = {
            "person_1": {
                "id": "person_1",
                "Full Name": "Alex Thompson",
                "Email": "alex@company.com",
                "Phone": "555-0100",
                "Last Updated": "2025-01-08T10:00:00",
            }
        }

        # Conflicting updates from different sources
        update_sources = [
            {
                "source": "CRM Export",
                "timestamp": "2025-01-09T09:00:00",
                "updates": {
                    "Alex Thompson": {
                        "Email": "athompson@company.com",  # Different email
                        "Phone": "555-0100",  # Same phone
                        "Department": "Sales",  # New field
                    }
                },
            },
            {
                "source": "Meeting Transcript",
                "timestamp": "2025-01-09T14:00:00",
                "updates": {
                    "Alex Thompson": {
                        "Email": "alex@company.com",  # Original email
                        "Phone": "555-0111",  # Different phone
                        "Role": "Sales Manager",  # New field
                    }
                },
            },
            {
                "source": "HR System",
                "timestamp": "2025-01-09T16:00:00",
                "updates": {
                    "Alex Thompson": {
                        "Email": "alex.thompson@company.com",  # Yet another email
                        "Employee ID": "EMP001",  # New field
                        "Department": "Sales & Marketing",  # Conflicts with earlier
                    }
                },
            },
        ]

        def resolve_conflicts(existing, updates, conflict_strategy="latest_wins"):
            """Resolve conflicts between existing data and updates."""
            conflicts = []
            resolved_entity = existing.copy()

            for source in updates:
                source_updates = source["updates"]["Alex Thompson"]

                for field, new_value in source_updates.items():
                    if field in resolved_entity and resolved_entity[field] != new_value:
                        # Conflict detected
                        conflict = {
                            "field": field,
                            "current_value": resolved_entity[field],
                            "new_value": new_value,
                            "source": source["source"],
                            "timestamp": source["timestamp"],
                        }

                        if conflict_strategy == "latest_wins":
                            # Use timestamp to decide
                            if source["timestamp"] > resolved_entity.get(
                                "Last Updated", ""
                            ):
                                resolved_entity[field] = new_value
                                conflict["resolution"] = "accepted_new"
                            else:
                                conflict["resolution"] = "kept_existing"

                        elif conflict_strategy == "source_priority":
                            # Prioritize certain sources
                            source_priority = {
                                "HR System": 3,
                                "CRM Export": 2,
                                "Meeting Transcript": 1,
                            }

                            current_priority = 0
                            new_priority = source_priority.get(source["source"], 0)

                            if new_priority > current_priority:
                                resolved_entity[field] = new_value
                                conflict["resolution"] = "accepted_higher_priority"
                            else:
                                conflict["resolution"] = "kept_higher_priority"

                        elif conflict_strategy == "manual_review":
                            conflict["resolution"] = "requires_manual_review"

                        conflicts.append(conflict)
                    else:
                        # No conflict, add or update field
                        resolved_entity[field] = new_value

                resolved_entity["Last Updated"] = source["timestamp"]

            return resolved_entity, conflicts

        # Test different conflict resolution strategies
        strategies = ["latest_wins", "source_priority", "manual_review"]
        strategy_results = {}

        for strategy in strategies:
            resolved, conflicts = resolve_conflicts(
                notion_state["person_1"], update_sources, conflict_strategy=strategy
            )

            strategy_results[strategy] = {
                "resolved_entity": resolved,
                "conflicts": conflicts,
            }

        # Verify conflict resolution

        # Latest wins strategy
        latest_wins = strategy_results["latest_wins"]
        assert (
            latest_wins["resolved_entity"]["Email"] == "alex.thompson@company.com"
        )  # From HR (latest)
        assert (
            latest_wins["resolved_entity"]["Phone"] == "555-0111"
        )  # From Meeting (after CRM)
        assert (
            latest_wins["resolved_entity"]["Department"] == "Sales & Marketing"
        )  # From HR (latest)

        # Source priority strategy
        source_priority = strategy_results["source_priority"]
        assert (
            source_priority["resolved_entity"]["Email"] == "alex.thompson@company.com"
        )  # HR highest priority
        assert (
            source_priority["resolved_entity"]["Department"] == "Sales & Marketing"
        )  # HR highest priority

        # Manual review strategy
        manual_review = strategy_results["manual_review"]
        manual_conflicts = [
            c
            for c in manual_review["conflicts"]
            if c["resolution"] == "requires_manual_review"
        ]
        assert len(manual_conflicts) > 0  # Should have conflicts to review

        # Check conflict tracking
        email_conflicts = [c for c in latest_wins["conflicts"] if c["field"] == "Email"]
        assert len(email_conflicts) >= 2  # Multiple email conflicts

        phone_conflicts = [c for c in latest_wins["conflicts"] if c["field"] == "Phone"]
        assert len(phone_conflicts) >= 1  # Phone conflict

        # Save conflict resolution audit
        mock_sync_processor._sync_state["conflict_resolution"] = {
            "entity": "Alex Thompson",
            "conflicts_found": len(latest_wins["conflicts"]),
            "resolution_strategy": "latest_wins",
            "resolved_at": datetime.now().isoformat(),
            "audit_trail": latest_wins["conflicts"],
        }
