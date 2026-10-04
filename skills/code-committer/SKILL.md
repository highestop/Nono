---
name: code-committer
description: Manage GitHub code changes from environment checks through conventional commits, push, pull-request creation and tracking, check or review remediation, and user-confirmed merge. Use for any task that changes files in a Git repository, including requests that only ask for edits; commit, push, and open or update a PR by default. Never commit directly to main or merge without confirmation.
---

# Git commits

Follow the steps strictly. Proceed to the next step only after completing or explicitly skipping the current step.

For any task that changes files in any Git repository, complete the requested changes and verification, then immediately commit the task-related changes, push the feature branch, and open a PR for review, even if the user only asked for edits. If the branch already has a PR, push the new commit to that PR and provide its link. Do not include unrelated pre-existing changes. Honor an explicit request not to commit or open a PR. If committing, pushing, or creating a PR is blocked, preserve the changes and explain the blocker.

## Configuration

Read preferences from the current request, project configuration, or global configuration. Precedence:

1. Current user request
2. Project configuration: `.agents/config/code-committer.config.json`, `.claude/config/code-committer.config.json`
3. Global configuration: `~/.agents/config/code-committer.config.json`, `~/.claude/config/code-committer.config.json`
4. Default values

Supported fields:

| Field | Type | Description | Default |
| - | - | - | - |
| `git_user.name` | `string` / `null` | Expected Git username | `null` |
| `git_user.email` | `string` / `null` | Expected Git email | `null` |
| `co_authors` | `string` / `string[]` / `null` | One or more co-authors, with each item containing only `<name> <email>` | `null` |

Single co-author configuration:

```json
{
  "co_authors": "Codex <noreply@openai.com>"
}
```

Multiple co-author configuration:

```json
{
  "co_authors": [
    "Codex <noreply@openai.com>",
    "Claude <noreply@anthropic.com>"
  ]
}
```

Do not include the fixed `Co-Authored-By: ` prefix in configuration values. When `co_authors` is configured, normalize a string to a single-item list and generate `Co-Authored-By: <name> <email>` for each item in configuration order. Do not append co-authors inferred from the current agent. When it is not configured, retain the default behavior of inferring a co-author from the current agent.

If the user temporarily overrides configuration in a request, ask whether to save it after completing the work. When saving, prefer `.agents/config/code-committer.config.json` unless the user specifies another agent directory. Do not commit configuration containing personal information to version control.

## Workflow

### 1. Check the environment

- Confirm that the current directory is a Git repository.
- Check `git config user.name` and `git config user.email`.
- Check only configured `git_user` fields: validate `user.name` when `git_user.name` is configured, and validate `user.email` when `git_user.email` is configured. Do not require unconfigured fields. Stop and provide remediation commands when a configured field is missing or does not match.
- When `git_user.name` is not configured, derive the user identifier for the feature branch name in this order:
  1. The current `git config user.name`
  2. The login of the account currently authenticated with `gh`, retrieved with `gh api user --jq '.login'`
- If neither method provides a user identifier, ask the user. Do not silently write Git configuration.
- Distinguish forked from non-forked repositories before choosing the PR target:
  - First use `git remote -v` to check for an `upstream` remote. If it exists, treat the repository as a fork and use the repository associated with `upstream` as the original repository.
  - If there is no `upstream`, use `gh repo view --json isFork,parent,nameWithOwner` to check whether the current `origin` is a GitHub fork. When `isFork` is `true`, use `parent.nameWithOwner` as the original repository.
  - Determine fork status from either the presence of an `upstream` remote or the `isFork` value returned by `gh repo view`: `true` means forked and `false` means non-forked.

### 2. Analyze changes

- Analyze changes with `git status`, `git diff`, and `git diff --cached`.
- If the user adds or modifies workspace content during execution, restart from this step.
- Split unrelated topics into separate commits. Do not include unrelated changes in the same commit.

### 3. Handle the branch

- Use a feature branch by default. Do not commit directly to `main`.
- Name feature branches `<user-name>-<short-description>` in kebab-case. Use the user identifier determined during the environment check for `<user-name>`.
- Keep history linear. Use `git pull --rebase` and do not create merge commits.

