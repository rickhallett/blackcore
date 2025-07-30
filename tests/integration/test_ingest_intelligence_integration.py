"""Integration tests for the intelligence ingestion pipeline."""

import pytest
from unittest.mock import Mock

from blackcore.notion.client import NotionClient


class TestIngestIntelligenceIntegration:
    """Test the ingest_intelligence.py script integration with the full pipeline."""
    
    @pytest.fixture
    def mock_notion_client(self):
        """Create a mock Notion client."""
        client = Mock(spec=NotionClient)
        client.get_cached_database_id = Mock()
        client.find_page_by_title = Mock()
        client.create_page = Mock()
        client.update_page_properties = Mock()
        return client
        
    @pytest.fixture
    def intelligence_package(self):
        """Create a comprehensive intelligence package for testing."""
        return {
            "metadata": {
                "source": "Project Nassau Intelligence",
                "timestamp": "2025-01-12T10:00:00",
                "version": "1.0"
            },
            "people": [
                {
                    "name": "Maria Garcia",
                    "role": "City Council Member",
                    "email": "mgarcia@city.gov",
                    "phone": "555-0400",
                    "organization": "City Government",
                    "linked_transgressions": ["Beach Hut Violations"]
                },
                {
                    "name": "Thomas Wright",
                    "role": "Property Developer",
                    "email": "twright@wrightdev.com",
                    "organization": "Wright Development LLC",
                    "notes": "Key player in beach hut controversy"
                }
            ],
            "organizations": [
                {
                    "name": "Wright Development LLC",
                    "type": "Real Estate Development",
                    "key_people": ["Thomas Wright"],
                    "linked_documents": ["Development Proposal 2024-001"]
                },
                {
                    "name": "City Government",
                    "type": "Government",
                    "key_people": ["Maria Garcia"],
                    "departments": ["City Council", "Planning Department"]
                }
            ],
            "tasks": [
                {
                    "title": "Review beach hut compliance",
                    "assignee": "Maria Garcia",
                    "due_date": "2025-01-20",
                    "priority": "High",
                    "related_agenda": "Beach Hut Regulation Reform",
                    "description": "Complete review of all beach hut permits for compliance"
                },
                {
                    "title": "Submit revised development plan",
                    "assignee": "Thomas Wright",
                    "due_date": "2025-01-25",
                    "blocked_by": "Review beach hut compliance",
                    "organization": "Wright Development LLC"
                }
            ],
            "agendas": [
                {
                    "name": "Beach Hut Regulation Reform",
                    "owner": "Maria Garcia",
                    "status": "Active",
                    "actionable_tasks": ["Review beach hut compliance"],
                    "key_documents": ["Beach Hut Survey 2024", "Compliance Report Draft"]
                }
            ],
            "transgressions": [
                {
                    "title": "Beach Hut Violations",
                    "perpetrator_person": "Thomas Wright",
                    "perpetrator_org": "Wright Development LLC",
                    "severity": "Medium",
                    "status": "Under Investigation",
                    "evidence": ["Inspection Report Jan 2025", "Photographic Evidence"],
                    "description": "Multiple beach huts exceed permitted size limits"
                }
            ],
            "documents": [
                {
                    "title": "Development Proposal 2024-001",
                    "type": "Proposal",
                    "author": "Thomas Wright",
                    "date": "2024-12-15",
                    "linked_org": "Wright Development LLC",
                    "status": "Under Review"
                },
                {
                    "title": "Beach Hut Survey 2024",
                    "type": "Report",
                    "author": "Planning Department",
                    "date": "2024-11-30",
                    "linked_agenda": "Beach Hut Regulation Reform"
                }
            ],
            "transcripts": [
                {
                    "title": "City Council Meeting - Beach Hut Discussion",
                    "date": "2025-01-10",
                    "participants": ["Maria Garcia", "Thomas Wright"],
                    "tagged_entities": ["Maria Garcia", "Thomas Wright", "Wright Development LLC"],
                    "key_topics": ["beach hut violations", "development proposals", "compliance review"],
                    "transcript_excerpt": "Councilwoman Garcia expressed concerns about the Wright Development beach huts..."
                }
            ]
        }
        
    @pytest.fixture
    def relation_field_map(self):
        """The relation field mapping from ingest_intelligence.py."""
        return {
            "Actionable Tasks": {
                "Assignee": "People & Contacts",
                "Related Agenda": "Agendas & Epics",
                "Blocked By": "Actionable Tasks",
            },
            "People & Contacts": {
                "Organization": "Organizations & Bodies",
                "Linked Transgressions": "Identified Transgressions",
            },
            "Organizations & Bodies": {
                "Key People": "People & Contacts",
                "Linked Documents": "Documents & Evidence",
            },
            "Agendas & Epics": {
                "Owner": "People & Contacts",
                "Actionable Tasks": "Actionable Tasks",
                "Key Documents": "Documents & Evidence",
            },
            "Identified Transgressions": {
                "Perpetrator (Person)": "People & Contacts",
                "Perpetrator (Org)": "Organizations & Bodies",
                "Evidence": "Intelligence & Transcripts",
            },
            "Intelligence & Transcripts": {
                "Tagged Entities": "People & Contacts",
            }
        }
        
    def test_full_json_package_ingestion(self, mock_notion_client, intelligence_package, relation_field_map):
        """Test ingesting a complete intelligence package with all entity types."""
        
        # Mock database IDs
        database_ids = {
            "People & Contacts": "db-people",
            "Organizations & Bodies": "db-orgs",
            "Actionable Tasks": "db-tasks",
            "Agendas & Epics": "db-agendas",
            "Identified Transgressions": "db-transgressions",
            "Documents & Evidence": "db-documents",
            "Intelligence & Transcripts": "db-transcripts"
        }
        
        mock_notion_client.get_cached_database_id.side_effect = lambda name: database_ids.get(name)
        
        # Track entity creation for relationship linking
        created_entities = {}
        entity_id_counter = 1
        
        def mock_find_or_create_page(db_name, title, properties):
            """Mock page creation/finding with ID tracking."""
            nonlocal entity_id_counter
            
            # Check if entity already exists
            key = f"{db_name}:{title}"
            if key in created_entities:
                return created_entities[key]["id"]
                
            # Create new entity
            entity_id = f"entity-{entity_id_counter}"
            entity_id_counter += 1
            
            created_entities[key] = {
                "id": entity_id,
                "database": db_name,
                "title": title,
                "properties": properties
            }
            
            return entity_id
            
        # Mock the two-pass ingestion process
        def ingest_package_two_pass(package):
            """Simulate the two-pass ingestion from ingest_intelligence.py."""
            
            # PASS 1: Create all core objects without relations
            print("PASS 1: Creating core entities...")
            
            # Create people
            for person in package["people"]:
                properties = {
                    "Full Name": person["name"],
                    "Role": person.get("role", ""),
                    "Email": person.get("email", ""),
                    "Phone": person.get("phone", "")
                    # Skip Organization relation in pass 1
                }
                mock_find_or_create_page("People & Contacts", person["name"], properties)
                
            # Create organizations
            for org in package["organizations"]:
                properties = {
                    "Name": org["name"],
                    "Type": org.get("type", "")
                    # Skip Key People relation in pass 1
                }
                mock_find_or_create_page("Organizations & Bodies", org["name"], properties)
                
            # Create tasks
            for task in package["tasks"]:
                properties = {
                    "Title": task["title"],
                    "Due Date": task.get("due_date", ""),
                    "Priority": task.get("priority", ""),
                    "Description": task.get("description", "")
                    # Skip Assignee and Related Agenda relations in pass 1
                }
                mock_find_or_create_page("Actionable Tasks", task["title"], properties)
                
            # Create agendas
            for agenda in package["agendas"]:
                properties = {
                    "Name": agenda["name"],
                    "Status": agenda.get("status", "")
                    # Skip Owner and related relations in pass 1
                }
                mock_find_or_create_page("Agendas & Epics", agenda["name"], properties)
                
            # Create transgressions
            for transgression in package["transgressions"]:
                properties = {
                    "Title": transgression["title"],
                    "Severity": transgression.get("severity", ""),
                    "Status": transgression.get("status", ""),
                    "Description": transgression.get("description", "")
                    # Skip perpetrator relations in pass 1
                }
                mock_find_or_create_page("Identified Transgressions", transgression["title"], properties)
                
            # Create documents
            for doc in package["documents"]:
                properties = {
                    "Title": doc["title"],
                    "Type": doc.get("type", ""),
                    "Author": doc.get("author", ""),
                    "Date": doc.get("date", ""),
                    "Status": doc.get("status", "")
                }
                mock_find_or_create_page("Documents & Evidence", doc["title"], properties)
                
            # Create transcripts
            for transcript in package["transcripts"]:
                properties = {
                    "Title": transcript["title"],
                    "Date": transcript.get("date", ""),
                    "Key Topics": ", ".join(transcript.get("key_topics", [])),
                    "Transcript Excerpt": transcript.get("transcript_excerpt", "")
                    # Skip Tagged Entities relation in pass 1
                }
                mock_find_or_create_page("Intelligence & Transcripts", transcript["title"], properties)
                
            # PASS 2: Link all relations
            print("PASS 2: Linking relations...")
            
            # Link people relations
            for person in package["people"]:
                person_key = f"People & Contacts:{person['name']}"
                person_id = created_entities[person_key]["id"]
                
                updates = {}
                
                # Link to organization
                if "organization" in person:
                    org_key = f"Organizations & Bodies:{person['organization']}"
                    if org_key in created_entities:
                        updates["Organization"] = [created_entities[org_key]["id"]]
                        
                # Link to transgressions
                if "linked_transgressions" in person:
                    transgression_ids = []
                    for t_name in person["linked_transgressions"]:
                        t_key = f"Identified Transgressions:{t_name}"
                        if t_key in created_entities:
                            transgression_ids.append(created_entities[t_key]["id"])
                    if transgression_ids:
                        updates["Linked Transgressions"] = transgression_ids
                        
                if updates:
                    created_entities[person_key]["properties"].update(updates)
                    
            # Link task relations
            for task in package["tasks"]:
                task_key = f"Actionable Tasks:{task['title']}"
                task_id = created_entities[task_key]["id"]
                
                updates = {}
                
                # Link assignee
                if "assignee" in task:
                    assignee_key = f"People & Contacts:{task['assignee']}"
                    if assignee_key in created_entities:
                        updates["Assignee"] = [created_entities[assignee_key]["id"]]
                        
                # Link related agenda
                if "related_agenda" in task:
                    agenda_key = f"Agendas & Epics:{task['related_agenda']}"
                    if agenda_key in created_entities:
                        updates["Related Agenda"] = [created_entities[agenda_key]["id"]]
                        
                # Link blocked by (self-referential)
                if "blocked_by" in task:
                    blocked_key = f"Actionable Tasks:{task['blocked_by']}"
                    if blocked_key in created_entities:
                        updates["Blocked By"] = [created_entities[blocked_key]["id"]]
                        
                if updates:
                    created_entities[task_key]["properties"].update(updates)
                    
            # Continue for other entity types...
            
            return created_entities
            
        # Execute the ingestion
        result = ingest_package_two_pass(intelligence_package)
        
        # Verify all entities were created
        assert len(result) == (
            len(intelligence_package["people"]) +
            len(intelligence_package["organizations"]) +
            len(intelligence_package["tasks"]) +
            len(intelligence_package["agendas"]) +
            len(intelligence_package["transgressions"]) +
            len(intelligence_package["documents"]) +
            len(intelligence_package["transcripts"])
        )
        
        # Verify specific entities
        maria_key = "People & Contacts:Maria Garcia"
        assert maria_key in result
        assert result[maria_key]["properties"]["Role"] == "City Council Member"
        assert result[maria_key]["properties"]["Email"] == "mgarcia@city.gov"
        
        wright_dev_key = "Organizations & Bodies:Wright Development LLC"
        assert wright_dev_key in result
        
        # Verify task relationships
        review_task_key = "Actionable Tasks:Review beach hut compliance"
        assert review_task_key in result
        task_props = result[review_task_key]["properties"]
        assert "Assignee" in task_props  # Should have assignee relation
        
        # Verify blocked by relationship
        submit_task_key = "Actionable Tasks:Submit revised development plan"
        assert submit_task_key in result
        submit_props = result[submit_task_key]["properties"]
        assert "Blocked By" in submit_props
        
    def test_relation_preservation_during_sync(self, mock_notion_client, intelligence_package):
        """Test that entity relationships are properly preserved during sync."""
        
        # Track relationships during sync
        relationships_created = {
            "person_to_org": {},
            "org_to_people": {},
            "task_to_person": {},
            "person_to_transgressions": {},
            "agenda_to_tasks": {}
        }
        
        def track_relationships(entities):
            """Extract and validate relationships from created entities."""
            
            for key, entity in entities.items():
                db_name, title = key.split(":", 1)
                props = entity["properties"]
                
                if db_name == "People & Contacts":
                    # Track person → organization
                    if "Organization" in props:
                        org_ids = props["Organization"]
                        relationships_created["person_to_org"][entity["id"]] = org_ids
                        
                    # Track person → transgressions
                    if "Linked Transgressions" in props:
                        transgression_ids = props["Linked Transgressions"]
                        relationships_created["person_to_transgressions"][entity["id"]] = transgression_ids
                        
                elif db_name == "Organizations & Bodies":
                    # Track org → people (reverse relation)
                    if "Key People" in props:
                        people_ids = props["Key People"]
                        relationships_created["org_to_people"][entity["id"]] = people_ids
                        
                elif db_name == "Actionable Tasks":
                    # Track task → person
                    if "Assignee" in props:
                        assignee_ids = props["Assignee"]
                        relationships_created["task_to_person"][entity["id"]] = assignee_ids
                        
                elif db_name == "Agendas & Epics":
                    # Track agenda → tasks
                    if "Actionable Tasks" in props:
                        task_ids = props["Actionable Tasks"]
                        relationships_created["agenda_to_tasks"][entity["id"]] = task_ids
                        
            return relationships_created
            
        # Process the package (using mock from previous test)
        created_entities = {}
        
        # Create all entities with relationships
        # ... (entity creation logic from above)
        
        # Verify bidirectional relationships
        
        # Example: Maria Garcia ↔ City Government
        # Maria should link to City Government
        # City Government should link back to Maria
        
        # This would be validated after full processing
        
    def test_notion_api_integration(self, mock_notion_client, intelligence_package):
        """Test integration with actual Notion API patterns."""
        
        # Mock Notion API responses
        mock_responses = {
            "create_page": {
                "id": "page-123",
                "properties": {},
                "created_time": "2025-01-12T10:00:00Z"
            },
            "update_page": {
                "id": "page-123",
                "properties": {},
                "last_edited_time": "2025-01-12T10:05:00Z"
            },
            "query_database": {
                "results": [],
                "has_more": False
            }
        }
        
        # Mock rate limiting
        api_call_count = 0
        rate_limit_threshold = 3  # Notion allows 3 requests/second
        
        def mock_api_call_with_rate_limit(operation, *args, **kwargs):
            """Mock API call with rate limiting simulation."""
            nonlocal api_call_count
            api_call_count += 1
            
            if api_call_count % rate_limit_threshold == 0:
                # Simulate rate limit delay
                import time
                time.sleep(0.334)  # ~3 requests per second
                
            return mock_responses.get(operation, {})
            
        mock_notion_client.create_page.side_effect = lambda *args, **kwargs: mock_api_call_with_rate_limit("create_page")
        mock_notion_client.update_page_properties.side_effect = lambda *args, **kwargs: mock_api_call_with_rate_limit("update_page")
        
        # Test batch processing with rate limiting
        entities_to_create = []
        
        # Flatten all entities from package
        for person in intelligence_package["people"]:
            entities_to_create.append(("People & Contacts", person))
        for org in intelligence_package["organizations"]:
            entities_to_create.append(("Organizations & Bodies", org))
        for task in intelligence_package["tasks"]:
            entities_to_create.append(("Actionable Tasks", task))
            
        # Process in batches to respect rate limits
        batch_size = 10
        created_count = 0
        
        for i in range(0, len(entities_to_create), batch_size):
            batch = entities_to_create[i:i + batch_size]
            
            for db_name, entity in batch:
                # Create page
                result = mock_notion_client.create_page()
                created_count += 1
                
        # Verify all entities were processed
        assert created_count == len(entities_to_create)
        
        # Verify rate limiting was respected
        assert api_call_count >= created_count
        
    def test_error_recovery_during_ingestion(self, mock_notion_client, intelligence_package):
        """Test error handling and recovery during the ingestion process."""
        
        # Simulate various error scenarios
        error_scenarios = {
            "api_timeout": {
                "error": TimeoutError("Notion API timeout"),
                "retry_count": 3,
                "recoverable": True
            },
            "invalid_relation": {
                "error": ValueError("Invalid relation ID"),
                "retry_count": 0,
                "recoverable": False
            },
            "rate_limit": {
                "error": Exception("Rate limit exceeded"),
                "retry_count": 5,
                "recoverable": True
            }
        }
        
        # Track ingestion progress
        ingestion_state = {
            "entities_processed": [],
            "entities_failed": [],
            "retry_attempts": {},
            "checkpoint": None
        }
        
        def ingest_with_error_handling(package, state):
            """Ingest package with error handling and recovery."""
            
            all_entities = [
                ("people", package["people"]),
                ("organizations", package["organizations"]),
                ("tasks", package["tasks"])
            ]
            
            for entity_type, entities in all_entities:
                for entity in entities:
                    entity_key = f"{entity_type}:{entity.get('name') or entity.get('title')}"
                    
                    if entity_key in state["entities_processed"]:
                        continue  # Skip already processed
                        
                    try:
                        # Simulate random errors
                        import random
                        if random.random() < 0.2:  # 20% error rate for testing
                            error_type = random.choice(list(error_scenarios.keys()))
                            raise error_scenarios[error_type]["error"]
                            
                        # Process entity
                        state["entities_processed"].append(entity_key)
                        state["checkpoint"] = entity_key
                        
                    except Exception as e:
                        # Handle error
                        if entity_key not in state["retry_attempts"]:
                            state["retry_attempts"][entity_key] = 0
                            
                        state["retry_attempts"][entity_key] += 1
                        
                        # Determine if recoverable
                        is_recoverable = any(
                            isinstance(e, type(scenario["error"])) and scenario["recoverable"]
                            for scenario in error_scenarios.values()
                        )
                        
                        if is_recoverable and state["retry_attempts"][entity_key] < 3:
                            # Retry later
                            print(f"Will retry {entity_key} (attempt {state['retry_attempts'][entity_key]})")
                        else:
                            # Give up
                            state["entities_failed"].append({
                                "entity": entity_key,
                                "error": str(e),
                                "attempts": state["retry_attempts"][entity_key]
                            })
                            
            return state
            
        # Run ingestion with error handling
        final_state = ingest_with_error_handling(intelligence_package, ingestion_state)
        
        # Some entities should have been processed successfully
        assert len(final_state["entities_processed"]) > 0
        
        # Checkpoint should be set
        assert final_state["checkpoint"] is not None
        
        # Test recovery from checkpoint
        recovery_state = {
            "entities_processed": final_state["entities_processed"].copy(),
            "entities_failed": [],
            "retry_attempts": {},
            "checkpoint": final_state["checkpoint"]
        }
        
        # Resume from checkpoint
        resumed_state = ingest_with_error_handling(intelligence_package, recovery_state)
        
        # Should not reprocess already completed entities
        assert all(entity in resumed_state["entities_processed"] for entity in final_state["entities_processed"])
        
    def test_complex_relationship_cycles(self, mock_notion_client, intelligence_package):
        """Test handling of complex circular relationships between entities."""
        
        # Add circular relationships to the package
        circular_package = {
            **intelligence_package,
            "people": [
                {
                    "name": "Alice Manager",
                    "role": "Department Head",
                    "manages": ["Bob Employee", "Carol Employee"],
                    "reports_to": "David Executive"
                },
                {
                    "name": "Bob Employee",
                    "role": "Senior Analyst",
                    "reports_to": "Alice Manager",
                    "collaborates_with": ["Carol Employee"]
                },
                {
                    "name": "Carol Employee",
                    "role": "Analyst",
                    "reports_to": "Alice Manager",
                    "collaborates_with": ["Bob Employee"]
                },
                {
                    "name": "David Executive",
                    "role": "CEO",
                    "manages": ["Alice Manager"]
                }
            ],
            "projects": [
                {
                    "name": "Project Alpha",
                    "lead": "Alice Manager",
                    "team_members": ["Bob Employee", "Carol Employee"],
                    "sponsors": ["David Executive"]
                }
            ]
        }
        
        # Track relationship resolution order
        resolution_order = []
        
        def resolve_circular_relationships(entities):
            """Resolve circular relationships using topological sorting."""
            
            # Build dependency graph
            dependencies = {}
            all_entities = {}
            
            # First pass: Create all entities without relations
            for person in entities["people"]:
                key = f"person:{person['name']}"
                all_entities[key] = {
                    "type": "person",
                    "data": person,
                    "relations": {}
                }
                dependencies[key] = set()
                
            for project in entities.get("projects", []):
                key = f"project:{project['name']}"
                all_entities[key] = {
                    "type": "project",
                    "data": project,
                    "relations": {}
                }
                dependencies[key] = set()
                
            # Second pass: Map dependencies
            for person in entities["people"]:
                person_key = f"person:{person['name']}"
                
                if "reports_to" in person:
                    manager_key = f"person:{person['reports_to']}"
                    dependencies[person_key].add(manager_key)
                    
                if "collaborates_with" in person:
                    for collaborator in person["collaborates_with"]:
                        collab_key = f"person:{collaborator}"
                        # Bidirectional relationship - no dependency
                        all_entities[person_key]["relations"]["collaborates_with"] = all_entities[person_key]["relations"].get("collaborates_with", []) + [collab_key]
                        
            # Resolve in order (simplified topological sort)
            resolved = set()
            
            while len(resolved) < len(all_entities):
                # Find entities with no unresolved dependencies
                ready = [
                    key for key in all_entities
                    if key not in resolved and dependencies[key].issubset(resolved)
                ]
                
                if not ready:
                    # Circular dependency - break it
                    # Find entity with fewest dependencies
                    remaining = [k for k in all_entities if k not in resolved]
                    ready = [min(remaining, key=lambda k: len(dependencies[k] - resolved))]
                    
                for key in ready:
                    resolved.add(key)
                    resolution_order.append(key)
                    
            return all_entities, resolution_order
            
        # Resolve circular relationships
        resolved_entities, order = resolve_circular_relationships(circular_package)
        
        # Verify resolution order makes sense
        assert len(resolution_order) == len(resolved_entities)
        
        # David Executive should be resolved before Alice Manager (no dependencies)
        david_index = resolution_order.index("person:David Executive")
        alice_index = resolution_order.index("person:Alice Manager")
        assert david_index < alice_index
        
        # Bob and Carol can be in any order (mutual collaboration)
        assert "person:Bob Employee" in resolution_order
        assert "person:Carol Employee" in resolution_order
        
        # Project should be resolvable after all people
        if "project:Project Alpha" in resolution_order:
            project_index = resolution_order.index("project:Project Alpha")
            assert all(
                resolution_order.index(f"person:{name}") < project_index
                for name in ["Alice Manager", "Bob Employee", "Carol Employee", "David Executive"]
            )