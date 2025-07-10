import json
import os
from pathlib import Path
from typing import Dict, Any, List


def get_simulated_notion_data() -> List[Dict[str, Any]]:
    """
    Returns a list of dictionaries simulating records already in Notion.
    This helps demonstrate the create, skip, and update logic.
    """
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
            # This one EXISTS but has a different status ("Planning" vs "Active").
            "Agenda Title": "Phase 2: Pressure Campaign Implementation",
            "Status": "Planning",  # The local JSON has this as "Active"
            "Owner": "Barricade",
            "Phase": "Phase 2: Pressure",
            "Actionable Tasks": [
                "Submit formal complaint to UK Statistics Authority",
                "Organize email pressure campaign targeting Cliff Sutton",
            ],
            "Key Documents": [
                "UK Statistics Authority Complaint Document",
                "Pressure Campaign Email Templates",
            ],
            "Objective Summary": "Execute targeted pressure campaign against key council members and submit formal complaints to higher authorities. Focus on Cliff Sutton vote influence and leveraging documented evidence with UK Statistics Authority.",
        },
        {
            # This is an extra record in Notion that isn't in our local file.
            "Agenda Title": "Internal Project Review Q2",
            "Status": "Completed",
            "Owner": "Blake Compton",
            "Phase": "Phase 2: Pressure",
            "Actionable Tasks": [],
            "Key Documents": [],
            "Objective Summary": "A quarterly review of internal progress.",
        },
    ]


def compare_items(local_item: Dict[str, Any], notion_item: Dict[str, Any]) -> Dict[str, Any]:
    """Compares two items and returns a dictionary of differences."""
    diff = {}
    all_keys = set(local_item.keys()) | set(notion_item.keys())
    for key in all_keys:
        local_val = local_item.get(key)
        notion_val = notion_item.get(key)
        if local_val != notion_val:
            diff[key] = {"local": local_val, "notion": notion_val}
    return diff


def dry_run_sync(data_file: Path):
    """
    Simulates the creation, skipping, or updating of Notion pages from a JSON file.
    """
    if not data_file.exists():
        print(f"Error: Data file not found at {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        local_data = json.load(f).get("Agendas and Epics", [])

    simulated_notion_data = get_simulated_notion_data()
    notion_data_map = {item["Agenda Title"]: item for item in simulated_notion_data}

    print("--- Starting Notion DB Sync Dry Run ---")
    print(f"Loaded {len(local_data)} agendas from '{data_file.name}'.")
    print(f"Simulating {len(simulated_notion_data)} existing pages in Notion.\n")

    for item in local_data:
        title = item.get("Agenda Title")
        if not title:
            continue

        print(f"--- Processing: '{title}' ---")

        existing_item = notion_data_map.get(title)

        if not existing_item:
            print("  [ACTION]: CREATE new page.")
            print("  [DETAILS]: Page does not exist in Notion.")
            print(f"  [DATA]: {item}")
        else:
            differences = compare_items(item, existing_item)
            if not differences:
                print("  [ACTION]: SKIP.")
                print("  [DETAILS]: Page exists in Notion and is identical.")
            else:
                print("  [ACTION]: UPDATE (Append).")
                print("  [DETAILS]: Page exists in Notion with differences.")
                for key, vals in differences.items():
                    print(f"    - Field '{key}':")
                    print(f"      - Local JSON:  '{vals['local']}'")
                    print(f"      - Notion:      '{vals['notion']}'")

        print("-" * (len(title) + 20) + "\n")


def main():
    workspace_root = Path(os.getcwd())
    json_file = workspace_root / "blackcore" / "models" / "json" / "agendas_epics.json"
    dry_run_sync(json_file)


if __name__ == "__main__":
    main()
