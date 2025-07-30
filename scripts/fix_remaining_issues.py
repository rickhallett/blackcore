#!/usr/bin/env python3
"""
Fix remaining relational integrity issues after the main data remediation.
"""

import json
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_json(filepath: Path):
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: Path, data):
    """Save JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fix_agenda_references():
    """Fix broken agenda references in actionable_tasks.json."""
    base_path = Path(__file__).parent.parent
    json_path = base_path / "blackcore" / "models" / "json"

    # Load files
    tasks_data = load_json(json_path / "actionable_tasks.json")
    agendas_data = load_json(json_path / "agendas_epics.json")

    # Get actual agenda names
    actual_agendas = {
        agenda["Agenda Title"] for agenda in agendas_data["Agendas & Epics"]
    }
    logger.info(f"Available agendas: {actual_agendas}")

    # Fix task references
    tasks = tasks_data["Actionable Tasks"]
    fixed_count = 0

    for task in tasks:
        related_agenda = task.get("Related Agenda", "")

        if isinstance(related_agenda, list):
            # Handle list of agendas
            fixed_list = []
            for agenda in related_agenda:
                if agenda not in actual_agendas:
                    # Try to find a matching agenda
                    if "Phase 1" in agenda:
                        fixed_list.append(
                            "Phase 1: Evidence Documentation & Intelligence Gathering"
                        )
                        fixed_count += 1
                    elif "Phase 2" in agenda:
                        fixed_list.append("Phase 2: Pressure Campaign Implementation")
                        fixed_count += 1
                    elif "Phase 3" in agenda:
                        fixed_list.append("Phase 3: Endgame & Accountability")
                        fixed_count += 1
                    else:
                        fixed_list.append(agenda)
                else:
                    fixed_list.append(agenda)
            task["Related Agenda"] = fixed_list
        elif related_agenda and related_agenda not in actual_agendas:
            # Handle single agenda
            if "Phase 1" in related_agenda:
                task["Related Agenda"] = (
                    "Phase 1: Evidence Documentation & Intelligence Gathering"
                )
                fixed_count += 1
            elif "Phase 2" in related_agenda:
                task["Related Agenda"] = "Phase 2: Pressure Campaign Implementation"
                fixed_count += 1
            elif "Phase 3" in related_agenda:
                task["Related Agenda"] = "Phase 3: Endgame & Accountability"
                fixed_count += 1

    # Save fixed tasks
    save_json(json_path / "actionable_tasks.json", tasks_data)
    logger.info(f"Fixed {fixed_count} agenda references in actionable_tasks.json")


def add_missing_organizations():
    """Add missing organizations to organizations_bodies.json."""
    base_path = Path(__file__).parent.parent
    json_path = base_path / "blackcore" / "models" / "json"

    # Load organizations
    orgs_data = load_json(json_path / "organizations_bodies.json")
    orgs = orgs_data["Organizations & Bodies"]

    # Check if missing organizations exist
    existing_orgs = {org["Organization Name"] for org in orgs}

    # Add missing organizations
    missing_orgs = [
        {
            "Organization Name": "Dorset Coast Forum",
            "Organization Type": "Public Body",
            "Website": "",
            "Notes": "Manages coastal activities and surveys",
        },
        {
            "Organization Name": "Granicus",
            "Organization Type": "Private Company",
            "Website": "https://granicus.com",
            "Notes": "Parent company of Engagement HQ, survey platform provider",
        },
    ]

    added_count = 0
    for org in missing_orgs:
        if org["Organization Name"] not in existing_orgs:
            orgs.append(org)
            added_count += 1
            logger.info(f"Added organization: {org['Organization Name']}")

    # Save updated organizations
    save_json(json_path / "organizations_bodies.json", orgs_data)
    logger.info(f"Added {added_count} missing organizations")


def create_concepts_database():
    """Create a concepts database for abstract entities."""
    base_path = Path(__file__).parent.parent
    json_path = base_path / "blackcore" / "models" / "json"

    concepts = {
        "Concepts": [
            {
                "Concept Name": "Survey Manipulation",
                "Category": "Strategy",
                "Description": "Various tactics used to manipulate survey results",
                "Related Intelligence": ["Intelligence from various transcripts"],
            },
            {
                "Concept Name": "Gemini AI",
                "Category": "Technology",
                "Description": "AI tool used for survey data analysis",
                "Related Intelligence": ["Intelligence from various transcripts"],
            },
            {
                "Concept Name": "Data Analysis",
                "Category": "Process",
                "Description": "Analysis of survey and other data",
                "Related Intelligence": ["Intelligence from various transcripts"],
            },
            {
                "Concept Name": "Scrutiny Committee",
                "Category": "Governance",
                "Description": "Committee responsible for oversight",
                "Related Intelligence": ["Intelligence from various transcripts"],
            },
        ]
    }

    # Save concepts database
    save_json(json_path / "concepts.json", concepts)
    logger.info("Created concepts.json database with 4 concepts")


def main():
    """Run all fixes."""
    logger.info("Starting fix for remaining issues...")

    fix_agenda_references()
    add_missing_organizations()
    create_concepts_database()

    logger.info("All fixes completed!")


if __name__ == "__main__":
    main()
