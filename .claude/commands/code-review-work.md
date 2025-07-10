Perform a high level (senior+) code review of the repository in its current state. Assume the reviewer (yourself) has not run most of the code
base yet. A functionality testing plan might be key; manually, programmatically or both. Be harsh, but be fair, and focus on what is effective
and "making this work". Ultrathink.

Use Claude Native tools over MCP.
Create folders/files if not exist.
Under no circumstances should files be deleted; create and append deletion recommendations to docs/recommended-cleanup.md

0. Understand and document the codebase structure in docs/codebase-structure.md.
1. Overall architecture and structure
2. Code quality and consistency
3. Testing coverage and quality
4. Security considerations
5. Documentation and maintainability
6. Potential bugs and issues
7. A functionality testing plan

Write up all findings and plans in docs/code-review-work-<timestamp: int>.md