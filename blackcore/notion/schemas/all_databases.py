"""Database schemas for all Project Nassau databases."""

from typing import List
from blackcore.models.notion_properties import (
    DatabaseSchema,
    TitleProperty,
    SelectProperty,
    SelectOption,
    DateProperty,
    EmailProperty,
    PhoneProperty,
    RichTextProperty,
    RelationProperty,
    PeopleProperty,
    URLProperty,
    FilesProperty,
)


def get_people_contacts_schema() -> DatabaseSchema:
    """Schema for People & Contacts database."""
    return DatabaseSchema(
        name="People & Contacts",
        properties=[
            TitleProperty(name="Full Name"),
            SelectProperty(
                name="Role",
                options=[
                    SelectOption(name="Target", color="red"),
                    SelectOption(name="Ally", color="green"),
                    SelectOption(name="Oversight", color="blue"),
                    SelectOption(name="Internal Team", color="purple"),
                    SelectOption(name="Operational Persona", color="orange"),
                ],
            ),
            SelectProperty(
                name="Status",
                options=[
                    SelectOption(name="Not Contacted", color="gray"),
                    SelectOption(name="Initial Contact Made", color="yellow"),
                    SelectOption(name="Active Engagement", color="green"),
                    SelectOption(name="Monitoring", color="blue"),
                ],
            ),
            RelationProperty(name="Organization"),  # Links to Organizations & Bodies
            EmailProperty(name="Email"),
            PhoneProperty(name="Phone"),
            RelationProperty(name="Linked Transgressions"),  # Links to Identified Transgressions
            DateProperty(name="Last Contacted"),
            RichTextProperty(name="Notes"),
        ],
    )


def get_organizations_bodies_schema() -> DatabaseSchema:
    """Schema for Organizations & Bodies database."""
    return DatabaseSchema(
        name="Organizations & Bodies",
        properties=[
            TitleProperty(name="Organization Name"),
            SelectProperty(
                name="Category",
                options=[
                    SelectOption(name="Antagonist", color="red"),
                    SelectOption(name="Lever of Power", color="blue"),
                    SelectOption(name="Weapon", color="orange"),
                ],
            ),
            RelationProperty(name="Key People"),  # Links to People & Contacts
            RelationProperty(name="Linked Documents"),  # Links to Documents & Evidence
            URLProperty(name="Website"),
        ],
    )


def get_agendas_epics_schema() -> DatabaseSchema:
    """Schema for Agendas & Epics database."""
    return DatabaseSchema(
        name="Agendas & Epics",
        properties=[
            TitleProperty(name="Agenda Title"),
            SelectProperty(
                name="Status",
                options=[
                    SelectOption(name="Planning", color="gray"),
                    SelectOption(name="Active", color="green"),
                    SelectOption(name="Completed", color="blue"),
                    SelectOption(name="Blocked", color="red"),
                ],
            ),
            PeopleProperty(name="Owner"),
            SelectProperty(
                name="Phase",
                options=[
                    SelectOption(name="Phase 1: Mobilization", color="yellow"),
                    SelectOption(name="Phase 2: Pressure", color="orange"),
                    SelectOption(name="Phase 3: Endgame", color="red"),
                ],
            ),
            RelationProperty(name="Actionable Tasks"),  # Links to Actionable Tasks
            RelationProperty(name="Key Documents"),  # Links to Documents & Evidence
            RichTextProperty(name="Objective Summary"),
        ],
    )


def get_actionable_tasks_schema() -> DatabaseSchema:
    """Schema for Actionable Tasks database."""
    return DatabaseSchema(
        name="Actionable Tasks",
        properties=[
            TitleProperty(name="Task Name"),
            PeopleProperty(name="Assignee"),
            SelectProperty(
                name="Status",
                options=[
                    SelectOption(name="To-Do", color="gray"),
                    SelectOption(name="In Progress", color="yellow"),
                    SelectOption(name="Done", color="green"),
                ],
            ),
            DateProperty(name="Due Date"),
            SelectProperty(
                name="Priority",
                options=[
                    SelectOption(name="High", color="red"),
                    SelectOption(name="Medium", color="yellow"),
                    SelectOption(name="Low", color="green"),
                ],
            ),
            RelationProperty(name="Related Agenda"),  # Links to Agendas & Epics
            RelationProperty(name="Blocked By"),  # Self-referential relation
        ],
    )


