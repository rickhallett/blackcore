# GEMINIv2.md - Executive Summary: Project Blackcore

## 1. Project Purpose & Vision

**Project Blackcore** is the intelligence engine for "Project Nassau," designed to transform raw data into a structured, actionable knowledge graph within Notion. The vision is to achieve strategic advantage through superior intelligence and flawless operational execution, systemizing intelligence, automating analysis via AI, and creating connections between key data points.

## 2. Architecture & Strategy

Blackcore employs a dual-architecture strategy to balance enterprise-grade robustness with rapid, streamlined execution:

1.  **The Core Engine (`blackcore/`)**: This is the primary, security-first application. It features a comprehensive architecture with a dedicated security layer, a repository pattern for data access, and an extensible set of handlers for all Notion property types. It is designed for scalability, reliability, and complex, automated workflows.

2.  **The Minimal Processor (`blackcore/minimal/`)**: A self-contained, lightweight module focused on a core workflow: processing transcripts, extracting entities with AI, and syncing data to Notion. It provides a simplified, CLI-driven approach for quick, targeted tasks and serves as a testbed for new features. This includes a `sync-json` command for direct data synchronization without AI processing.

This dual approach allows for both long-term, robust development and immediate, practical application of the core technology.

## 3. Key Features & Successes

- **Phase 0 Complete**: The foundational enterprise-grade infrastructure is complete, including the security layer, error handling, repository pattern, and handlers for all Notion property types.
- **High Test Coverage**: Both the core engine (>94%) and the minimal processor (>90%) are extensively tested, ensuring reliability.
- **Streamlined MVP**: The `minimal` processor provides a fully functional, end-to-end workflow for transcript processing, demonstrating immediate value.
- **Live Configuration**: The system can fetch Notion database configurations directly, making it more adaptive to schema changes.

## 4. Recent Work & Current Focus

The team's recent focus has been on **solving critical data synchronization challenges**.

- **Problem:** A significant blocker was identified where the Notion API rejected records with an "Invalid property value" error.
- **Root Cause:** The investigation, detailed in `specs/notion-sync-property-formatting-fix.md`, revealed that the data transformation pipeline was not correctly formatting properties for the Notion API.
- **Solution:** A clear, phased plan was created to inject a `_prepare_properties` step into the sync workflow. This involves creating a debugging script, modifying the sync pipeline, and performing gradual, validated rollouts.
- **Git Activity:** Recent commits reflect this focus, with work on data models, sync scripts, and configuration fetching. The history shows a methodical approach to building out features, testing, and addressing issues as they arise.

## 5. Problems, Blockers & Risks

- **Data Synchronization Integrity**: This remains the primary challenge. The recent property formatting bug highlights the complexity of the data transformation pipeline. Key ongoing issues include:
    - **Deduplication**: A strategy is needed to filter out duplicate entries before they are synced.
    - **Relational Accuracy**: AI-generated relationships are not yet reliable enough, requiring a manual or hybrid validation approach.
    - **Two-Way Sync**: The current one-way sync (local -> Notion) risks data loss if manual changes are made in Notion. A bidirectional sync is a critical future requirement.

- **Architectural Divergence**: The dual-architecture approach is a strength, but it carries a risk of the `core` and `minimal` systems diverging over time. This will require deliberate management to ensure features and fixes are shared where appropriate.

## 6. Next Steps for the Product Manager

The project is at a tactical inflection point, moving from foundational work to ensuring data quality and integrity.

- **Priority 1: Validate the Sync Fix & Complete Initial Data Load.** The immediate focus is on confirming that the property formatting fix is successful. The PM should oversee the validation plan outlined in the spec, starting with a single record and scaling up to the full test batch of 93 records.

- **Priority 2: Establish a Data Remediation Workflow.** The initial sync will likely surface data quality issues. The PM must lead the effort to:
    - **Use the `minimal` processor's `sync-json` command** for initial, controlled data loads.
    - **Implement a manual, side-by-side process** for validating and correcting database relationships.
    - **Develop a deduplication strategy** with the engineering team.

- **Priority 3: Plan for Two-Way Sync.** The limitations of one-way sync are clear. The PM should prioritize the specification and development of a bidirectional synchronization feature to make Notion the true source of truth.

**In summary, Blackcore is a powerful, well-architected system that is now facing the real-world challenges of data integration. The immediate path to success lies in a pragmatic, hands-on approach to data quality, validating the recent bug fix, and then systematically cleaning and relating the data within Notion.**
