"""Mock data loader for testing Agent B modules without Agent A.

This module provides a simple mock implementation of the DataLoader protocol
that Agent A will eventually provide.
"""

from typing import List, Dict, Any, Optional
import uuid
import random
from datetime import datetime, timedelta

from .relationships.interfaces import DataLoader


class MockDataLoader:
    """Mock implementation of DataLoader for testing."""
    
    def __init__(self):
        self.data = self._generate_mock_data()
    
    def load_entity(self, entity_id: str, database_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load a single entity by ID."""
        return self.data.get(entity_id)
    
    def load_entities(self, entity_ids: List[str], database_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load multiple entities by IDs."""
        entities = []
        for entity_id in entity_ids:
            entity = self.data.get(entity_id)
            if entity:
                entities.append(entity)
        return entities
    
    def load_related_entities(
        self,
        entity: Dict[str, Any],
        relationship_field: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Load entities related through a specific field."""
        related_ids = entity.get(relationship_field, [])
        
        # Handle single ID vs list of IDs
        if isinstance(related_ids, str):
            related_ids = [related_ids]
        
        # Load related entities
        related_entities = self.load_entities(related_ids)
        
        # Apply filters if provided
        if filters:
            filtered = []
            for e in related_entities:
                match = True
                for field, value in filters.items():
                    if field in e:
                        # Handle different filter types
                        if isinstance(value, dict):
                            # Complex filter
                            if not self._matches_complex_filter(e[field], value):
                                match = False
                                break
                        else:
                            # Simple equality
                            if e[field] != value:
                                match = False
                                break
                    else:
                        match = False
                        break
                
                if match:
                    filtered.append(e)
            
            return filtered
        
        return related_entities
    
    def _matches_complex_filter(self, value: Any, filter_spec: Dict[str, Any]) -> bool:
        """Check if value matches complex filter."""
        for op, expected in filter_spec.items():
            if op == "$in" and value not in expected:
                return False
            elif op == "$gt" and not (value > expected):
                return False
            elif op == "$gte" and not (value >= expected):
                return False
            elif op == "$lt" and not (value < expected):
                return False
            elif op == "$lte" and not (value <= expected):
                return False
            elif op == "$ne" and value == expected:
                return False
        
        return True
    
    def _generate_mock_data(self) -> Dict[str, Dict[str, Any]]:
        """Generate mock data for testing."""
        data = {}
        
        # Generate people
        people_names = [
            "John Smith", "Jane Doe", "Bob Johnson", "Alice Williams",
            "Charlie Brown", "Diana Prince", "Edward Norton", "Fiona Apple"
        ]
        
        people_ids = []
        for i, name in enumerate(people_names):
            person_id = f"person_{i+1}"
            people_ids.append(person_id)
            
            data[person_id] = {
                "id": person_id,
                "type": "person",
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}@example.com",
                "status": random.choice(["active", "inactive"]),
                "created_at": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                "organization_id": f"org_{random.randint(1, 3)}",
                "task_ids": []
            }
        
        # Generate organizations
        org_names = ["TechCorp", "DataSystems Inc", "Global Solutions"]
        org_ids = []
        
        for i, name in enumerate(org_names):
            org_id = f"org_{i+1}"
            org_ids.append(org_id)
            
            # Assign members
            members = random.sample(people_ids, k=random.randint(2, 4))
            
            data[org_id] = {
                "id": org_id,
                "type": "organization",
                "name": name,
                "industry": random.choice(["Technology", "Finance", "Healthcare"]),
                "size": random.choice(["Small", "Medium", "Large"]),
                "member_ids": members,
                "created_at": (datetime.now() - timedelta(days=random.randint(100, 500))).isoformat()
            }
        
        # Generate tasks
        task_titles = [
            "Complete project documentation",
            "Review code changes",
            "Prepare presentation",
            "Update database schema",
            "Fix security vulnerabilities",
            "Implement new feature",
            "Write unit tests",
            "Deploy to production"
        ]
        
        for i, title in enumerate(task_titles):
            task_id = f"task_{i+1}"
            assignee_id = random.choice(people_ids)
            
            task = {
                "id": task_id,
                "type": "task",
                "title": title,
                "description": f"Task description for: {title}",
                "status": random.choice(["open", "in_progress", "completed", "closed"]),
                "priority": random.choice(["low", "medium", "high", "critical"]),
                "assignee_id": assignee_id,
                "created_at": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                "due_date": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat()
            }
            
            data[task_id] = task
            
            # Add task to assignee's task list
            if assignee_id in data:
                data[assignee_id]["task_ids"].append(task_id)
        
        # Generate some relationships
        # Add manager relationships
        for i in range(1, len(people_ids)):
            person_id = people_ids[i]
            manager_id = people_ids[random.randint(0, i-1)]
            data[person_id]["manager_id"] = manager_id
        
        # Generate events
        event_names = [
            "Q1 Planning Meeting",
            "Annual Conference",
            "Team Building Event",
            "Product Launch"
        ]
        
        for i, name in enumerate(event_names):
            event_id = f"event_{i+1}"
            participants = random.sample(people_ids, k=random.randint(3, 6))
            
            data[event_id] = {
                "id": event_id,
                "type": "event",
                "name": name,
                "date": (datetime.now() + timedelta(days=random.randint(-30, 60))).isoformat(),
                "location": random.choice(["Conference Room A", "Virtual", "Auditorium"]),
                "participant_ids": participants,
                "organizer_id": random.choice(people_ids)
            }
        
        # Generate documents
        doc_titles = [
            "Project Proposal",
            "Technical Specification",
            "Meeting Minutes",
            "Budget Report"
        ]
        
        for i, title in enumerate(doc_titles):
            doc_id = f"doc_{i+1}"
            author_id = random.choice(people_ids)
            
            data[doc_id] = {
                "id": doc_id,
                "type": "document",
                "title": title,
                "content": f"Content of {title}...",
                "author_id": author_id,
                "created_at": (datetime.now() - timedelta(days=random.randint(1, 180))).isoformat(),
                "tags": random.sample(["important", "draft", "final", "confidential", "public"], k=2)
            }
        
        return data
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Get all data for testing search functionality."""
        return list(self.data.values())