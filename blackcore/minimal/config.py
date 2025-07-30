"""Configuration management for minimal transcript processor."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from .models import Config


class ConfigManager:
    """Manages configuration loading and validation."""

    DEFAULT_CONFIG = {
        "notion": {
            "databases": {
                "people": {
                    "name": "People & Contacts",
                    "mappings": {
                        "name": "Full Name",
                        "role": "Role",
                        "status": "Status",
                        "organization": "Organization",
                        "email": "Email",
                        "phone": "Phone",
                        "notes": "Notes",
                    },
                },
                "organizations": {
                    "name": "Organizations & Bodies",
                    "mappings": {
                        "name": "Organization Name",
                        "category": "Category",
                        "website": "Website",
                    },
                },
                "tasks": {
                    "name": "Actionable Tasks",
                    "mappings": {
                        "name": "Task Name",
                        "assignee": "Assignee",
                        "status": "Status",
                        "due_date": "Due Date",
                        "priority": "Priority",
                    },
                },
                "transcripts": {
                    "name": "Intelligence & Transcripts",
                    "mappings": {
                        "title": "Entry Title",
                        "date": "Date Recorded",
                        "source": "Source",
                        "content": "Raw Transcript/Note",
                        "summary": "AI Summary",
                        "entities": "Tagged Entities",
                        "status": "Processing Status",
                    },
                },
                "transgressions": {
                    "name": "Identified Transgressions",
                    "mappings": {
                        "summary": "Transgression Summary",
                        "perpetrator_person": "Perpetrator (Person)",
                        "perpetrator_org": "Perpetrator (Org)",
                        "date": "Date of Transgression",
                        "severity": "Severity",
                    },
                },
            }
        },
        "ai": {
            "extraction_prompt": """Analyze this transcript and extract:
1. People mentioned (names, roles, organizations)
2. Organizations mentioned
3. Tasks or action items
4. Any transgressions or issues identified
5. Key events or meetings
6. Important dates

For each entity, provide:
- Name
- Type (person/organization/task/transgression/event)
- Relevant properties
- Context from the transcript

Also provide:
- A brief summary (2-3 sentences)
- 3-5 key points

Format as JSON."""
        },
        "processing": {
            "batch_size": 10,
            "cache_ttl": 3600,
            "dry_run": False,
            "verbose": False,
            "enable_deduplication": True,
            "deduplication_threshold": 90.0,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize config manager.

        Args:
            config_path: Path to config file. If None, uses defaults + env vars
        """
        self.config_path = Path(config_path) if config_path else None
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from file and environment."""
        if self._config:
            return self._config

        # Start with defaults
        config_dict = self.DEFAULT_CONFIG.copy()

        # Load from file if provided
        if self.config_path and self.config_path.exists():
            with open(self.config_path, "r") as f:
                file_config = json.load(f)
                config_dict = self._deep_merge(config_dict, file_config)

        # Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)

        # Create and validate config model
        self._config = Config(**config_dict)
        return self._config

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        # Notion API key
        if not config.get("notion", {}).get("api_key"):
            api_key = os.getenv("NOTION_API_KEY")
            if api_key:
                config.setdefault("notion", {})["api_key"] = api_key

        # AI API key
        if not config.get("ai", {}).get("api_key"):
            # Try multiple AI providers
            ai_key = (
                os.getenv("ANTHROPIC_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or os.getenv("AI_API_KEY")
            )
            if ai_key:
                config.setdefault("ai", {})["api_key"] = ai_key

        # Database IDs from environment
        for db_name in ["people", "organizations", "tasks", "transcripts", "transgressions"]:
            env_key = f"NOTION_DB_{db_name.upper()}_ID"
            db_id = os.getenv(env_key)
            if db_id:
                config.setdefault("notion", {}).setdefault("databases", {}).setdefault(db_name, {})[
                    "id"
                ] = db_id

        # Processing options
        if os.getenv("BLACKCORE_DRY_RUN", "").lower() in ("true", "1", "yes"):
            config.setdefault("processing", {})["dry_run"] = True

        if os.getenv("BLACKCORE_VERBOSE", "").lower() in ("true", "1", "yes"):
            config.setdefault("processing", {})["verbose"] = True

        # Rate limiting
        rate_limit = os.getenv("NOTION_RATE_LIMIT")
        if rate_limit:
            config.setdefault("notion", {})["rate_limit"] = float(rate_limit)

        return config

    def save_template(self, path: str):
        """Save a configuration template file."""
        template = {
            "notion": {
                "api_key": "YOUR_NOTION_API_KEY",
                "databases": {
                    "people": {
                        "id": "YOUR_PEOPLE_DATABASE_ID",
                        "mappings": self.DEFAULT_CONFIG["notion"]["databases"]["people"][
                            "mappings"
                        ],
                    },
                    "organizations": {
                        "id": "YOUR_ORGANIZATIONS_DATABASE_ID",
                        "mappings": self.DEFAULT_CONFIG["notion"]["databases"]["organizations"][
                            "mappings"
                        ],
                    },
                    "tasks": {
                        "id": "YOUR_TASKS_DATABASE_ID",
                        "mappings": self.DEFAULT_CONFIG["notion"]["databases"]["tasks"]["mappings"],
                    },
                    "transcripts": {
                        "id": "YOUR_TRANSCRIPTS_DATABASE_ID",
                        "mappings": self.DEFAULT_CONFIG["notion"]["databases"]["transcripts"][
                            "mappings"
                        ],
                    },
                    "transgressions": {
                        "id": "YOUR_TRANSGRESSIONS_DATABASE_ID",
                        "mappings": self.DEFAULT_CONFIG["notion"]["databases"]["transgressions"][
                            "mappings"
                        ],
                    },
                },
                "rate_limit": 3.0,
                "retry_attempts": 3,
            },
            "ai": {
                "provider": "claude",
                "api_key": "YOUR_AI_API_KEY",
                "model": "claude-3-sonnet-20240229",
                "extraction_prompt": self.DEFAULT_CONFIG["ai"]["extraction_prompt"],
                "max_tokens": 4000,
                "temperature": 0.3,
            },
            "processing": self.DEFAULT_CONFIG["processing"],
        }

        with open(path, "w") as f:
            json.dump(template, f, indent=2)

        print(f"Configuration template saved to: {path}")
        print("Please update with your actual API keys and database IDs.")

    def validate(self) -> bool:
        """Validate the current configuration."""
        config = self.load()

        # Check required API keys
        if not config.notion.api_key:
            raise ValueError("Notion API key not configured")

        if not config.ai.api_key:
            raise ValueError("AI API key not configured")

        # Check database IDs
        for db_name, db_config in config.notion.databases.items():
            if not db_config.id:
                print(f"Warning: Database ID not configured for '{db_name}'")

        return True

    @property
    def config(self) -> Config:
        """Get the loaded configuration."""
        if not self._config:
            self._config = self.load()
        return self._config
