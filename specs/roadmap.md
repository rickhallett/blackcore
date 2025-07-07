# **Development Roadmap & Plan: The Blackcore Engine**

## **1. Core Principles & Philosophy**

This roadmap is built on a foundation of careful, disciplined development practices. Every phase and feature will adhere to the following principles:

*   **Test-Driven Development (TDD):** For every new feature, we will write the tests first. The feature is not considered "complete" until all tests pass. This ensures reliability and prevents regressions.
*   **Incremental & Iterative:** We will build from the simplest possible function upwards. Each new feature will be a small, self-contained, and fully tested addition to the existing codebase. We will deliberately follow a slow, steady complexity curve.
*   **Human-in-the-Middle (HITM) Verification:** Every phase will conclude with a clear checkpoint where a human (the Technician) can manually run a script and verify the output in the terminal or in Notion. This prevents the system from becoming a "black box."
*   **Proper Git Workflow:** All development will be done on dedicated `feature/` branches. Code will only be merged into the `main` branch via a Pull Request (PR), ensuring code review and a clean, stable main branch.
*   **API First, but Abstracted:** The primary interface will be the Notion API, but all interactions will be wrapped in our own Python functions and classes. This allows us to easily substitute underlying services (e.g., swapping Claude for Gemini for a specific task) without rewriting the core application logic.

#### **2. Technology & Environment Setup**

*   **Language:** Python
*   **Package Manager:** `uv` will be used for all dependency management (`uv pip install`, `uv pip freeze`).
*   **Environment:** A standard `.venv` will be created and managed by `uv`.
*   **Core Dependencies:** `notion-client`, `pydantic`, `python-dotenv`.
*   **AI SDKs:** `anthropic` (default), `google-generativeai`.
*   **Dev Dependencies:** `pytest`, `pytest-asyncio`, `ruff`.
*   **Security:** All API keys will be stored in a `.env` file, which will be added to `.gitignore` to prevent secrets from ever entering version control.

---

### **Phase 0: Foundation & Schema Automation**

**Goal:** To establish the project's bedrock by validating the core API connection and programmatically creating the entire database structure within Notion.

**Complexity:** Low

| Epic | Goal | User Story | Key Steps (TDD) | Human-in-the-Middle Checkpoint | Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0.1** Repository & Env Setup | Initialize the project with best practices. | As the technician, I want a clean, secure, and reproducible development environment. | 1. Initialize Git repo.<br>2. Create `.gitignore` (add `.venv`, `.env`, `__pycache__`).<br>3. Set up `requirements.txt` and `requirements-dev.txt` with `uv`. | Clone the repo, run `uv pip install -r requirements-dev.txt`. It should complete without error. | Low |
| **0.2** Programmatic DB Creation | Automate the creation of all 8 Notion databases via the API. | As the technician, I want to run a single script that builds the entire, empty database schema in Notion, saving hours of manual setup. | 1. **Test:** Write a test that asserts a specific database (e.g., `People & Contacts`) does *not* exist.<br>2. **Implement:** Write the `create_people_db()` function.<br>3. **Test:** Write a test that runs the function and then asserts the database *does* exist with the correct fields (`Name`, `Role`, etc.).<br>4. Repeat for all 8 databases. | Run `python scripts/setup_databases.py`. Go to the Notion workspace and visually confirm that all 8 empty databases have been created with the correct columns. | Low |

---

### **Phase 1: Read-Only Operations & Terminal Verification**

**Goal:** To build the "read" part of the engine. This phase is about safely fetching, querying, and displaying our data without making any changes. All outputs will be to the terminal.

**Complexity:** Low to Medium

| Epic | Goal | User Story | Key Steps (TDD) | Human-in-the-Middle Checkpoint | Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.1** Basic Object Fetcher | Create functions to retrieve all items from a single database. | As the technician, I want to fetch all entries from the `People & Contacts` database and display them in my terminal. | 1. **Test:** Write a test for a `get_all_people()` function that asserts the return value is a list of `Person` Pydantic models.<br>2. **Implement:** Write the function to query the Notion API and parse the results into the Pydantic models.<br>3. **Test:** Ensure tests pass. | Run `python main.py --get-people`. The terminal should print a clean, readable list of all people in the Notion database. | Low |
| **1.2** Advanced Query Engine | Develop functions to filter databases based on specific properties. | As the technician, I want to fetch only the tasks where `Status` is 'In Progress' and `Priority` is 'High'. | 1. **Test:** Write a test for `get_tasks(status="In Progress", priority="High")`.<br>2. **Implement:** Build the Notion API query filter logic within the function.<br>3. **Test:** Ensure tests pass. | Run `python main.py --get-tasks --status "In Progress"`. The terminal should only show the tasks that match the filter. | Medium |
| **1.3** Relational Data Display | Enhance fetchers to pull and display data from linked databases. | As the technician, when I fetch a `Task`, I also want to see the `Full Name` of the person it's assigned to from the `People` database. | 1. **Test:** Modify the `get_tasks` test to assert that the returned `Task` object has a nested `Person` object, not just a person ID.<br>2. **Implement:** This is a key step. You'll need to handle Notion's relational data structure, possibly by making a second API call to "enrich" the data.<br>3. **Test:** Ensure tests pass. | Run `python main.py --get-tasks`. The terminal output should now be a nested structure, clearly showing the task and its assignee's details. | Medium |

