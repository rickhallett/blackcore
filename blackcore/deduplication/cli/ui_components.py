"""
Rich UI components for the deduplication CLI.

Provides interactive, visually appealing components for progress tracking,
entity comparison, and match review.
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeRemainingColumn,
    SpinnerColumn, MofNCompleteColumn, TimeElapsedColumn
)
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.text import Text
from rich import box
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.syntax import Syntax

from .async_engine import ProgressUpdate


class UIComponents:
    """Collection of Rich UI components for the CLI."""
    
    def __init__(self):
        """Initialize UI components."""
        self.console = Console()
        
    def create_welcome_panel(self, version: str = "1.0.0") -> Panel:
        """Create the welcome panel."""
        content = f"""[bold cyan]Blackcore Deduplication Engine[/bold cyan]
[dim]Standard Mode v{version}[/dim]

[yellow]Intelligent entity resolution with AI-powered analysis[/yellow]

Press [bold]Enter[/bold] to continue..."""
        
        return Panel(
            Align.center(content, vertical="middle"),
            title="Welcome",
            border_style="cyan",
            height=10
        )
        
    def create_main_menu(self) -> Panel:
        """Create the main menu panel."""
        menu_items = [
            "[1] 🔍 New Analysis",
            "[2] ⚙️  Configure Settings", 
            "[3] 📊 View Statistics",
            "[4] ❓ Help & Documentation",
            "[5] 🚪 Exit"
        ]
        
        content = "\n".join(menu_items)
        
        return Panel(
            content,
            title="Main Menu",
            border_style="blue",
            padding=(1, 2)
        )
        
    def create_database_selection_table(
        self,
        databases: Dict[str, Dict[str, Any]]
    ) -> Table:
        """Create a table for database selection."""
        table = Table(
            title="Available Databases",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("#", justify="right", style="dim", width=4)
        table.add_column("Database Name", style="cyan", no_wrap=True)
        table.add_column("Records", justify="right", style="green")
        table.add_column("Last Modified", justify="center")
        table.add_column("Selected", justify="center")
        
        for idx, (name, info) in enumerate(databases.items(), 1):
            last_modified = info.get("last_modified", "Unknown")
            if isinstance(last_modified, datetime):
                last_modified = last_modified.strftime("%Y-%m-%d %H:%M")
                
            table.add_row(
                str(idx),
                name,
                str(info.get("record_count", 0)),
                last_modified,
                "✓" if info.get("selected", False) else ""
            )
            
        return table
        
    def create_threshold_config_panel(
        self,
        auto_merge: float = 90.0,
        review: float = 70.0
    ) -> Panel:
        """Create threshold configuration panel with preview."""
        content = f"""[bold cyan]Confidence Thresholds[/bold cyan]

[yellow]Auto-merge threshold:[/yellow] {auto_merge}%
  Matches above this confidence will be marked for automatic merging
  
[yellow]Review threshold:[/yellow] {review}%
  Matches above this confidence will be flagged for human review
  
[dim]Matches below {review}% are considered unlikely duplicates[/dim]

