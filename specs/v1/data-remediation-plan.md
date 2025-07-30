# Data Remediation and Deduplication Plan

## 1. Introduction

This document outlines a systematic plan to cleanse, deduplicate, merge, and standardize the data within the project's JSON models. The goal is to establish a single, consistent source of truth for each database object and ensure full relational integrity across the dataset, as defined in `blackcore/config/notion_config.json`.

The plan is based on a file-by-file analysis and will be executed before any modifications are made to the live data.

**Note on File Mismatches:** The analysis assumes that `places_events.json` in the file system corresponds to the `"Key Places & Events"` database defined in the configuration.

## 2. Analysis & Proposed Changes by File

### 2.1. `people_contacts.json` ("People & Contacts")

*   **Analysis:** The file is currently empty, containing `{"People & Contacts": []}`.
*   **Proposed Changes:**
    *   **Populate Data:** This file needs to be populated with entries for all individuals mentioned in the `Tagged Entities` of `intelligence_transcripts.json` and other relational fields. This will be detailed in the Relational Integrity section.

### 2.2. `places_events.json` ("Key Places & Events")

*   **Analysis:** This file contains entries that belong to the "Organizations & Bodies" database. The actual event/place entries are unique and require no changes.
*   **Proposed Changes:**
    *   **Move Mismatched Data:** The following five organization objects will be removed from this file. They will be merged into `organizations_bodies.json`.
        1.  `{ "Organization Name": "Dorset Coast Forum (DCF)", ... }`
        2.  `{ "Organization Name": "Swanage Town Council (STC)", ... }`
        3.  `{ "Organization Name": "Dorset Highways", ... }`
        4.  `{ "Organization Name": "Engagement HQ / Granicus", ... }`
        5.  `{ "Organization Name": "North Swanage Traffic Concern Group (NSTCG)", ... }`

### 2.3. `organizations_bodies.json` ("Organizations & Bodies")

*   **Analysis:** The file has an incorrect root structure, contains duplicate entries, and needs to be merged with the data identified in `places_events.json`.
*   **Proposed Changes:**
    *   **Correct JSON Structure:** The root of the file will be changed from a list `[...]` to a dictionary `{"Organizations & Bodies": [...]}` to match the configuration.
    *   **Deduplicate Entries:** The following five duplicate entries will be removed (keeping the first instance):
        1.  `"UK Statistics Authority (UKSA)"`
        2.  `"Office of Statistical Regulation (OSR)"`
        3.  `"Local Government Ombudsman"`
        4.  `"Dorset Council - Scrutiny Committee"`
        5.  `"Dorset Council - Governance and Audit Committee"`
    *   **Merge Entries:** The data for `"North Swanage Traffic Concern Group (NSTCG)"` from `places_events.json` will be merged with the existing entry to create a single, complete record containing both `Website` and `Notes` properties.

### 2.4. `identified_transgressions.json` ("Identified Transgressions")

*   **Analysis:** The file has a malformed, nested list structure and contains several duplicate entries.
*   **Proposed Changes:**
    *   **Correct JSON Structure:** The data will be flattened from a list-of-lists `[[...]]` to a single list of objects `[...]`.
    *   **Deduplicate Entries:** The following duplicate entries will be removed:
        1.  `"Unilateral change of survey review timeline"`
        2.  `"Implementation of a 'Tier 4' Captcha leading to poisoned data"`
        3.  `"David Hollister public information 'indiscretion'"`
    *   **Merge Entries:** The two entries for `"Paper survey chain of custody breach"` will be merged into one, preserving the version with the specific date (`2024-06-06`).

### 2.5. `documents_evidence.json` ("Documents & Evidence")

*   **Analysis:** The JSON objects have an inconsistent and overly complex structure, likely from a raw API dump.
*   **Proposed Changes:**
    *   **Standardize Structure:** All entries will be converted to a simple key-value format. For example, `{"Document Name": {"title": [{"text": {"content": "Doc Name"}}]}}` will become `{"Document Name": "Doc Name"}`. This will be applied to all properties (`Document Name`, `Document Type`, `AI Analysis`, etc.).
    *   **Correct Key:** The top-level key will be corrected from `"Documents and Evidence"` to `"Documents & Evidence"`.