---

### **Phase 2: Write Operations & First AI Integration**

**Goal:** To introduce "write" capabilities and our first interaction with an LLM. This phase is where the system starts to become truly powerful.

**Complexity:** Medium

| Epic | Goal | User Story | Key Steps (TDD) | Human-in-the-Middle Checkpoint | Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2.1** Simple Object Creation | Create a function to add a new page (entry) to a database. | As the technician, I want to programmatically create a new task in Notion based on data from a script. | 1. **Test:** Write a test that calls `create_new_task()` and then uses the fetcher from Phase 1 to verify the new task exists in the database.<br>2. **Implement:** Write the function to format the data correctly and call the `pages.create` Notion API endpoint. | Run a script like `python scripts/add_task.py --name "Finalize Leaflet"`. Go to Notion and see the new task appear instantly. | Medium |
| **2.2** Relational Linking Engine | Create a function to link two existing objects together. | As the technician, I want to programmatically assign an existing task to an existing person. | 1. **Test:** Write a test for a function `link_task_to_person(task_id, person_id)`.<br>2. **Implement:** Write the API call to update the `Relation` property of the task page.<br>3. **Test:** Verify the link is correctly established. | Run a script with the relevant IDs. Go to Notion and see the `Person` bubble appear in the `Assignee` field of the `Task`. | Medium |
| **2.3** AI Summarization Module | Integrate with Claude to perform a simple summarization task. | As the technician, I want to take the text from a long voice memo transcript and get a concise AI-generated summary. | 1. **Test:** Write a test for a `summarize_text(text)` function that asserts it returns a non-empty string.<br>2. **Implement:** Create a simple wrapper for the Claude API (or Gemini).<br>3. **Test:** Ensure tests pass. | Create a script that takes a Notion page ID for a transcript, fetches its content, summarizes it via the AI, and prints both the original and summary to the terminal. | Medium |

---

### **Phase 3: The Full Workflow & Agentic Research**

**Goal:** To connect all the pieces into the full, automated "Ouroboros" loop and build our first agentic research capability.

**Complexity:** High

| Epic | Goal | User Story | Key Steps (TDD) | Human-in-the-Middle Checkpoint | Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **3.1** End-to-End Transcript Processor | Automate the entire workflow from raw transcript to structured intelligence. | As the technician, I want a single script that finds unprocessed transcripts, extracts entities, links them, gets a summary, and updates the status. | 1. **Test:** This is an integration test. It will involve mocking Notion API responses to simulate the entire chain of events.<br>2. **Implement:** This is the core script. It will call functions from all previous phases: fetch new transcripts, parse them for entities, create/link those entities, call the AI for a summary, and finally, update the original Notion page with the summary and a "Processed" status.<br>3. **Test:** Ensure the complex integration test passes. | **The "Magic Moment":** Manually paste a new, raw transcript into the `Intelligence & Transcripts` database. Run `python scripts/process_new_intelligence.py`. Watch as all the other databases (`People`, `Tasks`, etc.) are automatically populated and linked, and the original entry is updated with a summary. | High |
| **3.2** The Agentic Research Module | Build a function that uses an LLM to perform a multi-step research task. | As the technician, I want to ask a high-level question like "Find all evidence of procedural failures by Dorset Coast Forum" and get a structured report. | 1. **Test:** This will be a high-level test that checks if the output is a structured markdown report.<br>2. **Implement:** This is an advanced function. It will need to: query Notion for all documents linked to "Dorset Coast Forum," send each document to the LLM for analysis against a "procedural failure" rubric, synthesize the findings from all documents, and format the result into a clean report.<br>3. **Test:** This will likely involve significant prompt engineering and iteration. | Run `python scripts/run_research.py --topic "DCF_Failures"`. The script should output a detailed markdown report to the terminal, complete with citations linking back to the source document pages in Notion. | High |