[bold]Impact Preview:[/bold]
  • High confidence (>{auto_merge}%): Auto-merge candidates
  • Medium confidence ({review}-{auto_merge}%): Human review required
  • Low confidence (<{review}%): Likely not duplicates"""
        
        return Panel(
            content,
            title="Threshold Configuration",
            border_style="yellow",
            padding=(1, 2)
        )
        
    def prompt_threshold(
        self,
        prompt_text: str,
        default: int,
        min_value: int = 0,
        max_value: int = 100
    ) -> int:
        """Prompt for threshold value with validation."""
        while True:
            try:
                value = IntPrompt.ask(
                    prompt_text,
                    default=default,
                    show_default=True
                )
                
                if min_value <= value <= max_value:
                    return value
                else:
                    self.console.print(
                        f"[red]Value must be between {min_value} and {max_value}[/red]"
                    )
            except KeyboardInterrupt:
                raise
            except Exception:
                self.console.print("[red]Invalid input, please enter a number[/red]")


class ProgressTracker:
    """Advanced progress tracking with Rich."""
    
    def __init__(self, console: Console):
        """Initialize progress tracker."""
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
            refresh_per_second=10
        )
        self.live = None
        self.layout = None
        self.stats_panel = None
        
    def create_dashboard_layout(self) -> Layout:
        """Create the analysis dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=7),
            Layout(name="stats", size=10),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(
            Panel(
                "[bold cyan]Deduplication Analysis in Progress[/bold cyan]",
                border_style="cyan"
            )
        )
        
        # Footer
        layout["footer"].update(
            Panel(
                "[dim]Press Ctrl+C to cancel[/dim]",
                border_style="dim"
            )
        )
        
        return layout
        
    async def track_progress(self, total_stages: int = 5):
        """Start progress tracking."""
        self.layout = self.create_dashboard_layout()
        
        # Just use the progress bar without Live display for now
        # to avoid nested Live display issues
        with self.progress:
            # Add progress to layout
            self.layout["progress"].update(
                Panel(self.progress, title="Progress", border_style="green")
            )
            
            # Print the layout once
            self.console.print(self.layout)
            
            yield self
                
    async def update_progress(self, update: ProgressUpdate):
        """Update progress display."""
        # Update progress bar
        if hasattr(self, 'current_task'):
            self.progress.update(
                self.current_task,
                completed=update.current,
                total=update.total,
                description=update.stage
            )
        else:
            self.current_task = self.progress.add_task(
                update.stage,
                total=update.total,
                completed=update.current
            )
            
        # Update statistics
        self._update_stats(update)
        
    def _update_stats(self, update: ProgressUpdate):
        """Update statistics panel."""
        stats_lines = [
            f"[bold]Stage:[/bold] {update.stage}",
            f"[bold]Progress:[/bold] {update.current}/{update.total} entities",
            f"[bold]Percentage:[/bold] {(update.current/update.total*100):.1f}%" if update.total > 0 else "0%",
        ]
        
        if update.processing_rate > 0:
            stats_lines.append(
                f"[bold]Rate:[/bold] {update.processing_rate:.1f} entities/sec"
            )
            
        if update.eta_seconds:
            eta = timedelta(seconds=int(update.eta_seconds))
            stats_lines.append(f"[bold]ETA:[/bold] {eta}")
            
        if update.message:
            stats_lines.append(f"\n[dim]{update.message}[/dim]")
            
        self.stats_panel = Panel(
            "\n".join(stats_lines),
            title="Statistics",
            border_style="blue"
        )
        
        if self.layout:
            self.layout["stats"].update(self.stats_panel)