### 2.6. `agendas_epics.json` ("Agendas & Epics")

*   **Analysis:** The file contains multiple entries for the same strategic phases, which should be consolidated. The top-level key is also incorrect.
*   **Proposed Changes:**
    *   **Correct Key:** The top-level key will be renamed from `"Agendas and Epics"` to `"Agendas & Epics"`.
    *   **Merge Agendas:**
        *   Merge the two "Phase 1" agendas into a single, comprehensive `"Phase 1: Mobilization & Evidence Gathering"`.
        *   Merge the two "Phase 2" agendas into a single `"Phase 2: Pressure & Credibility Attack"`.
        *   Merge the two "Phase 3" agendas into a single `"Phase 3: Endgame & Accountability"`.
        *   The merge will involve combining `Actionable Tasks`, `Key Documents`, and synthesizing new `Objective Summary` fields.
    *   **Review Overarching Epic:** The `"Shore Road Closure Opposition Campaign"` will be flagged for review to rationalize its content against the newly merged phase-based agendas.

### 2.7. `actionable_tasks.json` ("Actionable Tasks")

*   **Analysis:** The tasks themselves are unique, but their relational links to agendas are broken due to the inconsistencies in `agendas_epics.json`.
*   **Proposed Changes:**
    *   **Update Relational Links:** After the agendas are merged and renamed in `agendas_epics.json`, the `Related Agenda` values in this file will be updated to point to the correct, new agenda titles. For example, tasks related to `"Phase 2: Pressure Campaign"` will be updated to link to `"Phase 2: Pressure & Credibility Attack"`.

### 2.8. `intelligence_transcripts.json` ("Intelligence & Transcripts")

*   **Analysis:** The entries are unique, but the `Tagged Entities` field highlights significant gaps in the relational data.
*   **Proposed Changes:**
    *   No direct file changes are proposed. The resolution of its relational data is covered in the next section.

## 3. Relational Integrity Master Plan

After the individual file clean-up is complete, a final pass is required to ensure the entire dataset is relationally consistent.

1.  **Populate `people_contacts.json`:**
    *   Create a new entry in `people_contacts.json` for every unique person name found in the `Tagged Entities` of `intelligence_transcripts.json` and any other relational fields (e.g., `People Involved` in `places_events.json`).
    *   This includes, but is not limited to: `Phillippe Eed`, `Gary Suttle`, `David Hollister`, `Angelo Wiggins`, `Mel`, `Colvin Milmer`, `Karen Leyland`, `Colin Bright`, `Tony Powell`, `Sarah Streams`, `Pete Mitchell`, `Blake Compton`, `Barry Cade`, `Graham Heather`, `Reuben`, and `Chris Toms`.

2.  **Validate All Relations:**
    *   A script will be run to check every relational property in every file (e.g., `People Involved`, `Related Transgressions`, `Perpetrator (Org)`, `Tagged Entities`).
    *   It will verify that the value in the relation (e.g., the name "David Hollister") exists as a primary entry (defined by `title_property`) in the correct target database (e.g., `people_contacts.json`).
    *   Any remaining broken links after the population step will be flagged for manual review.

3.  **Address Un-linkable Concepts:**
    *   Entities tagged in `intelligence_transcripts.json` that do not fit existing schemas, such as `"Survey Manipulation"` or `"Gemini AI"`, will be compiled.
    *   **Proposal:** Create a new database and corresponding JSON file named `concepts.json` with a `title_property` of "Concept Name" to house these abstract entities, allowing them to be properly linked across the knowledge graph.

This plan ensures a thorough and systematic approach to resolving the data inconsistencies, resulting in a clean, reliable, and fully interconnected dataset. 