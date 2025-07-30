import json
import sys
from typing import Dict, Any
from blackcore.notion.client import (
    NotionClient,
    load_config_from_file,
    console,
    CACHE_DIR,
)


class SyncEngine:
    """Manages the core logic of diffing and planning the sync."""

    def __init__(
        self, db_name: str, config: Dict[str, Any], notion_client: NotionClient
    ):
        self.db_name = db_name
        self.config = config
        self.notion = notion_client
        self.title_prop = config["title_property"]
        self.cache_path = (
            CACHE_DIR
            / f"{db_name.lower().replace(' & ', '_').replace(' ', '_')}_cache.json"
        )
        self.db_schema = None  # Will be loaded during fetch

    def _prepare_relation_lookups(self) -> Dict[str, Any]:
        """Loads caches for related DBs and builds title->id lookup maps."""
        lookups = {}
        defined_relations = self.config.get("relations", {})
        if not defined_relations:
            return {}

        console.print("Preparing relation lookups...", style="yellow")
        for prop_name, target_db_name in defined_relations.items():
            cache_path = (
                CACHE_DIR
                / f"{target_db_name.lower().replace(' & ', '_').replace(' ', '_')}_cache.json"
            )
            if not cache_path.exists():
                console.print(
                    f"[bold red]Error:[/] Prerequisite cache file not found at '{cache_path}'.",
                    style="red",
                )
                console.print(
                    f"Please run the sync for the '[bold cyan]{target_db_name}[/]' database first.",
                    style="yellow",
                )
                continue

            with open(cache_path, "r", encoding="utf-8") as f:
                target_items = json.load(f)

            # Find the title property for the target database from the main config
            all_configs = load_config_from_file()
            target_config = all_configs.get(target_db_name, {})
            target_title_prop = target_config.get("title_property")

            if not target_title_prop:
                console.print(
                    f"[bold red]Error:[/] Could not find title property for target DB '{target_db_name}' in config.",
                    style="red",
                )
                continue

            id_map = {
                item.get(target_title_prop): item.get("notion_page_id")
                for item in target_items
            }
            lookups[prop_name] = {"target_db": target_db_name, "id_map": id_map}
            console.print(
                f"  - Prepared lookup for property '[magenta]{prop_name}[/]' -> DB '[cyan]{target_db_name}[/]' ({len(id_map)} items)."
            )

        return lookups

    def fetch_and_cache_db(self):
        """Fetches the full DB from Notion and saves a simplified version to a local cache file."""
        console.print(
            f"Fetching schema for '[bold cyan]{self.db_name}[/]'...",
            style="yellow",
        )
        self.db_schema = self.notion.get_database_schema(self.config["id"])
        if not self.db_schema:
            console.print(
                "[bold red]Error:[/] Could not fetch database schema. Aborting."
            )
            return

        console.print(
            f"Fetching pages from Notion for '[bold cyan]{self.db_name}[/]'...",
            style="yellow",
        )
        pages = self.notion.get_all_database_pages(self.config["id"])

        simple_pages = [self.notion.simplify_page_properties(p) for p in pages]
        self.cache_path.parent.mkdir(exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(simple_pages, f, indent=2)
        console.print(
            f"Success! Cached {len(simple_pages)} pages to '{self.cache_path}'.\n",
            style="green",
        )

    def plan_sync(self):
        """Compares local JSON to the cache and creates a transaction plan."""
        console.print("Planning sync...")

        # Load local source data
        local_path = self.config["local_json_path"]
        with open(local_path, "r", encoding="utf-8") as f:
            local_items = json.load(f).get(self.config["json_data_key"], [])

        # Load cached Notion data
        with open(self.cache_path, "r", encoding="utf-8") as f:
            notion_items = json.load(f)

        notion_map = {item.get(self.title_prop): item for item in notion_items}
        plan = []

        for item in local_items:
            title = item.get(self.title_prop)
            if not title:
                continue

            if title not in notion_map:
                plan.append({"action": "CREATE", "data": item})
            else:
                # In the future, this is where the UPDATE logic would go
                plan.append({"action": "SKIP", "title": title})

        console.print(
            f"Plan ready: {len([p for p in plan if p['action'] == 'CREATE'])} to CREATE, {len([p for p in plan if p['action'] == 'SKIP'])} to SKIP."
        )
        return plan

    def execute_plan(self, plan: list, is_live: bool = False):
        """Executes the transaction plan against the Notion API."""
        relation_lookups = self._prepare_relation_lookups()

        if not is_live:
            console.print("\n[bold]Executing Sync Plan (Dry Run)...[/bold]")
        else:
            console.print("\n[bold yellow]Executing Sync Plan (LIVE)...[/bold]")

        for item in plan:
            action = item["action"]
            if action == "CREATE":
                title = item["data"].get(self.title_prop, "Untitled")
                if is_live:
                    console.print(
                        f"  [CREATE] Creating page: '[cyan]{title}[/cyan]'...", end=""
                    )
                    properties = self.notion.build_payload_properties(
                        self.db_schema, item["data"], relation_lookups
                    )
                    response = self.notion.create_page(self.config["id"], properties)
                    if response:
                        console.print(" [bold green]Success![/bold green]")
                    else:
                        console.print(" [bold red]Failed.[/bold red]")
                else:
                    console.print(
                        f"  [DRY RUN - CREATE] Would create page for: '{title}'"
                    )

            elif action == "SKIP":
                console.print(f"  [SKIP] Page exists: '{item['title']}'")

        if not is_live:
            console.print(
                "\n[bold green]Dry run complete.[/bold] Use the --live flag to make actual changes."
            )
        else:
            console.print("\n[bold green]Live run complete.[/bold]")


def main():
    """Main function to orchestrate the sync process for a given database."""
    try:
        notion_client = NotionClient()
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}", style="red")
        return

    # Check if --refresh-config flag is present
    if "--refresh-config" in sys.argv:
        console.print("Refreshing Notion configuration...", style="yellow")
        notion_client.refresh_config()
        console.print("[bold green]Configuration refreshed successfully![/bold]")

    DATABASE_CONFIG = load_config_from_file()
    if not DATABASE_CONFIG:
        return

    # Determine which database to sync and if it's a live run
    is_live_run = "--live" in sys.argv
    db_to_sync = None
    for arg in sys.argv[1:]:
        if arg not in ["--live", "--refresh-config"]:
            db_to_sync = arg
            break

    if not db_to_sync:
        console.print(
            "[bold red]Error:[/] Please specify which database to sync.", style="red"
        )
        console.print('Example: `python3 -m scripts.notion_sync "Agendas & Epics"`')
        return

    config = DATABASE_CONFIG.get(db_to_sync)
    if not config:
        console.print(
            f"[bold red]Error:[/] No configuration found for database '{db_to_sync}'."
        )
        return

    # Validate that the database still exists
    db_id = config.get("id")
    if db_id and not notion_client.validate_database_exists(db_id):
        console.print(
            f"[bold red]Error:[/] Database '{db_to_sync}' (ID: {db_id}) not found or inaccessible."
        )
        refresh = (
            input("Would you like to refresh the configuration? (y/n): ")
            .lower()
            .strip()
        )
        if refresh == "y":
            notion_client.refresh_config()
            console.print("[bold green]Configuration refreshed![/bold]")
            # Reload config and try again
            DATABASE_CONFIG = load_config_from_file()
            config = DATABASE_CONFIG.get(db_to_sync)
            if not config:
                console.print(
                    f"[bold red]Error:[/] Database '{db_to_sync}' still not found after refresh."
                )
                return
        else:
            return

    # Run the sync process
    engine = SyncEngine(db_to_sync, config, notion_client)
    engine.fetch_and_cache_db()
    plan = engine.plan_sync()
    engine.execute_plan(plan, is_live=is_live_run)


if __name__ == "__main__":
    main()
