#!/usr/bin/env python3
"""
Test deduplication on the People & Contacts database.

This script:
1. Loads the People & Contacts database
2. Runs deduplication analysis in safety mode
3. Shows all potential duplicates found
"""

import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication import DeduplicationEngine


def main():
    """Run deduplication analysis on People & Contacts."""
    console = Console()

    console.print(
        Panel(
            "[bold cyan]People & Contacts Deduplication Test[/bold cyan]\n\n"
            "This will analyze the People & Contacts database for potential duplicates.\n"
            "Running in SAFETY MODE - no changes will be made.",
            border_style="cyan",
        )
    )

    # Load the People & Contacts data
    json_path = (
        Path(__file__).parent.parent
        / "blackcore"
        / "models"
        / "json"
        / "people_places.json"
    )

    if not json_path.exists():
        console.print(f"[red]Error: Could not find {json_path}[/red]")
        return 1

    with open(json_path) as f:
        data = json.load(f)

    people_data = data.get("People & Contacts", [])
    console.print(f"\n[bold]Loaded {len(people_data)} people from database[/bold]")

    # Show sample of data
    console.print("\n[bold]Sample entries:[/bold]")
    for i, person in enumerate(people_data[:5]):
        name = person.get("Full Name", "Unknown")
        email = person.get("Email", "No email")
        org = person.get("Organization", "No org")
        console.print(f"  {i+1}. {name} - {email} ({org})")
    if len(people_data) > 5:
        console.print(f"  ... and {len(people_data) - 5} more")

    # Initialize deduplication engine
    console.print("\n[bold]Initializing deduplication engine...[/bold]")
    engine = DeduplicationEngine()

    # Configure for safety mode
    engine.config.update(
        {
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "enable_ai_analysis": False,  # Disable AI for faster testing
            "safety_mode": True,  # SAFETY MODE - no automatic changes
        }
    )

    console.print("Configuration:")
    console.print(f"  • Auto-merge threshold: {engine.config['auto_merge_threshold']}%")
    console.print(f"  • Review threshold: {engine.config['human_review_threshold']}%")
    console.print(
        f"  • AI analysis: {'Enabled' if engine.config['enable_ai_analysis'] else 'Disabled'}"
    )
    console.print(f"  • [green]Safety mode: ON[/green] (no automatic changes)")

    # Run analysis
    console.print("\n[bold]Running deduplication analysis...[/bold]")
    result = engine.analyze_database("People & Contacts", people_data, enable_ai=False)

    # Display results
    console.print(f"\n[bold]Analysis Results:[/bold]")
    console.print(f"  • Total entities analyzed: {result.total_entities}")
    console.print(f"  • Potential duplicates found: {result.potential_duplicates}")
    console.print(
        f"  • High confidence matches (>90%): {len(result.high_confidence_matches)}"
    )
    console.print(
        f"  • Medium confidence matches (70-90%): {len(result.medium_confidence_matches)}"
    )
    console.print(
        f"  • Low confidence matches (<70%): {len(result.low_confidence_matches)}"
    )

    # Show all matches
    all_matches = []
    all_matches.extend([(m, "HIGH") for m in result.high_confidence_matches])
    all_matches.extend([(m, "MEDIUM") for m in result.medium_confidence_matches])
    all_matches.extend([(m, "LOW") for m in result.low_confidence_matches])

    if all_matches:
        console.print(
            f"\n[bold]Found {len(all_matches)} potential duplicate pairs:[/bold]\n"
        )

        # Create a table for matches
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Person A", style="cyan", no_wrap=True)
        table.add_column("Person B", style="cyan", no_wrap=True)
        table.add_column("Confidence", justify="right")
        table.add_column("Level", justify="center")
        table.add_column("Key Evidence")

        for idx, (match, level) in enumerate(all_matches, 1):
            entity_a = match["entity_a"]
            entity_b = match["entity_b"]

            name_a = entity_a.get("Full Name", "Unknown")
            name_b = entity_b.get("Full Name", "Unknown")
            confidence = match["confidence_score"]

            # Determine evidence
            evidence = []
            if entity_a.get("Email") == entity_b.get("Email") and entity_a.get("Email"):
                evidence.append("Same email")
            if entity_a.get("Phone") == entity_b.get("Phone") and entity_a.get("Phone"):
                evidence.append("Same phone")
            if entity_a.get("Organization") == entity_b.get(
                "Organization"
            ) and entity_a.get("Organization"):
                evidence.append("Same org")

            # Check for nickname patterns
            if (
                "Tony" in name_a
                and "Anthony" in name_b
                or "Tony" in name_b
                and "Anthony" in name_a
            ):
                evidence.append("Nickname match")
            if (
                "Bob" in name_a
                and "Robert" in name_b
                or "Bob" in name_b
                and "Robert" in name_a
            ):
                evidence.append("Nickname match")

            evidence_str = ", ".join(evidence[:2]) if evidence else "Name similarity"

            # Color code by confidence level
            if level == "HIGH":
                conf_color = "green"
            elif level == "MEDIUM":
                conf_color = "yellow"
            else:
                conf_color = "red"

            table.add_row(
                str(idx),
                name_a,
                name_b,
                f"[{conf_color}]{confidence:.1f}%[/{conf_color}]",
                f"[{conf_color}]{level}[/{conf_color}]",
                evidence_str,
            )

        console.print(table)

        # Show detailed view of top matches
        if result.high_confidence_matches:
            console.print(f"\n[bold]Detailed view of HIGH confidence matches:[/bold]")

            for i, match in enumerate(result.high_confidence_matches[:3], 1):
                entity_a = match["entity_a"]
                entity_b = match["entity_b"]

                detail_text = f"""[bold]Match {i}:[/bold]
                
Entity A:
  Name: {entity_a.get('Full Name', 'Unknown')}
  Email: {entity_a.get('Email', 'None')}
  Phone: {entity_a.get('Phone', 'None')}
  Organization: {entity_a.get('Organization', 'None')}
  
Entity B:
  Name: {entity_b.get('Full Name', 'Unknown')}
  Email: {entity_b.get('Email', 'None')}
  Phone: {entity_b.get('Phone', 'None')}
  Organization: {entity_b.get('Organization', 'None')}
  
Confidence: {match['confidence_score']:.1f}%
Recommendation: {match.get('recommended_action', 'Review needed')}"""

                console.print(Panel(detail_text, border_style="green"))

    else:
        console.print("\n[green]No potential duplicates found![/green]")

    console.print("\n[bold]Summary:[/bold]")
    console.print("• Analysis completed successfully")
    console.print("• Running in SAFETY MODE - no changes were made")
    console.print(
        "• To review matches interactively, run: python scripts/dedupe_cli.py"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
