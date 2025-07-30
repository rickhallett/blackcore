#!/usr/bin/env python3
"""
Demo script for the Deduplication CLI.

Shows how to use the CLI programmatically and demonstrates key features.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication.cli import AsyncDeduplicationEngine
from rich.console import Console
from rich.panel import Panel


async def demo_programmatic_usage():
    """Demonstrate programmatic usage of the CLI components."""
    console = Console()
    
    console.print(Panel(
        "[bold cyan]Deduplication CLI Demo[/bold cyan]\n\n"
        "This demo shows programmatic usage of the CLI components.",
        border_style="cyan"
    ))
    
    # Create test data with known duplicates
    test_data = {
        "Demo Database": [
            # Clear duplicates
            {"id": "1", "Full Name": "Anthony Smith", "Email": "tony.smith@example.com", "Organization": "Swanage Town Council"},
            {"id": "2", "Full Name": "Tony Smith", "Email": "tony.smith@example.com", "Organization": "STC"},
            
            # Another duplicate pair
            {"id": "3", "Full Name": "Robert Johnson", "Email": "bob@example.com", "Phone": "555-1234"},
            {"id": "4", "Full Name": "Bob Johnson", "Email": "robert.j@example.com", "Phone": "555-1234"},
            
            # Non-duplicate
            {"id": "5", "Full Name": "Alice Williams", "Email": "alice@example.com", "Organization": "Tech Corp"},
        ]
    }
    
    # Configure engine
    config = {
        "auto_merge_threshold": 90.0,
        "human_review_threshold": 70.0,
        "enable_ai_analysis": False,  # Disable AI for demo
        "safety_mode": True
    }
    
    console.print("\n[bold]1. Initializing Engine[/bold]")
    engine = AsyncDeduplicationEngine(config)
    
    # Progress callback
    async def on_progress(update):
        console.print(f"   📊 {update.stage}: {update.current}/{update.total}")
    
    console.print("\n[bold]2. Running Analysis[/bold]")
    results = await engine.analyze_databases_async(
        test_data,
        progress_callback=on_progress
    )
    
    # Display results
    console.print("\n[bold]3. Analysis Results[/bold]")
    
    for db_name, result in results.items():
        console.print(f"\n   Database: [cyan]{db_name}[/cyan]")
        console.print(f"   Total entities: {result.total_entities}")
        console.print(f"   Potential duplicates: {result.potential_duplicates}")
        
        if result.high_confidence_matches:
            console.print("\n   [green]High Confidence Matches:[/green]")
            for match in result.high_confidence_matches:
                name_a = match["entity_a"].get("Full Name", "Unknown")
                name_b = match["entity_b"].get("Full Name", "Unknown")
                confidence = match["confidence_score"]
                console.print(f"      • {name_a} ↔ {name_b} ({confidence:.1f}%)")
        
        if result.medium_confidence_matches:
            console.print("\n   [yellow]Medium Confidence Matches:[/yellow]")
            for match in result.medium_confidence_matches:
                name_a = match["entity_a"].get("Full Name", "Unknown")
                name_b = match["entity_b"].get("Full Name", "Unknown")
                confidence = match["confidence_score"]
                console.print(f"      • {name_a} ↔ {name_b} ({confidence:.1f}%)")
    
    # Cleanup
    await engine.shutdown()
    
    console.print("\n[green]✅ Demo completed successfully![/green]")


async def demo_ui_components():
    """Demonstrate UI components."""
    from blackcore.deduplication.cli.ui_components import UIComponents, MatchReviewDisplay
    
    console = Console()
    ui = UIComponents()
    
    console.print("\n[bold]UI Components Demo[/bold]\n")
    
    # Show threshold configuration panel
    threshold_panel = ui.create_threshold_config_panel(92, 75)
    console.print(threshold_panel)
    
    # Show match review display
    review_display = MatchReviewDisplay(console)
    
    # Create a sample match
    sample_match = {
        "entity_a": {
            "Full Name": "Anthony Smith",
            "Email": "tony.smith@example.com",
            "Organization": "Swanage Town Council",
            "Phone": "01234567890"
        },
        "entity_b": {
            "Full Name": "Tony Smith",
            "Email": "tony.smith@example.com",
            "Organization": "STC",
            "Phone": "01234 567 890"
        },
        "confidence_score": 92.5,
        "similarity_scores": {
            "Full Name": {"composite": 85.4},
            "Email": {"composite": 100.0},
            "Organization": {"composite": 90.0}
        },
        "key_evidence": [
            "Exact email match",
            "Tony is common nickname for Anthony",
            "STC = Swanage Town Council"
        ]
    }
    
    console.print("\n[bold]Match Review Display:[/bold]")
    layout = review_display.create_match_comparison(sample_match, 1, 1)
    console.print(layout)


async def main():
    """Run all demos."""
    console = Console()
    
    console.print(Panel(
        "[bold cyan]Blackcore Deduplication CLI Demo[/bold cyan]\n\n"
        "This demo showcases the key features of the Standard Mode CLI.",
        title="Welcome",
        border_style="cyan"
    ))
    
    # Run demos
    await demo_programmatic_usage()
    await demo_ui_components()
    
    console.print("\n" + "="*60)
    console.print("[bold]To run the interactive CLI:[/bold]")
    console.print("  python scripts/dedupe_cli.py")
    console.print("\n[bold]For more information:[/bold]")
    console.print("  See specs/dedupe-cli-standard-mode.md")
    console.print("  See dedupe-engine-commands.md")
    console.print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())