# **Notion Database Architecture for Project Nassau**

This architecture is designed around a core principle: every piece of information is an object, and every object can be related to another. This creates a powerful, queryable knowledge graph instead of a simple collection of documents.

#### **Database 1: `People & Contacts`**
*   **Purpose:** The central CRM for every individual involved in the campaign, from our team to our targets.
*   **View:** Icon view with profile photos, or a table grouped by Role.

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Full Name** | `Title` | The primary identifier for the person (e.g., "The Mayor of Swanage"). |
| **Role** | `Select` | Their function in this project. Options: `Target`, `Ally`, `Oversight`, `Internal Team`, `Operational Persona`. |
| **Status** | `Select` | Our current level of interaction. Options: `Not Contacted`, `Initial Contact Made`, `Active Engagement`, `Monitoring`. |
| **Organization** | `Relation` | Links to an entry in the `Organizations & Bodies` database. |
| **Email** | `Email` | Their primary email address. |
| **Phone** | `Phone` | Their primary phone number. |
| **Linked Transgressions** | `Relation` | Links to every specific transgression this person has committed from the `Identified Transgressions` database. |
| **Last Contacted** | `Date` | The date of our last interaction, for tracking engagement. |
| **Notes** | `Text` | General notes, observations, or background information. |

---
#### **Database 2: `Organizations & Bodies`**
*   **Purpose:** To track all institutional players.
*   **View:** A gallery view with logos, or a board view Kanban-style by Category.

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Organization Name** | `Title` | The full name of the organization (e.g., "Swanage Town Council"). |
| **Category** | `Select` | Their strategic role. Options: `Antagonist`, `Lever of Power` (e.g., County Council), `Weapon` (e.g., Ombudsman). |
| **Key People** | `Relation` | Links to all individuals in the `People & Contacts` database associated with this organization. |
| **Linked Documents** | `Relation` | Links to all documents in the `Documents & Evidence` database produced by or related to this organization. |
| **Website** | `URL` | The official website for quick reference. |

---
#### **Database 3: `Agendas & Epics`**
*   **Purpose:** To define and track our high-level strategic goals. This is the "master plan."
*   **View:** A board view (Kanban) with columns for Status (`Planning`, `Active`, `Completed`).

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Agenda Title** | `Title` | The name of the strategic objective (e.g., "Challenge the Survey's Integrity"). |
| **Status** | `Select` | The current state of this agenda. Options: `Planning`, `Active`, `Completed`, `Blocked`. |
| **Owner** | `Person` | Links to the internal team member responsible (`The Captain` or `The Architect`). |
| **Phase** | `Select` | Ties the agenda to the campaign timeline. Options: `Phase 1: Mobilization`, `Phase 2: Pressure`, `Phase 3: Endgame`. |
| **Actionable Tasks** | `Relation` | A roll-up showing all specific tasks from the `Actionable Tasks` database needed to complete this agenda. |
| **Key Documents** | `Relation` | Links to the most important documents related to this objective. |
| **Objective Summary** | `Text` | A brief, one-sentence summary of what "winning" looks like for this agenda. |

---
#### **Database 4: `Actionable Tasks`**
*   **Purpose:** The granular, day-to-day to-do list for the project.
*   **View:** A calendar view by Due Date, or a table grouped by Assignee.

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Task Name** | `Title` | The specific to-do item (e.g., "Draft email to Mayor forcing abstention"). |
| **Assignee** | `Person` | The internal team member responsible for this task. |
| **Status** | `Select` | The progress of the task. Options: `To-Do`, `In Progress`, `Done`. |
| **Due Date** | `Date` | The target completion date. |
| **Priority** | `Select` | The urgency of the task. Options: `High`, `Medium`, `Low`. |
| **Related Agenda** | `Relation` | **Crucial Field:** Links the task back to its parent goal in the `Agendas & Epics` database. |
| **Blocked By** | `Relation` | Links to another task that must be completed first (for dependencies). |

---
#### **Database 5: `Intelligence & Transcripts`**
*   **Purpose:** The central repository for all raw, unstructured input from the Strategist.
*   **View:** A simple table view, sorted by Date Recorded (Newest First).

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Entry Title** | `Title` | A descriptive title, e.g., "2025-06-15 - Voice Memo on Mayor's Weaknesses". |
| **Date Recorded** | `Date` | The date the intelligence was captured. |
| **Source** | `Select` | The origin of the data. Options: `Voice Memo`, `Google Meet`, `Personal Note`, `External Source`. |
| **Raw Transcript/Note** | `Text` | The full, pasted text from the voice note, meeting, or observation. |
| **AI Summary** | `Text` | The AI-generated executive summary of the raw transcript. |
| **Tagged Entities** | `Relation` | **Crucial Field:** Multi-select relations linking to every Person, Organization, Place, Event, or Document mentioned in the transcript. |
| **Processing Status** | `Select` | Tracks the Technician's workflow. Options: `Needs Processing`, `Processed`. |

---
#### **Database 6: `Documents & Evidence`**
*   **Purpose:** The project's library for all external and internal files.
*   **View:** A table view, groupable by Document Type.

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Document Name** | `Title` | The name of the document (e.g., "Dorset Highways Proposal - Option 3"). |
| **File** | `File & Media` | The actual uploaded PDF, image, or Word document. |
| **Document Type** | `Select` | Categorization. Options: `Council Report`, `Legal Precedent`, `Meeting Minutes`, `Our Output`, `Evidence`. |
| **Source Organization** | `Relation` | Links to the `Organizations & Bodies` database to show who produced it. |
| **AI Analysis (from Colab)** | `Text` | The Technician pastes the findings from their deep-dive AI research here. |

---
#### **Database 7: `Key Places & Events`**
*   **Purpose:** The "where" and "when" of pivotal incidents and locations.
*   **View:** A timeline view for events, or a gallery view for places.

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Event / Place Name** | `Title` | The name of the incident or location (e.g., "The Co-op Incident"). |
| **Type** | `Select` | Differentiates the entry. Options: `Pivotal Event`, `Key Location`. |
| **Date of Event** | `Date` | The date the event occurred. |
| **Description** | `Text` | A summary of what happened or why the place is important. |
| **People Involved** | `Relation` | Links to all individuals from the `People & Contacts` database present at the event or associated with the place. |
| **Related Transgressions** | `Relation` | Links to specific rule violations from the `Identified Transgressions` database that occurred here. |

---
#### **Database 8: `Identified Transgressions`**
*   **Purpose:** To meticulously catalog every mistake, procedural failure, or conflict of interest committed by the opposition. This is the ammunition for the campaign.
*   **View:** A board view (Kanban) with columns for Severity (`Low`, `Medium`, `Critical`).

| Field Name | Notion Field Type | Description |
| :--- | :--- | :--- |
| **Transgression Summary** | `Title` | A concise summary of the wrongdoing (e.g., "Mayor's statement creates conflict of interest"). |
| **Perpetrator (Person)** | `Relation` | Links to the individual from the `People & Contacts` database who committed the transgression. |
| **Perpetrator (Org)** | `Relation` | Links to the organization responsible from the `Organizations & Bodies` database. |
| **Date of Transgression** | `Date` | The date the transgression occurred or was discovered. |
| **Evidence** | `Relation` | **Crucial Field:** Links to the specific entries in the `Documents & Evidence` or `Intelligence & Transcripts` databases that prove the transgression. |
| **Severity** | `Select` | Assesses the strategic value of the transgression. Options: `Low`, `Medium`, `High`, `Critical`. |