"""Test transcript library with expected entity extraction outcomes.

This module provides a structured collection of test transcripts with known
expected entity extraction results for validating AI semantic accuracy.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum

from blackcore.minimal.models import EntityType, ExtractedEntities, Entity, Relationship


class TranscriptCategory(Enum):
    """Categories of test transcripts."""
    MEETING = "meeting"
    SECURITY_INCIDENT = "security_incident"
    PARTNERSHIP = "partnership"
    PROJECT_PLANNING = "project_planning"
    INVESTIGATION = "investigation"
    BOARD_MEETING = "board_meeting"


@dataclass
class ExpectedEntity:
    """Expected entity extraction result."""
    name: str
    type: EntityType
    required_properties: Dict[str, Any] = field(default_factory=dict)
    optional_properties: Dict[str, Any] = field(default_factory=dict)
    name_variations: List[str] = field(default_factory=list)  # Alternative names that should match
    
    def matches_extracted_entity(self, entity: Entity) -> bool:
        """Check if an extracted entity matches this expected entity."""
        # Check name match (exact or variations)
        name_match = (
            self.name.lower() in entity.name.lower() or
            entity.name.lower() in self.name.lower() or
            any(var.lower() in entity.name.lower() for var in self.name_variations)
        )
        
        # Check type match
        type_match = entity.type == self.type
        
        # Check required properties are present
        props_match = all(
            key in entity.properties for key in self.required_properties.keys()
        )
        
        return name_match and type_match and props_match


@dataclass  
class ExpectedRelationship:
    """Expected relationship extraction result."""
    source_entity_name: str
    target_entity_name: str
    relationship_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpectedExtractionOutcome:
    """Complete expected outcome for a test transcript."""
    min_entities: int  # Minimum number of entities expected
    max_entities: Optional[int] = None  # Maximum entities (None = no limit)
    required_entities: List[ExpectedEntity] = field(default_factory=list)
    optional_entities: List[ExpectedEntity] = field(default_factory=list)
    expected_relationships: List[ExpectedRelationship] = field(default_factory=list)
    required_entity_types: Set[EntityType] = field(default_factory=set)
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "entity_coverage": 0.8,  # Min % of required entities found
        "type_accuracy": 0.9,    # Min % of entities with correct types
        "name_accuracy": 0.7,    # Min % of entities with acceptable names
    })


@dataclass
class TestTranscript:
    """A test transcript with expected extraction outcomes."""
    id: str
    title: str
    category: TranscriptCategory
    content: str
    expected_outcome: ExpectedExtractionOutcome
    description: str = ""
    tags: List[str] = field(default_factory=list)


class TestTranscriptLibrary:
    """Library of test transcripts for entity extraction validation."""
    
    def __init__(self):
        self._transcripts = self._build_transcript_library()
    
    def get_transcript(self, transcript_id: str) -> Optional[TestTranscript]:
        """Get a specific transcript by ID."""
        return self._transcripts.get(transcript_id)
    
    def get_transcripts_by_category(self, category: TranscriptCategory) -> List[TestTranscript]:
        """Get all transcripts in a specific category."""
        return [t for t in self._transcripts.values() if t.category == category]
    
    def get_all_transcripts(self) -> List[TestTranscript]:
        """Get all transcripts in the library."""
        return list(self._transcripts.values())
    
    def get_transcripts_by_tags(self, tags: List[str]) -> List[TestTranscript]:
        """Get transcripts that have any of the specified tags."""
        return [
            t for t in self._transcripts.values() 
            if any(tag in t.tags for tag in tags)
        ]
    
    def _build_transcript_library(self) -> Dict[str, TestTranscript]:
        """Build the complete library of test transcripts."""
        transcripts = {}
        
        # Simple meeting transcript
        transcripts["simple_meeting"] = TestTranscript(
            id="simple_meeting",
            title="Q4 Strategy Session",
            category=TranscriptCategory.MEETING,
            description="Basic meeting with clear entities and action items",
            tags=["basic", "meeting", "strategy"],
            content="""
            Meeting Notes - Q4 Strategy Session
            Date: October 15, 2025
            
            Attendees:
            - John Smith (CEO, Acme Corporation) - john.smith@acme.com
            - Sarah Johnson (VP Sales, Acme Corporation)
            - Mike Chen (Senior Engineer, Acme Corporation)
            
            Discussion Points:
            1. Q4 revenue targets - need to hit $2.5M 
            2. New product launch timeline - targeting January 2026
            3. Team expansion plans - hiring 5 engineers
            
            Action Items:
            - Sarah to prepare sales forecast by Friday
            - Mike to complete technical feasibility study for new product
            - Schedule follow-up meeting for next week
            
            Location: NYC Headquarters, Conference Room A
            """,
            expected_outcome=ExpectedExtractionOutcome(
                min_entities=7,
                max_entities=12,
                required_entities=[
                    ExpectedEntity(
                        name="John Smith",
                        type=EntityType.PERSON,
                        required_properties={"role": "CEO", "email": "john.smith@acme.com"},
                        name_variations=["John", "Smith"]
                    ),
                    ExpectedEntity(
                        name="Sarah Johnson", 
                        type=EntityType.PERSON,
                        required_properties={"role": "VP Sales"},
                        name_variations=["Sarah"]
                    ),
                    ExpectedEntity(
                        name="Mike Chen",
                        type=EntityType.PERSON, 
                        required_properties={"role": "Senior Engineer"},
                        name_variations=["Mike"]
                    ),
                    ExpectedEntity(
                        name="Acme Corporation",
                        type=EntityType.ORGANIZATION,
                        name_variations=["Acme"]
                    ),
                    ExpectedEntity(
                        name="sales forecast",
                        type=EntityType.TASK,
                        required_properties={"assignee": "Sarah", "deadline": "Friday"}
                    ),
                    ExpectedEntity(
                        name="technical feasibility study", 
                        type=EntityType.TASK,
                        required_properties={"assignee": "Mike"}
                    ),
                ],
                required_entity_types={EntityType.PERSON, EntityType.ORGANIZATION, EntityType.TASK, EntityType.PLACE}
            )
        )
        
        # Security incident transcript
        transcripts["security_incident"] = TestTranscript(
            id="security_incident",
            title="Database Breach Incident",
            category=TranscriptCategory.SECURITY_INCIDENT,
            description="Security incident with transgression, people, and response actions",
            tags=["security", "incident", "breach", "complex"],
            content="""
            CONFIDENTIAL - Security Incident Report
            Date: January 15, 2025
            Incident ID: SEC-2025-001
            
            Summary: Unauthorized access detected to customer database
            Severity: High
            
            Timeline:
            - 14:30 UTC: Suspicious login attempts detected
            - 14:45 UTC: Database breach confirmed
            - 15:00 UTC: Systems isolated by security team
            - 15:30 UTC: Incident response team activated
            
            Affected Systems:
            - Customer Database (PostgreSQL)
            - Backup systems temporarily compromised
            - User authentication service
            
            Response Team:
            - Alex Rodriguez (Security Lead) - alex.rodriguez@company.com
            - Dr. Lisa Wang (CISO) 
            - Tom Brown (Infrastructure Manager)
            
            Immediate Actions:
            - Reset all administrative passwords
            - Audit database access logs
            - Notify legal team and affected customers
            - Implement additional firewall rules
            
            Impact: ~500 customer records potentially accessed
            Location: Data Center Alpha, Server Room B
            """,
            expected_outcome=ExpectedExtractionOutcome(
                min_entities=10,
                max_entities=18,
                required_entities=[
                    ExpectedEntity(
                        name="Unauthorized access to customer database",
                        type=EntityType.TRANSGRESSION,
                        required_properties={"severity": "High", "impact": "~500 customer records"},
                        name_variations=["Database breach", "Security incident", "Breach"]
                    ),
                    ExpectedEntity(
                        name="Alex Rodriguez",
                        type=EntityType.PERSON,
                        required_properties={"role": "Security Lead", "email": "alex.rodriguez@company.com"},
                        name_variations=["Alex"]
                    ),
                    ExpectedEntity(
                        name="Lisa Wang",
                        type=EntityType.PERSON,
                        required_properties={"role": "CISO"},
                        name_variations=["Dr. Lisa Wang", "Dr. Wang"]
                    ),
                    ExpectedEntity(
                        name="Tom Brown",
                        type=EntityType.PERSON,
                        required_properties={"role": "Infrastructure Manager"},
                        name_variations=["Tom"]
                    ),
                    ExpectedEntity(
                        name="Reset all administrative passwords",
                        type=EntityType.TASK,
                        name_variations=["Password reset", "Reset passwords"]
                    ),
                    ExpectedEntity(
                        name="Data Center Alpha",
                        type=EntityType.PLACE,
                        name_variations=["Data Center"]
                    ),
                ],
                required_entity_types={EntityType.TRANSGRESSION, EntityType.PERSON, EntityType.TASK, EntityType.PLACE}
            )
        )
        
        # Complex multi-organization partnership
        transcripts["multi_org_partnership"] = TestTranscript(
            id="multi_org_partnership",
            title="Three-Way Partnership Agreement",
            category=TranscriptCategory.PARTNERSHIP,
            description="Complex partnership with multiple organizations, people, and relationships",
            tags=["partnership", "complex", "multi-org", "relationships"],
            content="""
            Partnership Agreement Meeting
            Date: March 10, 2025
            
            Organizations Present:
            - TechCorp Industries (represented by CEO Maria Gonzalez)
            - Global Solutions Ltd (represented by CTO James Wilson) 
            - Innovation Partners LLC (represented by Managing Partner David Kim)
            
            Meeting Purpose: Establish three-way partnership for AI research project
            
            Key Discussion Points:
            1. Intellectual Property sharing agreements
            2. Revenue sharing model (40% TechCorp, 35% Global Solutions, 25% Innovation Partners)
            3. Joint research facility location - Austin, Texas
            4. Project timeline: 18-month development cycle
            5. Regulatory compliance requirements
            
            Decisions Made:
            - TechCorp will lead AI algorithm development
            - Global Solutions will handle data infrastructure
            - Innovation Partners will manage commercial partnerships
            - Establish joint steering committee with rotating chair
            
            Next Steps:
            - Legal teams to draft formal partnership agreement
            - Technical teams to create detailed project specifications  
            - Establish monthly progress review meetings
            - Set up secure collaboration platform
            
            Budget: $15M total investment over 18 months
            Project Codename: "Project Phoenix"
            """,
            expected_outcome=ExpectedExtractionOutcome(
                min_entities=15,
                max_entities=25,
                required_entities=[
                    ExpectedEntity(
                        name="TechCorp Industries",
                        type=EntityType.ORGANIZATION,
                        name_variations=["TechCorp"]
                    ),
                    ExpectedEntity(
                        name="Global Solutions Ltd",
                        type=EntityType.ORGANIZATION,
                        name_variations=["Global Solutions"]
                    ),
                    ExpectedEntity(
                        name="Innovation Partners LLC",
                        type=EntityType.ORGANIZATION,
                        name_variations=["Innovation Partners"]
                    ),
                    ExpectedEntity(
                        name="Maria Gonzalez",
                        type=EntityType.PERSON,
                        required_properties={"role": "CEO"},
                        name_variations=["Maria"]
                    ),
                    ExpectedEntity(
                        name="James Wilson",
                        type=EntityType.PERSON,
                        required_properties={"role": "CTO"},
                        name_variations=["James"]
                    ),
                    ExpectedEntity(
                        name="David Kim",
                        type=EntityType.PERSON,
                        required_properties={"role": "Managing Partner"},
                        name_variations=["David"]
                    ),
                    ExpectedEntity(
                        name="Austin, Texas",
                        type=EntityType.PLACE,
                        name_variations=["Austin"]
                    ),
                    ExpectedEntity(
                        name="Project Phoenix",
                        type=EntityType.TASK,
                        required_properties={"budget": "$15M", "timeline": "18 months"},
                        name_variations=["AI research project"]
                    ),
                ],
                required_entity_types={EntityType.ORGANIZATION, EntityType.PERSON, EntityType.PLACE, EntityType.TASK},
                expected_relationships=[
                    ExpectedRelationship("Maria Gonzalez", "TechCorp Industries", "WORKS_FOR"),
                    ExpectedRelationship("James Wilson", "Global Solutions Ltd", "WORKS_FOR"),  
                    ExpectedRelationship("David Kim", "Innovation Partners LLC", "WORKS_FOR"),
                ]
            )
        )
        
        # Board meeting with decisions
        transcripts["board_meeting"] = TestTranscript(
            id="board_meeting",
            title="Board Meeting with Key Decisions",
            category=TranscriptCategory.BOARD_MEETING,
            description="Board meeting with hiring decisions and budget approvals",
            tags=["board", "decisions", "hiring", "budget"],
            content="""
            Board Meeting Minutes
            Date: February 5, 2025
            
            Board Members Present:
            - Chairman Robert Davis
            - Director Jane Thompson  
            - Director Michael Brown
            
            Key Agenda Items:
            1. CEO hiring decision
            2. Q1 budget approval
            3. Acquisition proposal review
            
            Decisions:
            - Approved hiring of new CEO (start date March 1)
            - Approved Q1 budget of $5.2M
            - Rejected acquisition proposal for SmallTech Inc
            
            Action Items:
            - HR to finalize CEO employment contract
            - Finance to allocate Q1 budget across departments
            - Legal to prepare rejection letter for SmallTech Inc
            """,
            expected_outcome=ExpectedExtractionOutcome(
                min_entities=8,
                max_entities=14,
                required_entities=[
                    ExpectedEntity(
                        name="Robert Davis",
                        type=EntityType.PERSON,
                        required_properties={"role": "Chairman"},
                        name_variations=["Robert", "Chairman Davis"]
                    ),
                    ExpectedEntity(
                        name="Jane Thompson",
                        type=EntityType.PERSON,
                        required_properties={"role": "Director"},
                        name_variations=["Jane"]
                    ),
                    ExpectedEntity(
                        name="Michael Brown",
                        type=EntityType.PERSON,
                        required_properties={"role": "Director"},
                        name_variations=["Michael"]
                    ),
                    ExpectedEntity(
                        name="SmallTech Inc",
                        type=EntityType.ORGANIZATION,
                        name_variations=["SmallTech"]
                    ),
                    ExpectedEntity(
                        name="CEO hiring",
                        type=EntityType.TASK,
                        required_properties={"status": "Approved", "start_date": "March 1"},
                        name_variations=["Hire new CEO", "CEO recruitment"]
                    ),
                    ExpectedEntity(
                        name="Q1 budget approval",
                        type=EntityType.TASK,
                        required_properties={"amount": "$5.2M", "status": "Approved"},
                        name_variations=["Budget approval", "Q1 budget"]
                    ),
                ],
                required_entity_types={EntityType.PERSON, EntityType.ORGANIZATION, EntityType.TASK}
            )
        )
        
        return transcripts


class ExtractionResultValidator:
    """Validates entity extraction results against expected outcomes."""
    
    @staticmethod
    def validate_extraction(
        actual: ExtractedEntities,
        expected: ExpectedExtractionOutcome
    ) -> Dict[str, Any]:
        """Validate extraction results and return detailed metrics."""
        results = {
            "overall_score": 0.0,
            "entity_count_valid": False,
            "required_entities_found": 0,
            "required_entities_total": len(expected.required_entities),
            "entity_coverage": 0.0,
            "type_accuracy": 0.0, 
            "name_accuracy": 0.0,
            "required_types_found": set(),
            "required_types_missing": set(),
            "validation_details": [],
            "passed": False
        }
        
        # Validate entity count
        entity_count = len(actual.entities)
        if expected.max_entities:
            results["entity_count_valid"] = expected.min_entities <= entity_count <= expected.max_entities
        else:
            results["entity_count_valid"] = entity_count >= expected.min_entities
            
        results["validation_details"].append(
            f"Entity count: {entity_count} (expected: {expected.min_entities}+)"
        )
        
        # Check required entities
        found_entities = 0
        correct_types = 0
        correct_names = 0
        
        for expected_entity in expected.required_entities:
            matches = [
                entity for entity in actual.entities 
                if expected_entity.matches_extracted_entity(entity)
            ]
            
            if matches:
                found_entities += 1
                # Check if any match has correct type
                if any(m.type == expected_entity.type for m in matches):
                    correct_types += 1
                # Name is correct if we found a match (matching logic includes name check)
                correct_names += 1
                results["validation_details"].append(
                    f"✅ Found required entity: {expected_entity.name} ({expected_entity.type.value})"
                )
            else:
                results["validation_details"].append(
                    f"❌ Missing required entity: {expected_entity.name} ({expected_entity.type.value})"
                )
        
        results["required_entities_found"] = found_entities
        results["entity_coverage"] = found_entities / len(expected.required_entities) if expected.required_entities else 1.0
        results["type_accuracy"] = correct_types / len(expected.required_entities) if expected.required_entities else 1.0
        results["name_accuracy"] = correct_names / len(expected.required_entities) if expected.required_entities else 1.0
        
        # Check required entity types
        actual_types = {entity.type for entity in actual.entities}
        results["required_types_found"] = actual_types & expected.required_entity_types
        results["required_types_missing"] = expected.required_entity_types - actual_types
        
        # Calculate overall score
        scores = [
            results["entity_coverage"],
            results["type_accuracy"],
            results["name_accuracy"],
            1.0 if results["entity_count_valid"] else 0.5,
            len(results["required_types_found"]) / len(expected.required_entity_types) if expected.required_entity_types else 1.0
        ]
        results["overall_score"] = sum(scores) / len(scores)
        
        # Check if passed based on quality thresholds
        thresholds = expected.quality_thresholds
        results["passed"] = (
            results["entity_coverage"] >= thresholds.get("entity_coverage", 0.8) and
            results["type_accuracy"] >= thresholds.get("type_accuracy", 0.9) and
            results["name_accuracy"] >= thresholds.get("name_accuracy", 0.7) and
            results["entity_count_valid"]
        )
        
        return results