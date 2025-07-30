# Notion Database Synchronization Workflow

This document outlines the process for discovering, configuring, and synchronizing your local JSON data with your Notion databases.

## Architecture Overview

The synchronization process is designed to be efficient and scalable. It uses a two-script system to avoid hardcoding database IDs and to minimize API calls.

1.  **`scripts/discover_and_configure.py`**: A utility script that connects to your Notion workspace, finds all accessible databases, and generates a configuration file.
2.  **`blackcore/config/notion_config.json`**: A central configuration file that stores the mapping between your Notion databases and your local project files. **This file requires manual review after generation.**
3.  **`scripts/notion_sync.py`**: The main script that performs the synchronization. It reads its configuration, fetches the current state of a Notion database into a local cache, and then compares your local JSON against that cache to determine what to create or update.
4.  **`blackcore/labs/`**: This directory contains previous and experimental versions of the scripts for reference and testing.

---

## Step 1: Initial Setup

Before running any scripts, ensure you have:

1.  A `.env` file in the project root containing your Notion API key:
    ```
    NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    ```
2.  Shared your specific Notion databases with your integration. In Notion, go to the database page, click the `...` menu, and select `+ Add connections` to find and add your integration.

---

## Step 2: Discover and Configure Databases

This step populates the `blackcore/config/notion_config.json` file. You only need to run this when you add new databases to your Notion workspace or grant the integration access to more of them.

1.  **Run the discovery script from your terminal:**
    ```bash
    python3 -m scripts.discover_and_configure
    ```

2.  **Manually Edit `blackcore/config/notion_config.json`:** The script will create the config file in the `blackcore/config` directory. You **must** open this file and verify the settings for each database. Pay close attention to:
    *   `local_json_path`: Make sure this points to the correct source JSON file for this database.
    *   `json_data_key`: Ensure this matches the top-level key inside your JSON file that contains the list of records.
    *   `title_property`: This is now discovered automatically, but it's good practice to verify it's correct.
    *   `list_properties`: **(Manual Step)** You must populate this array with the names of any properties that should be treated as lists (like multi-selects or relations where you want to append new values rather than overwrite). For example: `["Actionable Tasks", "Key Documents"]`.

---

## Step 3: Run the Synchronization

This is the script you will run regularly to keep your data in sync. It operates on one database at a time.

1.  **Execute the sync script from your terminal**, specifying the name of the database you wish to sync (the name must match a key in your config file).

    ```bash
    # Example for the "Agendas & Epics" database
    python3 -m scripts.notion_sync "Agendas & Epics"
    ```

2.  The script will perform a **safe dry run**:
    *   It will connect to Notion and fetch the latest version of the specified database.
    *   It will save this data to a cache file (e.g., `agendas_epics_cache.json`) inside `blackcore/models/notion_cache/`.
    *   It will then show you a plan of what it *would* create or update. No actual changes are made to your Notion database. 