### 4. Create commits

- Stage the files needed for the commit with `git add`.
- Write commit messages in English using Angular Conventional Commits.
  - Add a concise scope when it clearly identifies the affected area, such as a component, module, or skill.
  - Omit the scope for cross-cutting changes or when it would not add useful context.
  - Examples: `chore(skills): update fetch article skill`, `feat: add article formatter`
- Do not amend existing commits. Create a new commit.
- Add co-authors at the end of the commit body:
  - When `co_authors` is configured, append every `Co-Authored-By: <name> <email>` trailer generated from the configuration.
  - When it is not configured, infer the co-author from the current agent:
    - Claude: `Co-Authored-By: Claude <noreply@anthropic.com>`
    - Codex: `Co-Authored-By: Codex <noreply@openai.com>`
    - If the current agent cannot be determined, ask the user or skip the co-author and explain why.

### 5. Push and create a PR

- Push automatically after creating a commit.
- Write PR titles in English using Angular Conventional Commits.
  - Add a concise scope when it clearly identifies the affected area, such as a component, module, or skill.
  - Omit the scope for cross-cutting changes or when it would not add useful context.
  - Examples: `chore(skills): update fetch article skill`, `feat: add article formatter`
- If a push fails because of a non-fast-forward update:
  1. Run `git pull --rebase`
  2. If conflicts occur, identify the conflicting files and resolve them or wait for the user to handle them
  3. After the rebase completes, use `git push --force-with-lease`
- If `--force-with-lease` fails, do not use `--force` directly. Explain the risk and ask the user first.
- If the current branch is a feature branch without a PR, create one by default. Skip PR creation only when the user explicitly requests a commit without a PR.
  - Forked repository: push the feature branch to your fork, then create a cross-repository PR against the original repository with `gh pr create --repo <upstream-owner>/<upstream-repo> --head <fork-owner>:<feature-branch>`. You do not need to switch to the original repository owner's identity.
  - Non-forked repository: push the current feature branch, then use `gh pr create` to open a PR against the current repository.
- State in the PR description that rebase merge is the default and request deletion of the feature branch after merge.
- When `co_authors` is configured, append every generated `Co-Authored-By: <name> <email>` trailer to the end of the PR description. When it is not configured, do not append inferred co-authors to the PR description.
- Link any related issue in the PR.

### 6. Track the PR

- After creating or finding a PR, give the user its link.
- Track check and review status with `gh pr checks` and `gh pr view`.
- If a check fails:
  1. Summarize the failed job and key errors
  2. Fix the problem
  3. Create a new commit and push it by following the commit workflow, then continue tracking the PR
- If a review raises a serious issue:
  1. Summarize the issue
  2. Determine whether it is real, reasonable, and requires a fix, and explain the evidence
  3. Ask the user whether to fix or reject it
  4. If fixing it, create a new commit and continue tracking. If rejecting it, dismiss the review and provide a reason

### 7. Merge the PR

- After PR checks and reviews have no issues, ask the user whether to merge automatically.
- If the user chooses not to merge, stop here.
- If the user chooses to merge:
  - Prefer the merge queue when the project has one enabled
  - Use rebase merge by default, preserving every commit and its complete message and co-author trailers
  - When using squash merge if needed, preserve all required `Co-Authored-By` trailers in the squash commit body
  - Do not use a merge commit, to avoid branches in `main` history
  - Wait for the PR to merge successfully
  - Confirm that the remote feature branch has been deleted
  - If there is a related issue, confirm that it has been closed
  - If a preview environment exists, provide the latest preview link

## Critical rules

- Use the `gh` CLI to manage PRs.
- Keep history linear by default.
- Use rebase merge by default to preserve every commit and its co-author information.
- Do not commit directly to `main`.
- Do not amend commits.
- Write PR titles and commit messages in English using Angular Conventional Commits; add a concise scope when it provides useful context, and otherwise omit it.
- Handle Git errors properly and explain the cause, impact, and next step.