def get_intelligence_transcripts_schema() -> DatabaseSchema:
    """Schema for Intelligence & Transcripts database."""
    return DatabaseSchema(
        name="Intelligence & Transcripts",
        properties=[
            TitleProperty(name="Entry Title"),
            DateProperty(name="Date Recorded"),
            SelectProperty(
                name="Source",
                options=[
                    SelectOption(name="Voice Memo", color="purple"),
                    SelectOption(name="Google Meet", color="blue"),
                    SelectOption(name="Personal Note", color="green"),
                    SelectOption(name="External Source", color="orange"),
                ],
            ),
            RichTextProperty(name="Raw Transcript/Note"),
            RichTextProperty(name="AI Summary"),
            RelationProperty(name="Tagged Entities"),  # Multi-relation to various databases
            SelectProperty(
                name="Processing Status",
                options=[
                    SelectOption(name="Needs Processing", color="red"),
                    SelectOption(name="Processed", color="green"),
                ],
            ),
        ],
    )


def get_documents_evidence_schema() -> DatabaseSchema:
    """Schema for Documents & Evidence database."""
    return DatabaseSchema(
        name="Documents & Evidence",
        properties=[
            TitleProperty(name="Document Name"),
            FilesProperty(name="File"),
            SelectProperty(
                name="Document Type",
                options=[
                    SelectOption(name="Council Report", color="blue"),
                    SelectOption(name="Legal Precedent", color="purple"),
                    SelectOption(name="Meeting Minutes", color="green"),
                    SelectOption(name="Our Output", color="orange"),
                    SelectOption(name="Evidence", color="red"),
                ],
            ),
            RelationProperty(name="Source Organization"),  # Links to Organizations & Bodies
            RichTextProperty(name="AI Analysis (from Colab)"),
        ],
    )


def get_key_places_events_schema() -> DatabaseSchema:
    """Schema for Key Places & Events database."""
    return DatabaseSchema(
        name="Key Places & Events",
        properties=[
            TitleProperty(name="Event / Place Name"),
            SelectProperty(
                name="Type",
                options=[
                    SelectOption(name="Pivotal Event", color="red"),
                    SelectOption(name="Key Location", color="blue"),
                ],
            ),
            DateProperty(name="Date of Event"),
            RichTextProperty(name="Description"),
            RelationProperty(name="People Involved"),  # Links to People & Contacts
            RelationProperty(name="Related Transgressions"),  # Links to Identified Transgressions
        ],
    )


def get_identified_transgressions_schema() -> DatabaseSchema:
    """Schema for Identified Transgressions database."""
    return DatabaseSchema(
        name="Identified Transgressions",
        properties=[
            TitleProperty(name="Transgression Summary"),
            RelationProperty(name="Perpetrator (Person)"),  # Links to People & Contacts
            RelationProperty(name="Perpetrator (Org)"),  # Links to Organizations & Bodies
            DateProperty(name="Date of Transgression"),
            RelationProperty(name="Evidence"),  # Links to Documents & Evidence and Intelligence
            SelectProperty(
                name="Severity",
                options=[
                    SelectOption(name="Low", color="green"),
                    SelectOption(name="Medium", color="yellow"),
                    SelectOption(name="High", color="orange"),
                    SelectOption(name="Critical", color="red"),
                ],
            ),
        ],
    )


def get_all_database_schemas() -> List[DatabaseSchema]:
    """Get all database schemas in creation order."""
    return [
        get_people_contacts_schema(),
        get_organizations_bodies_schema(),
        get_agendas_epics_schema(),
        get_actionable_tasks_schema(),
        get_intelligence_transcripts_schema(),
        get_documents_evidence_schema(),
        get_key_places_events_schema(),
        get_identified_transgressions_schema(),
    ]


# Define relation mappings for updating after creation
RELATION_MAPPINGS = {
    "People & Contacts": {
        "Organization": "Organizations & Bodies",
        "Linked Transgressions": "Identified Transgressions",
    },
    "Organizations & Bodies": {
        "Key People": "People & Contacts",
        "Linked Documents": "Documents & Evidence",
    },
    "Agendas & Epics": {
        "Actionable Tasks": "Actionable Tasks",
        "Key Documents": "Documents & Evidence",
    },
    "Actionable Tasks": {
        "Related Agenda": "Agendas & Epics",
        "Blocked By": "Actionable Tasks",  # Self-referential
    },
    "Intelligence & Transcripts": {
        "Tagged Entities": None,  # Special multi-relation case
    },
    "Documents & Evidence": {
        "Source Organization": "Organizations & Bodies",
    },
    "Key Places & Events": {
        "People Involved": "People & Contacts",
        "Related Transgressions": "Identified Transgressions",
    },
    "Identified Transgressions": {
        "Perpetrator (Person)": "People & Contacts",
        "Perpetrator (Org)": "Organizations & Bodies",
        "Evidence": None,  # Special multi-relation case
    },
}