class MatchReviewDisplay:
    """Display component for reviewing matches."""
    
    def __init__(self, console: Console):
        """Initialize match review display."""
        self.console = console
        
    def create_match_comparison(
        self,
        match: Dict[str, Any],
        match_number: int,
        total_matches: int
    ) -> Layout:
        """Create a comparison view for a match."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="comparison", size=15),
            Layout(name="evidence", size=8),
            Layout(name="actions", size=3)
        )
        
        # Header with confidence
        confidence = match.get("confidence_score", 0)
        confidence_level = self._get_confidence_level(confidence)
        
        # Get primary entity indicator (default to A)
        primary_entity = match.get("primary_entity", "A")
        
        layout["header"].update(
            Panel(
                f"[bold]Match {match_number} of {total_matches}[/bold] • "
                f"Confidence: [bold {confidence_level['color']}]{confidence:.1f}%[/bold {confidence_level['color']}] "
                f"[{confidence_level['label']}]\n"
                f"[dim]Primary Entity: [bold yellow]{primary_entity}[/bold yellow] (will be kept)[/dim]",
                border_style=confidence_level['color']
            )
        )
        
        # Entity comparison
        comparison_table = self._create_comparison_table(
            match.get("entity_a", {}),
            match.get("entity_b", {}),
            primary_entity
        )
        layout["comparison"].update(
            Panel(comparison_table, title="Entity Comparison", border_style="cyan")
        )
        
        # Evidence
        evidence_text = self._format_evidence(match)
        layout["evidence"].update(
            Panel(evidence_text, title="Evidence", border_style="yellow")
        )
        
        # Actions
        layout["actions"].update(
            Panel(
                "[bold][A][/bold]pprove  [bold][R][/bold]eject  "
                "[bold][D][/bold]efer  [bold][S][/bold]wap Primary  "
                "[bold][E][/bold]vidence  [bold][M][/bold]erge Preview\n"
                "[bold][N][/bold]ext  [bold][P][/bold]rev  [bold][Q][/bold]uit",
                border_style="green"
            )
        )
        
        return layout
        
    def _create_comparison_table(
        self,
        entity_a: Dict[str, Any],
        entity_b: Dict[str, Any],
        primary_entity: str = "A"
    ) -> Table:
        """Create side-by-side comparison table."""
        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold",
            expand=True
        )
        
        table.add_column("Field", style="cyan", width=20)
        
        # Highlight primary entity column
        if primary_entity == "A":
            table.add_column("Entity A [PRIMARY]", style="bright_white bold")
            table.add_column("Entity B", style="white")
        else:
            table.add_column("Entity A", style="white")
            table.add_column("Entity B [PRIMARY]", style="bright_white bold")
            
        table.add_column("Match", justify="center", width=10)
        
        # Get all fields
        all_fields = sorted(set(entity_a.keys()) | set(entity_b.keys()))
        
        # Filter out internal fields
        display_fields = [
            f for f in all_fields 
            if not f.startswith("_") and f != "id"
        ]
        
        # Calculate completeness
        completeness_a = sum(1 for f in display_fields if entity_a.get(f))
        completeness_b = sum(1 for f in display_fields if entity_b.get(f))
        total_fields = len(display_fields)
        
        # Add completeness row
        table.add_row(
            "[bold]Completeness[/bold]",
            f"[green]{completeness_a}/{total_fields} fields[/green]",
            f"[green]{completeness_b}/{total_fields} fields[/green]",
            ""
        )
        table.add_row("", "", "", "")  # Empty row for spacing
        
        for field in display_fields:
            val_a = entity_a.get(field, "")
            val_b = entity_b.get(field, "")
            
            # Handle list values
            if isinstance(val_a, list):
                val_a = ", ".join(str(v) for v in val_a) if val_a else ""
            else:
                val_a = str(val_a) if val_a else ""
                
            if isinstance(val_b, list):
                val_b = ", ".join(str(v) for v in val_b) if val_b else ""
            else:
                val_b = str(val_b) if val_b else ""
            
            # Determine match status
            if not val_a or not val_b:
                match_icon = "➖"
                match_color = "dim"
            elif val_a.lower() == val_b.lower():
                match_icon = "✅"
                match_color = "green"
            else:
                match_icon = "❌"
                match_color = "red"
                
            table.add_row(
                field,
                val_a or "[dim]—[/dim]",
                val_b or "[dim]—[/dim]",
                f"[{match_color}]{match_icon}[/{match_color}]"
            )
            
        return table
        
    def _format_evidence(self, match: Dict[str, Any]) -> str:
        """Format evidence for display."""
        evidence_lines = []
        
        # Similarity scores
        scores = match.get("similarity_scores", {})
        if scores:
            evidence_lines.append("[bold]Similarity Scores:[/bold]")
            for field, score_data in scores.items():
                if isinstance(score_data, dict):
                    score = score_data.get("composite", 0)
                    evidence_lines.append(f"  • {field}: {score:.1f}%")
                    
        # AI analysis
        ai_analysis = match.get("ai_analysis", {})
        if ai_analysis:
            evidence_lines.append("\n[bold]AI Analysis:[/bold]")
            if ai_analysis.get("reasoning"):
                evidence_lines.append(f"  {ai_analysis['reasoning']}")
            if ai_analysis.get("risk_assessment"):
                evidence_lines.append(f"  Risk: {ai_analysis['risk_assessment']}")
                
        # Key evidence points
        if match.get("key_evidence"):
            evidence_lines.append("\n[bold]Key Evidence:[/bold]")
            for evidence in match["key_evidence"]:
                evidence_lines.append(f"  • {evidence}")
                
        return "\n".join(evidence_lines) if evidence_lines else "[dim]No additional evidence[/dim]"
        
    def _get_confidence_level(self, confidence: float) -> Dict[str, str]:
        """Get confidence level label and color."""
        if confidence >= 90:
            return {"label": "HIGH", "color": "green"}
        elif confidence >= 70:
            return {"label": "MEDIUM", "color": "yellow"}
        else:
            return {"label": "LOW", "color": "red"}
            
    def display_review_summary(
        self,
        total_reviewed: int,
        approved: int,
        rejected: int,
        deferred: int
    ) -> Panel:
        """Display review session summary."""
        summary = f"""[bold cyan]Review Session Complete[/bold cyan]

