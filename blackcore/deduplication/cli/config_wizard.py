"""
Interactive configuration wizard for the deduplication CLI.

Guides users through setting up thresholds, AI settings, and database selection.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich import box

from .ui_components import UIComponents


class ConfigurationWizard:
    """
    Interactive configuration wizard for deduplication settings.
    
    Provides step-by-step guidance for configuring:
    - Database selection
    - Confidence thresholds
    - AI settings
    - Processing options
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the configuration wizard."""
        self.console = console or Console()
        self.ui = UIComponents()
        self.config = self._load_default_config()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "thresholds": {
                "auto_merge": 90.0,
                "human_review": 70.0
            },
            "ai": {
                "enabled": True,
                "model": "claude-3-7-sonnet-20250219",
                "fallback_model": "gpt-4",
                "max_concurrent": 5,
                "timeout": 30
            },
            "processing": {
                "batch_size": 100,
                "enable_graph_analysis": True,
                "safety_mode": True
            },
            "ui": {
                "page_size": 10,
                "show_memory": False,
                "color_scheme": "default"
            }
        }
        
    async def run_wizard(self, available_databases: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Run the configuration wizard.
        
        Args:
            available_databases: Dict of database names to record counts
            
        Returns:
            Complete configuration dictionary
        """
        self.console.clear()
        
        # Welcome
        self.console.print(Panel(
            "[bold cyan]Configuration Wizard[/bold cyan]\n\n"
            "This wizard will help you configure the deduplication engine.\n"
            "Press Ctrl+C at any time to cancel.",
            border_style="cyan",
            padding=(1, 2)
        ))
        
        try:
            # Step 1: Database Selection
            if available_databases:
                selected_databases = await self._select_databases(available_databases)
                self.config["databases"] = selected_databases
            
            # Step 2: Threshold Configuration
            thresholds = await self._configure_thresholds()
            self.config["thresholds"] = thresholds
            
            # Step 3: AI Settings
            ai_config = await self._configure_ai()
            self.config["ai"] = ai_config
            
            # Step 4: Processing Options
            processing = await self._configure_processing()
            self.config["processing"] = processing
            
            # Step 5: Review and Confirm
            if await self._review_configuration():
                return self.config
            else:
                # Start over
                return await self.run_wizard(available_databases)
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Configuration cancelled[/yellow]")
            raise
            
    async def _select_databases(self, available_databases: Dict[str, int]) -> List[str]:
        """Database selection step."""
        self.console.print("\n[bold]Step 1: Database Selection[/bold]")
        
        # Create selection table
        table = Table(
            title="Available Databases",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("#", justify="right", style="dim", width=4)
        table.add_column("Database Name", style="cyan")
        table.add_column("Records", justify="right", style="green")
        
        db_list = list(available_databases.items())
        for idx, (name, count) in enumerate(db_list, 1):
            table.add_row(str(idx), name, f"{count:,}")
            
        self.console.print(table)
        
        # Get selection
        selected = []
        
        if Confirm.ask("\n[yellow]Analyze all databases?[/yellow]", default=True):
            selected = [name for name, _ in db_list]
        else:
            self.console.print("\nEnter database numbers to analyze (comma-separated):")
            selection = Prompt.ask("Selection", default="1")
            
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(",")]
                selected = [db_list[i][0] for i in indices if 0 <= i < len(db_list)]
            except (ValueError, IndexError):
                self.console.print("[red]Invalid selection, using all databases[/red]")
                selected = [name for name, _ in db_list]
                
        self.console.print(f"\n[green]Selected {len(selected)} database(s)[/green]")
        return selected
        
    async def _configure_thresholds(self) -> Dict[str, float]:
        """Threshold configuration step."""
        self.console.print("\n[bold]Step 2: Confidence Thresholds[/bold]")
        
        # Show explanation
        self.console.print(Panel(
            "Confidence thresholds determine how matches are handled:\n\n"
            "• [bold]Auto-merge[/bold]: Matches above this are merge candidates\n"
            "• [bold]Review[/bold]: Matches above this need human review\n"
            "• Below review threshold: Considered non-duplicates",
            border_style="blue",
            padding=(1, 2)
        ))
        
        # Get thresholds
        auto_merge = self._prompt_threshold(
            "\n[yellow]Auto-merge threshold (%)[/yellow]",
            default=self.config["thresholds"]["auto_merge"],
            min_value=80,
            max_value=100
        )
        
        review = self._prompt_threshold(
            "[yellow]Review threshold (%)[/yellow]",
            default=self.config["thresholds"]["human_review"],
            min_value=50,
            max_value=auto_merge - 1
        )
        
        # Show impact
        self._show_threshold_impact(auto_merge, review)
        
        return {
            "auto_merge": auto_merge,
            "human_review": review
        }
        
    def _prompt_threshold(
        self,
        prompt: str,
        default: float,
        min_value: float,
        max_value: float
    ) -> float:
        """Prompt for a threshold value with validation."""
        while True:
            try:
                value = FloatPrompt.ask(
                    prompt,
                    default=default,
                    show_default=True
                )
                
                if min_value <= value <= max_value:
                    return value
                else:
                    self.console.print(
                        f"[red]Value must be between {min_value} and {max_value}[/red]"
                    )
            except ValueError:
                self.console.print("[red]Please enter a valid number[/red]")
                
    def _show_threshold_impact(self, auto_merge: float, review: float):
        """Show the impact of threshold settings."""
        self.console.print(Panel(
            f"[bold]Threshold Impact:[/bold]\n\n"
            f"• Confidence ≥ {auto_merge}%: [green]Auto-merge candidates[/green]\n"
            f"• Confidence {review}-{auto_merge}%: [yellow]Human review required[/yellow]\n"
            f"• Confidence < {review}%: [red]Not duplicates[/red]",
            border_style="cyan"
        ))
        
    async def _configure_ai(self) -> Dict[str, Any]:
        """AI configuration step."""
        self.console.print("\n[bold]Step 3: AI Settings (Optional)[/bold]")
        
        # Check if AI should be enabled
        enable_ai = Confirm.ask(
            "[yellow]Enable AI-powered analysis?[/yellow]",
            default=True
        )
        
        if not enable_ai:
            return {
                "enabled": False,
                "model": None,
                "fallback_model": None,
                "max_concurrent": 5,
                "timeout": 30
            }
            
        # Check for API keys
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        
        # Check if keys are valid (not empty and not placeholder)
        has_claude = bool(anthropic_key and anthropic_key != "your_key_here")
        has_openai = bool(openai_key and openai_key != "your_key_here")
        
        if not has_claude and not has_openai:
            self.console.print(Panel(
                "[yellow]No AI API keys found![/yellow]\n\n"
                "To use AI analysis, set one of:\n"
                "• ANTHROPIC_API_KEY for Claude\n"
                "• OPENAI_API_KEY for GPT\n\n"
                "Continuing without AI analysis.",
                border_style="yellow"
            ))
            return {"enabled": False}
            
        # Select primary model
        available_models = []
        if has_claude:
            available_models.extend([
                "claude-3-7-sonnet-20250219",
                "claude-sonnet-4-20250514",
                "claude-opus-4-20250514",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229"
            ])
        if has_openai:
            available_models.extend(["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"])
            
        primary_model = Prompt.ask(
            "[yellow]Primary AI model[/yellow]",
            choices=available_models,
            default=available_models[0]
        )
        
        # Configure limits
        max_concurrent = IntPrompt.ask(
            "[yellow]Max concurrent AI requests[/yellow]",
            default=5,
            show_default=True
        )
        
        timeout = IntPrompt.ask(
            "[yellow]AI request timeout (seconds)[/yellow]",
            default=30,
            show_default=True
        )
        
        return {
            "enabled": True,
            "model": primary_model,
            "fallback_model": "gpt-3.5-turbo" if has_openai else None,
            "max_concurrent": max_concurrent,
            "timeout": timeout
        }
        
    async def _configure_processing(self) -> Dict[str, Any]:
        """Processing options configuration."""
        self.console.print("\n[bold]Step 4: Processing Options[/bold]")
        
        batch_size = IntPrompt.ask(
            "[yellow]Batch size for processing[/yellow]",
            default=100,
            show_default=True
        )
        
        enable_graph = Confirm.ask(
            "[yellow]Enable graph-based relationship analysis?[/yellow]",
            default=True
        )
        
        safety_mode = Confirm.ask(
            "[yellow]Enable safety mode (no automatic changes)?[/yellow]",
            default=True
        )
        
        return {
            "batch_size": batch_size,
            "enable_graph_analysis": enable_graph,
            "safety_mode": safety_mode
        }
        
    async def _review_configuration(self) -> bool:
        """Review and confirm configuration."""
        self.console.print("\n[bold]Step 5: Review Configuration[/bold]")
        
        # Create summary
        summary_lines = []
        
        # Databases
        if "databases" in self.config:
            summary_lines.append(f"[bold]Databases:[/bold] {', '.join(self.config['databases'])}")
        
        # Thresholds
        t = self.config["thresholds"]
        summary_lines.append(
            f"[bold]Thresholds:[/bold] Auto-merge={t['auto_merge']}%, "
            f"Review={t['human_review']}%"
        )
        
        # AI
        ai = self.config["ai"]
        if ai["enabled"]:
            summary_lines.append(f"[bold]AI:[/bold] {ai['model']} (enabled)")
        else:
            summary_lines.append("[bold]AI:[/bold] Disabled")
            
        # Processing
        p = self.config["processing"]
        summary_lines.append(
            f"[bold]Processing:[/bold] Batch size={p['batch_size']}, "
            f"Graph={'enabled' if p['enable_graph_analysis'] else 'disabled'}, "
            f"Safety mode={'ON' if p['safety_mode'] else 'OFF'}"
        )
        
        self.console.print(Panel(
            "\n".join(summary_lines),
            title="Configuration Summary",
            border_style="green",
            padding=(1, 2)
        ))
        
        return Confirm.ask("\n[yellow]Proceed with this configuration?[/yellow]", default=True)
        
    def save_config(self, config: Dict[str, Any], path: Optional[Path] = None):
        """Save configuration to file."""
        if path is None:
            config_dir = Path.home() / ".blackcore"
            config_dir.mkdir(exist_ok=True)
            path = config_dir / "dedupe-config.json"
            
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
            
        self.console.print(f"[green]Configuration saved to {path}[/green]")
        
    def load_config(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from file."""
        if path is None:
            path = Path.home() / ".blackcore" / "dedupe-config.json"
            
        if path.exists():
            with open(path) as f:
                return json.load(f)
        else:
            return self._load_default_config()
            
    def quick_config(self) -> Dict[str, Any]:
        """Quick configuration with all defaults."""
        self.console.print(Panel(
            "[bold cyan]Quick Configuration[/bold cyan]\n\n"
            "Using default settings:\n"
            "• Auto-merge: 90%\n"
            "• Review: 70%\n"
            "• AI: Enabled (if keys available)\n"
            "• Safety mode: ON",
            border_style="cyan"
        ))
        
        return self.config