import json
import os
from pathlib import Path

# --- Schema Definition based on all_databases.py ---

DB_INFO = {
    "People & Contacts": {
        "title_property": "Full Name",
        "relations": {
            "Organization": "Organizations & Bodies",
            "Linked Transgressions": "Identified Transgressions",
        },
        "files": ["people_places.json"],
    },
    "Organizations & Bodies": {
        "title_property": "Organization Name",
        "relations": {
            "Key People": "People & Contacts",
            "Linked Documents": "Documents & Evidence",
        },
        "files": ["organizations_bodies.json"],
    },
    "Agendas & Epics": {
        "title_property": "Agenda Title",
        "relations": {
            "Actionable Tasks": "Actionable Tasks",
            "Key Documents": "Documents & Evidence",
        },
        "files": ["agendas_epics.json"],
    },
    "Actionable Tasks": {
        "title_property": "Task Name",
        "relations": {
            "Related Agenda": "Agendas & Epics",
            "Blocked By": "Actionable Tasks",
        },
        "files": ["actionable_tasks.json"],
    },
    "Intelligence & Transcripts": {
        "title_property": "Entry Title",
        "relations": {
            "Tagged Entities": [
                "People & Contacts",
                "Organizations & Bodies",
                "Key Places & Events",
                "Identified Transgressions",
                "Documents & Evidence",
            ]
        },
        "files": ["intelligence_transcripts.json"],
    },
    "Documents & Evidence": {
        "title_property": "Document Name",
        "relations": {
            "Source Organization": "Organizations & Bodies",
        },
        "files": ["documents_evidence.json"],
    },
    "Key Places & Events": {
        "title_property": "Event / Place Name",
        "relations": {
            "People Involved": "People & Contacts",
            "Related Transgressions": "Identified Transgressions",
        },
        "files": ["places_events.json"],
    },
    "Identified Transgressions": {
        "title_property": "Transgression Summary",
        "relations": {
            "Perpetrator (Person)": "People & Contacts",
            "Perpetrator (Org)": "Organizations & Bodies",
            "Evidence": ["Documents & Evidence", "Intelligence & Transcripts"],
        },
        "files": ["identified_transgressions.json"],
    },
}


def load_data(json_dir: Path):
    data = {}
    for db_name, info in DB_INFO.items():
        data[db_name] = []
        for filename in info["files"]:
            file_path = json_dir / filename
            if file_path.exists() and file_path.stat().st_size > 0:
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        content = json.load(f)
                        if isinstance(content, list):
                            data[db_name].extend(content)
                        else:
                            data[db_name].append(content)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode JSON from {filename}")
    return data


def find_potential_relations(data):
    potential_relations = []

    for source_db, source_items in data.items():
        if not source_items:
            continue

        source_db_info = DB_INFO[source_db]
        source_title_prop = source_db_info["title_property"]

        for source_item in source_items:
            source_title_val = source_item.get(source_title_prop)
            if not source_title_val:
                continue

            for rel_prop, target_dbs in source_db_info["relations"].items():
                if rel_prop in source_item:
                    rel_values = source_item[rel_prop]
                    if not isinstance(rel_values, list):
                        rel_values = [rel_values]

                    if not isinstance(target_dbs, list):
                        target_dbs = [target_dbs]

                    for rel_val in rel_values:
                        if not rel_val:
                            continue

                        for target_db in target_dbs:
                            target_db_info = DB_INFO[target_db]
                            target_title_prop = target_db_info["title_property"]

                            for target_item in data.get(target_db, []):
                                target_title_val = target_item.get(target_title_prop)
                                if (
                                    target_title_val
                                    and str(rel_val).strip().lower()
                                    == str(target_title_val).strip().lower()
                                ):
                                    potential_relations.append(
                                        {
                                            "source_entity_type": source_db,
                                            "source_entity_name": source_title_val,
                                            "relationship_type": rel_prop,
                                            "target_entity_type": target_db,
                                            "target_entity_name": target_title_val,
                                            "found_in_value": rel_val,
                                        }
                                    )

    return potential_relations


def main():
    workspace_root = Path(os.getcwd())
    json_dir = workspace_root / "blackcore" / "models" / "json"
    output_file = workspace_root / "potential_relations.json"

    print(f"Reading JSON files from: {json_dir}")
    all_data = load_data(json_dir)

    print("Finding potential relationships...")
    relations = find_potential_relations(all_data)

    print(f"Found {len(relations)} potential relationships.")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(relations, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote potential relations to {output_file}")


if __name__ == "__main__":
    main()