[bold]Total Reviewed:[/bold] {total_reviewed}
[bold green]Approved:[/bold green] {approved}
[bold red]Rejected:[/bold red] {rejected}
[bold yellow]Deferred:[/bold yellow] {deferred}

[dim]Results have been saved to the audit system.[/dim]"""
        
        return Panel(
            summary,
            title="Summary",
            border_style="cyan",
            padding=(1, 2)
        )
        
    def display_help(self) -> Panel:
        """Display help information."""
        help_text = """[bold cyan]Keyboard Shortcuts[/bold cyan]

[bold]Navigation:[/bold]
  j, ↓    Next match
  k, ↑    Previous match
  g       Go to first match
  G       Go to last match
  /       Search matches

[bold]Actions:[/bold]
  a       Approve merge
  r       Reject (not duplicates)
  d       Defer decision
  s       Swap primary entity
  e       View detailed evidence
  m       Show merge preview
  
[bold]Other:[/bold]
  h, ?    Show this help
  q       Quit review session
  
[bold]About Merging:[/bold]
  • The PRIMARY entity is kept as the base record
  • Empty fields are filled from the secondary entity
  • Conflicting data is preserved in metadata
  • Use 's' to swap which entity is primary
  
[dim]Press any key to continue...[/dim]"""
        
        return Panel(
            help_text,
            title="Help",
            border_style="blue",
            padding=(1, 2)
        )
        
    def create_merge_preview(
        self,
        entity_a: Dict[str, Any],
        entity_b: Dict[str, Any],
        primary_entity: str = "A"
    ) -> Panel:
        """Create a preview of what the merged entity will look like."""
        # Determine primary and secondary based on selection
        if primary_entity == "A":
            primary = entity_a.copy()
            secondary = entity_b.copy()
        else:
            primary = entity_b.copy()
            secondary = entity_a.copy()
            
        # Simulate merge (conservative strategy)
        merged = primary.copy()
        conflicts = []
        filled_fields = []
        
        for key, value in secondary.items():
            if key.startswith("_") or key == "id":
                continue
                
            if key in merged and merged[key] and merged[key] != value:
                # Conflict detected
                conflicts.append(f"{key}: '{merged[key]}' vs '{value}'")
            elif key not in merged or not merged[key]:
                # Fill empty field
                merged[key] = value
                filled_fields.append(f"{key}: '{value}'")
                
        # Create preview text
        preview_lines = ["[bold]Merged Entity Preview:[/bold]\n"]
        
        # Show key fields
        key_fields = ["Full Name", "Email", "Phone", "Organization"]
        for field in key_fields:
            if field in merged and merged[field]:
                preview_lines.append(f"[cyan]{field}:[/cyan] {merged[field]}")
                
        # Show other fields
        other_fields = [f for f in sorted(merged.keys()) 
                       if f not in key_fields and not f.startswith("_") and f != "id"]
        if other_fields:
            preview_lines.append("\n[dim]Other fields:[/dim]")
            for field in other_fields[:5]:  # Show first 5
                if merged[field]:
                    preview_lines.append(f"[dim]{field}: {merged[field]}[/dim]")
                    
        # Show merge information
        preview_lines.append(f"\n[bold]Merge Information:[/bold]")
        preview_lines.append(f"Primary entity: [yellow]{primary_entity}[/yellow]")
        preview_lines.append(f"Fields filled from secondary: [green]{len(filled_fields)}[/green]")
        
        if filled_fields:
            preview_lines.append("\n[dim]Filled fields:[/dim]")
            for field in filled_fields[:3]:
                preview_lines.append(f"  • {field}")
            if len(filled_fields) > 3:
                preview_lines.append(f"  ... and {len(filled_fields) - 3} more")
                
        if conflicts:
            preview_lines.append(f"\n[yellow]Conflicts detected: {len(conflicts)}[/yellow]")
            preview_lines.append("[dim]These will be preserved in metadata:[/dim]")
            for conflict in conflicts[:3]:
                preview_lines.append(f"  • {conflict}")
            if len(conflicts) > 3:
                preview_lines.append(f"  ... and {len(conflicts) - 3} more")
                
        return Panel(
            "\n".join(preview_lines),
            title="Merge Preview",
            border_style="cyan",
            padding=(1, 2)
        )