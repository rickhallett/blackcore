import json
import os
from pathlib import Path
from typing import Dict, Any, List

# --- Schema and Simulated Data ---

# A simplified version of the schema to know the title property for each DB
DB_SCHEMAS = {
    "Agendas & Epics": {
        "title_property": "Agenda Title",
        "list_properties": ["Actionable Tasks", "Key Documents"],
    },
    "Actionable Tasks": {
        "title_property": "Task Name",
        "list_properties": ["Blocked By"],
    },
    # Add other DBs here to make the script work for them
}


def get_simulated_notion_db(db_name: str) -> List[Dict[str, Any]]:
    """
    Returns a list of dictionaries simulating records already in a given Notion DB.
    """
    if db_name == "Agendas & Epics":
        return [
            {
                # This one is IDENTICAL to the entry in the JSON file.
                "Agenda Title": "Phase 1: Evidence Documentation & Intelligence Gathering",
                "Status": "Completed",
                "Owner": "Pete Mitchell",
                "Phase": "Phase 1: Mobilization",
                "Actionable Tasks": [
                    "Document and archive Purdah violation evidence",
                    "Analyze Granicus/Engagement HQ relationship",
                    "Engage local ground contacts for intelligence gathering",
                ],
                "Key Documents": [
                    "Tony Powell CAPTCHA Email",
                    "Gemini AI Survey Analysis",
                    "David Hollister's Purdah Comment",
                ],
                "Objective Summary": "Systematic collection and documentation of evidence regarding survey manipulation and Purdah violations. Establish ground intelligence network and preserve critical evidence for use in subsequent phases.",
            },
            {
                # This one EXISTS but has a different status AND is missing an actionable task.
                "Agenda Title": "Shore Road Closure Opposition Campaign",
                "Status": "Planning",  # Local JSON is "Active"
                "Owner": "Barry Cade",
                "Phase": "Phase 2: Pressure",
                "Actionable Tasks": [
                    # Missing "Engage local ground contacts..." from local JSON
                    "Submit formal complaint to UK Statistics Authority",
                    "Organize email pressure campaign targeting Cliff Sutton",
                ],
                "Key Documents": [
                    "Tony Powell CAPTCHA Email",
                    "Gemini AI Survey Analysis",
                    "David Hollister's Purdah Comment",
                ],
                "Objective Summary": "Master campaign to prevent Shore Road closure through systematic opposition leveraging survey manipulation evidence, Purdah violations, and targeted pressure on key decision makers. Primary focus on protecting North Swanage community interests.",
            },
        ]
    return []


# --- Core Sync Logic ---


def dry_run_sync(db_name: str, local_data_key: str, data_file: Path):
    """
    Simulates a generic sync process for a specified Notion database.

    Args:
        db_name: The name of the Notion database (e.g., "Agendas & Epics").
        local_data_key: The top-level key in the JSON file that holds the list of items.
        data_file: Path to the local JSON file.
    """
    # 1. Load Schema and Data
    schema = DB_SCHEMAS.get(db_name)
    if not schema:
        print(
            f"Error: No schema defined for database '{db_name}'. Please update DB_SCHEMAS."
        )
        return

    title_prop = schema["title_property"]
    list_props = schema.get("list_properties", [])

    if not data_file.exists():
        print(f"Error: Data file not found at {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        local_items = json.load(f).get(local_data_key, [])

    notion_db = get_simulated_notion_db(db_name)
    notion_map = {item[title_prop]: item for item in notion_db if title_prop in item}

    print(f"--- Starting Generic Notion Sync Dry Run for: '{db_name}' ---")
    print(f"Loaded {len(local_items)} items from '{data_file.name}'.")
    print(f"Simulating {len(notion_db)} existing pages in Notion.\n")

    # 2. Process each item from the local file
    for local_item in local_items:
        title = local_item.get(title_prop)
        if not title:
            continue

        print(f"--- Processing: '{title}' ---")

        existing_item = notion_map.get(title)

        if not existing_item:
            print("  [ACTION]: CREATE")
            print("  [REASON]: Page with this title does not exist in Notion.")
            print(f"  [DATA]: {json.dumps(local_item, indent=4)}")
        else:
            updates = {}
            # Compare each property
            all_keys = set(local_item.keys()) | set(existing_item.keys())
            for key in all_keys:
                local_val = local_item.get(key)
                notion_val = existing_item.get(key)

                if local_val == notion_val:
                    continue

                # Logic for list-based properties (e.g., relations)
                if key in list_props:
                    local_set = set(local_val or [])
                    notion_set = set(notion_val or [])
                    new_items_to_add = list(local_set - notion_set)
                    if new_items_to_add:
                        updates[key] = {
                            "action": "APPEND",
                            "values_to_add": new_items_to_add,
                        }
                # Logic for single-value properties
                else:
                    updates[key] = {"action": "OVERWRITE", "new_value": local_val}

            if not updates:
                print("  [ACTION]: SKIP")
                print("  [REASON]: Local data is identical to Notion page.")
            else:
                print("  [ACTION]: UPDATE")
                print("  [REASON]: Page exists but has new data.")
                for prop, change in updates.items():
                    if change["action"] == "OVERWRITE":
                        print(
                            f"    - Field '{prop}': OVERWRITE with new value '{change['new_value']}'"
                        )
                    elif change["action"] == "APPEND":
                        print(
                            f"    - Field '{prop}': APPEND with new item(s): {change['values_to_add']}"
                        )

        print("-" * (len(title) + 20) + "\n")


def main():
    workspace_root = Path(os.getcwd())
    # --- Configuration ---
    # You can change these values to sync a different DB
    database_name_to_sync = "Agendas & Epics"
    json_file_path = (
        workspace_root / "blackcore" / "models" / "json" / "agendas_epics.json"
    )
    json_top_level_key = (
        "Agendas and Epics"  # The key in the JSON file containing the data array
    )
    # -------------------

    dry_run_sync(
        db_name=database_name_to_sync,
        local_data_key=json_top_level_key,
        data_file=json_file_path,
    )


if __name__ == "__main__":
    main()
