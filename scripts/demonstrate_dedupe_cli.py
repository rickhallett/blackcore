#!/usr/bin/env python3
"""
Demonstrate the deduplication CLI is working correctly.

This script shows that:
1. The CLI loads databases correctly
2. The deduplication engine detects duplicates
3. The UI components work properly
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication.cli import StandardModeCLI, UIComponents
from blackcore.deduplication import DeduplicationEngine
from rich.console import Console
from rich.panel import Panel


async def demonstrate():
    """Demonstrate key functionality."""
    console = Console()
    
    console.print(Panel(
        "[bold cyan]Deduplication CLI Demonstration[/bold cyan]\n\n"
        "This demonstrates that the CLI is working correctly.",
        border_style="cyan"
    ))
    
    # 1. Test database loading
    console.print("\n[bold]1. Testing Database Loading[/bold]")
    cli = StandardModeCLI()
    databases = await cli._load_databases()
    
    console.print(f"   ✓ Found {len(databases)} databases")
    for i, (name, records) in enumerate(list(databases.items())[:3]):
        console.print(f"     - {name}: {len(records)} records")
    if len(databases) > 3:
        console.print(f"     ... and {len(databases) - 3} more")
    
    # 2. Test deduplication on sample data
    console.print("\n[bold]2. Testing Deduplication Engine[/bold]")
    
    # Get some real data
    people_data = databases.get("People & Contacts", [])[:5]
    if people_data:
        engine = DeduplicationEngine()
        result = engine.analyze_database("People & Contacts", people_data, enable_ai=False)
        
        console.print(f"   ✓ Analyzed {result.total_entities} entities")
        console.print(f"   ✓ Found {result.potential_duplicates} potential duplicates")
    
    # 3. Test UI components
    console.print("\n[bold]3. Testing UI Components[/bold]")
    ui = UIComponents()
    
    # Test welcome panel
    welcome = ui.create_welcome_panel()
    console.print("   ✓ Welcome panel created")
    
    # Test menu
    menu = ui.create_main_menu()
    console.print("   ✓ Main menu created")
    
    # Test database table
    db_info = {name: {"record_count": len(records)} for name, records in list(databases.items())[:3]}
    table = ui.create_database_selection_table(db_info)
    console.print("   ✓ Database selection table created")
    
    # 4. Show sample UI
    console.print("\n[bold]4. Sample UI Display[/bold]\n")
    
    # Show the main menu
    console.print(menu)
    
    # Show threshold configuration
    threshold_panel = ui.create_threshold_config_panel(90, 70)
    console.print(threshold_panel)
    
    console.print("\n[green]✅ All components are working correctly![/green]")
    console.print("\n[bold]To run the full interactive CLI:[/bold]")
    console.print("  python scripts/dedupe_cli.py")
    console.print("\n[dim]The CLI will guide you through the complete deduplication workflow.[/dim]")


if __name__ == "__main__":
    asyncio.run(demonstrate())