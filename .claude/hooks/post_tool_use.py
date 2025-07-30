#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import sys
import os
from pathlib import Path

# Import from utils.constants (if available)
try:
    from utils.constants import ensure_session_log_dir

    HAS_UTILS = True
except ImportError:
    HAS_UTILS = False


def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Extract session_id
        session_id = input_data.get("session_id", "unknown")

        # Ensure session log directory exists (prefer session-specific logging)
        if HAS_UTILS:
            try:
                log_dir = ensure_session_log_dir(session_id)
            except Exception:
                # Fallback if session logging fails
                log_dir = Path.cwd() / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Fallback if utils not available
            log_dir = Path.cwd() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / "post_tool_use.json"

        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, "r") as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        # Append new data
        log_data.append(input_data)

        # Write back to file with formatting
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)


if __name__ == "__main__":
    main()
