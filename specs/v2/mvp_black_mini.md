                                                                                                      q# MVP Product Requirements Document: Blackcore Simple Syncer

## 1. Introduction & Vision

**Product:** Blackcore Simple Syncer
**Vision:** To provide a simple, reliable, and fast command-line tool for users to process unstructured text data (like meeting transcripts), extract key entities, identify obvious duplicates, and sync this structured information into a Notion workspace. This MVP will form the foundation of the larger Blackcore intelligence engine by solving the most immediate user problem with minimal complexity.

### Reasoning

The full repository contains a highly sophisticated, multi-layered system for data processing and deduplication. While powerful, it is too complex for an initial release. This MVP focuses on delivering the core value proposition—turning messy text into structured, de-duplicated Notion data—in the simplest way possible.

## 2. Problem Statement

Intelligence analysts and data managers spend significant time manually parsing unstructured notes and transcripts, identifying key pieces of information (like people and organizations), and entering them into a structured system like Notion. This process is slow, error-prone, and leads to inconsistent and duplicated data entries. Without an automated solution, valuable connections are missed and data integrity suffers, hindering effective analysis.

### Reasoning

The core problem isn't the lack of a perfect, AI-driven graph database; it's the tedious, manual bridge between raw text and a structured database. This MVP directly attacks that primary pain point.

## 3. User Persona

**Name:** Alex, The Intelligence Analyst

**Role:** Responsible for gathering, processing, and analyzing intelligence for "Project Nassau."

**Needs & Goals:**
*   Quickly process daily transcripts and notes without manual data entry.
*   Ensure that when "Tony Smith" is mentioned, it links to the existing "Anthony Smith" record.
*   Have a single, reliable source of truth for every person and organization in Notion.
*   Spend more time analyzing connections and less time on data cleanup.

### Reasoning

Defining a clear user helps to prioritize features. Alex doesn't need a complex interactive GUI or graph visualization for the MVP; they need a fast, scriptable tool that fits into their existing workflow and solves the duplication problem at the point of entry.

## 4. MVP Features

This MVP will be built upon the existing `blackcore/minimal` module, which provides a solid foundation for the required workflow.

### Feature 1: Transcript Ingestion and Processing

*   **Description:** The tool will accept a single text or JSON file as input. It will read the content and prepare it for AI analysis.
*   **User Story:** As Alex, I want to point the tool at a meeting transcript file so that it can be automatically processed.
*   **Acceptance Criteria:**
    *   The CLI accepts a single file path as an argument.
    *   Supports both `.txt` and `.json` file formats.
    *   Successfully reads the content into memory.
    *   Gracefully handles file-not-found and read permission errors.

### Reasoning

This is the entry point of the entire workflow. Keeping it simple (one file at a time) is key for an MVP. The `blackcore/minimal/transcript_processor.py` file already provides a strong basis for this feature.

### Feature 2: AI-Powered Entity Extraction

*   **Description:** The tool will send the transcript content to an AI model (e.g., Claude) to extract key entities such as People, Organizations, and Tasks.
*   **User Story:** As Alex, I want the system to automatically identify all people and organizations mentioned in a transcript so I don't have to do it manually.
*   **Acceptance Criteria:**
    *   Integrates with an AI provider (configurable via environment variables).
    *   Parses the AI's response to identify a list of entities.
    *   Maps extracted information to the predefined data models (`Person`, `Organization`, etc.).

### Reasoning

This feature provides the core "intelligence" of the system and is the primary value driver. `blackcore/minimal/ai_extractor.py` is the perfect component for this.

### Feature 3: Simple Pre-Sync Deduplication

*   **Description:** Before creating a new entity in Notion, the tool will perform a simple, rule-based check to see if a similar entity already exists. If a high-confidence match is found, it will update the existing record instead of creating a new one.
*   **User Story:** As Alex, when a transcript mentions "Tony Smith," I want the tool to find the existing "Anthony Smith" record and update it, rather than creating a duplicate.
*   **Acceptance Criteria:**
    *   For each extracted entity, the tool queries Notion for potential duplicates based on name and other key identifiers (e.g., email).
    *   It uses a simple, non-AI scoring model to determine if a match is high-confidence (e.g., >90% similarity).
    *   If a match is found, the new information is merged with the existing Notion data.
    *   If no match is found, a new record is created.

### Reasoning

