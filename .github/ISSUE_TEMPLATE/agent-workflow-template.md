---
name: Agent workflow template
about: Template for creating an issue to initialize an agent workflow
---

-

---

### 1. Understand the problem and gather relevant information

If the request includes a GitHub link, such as an issue or PR, use the `gh` CLI to retrieve relevant information. Notify me if it is not installed or the current directory is not a repository.

### 2. Analyze the problem and discuss details and approaches without modifying any code

**Important**: At the end of every conversation turn, post a summary as a comment on the issue without asking me for confirmation. Key information, such as analysis results and implementation plans, must be sufficiently detailed and clear, omit no important information, and use lists, tables, flowcharts, or other intuitive formats whenever possible.

### 3. Complete and submit the changes

**Important**: After every code change, use the `code-committer` skill to commit the code, create a PR, and link the PR to this issue. Do not ask me for confirmation, but do not merge the PR until I review it manually.
