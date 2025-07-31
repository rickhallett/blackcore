"""
Purpose: A comprehensive script to clean, deduplicate, merge, and standardize data across multiple local JSON files. It follows a specific, hardcoded remediation plan.
Utility: A one-time or occasional-use script to fix known data quality issues in the local JSON dataset. It's crucial for preparing the data for a clean import into Notion and ensuring consistency. It also includes a backup mechanism for safety.
"""
#!/usr/bin/env python3
"""
Data Remediation Script for Blackcore JSON Files

This script implements the data remediation plan outlined in specs/data-remediation-plan.md
to cleanse, deduplicate, merge, and standardize the data within the project's JSON models.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataRemediator:
    """Handles the remediation of JSON data files according to the plan."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.json_path = base_path / "blackcore" / "models" / "json"
        self.backup_path = (
            base_path / "backups" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

    def run(self):
        """Execute the full remediation process."""
        logger.info("Starting data remediation process...")

        # Step 1: Create backups
        self.create_backups()

        # Step 2: Fix each file according to the plan
        self.fix_people_contacts()
        self.fix_places_events()
        self.fix_organizations_bodies()
        self.fix_identified_transgressions()
        self.fix_documents_evidence()
        self.fix_agendas_epics()
        self.fix_actionable_tasks()

        # Step 3: Validate relational integrity
        self.validate_relations()

        logger.info("Data remediation completed successfully!")

    def create_backups(self):
        """Create backup copies of all JSON files."""
        logger.info(f"Creating backups in {self.backup_path}")
        self.backup_path.mkdir(parents=True, exist_ok=True)

        for json_file in self.json_path.glob("*.json"):
            shutil.copy2(json_file, self.backup_path / json_file.name)
            logger.info(f"Backed up {json_file.name}")

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON file and return its contents."""
        filepath = self.json_path / filename
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, filename: str, data: Dict[str, Any]):
        """Save data to JSON file."""
        filepath = self.json_path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {filename}")

    def fix_people_contacts(self):
        """Populate people_places.json with entities from intelligence_transcripts.json."""
        logger.info("Fixing people_places.json...")

        # Load intelligence transcripts to extract people
        intel_data = self.load_json("intelligence_transcripts.json")
        people_set = set()

        # Extract people from Tagged Entities
        for transcript in intel_data.get("Intelligence & Transcripts", []):
            tagged = transcript.get("Tagged Entities", [])
            if isinstance(tagged, list):
                for entity in tagged:
                    # Filter out non-person entities based on the plan
                    if entity not in [
                        "Survey Manipulation",
                        "Gemini AI",
                        "Data Analysis",
                        "Scrutiny Committee",
                    ]:
                        people_set.add(entity)

        # Load places_events to extract People Involved
        places_data = self.load_json("places_events.json")
        for item in places_data.get("Key Places & Events", []):
            people_involved = item.get("People Involved", [])
            if isinstance(people_involved, list):
                people_set.update(people_involved)

        # Create people entries
        people_entries = []
        for person_name in sorted(people_set):
            people_entries.append(
                {
                    "Person Name": person_name,
                    "Role": "",
                    "Organization": "",
                    "Contact Info": "",
                    "Notes": "",
                }
            )

        # Load existing people to avoid duplicates
        existing_data = self.load_json("people_places.json")
        existing_people = {
            p.get("Full Name", p.get("Person Name", ""))
            for p in existing_data.get("People & Contacts", [])
        }

        # Only add new people
        new_people = []
        for person_name in sorted(people_set):
            if person_name not in existing_people:
                new_people.append(
                    {
                        "Full Name": person_name,
                        "Role": "",
                        "Status": "",
                        "Organization": [],
                        "Notes": "",
                    }
                )

        # Merge with existing
        all_people = existing_data.get("People & Contacts", []) + new_people

        # Save updated people_places.json
        self.save_json("people_places.json", {"People & Contacts": all_people})
        logger.info(
            f"Added {len(new_people)} new people to people_places.json (total: {len(all_people)})"
        )

    def fix_places_events(self):
        """Move organization entries from places_events.json to organizations_bodies.json."""
        logger.info("Fixing places_events.json...")

        data = self.load_json("places_events.json")
        events = data.get("Key Places & Events", [])

        # Organizations to move
        orgs_to_move = [
            "Dorset Coast Forum (DCF)",
            "Swanage Town Council (STC)",
            "Dorset Highways",
            "Engagement HQ / Granicus",
            "North Swanage Traffic Concern Group (NSTCG)",
        ]

        # Separate organizations from events
        organizations = []
        cleaned_events = []

        for item in events:
            if item.get("Organization Name") in orgs_to_move:
                organizations.append(item)
            else:
                cleaned_events.append(item)

        # Save cleaned places_events.json
        self.save_json("places_events.json", {"Key Places & Events": cleaned_events})
        logger.info(
            f"Removed {len(organizations)} organizations from places_events.json"
        )

        # Return organizations for merging
        return organizations

    def fix_organizations_bodies(self):
        """Fix structure, deduplicate, and merge entries in organizations_bodies.json."""
        logger.info("Fixing organizations_bodies.json...")

        # Get organizations from places_events
        orgs_from_places = self.fix_places_events()

        # Load current data (it's a list, needs to be a dict)
        data = self.load_json("organizations_bodies.json")

        # Convert to proper structure if needed
        if isinstance(data, list):
            orgs_list = data
        else:
            orgs_list = data.get("Organizations & Bodies", [])

        # Track seen organizations for deduplication
        seen_orgs = {}
        deduplicated = []

        for org in orgs_list:
            org_name = org.get("Organization Name", "")
            if org_name not in seen_orgs:
                seen_orgs[org_name] = org
                deduplicated.append(org)
            else:
                logger.info(f"Removing duplicate: {org_name}")

        # Add organizations from places_events
        for org in orgs_from_places:
            org_name = org.get("Organization Name", "")
            if org_name in seen_orgs:
                # Merge with existing (specifically for NSTCG)
                existing = seen_orgs[org_name]
                for key, value in org.items():
                    if key not in existing or not existing[key]:
                        existing[key] = value
                logger.info(f"Merged data for: {org_name}")
            else:
                deduplicated.append(org)

        # Save with correct structure
        self.save_json(
            "organizations_bodies.json", {"Organizations & Bodies": deduplicated}
        )
        logger.info(f"Fixed organizations_bodies.json with {len(deduplicated)} entries")

    def fix_identified_transgressions(self):
        """Flatten structure and deduplicate identified_transgressions.json."""
        logger.info("Fixing identified_transgressions.json...")

        data = self.load_json("identified_transgressions.json")
        transgressions = data.get("Identified Transgressions", [])

        # Flatten if nested
        flattened = []
        for item in transgressions:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)

        # Deduplicate while preserving the most complete entries
        seen_names = {}
        deduplicated = []

        for trans in flattened:
            trans_name = trans.get("Transgression Name", "")

            if trans_name == "Paper survey chain of custody breach":
                # Keep the one with the specific date
                if "2024-06-06" in str(trans.get("Date/Period", "")):
                    seen_names[trans_name] = trans
                    deduplicated.append(trans)
                elif trans_name not in seen_names:
                    deduplicated.append(trans)
            elif trans_name not in seen_names:
                seen_names[trans_name] = trans
                deduplicated.append(trans)
            else:
                logger.info(f"Removing duplicate: {trans_name}")

        # Save fixed data
        self.save_json(
            "identified_transgressions.json",
            {"Identified Transgressions": deduplicated},
        )
        logger.info(
            f"Fixed identified_transgressions.json with {len(deduplicated)} entries"
        )

    def fix_documents_evidence(self):
        """Standardize structure and correct key in documents_evidence.json."""
        logger.info("Fixing documents_evidence.json...")

        data = self.load_json("documents_evidence.json")

        # Extract documents (handle incorrect key)
        documents = data.get(
            "Documents and Evidence", data.get("Documents & Evidence", [])
        )

        # Standardize structure
        standardized = []
        for doc in documents:
            clean_doc = {}
            for key, value in doc.items():
                # Extract actual value from nested structure
                if isinstance(value, dict) and "title" in value:
                    # Handle Notion API structure
                    title_val = value["title"]
                    if isinstance(title_val, list) and len(title_val) > 0:
                        text_obj = title_val[0]
                        if isinstance(text_obj, dict) and "text" in text_obj:
                            content = text_obj["text"]
                            if isinstance(content, dict) and "content" in content:
                                clean_doc[key] = content["content"]
                            else:
                                clean_doc[key] = str(content)
                        else:
                            clean_doc[key] = str(text_obj)
                    else:
                        clean_doc[key] = str(title_val)
                else:
                    clean_doc[key] = value
            standardized.append(clean_doc)

        # Save with correct key
        self.save_json(
            "documents_evidence.json", {"Documents & Evidence": standardized}
        )
        logger.info(f"Fixed documents_evidence.json with {len(standardized)} entries")

    def fix_agendas_epics(self):
        """Merge duplicate phases and correct key in agendas_epics.json."""
        logger.info("Fixing agendas_epics.json...")

        data = self.load_json("agendas_epics.json")

        # Get agendas (handle incorrect key)
        agendas = data.get("Agendas and Epics", data.get("Agendas & Epics", []))

        # Group by phase
        phase_groups = defaultdict(list)
        other_agendas = []

        for agenda in agendas:
            agenda_name = agenda.get("Agenda Name", "")
            if "Phase 1" in agenda_name:
                phase_groups["Phase 1"].append(agenda)
            elif "Phase 2" in agenda_name:
                phase_groups["Phase 2"].append(agenda)
            elif "Phase 3" in agenda_name:
                phase_groups["Phase 3"].append(agenda)
            else:
                other_agendas.append(agenda)

        # Merge phases
        merged_agendas = []

        # Merge Phase 1
        if phase_groups["Phase 1"]:
            merged_phase1 = self._merge_agendas(
                phase_groups["Phase 1"], "Phase 1: Mobilization & Evidence Gathering"
            )
            merged_agendas.append(merged_phase1)

        # Merge Phase 2
        if phase_groups["Phase 2"]:
            merged_phase2 = self._merge_agendas(
                phase_groups["Phase 2"], "Phase 2: Pressure & Credibility Attack"
            )
            merged_agendas.append(merged_phase2)

        # Merge Phase 3
        if phase_groups["Phase 3"]:
            merged_phase3 = self._merge_agendas(
                phase_groups["Phase 3"], "Phase 3: Endgame & Accountability"
            )
            merged_agendas.append(merged_phase3)

        # Add other agendas
        merged_agendas.extend(other_agendas)

        # Save with correct key
        self.save_json("agendas_epics.json", {"Agendas & Epics": merged_agendas})
        logger.info(f"Fixed agendas_epics.json with {len(merged_agendas)} entries")

    def _merge_agendas(self, agendas: List[Dict], new_name: str) -> Dict:
        """Helper to merge multiple agenda entries."""
        merged = {
            "Agenda Name": new_name,
            "Objective Summary": "",
            "Actionable Tasks": [],
            "Key Documents": [],
            "Status": "Active",
        }

        # Combine objectives
        objectives = []
        all_tasks = []
        all_docs = []

        for agenda in agendas:
            obj = agenda.get("Objective Summary", "")
            if obj:
                objectives.append(obj)

            tasks = agenda.get("Actionable Tasks", [])
            if isinstance(tasks, list):
                all_tasks.extend(tasks)

            docs = agenda.get("Key Documents", [])
            if isinstance(docs, list):
                all_docs.extend(docs)

        # Create synthesized objective
        if objectives:
            merged["Objective Summary"] = " | ".join(objectives)

        # Deduplicate tasks and docs
        merged["Actionable Tasks"] = list(set(all_tasks))
        merged["Key Documents"] = list(set(all_docs))

        return merged

    def fix_actionable_tasks(self):
        """Update relational links in actionable_tasks.json after agenda merge."""
        logger.info("Fixing actionable_tasks.json...")

        data = self.load_json("actionable_tasks.json")
        tasks = data.get("Actionable Tasks", [])

        # Mapping of old agenda names to new names
        agenda_mapping = {
            "Phase 1: Evidence Gathering": "Phase 1: Mobilization & Evidence Gathering",
            "Phase 1: Mobilization": "Phase 1: Mobilization & Evidence Gathering",
            "Phase 2: Pressure Campaign": "Phase 2: Pressure & Credibility Attack",
            "Phase 2: Credibility Attack": "Phase 2: Pressure & Credibility Attack",
            "Phase 3: Endgame": "Phase 3: Endgame & Accountability",
            "Phase 3: Accountability": "Phase 3: Endgame & Accountability",
        }

        # Update tasks
        updated_count = 0
        for task in tasks:
            related_agenda = task.get("Related Agenda", "")
            # Handle if Related Agenda is a list
            if isinstance(related_agenda, list):
                updated_list = []
                for agenda in related_agenda:
                    if agenda in agenda_mapping:
                        updated_list.append(agenda_mapping[agenda])
                        updated_count += 1
                    else:
                        updated_list.append(agenda)
                task["Related Agenda"] = updated_list
            elif related_agenda in agenda_mapping:
                task["Related Agenda"] = agenda_mapping[related_agenda]
                updated_count += 1

        # Save updated tasks
        self.save_json("actionable_tasks.json", {"Actionable Tasks": tasks})
        logger.info(
            f"Updated {updated_count} task relationships in actionable_tasks.json"
        )

    def validate_relations(self):
        """Validate all relational integrity across files."""
        logger.info("Validating relational integrity...")

        # Load all data
        all_data = {}
        for json_file in self.json_path.glob("*.json"):
            all_data[json_file.stem] = self.load_json(json_file.name)

        # Build lookup tables for each database
        lookups = {}

        # Map JSON files to their title properties
        title_properties = {
            "people_places": "Full Name",
            "organizations_bodies": "Organization Name",
            "agendas_epics": "Agenda Title",  # Changed from Agenda Name to Agenda Title
            "actionable_tasks": "Task Name",
            "places_events": "Event/Place Name",
            "identified_transgressions": "Transgression Name",
            "documents_evidence": "Document Name",
            "intelligence_transcripts": "Transcript Title",
            "concepts": "Concept Name",  # Added concepts database
        }

        # Build lookups
        for file_key, title_prop in title_properties.items():
            if file_key in all_data:
                lookup_set = set()
                db_key = next(iter(all_data[file_key].keys()))  # Get the database key
                items = all_data[file_key].get(db_key, [])
                for item in items:
                    if title_prop in item:
                        lookup_set.add(item[title_prop])
                lookups[file_key] = lookup_set

        # Validate relations
        issues = []

        # Check each file for broken relations
        relation_mappings = {
            "actionable_tasks": {
                "Related Agenda": "agendas_epics",
                "People Involved": "people_places",
            },
            "intelligence_transcripts": {
                "Tagged Entities": "people_places"  # Note: some may be concepts
            },
            "identified_transgressions": {
                "Perpetrator (Org)": "organizations_bodies",
                "Perpetrator (Individual)": "people_places",
            },
            "documents_evidence": {
                "Related Transgressions": "identified_transgressions"
            },
        }

        for file_key, relations in relation_mappings.items():
            if file_key in all_data:
                db_key = next(iter(all_data[file_key].keys()))
                items = all_data[file_key].get(db_key, [])

                for item in items:
                    item_title = item.get(title_properties.get(file_key, ""), "Unknown")

                    for rel_field, target_file in relations.items():
                        if rel_field in item:
                            rel_values = item[rel_field]
                            if isinstance(rel_values, str):
                                rel_values = [rel_values]
                            elif not isinstance(rel_values, list):
                                continue

                            for rel_value in rel_values:
                                if rel_value and target_file in lookups:
                                    if rel_value not in lookups[target_file]:
                                        # Special case for concepts
                                        if (
                                            file_key == "intelligence_transcripts"
                                            and rel_field == "Tagged Entities"
                                        ):
                                            if rel_value in [
                                                "Survey Manipulation",
                                                "Gemini AI",
                                                "Data Analysis",
                                                "Scrutiny Committee",
                                            ]:
                                                # Check if concept exists in concepts database
                                                if (
                                                    "concepts" in lookups
                                                    and rel_value
                                                    not in lookups["concepts"]
                                                ):
                                                    issues.append(
                                                        f"Concept '{rel_value}' in {item_title} not found in concepts database"
                                                    )
                                                continue
                                        issues.append(
                                            f"Broken relation: {item_title} -> {rel_field} -> '{rel_value}' (not found in {target_file})"
                                        )

        # Report validation results
        if issues:
            logger.warning(f"Found {len(issues)} relational integrity issues:")
            for issue in issues[:10]:  # Show first 10
                logger.warning(f"  - {issue}")
            if len(issues) > 10:
                logger.warning(f"  ... and {len(issues) - 10} more")
        else:
            logger.info("All relational integrity checks passed!")

        # Save validation report
        report = {
            "validation_date": datetime.now().isoformat(),
            "total_issues": len(issues),
            "issues": issues,
        }

        report_path = self.base_path / "validation_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Validation report saved to {report_path}")


def main():
    """Main entry point."""
    base_path = Path(__file__).parent.parent
    remediator = DataRemediator(base_path)
    remediator.run()


if __name__ == "__main__":
    main()
