# GEMINI.md - Executive Summary: Project Blackcore

## 1. Project Purpose & Vision

**Project Blackcore** is the intelligence engine for "Project Nassau." Its mission is to transform raw, unstructured data from various sources into a structured, actionable knowledge graph within a Notion workspace. The system is designed to provide a significant strategic advantage by enabling superior intelligence analysis and operational synchronization.

The core philosophy is to:
- **Systemize Intelligence:** Convert field data (transcripts, notes, documents) into a relational database.
- **Automate Analysis:** Use AI (Claude, Gemini) to extract entities, summarize content, and uncover hidden connections.
- **Maintain Operational Rhythm:** Ensure strategic actions are driven by real-time, data-backed insights.

## 2. High-Level Architecture

Blackcore is a robust, security-focused Python application built on a modern, modular architecture.

- **Technology Stack:** Python 3.11+, `notion-client`, `pydantic` for data validation, `cryptography` for security, and `ruff` for code quality.
- **Security-First Design:** The system incorporates a dedicated security layer with encrypted secrets, SSRF protection, input sanitization, and comprehensive audit logging. This is a production-ready, enterprise-grade foundation.
- **Repository Pattern:** A clean data access layer abstracts Notion's API, providing type-safe, batch-capable CRUD operations for pages and databases.
- **Property Handlers:** A powerful, extensible system manages the bidirectional conversion for all 15+ Notion property types, ensuring data integrity.
- **AI Integration:** The architecture is designed to integrate with multiple AI providers (Anthropic, Google) for entity extraction and content generation.

## 3. Key Features & Successes

The project has rapidly achieved a solid foundation (Phase 0) and is moving into Phase 1.

- **Automated Database Schema:** The system can automatically provision a complex, 8-database schema in Notion, complete with inter-database relations. This is a major initial undertaking and is fully functional.
- **Comprehensive Test Coverage:** With over 112 tests and >94% code coverage, the codebase is reliable and well-tested.
- **Full Notion Type Support:** All standard and advanced Notion property types are handled, which is critical for data fidelity.
- **Robust Error Handling & Rate Limiting:** The system is resilient to transient API errors and respects Notion's rate limits, making it suitable for production workloads.
- **Live Configuration Fetching:** A recently added feature allows the system to fetch Notion database configurations directly, reducing manual setup and ensuring the system adapts to schema changes.

## 4. Recent Work & Current Focus (Last 7 Days)

Development has been extremely active. The focus has been on maturing the core application and preparing for data synchronization.

- **Feature Development:** The primary new feature is the **live Notion configuration fetching**, which makes the system more dynamic.
- **Code Quality & Refactoring:** Significant effort has been invested in applying consistent code formatting, fixing minor bugs, and improving security validation.
- **Documentation:** The `README.md` and `CLAUDE.md` files have been significantly enhanced to provide a comprehensive overview of the project, its architecture, and development practices.
- **Data Models:** The local JSON data models have been updated to reflect the latest content from Notion.

## 5. Problems, Blockers & Risks

- **Data Integrity and Synchronization:** The core challenge has shifted from schema creation to ensuring data integrity during synchronization. Several critical issues have been identified:
    - **Duplicate Entries:** The initial data sync has revealed the presence of duplicate entries that need to be systematically identified and filtered out to maintain a clean knowledge graph.
    - **Relational Accuracy:** Automating complex database relationships has proven difficult. The accuracy of these AI-generated links is not yet reliable enough for production.
    - **One-Way Sync Limitations:** The current sync process is one-way (local to Notion). Any manual corrections or additions made directly in Notion are at risk of being overwritten.

- **Scalability:** While the system is well-designed, it has not yet been tested with a large-scale data load. Performance under pressure is a potential unknown.
- **Dependency on Notion API:** The system is tightly coupled to the Notion API. Any changes or outages in the Notion platform could significantly impact the project.

## 6. Next Steps for the Product Manager

The foundational work is complete, but the data synchronization process requires a more hands-on, tactical approach to ensure accuracy.

- **Priority 1: Implement a Hybrid Data Remediation Strategy.**
    - **Manual Relationship Validation:** For the initial sync, database relationships should be established manually in a side-by-side process. This will ensure accuracy and help train future AI-driven automation.
    - **Develop Deduplication Logic:** Work with the engineering team to create and validate scripts that can identify and merge duplicate entries before they are synced.
    - **Enable Two-Way Sync:** The highest priority is to ensure that any manual entries or corrections made in Notion are synced back to the local Blackcore JSON files. This prevents data loss and makes Notion the source of truth.

- **Priority 2: Campaign Strategy based on Verified Data.** Once the data is cleaned, de-duplicated, and accurately related, the product manager can begin campaign strategy work with high confidence in the underlying data.

- **Priority 3: Define AI-Driven Enrichment (Post-Remediation).** With a clean and reliable dataset, the focus can shift back to leveraging AI for enrichment tasks like summaries and insight generation.

**In summary, the project is now in a critical data remediation phase. The focus has shifted from pure automation to a hybrid human-in-the-loop model to guarantee the quality and accuracy of the knowledge graph. Success now depends on meticulously cleaning and validating before manually confirming all entries with The Captain.**