This is the MVP solution to the deduplication problem. It avoids the complexity of the full `blackcore/deduplication` engine by performing a simple, synchronous check *before* writing to Notion. This is a crucial feature that delivers significant value without over-engineering.

### Feature 4: Notion Database Synchronization

*   **Description:** The tool will create or update pages in the relevant Notion databases based on the extracted and de-duplicated entities.
*   **User Story:** As Alex, I want all the extracted information to be automatically and correctly saved to my Notion databases.
*   **Acceptance Criteria:**
    *   Successfully creates new pages in Notion for new entities.
    *   Successfully updates existing pages for matched entities.
    *   Handles all necessary Notion property types (text, select, relation, etc.).
    *   Respects Notion's API rate limits.

### Reasoning

This is the final, essential step that delivers the structured data to the user's target system. The `blackcore/minimal/notion_updater.py` and `property_handlers.py` provide the necessary foundation.

### Feature 5: Simple Command-Line Interface (CLI)

*   **Description:** A straightforward command-line interface to run the entire process.
*   **User Story:** As Alex, I want to run the tool from my terminal with a single command.
*   **Acceptance Criteria:**
    *   A primary command `sync-transcript <file_path>` initiates the process.
    *   Provides clear, concise output on progress (e.g., "Extracting entities...", "Found 2 duplicates...", "Syncing to Notion...").
    *   Outputs a final summary of actions taken (e.g., "Created: 5 pages, Updated: 2 pages").
    *   Includes a `--dry-run` flag to preview changes without writing to Notion.

### Reasoning

A simple, scriptable CLI is the fastest way to provide a usable interface for the MVP. The complex, interactive UI in the full repository (`blackcore/deduplication/cli/`) is out of scope. The `blackcore/minimal/cli.py` is a suitable starting point.

## 5. Out of Scope for MVP

To ensure focus and rapid delivery, the following features are explicitly excluded from the MVP.

*   **Advanced Interactive CLI:** The `rich`-based, multi-screen interactive CLI is too complex.
*   **Sophisticated Deduplication Engine:** The multi-layer pipeline (Fuzzy -> LLM -> Graph) will not be used. The MVP will use a simple, pre-sync check.
*   **Graph Analysis:** No graph-based relationship analysis will be performed.
*   **Real-time Synchronization/Monitoring:** The tool will be run manually; no background services.
*   **Advanced Security & Enterprise Features:** The MVP will rely on API keys in environment variables and will not include advanced features like a full service layer, secrets management, or multi-user support.
*   **Web UI/API:** No web-based components will be built.

### Reasoning

Excluding these features directly addresses the prompt's constraints: "do not over engineer, optimise prematurely, or use unnecessarily complex code." These features add significant development overhead without being essential to solving the core user problem initially.

## 6. Technical Implementation Plan

*   **Foundation:** The MVP will be built by refining and extending the `blackcore/minimal/` module.
*   **Core Logic:**
    *   `transcript_processor.py`: Will be the central orchestrator. New deduplication logic will be added here.
    *   `ai_extractor.py`: Will be used as-is for entity extraction.
    *   `notion_updater.py`: Will handle the final write operations to Notion.
*   **Deduplication Logic:**
    *   Inside `TranscriptProcessor.process_transcript`, before creating entities, a new private method `_find_existing_entity(entity)` will be implemented.
    *   This method will use `notion_updater.find_page` to search for matches based on the entity's name and key properties.
    *   A simple scoring function from `blackcore.deduplication.similarity_scoring` can be borrowed to calculate a confidence score.
*   **Dependencies:** The MVP will use the existing dependencies defined in `blackcore/minimal/`: `notion-client`, `pydantic`, `anthropic`/`openai`.

### Reasoning

Basing the MVP on the `minimal` module is the most efficient path forward. It already contains the core pipeline and avoids the complexity of the full `blackcore` engine, aligning perfectly with MVP principles.

## 7. Success Metrics

*   **Functionality:** The tool can successfully process a 1,000-word transcript, identify at least 80% of obvious entities, correctly match at least 90% of clear duplicates, and sync the results to Notion with zero errors.
*   **Performance:** The end-to-end process for a 1,000-word transcript completes in under 45 seconds.
*   **Usability:** A user can successfully set up and run the tool in under 15 minutes using the README documentation.
*   **Adoption:** The tool is used at least once per day by the target user.

### Reasoning

These metrics are specific, measurable, and directly tied to the core value proposition of the MVP: providing a functional, fast, and easy-to-use tool that solves the user's primary problem.