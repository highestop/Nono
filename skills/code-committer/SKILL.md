---
name: code-committer
description: Handle Git repository changes with verified commit identities, automatic agent co-authorship, conventional commits, and GitHub PR management. Use when editing files in a Git repository; ask whether to submit a PR unless the user has already authorized it for that workspace.
---

# Code committer

## Scope and authorization

- Complete requested edits and relevant verification before asking whether to submit a PR. Include a concise change summary so the user can review the proposed work.
- When `git status --short` shows modified, staged, deleted, or untracked files, ask whether to submit a PR before committing or pushing, unless the user has already authorized the workflow for this task or workspace. Existing changes also count, but do not assume they belong to the task. Do not ask when there are no changes or the user has already declined.
- A request such as "automatically submit PRs in this workspace by default" applies only to that workspace. Honor it without asking again; do not change this skill, `AGENTS.md`, shared rules, or configuration files to record it, and do not carry it into other workspaces.
- If the user declines a PR, preserve the edits. Commit or push separately only when requested. If a PR is authorized, commit, push, and create or update it.
- Use the user's instructions directly; do not read or write skill-specific configuration files.

## Inspect the repository and identity

- Inspect the repository, branch, remotes, `git status`, `git diff`, and `git diff --cached`. Include only task-related changes and split unrelated topics into separate commits. Recheck if the user changes files during the task.
- Before each commit, run `git config --show-origin --get user.name`, `git config --show-origin --get user.email`, `git var GIT_AUTHOR_IDENT`, and `git var GIT_COMMITTER_IDENT` in the target workspace using the same environment as the commit. Report the effective author and committer names and emails, the Git setting sources, and any difference caused by environment overrides. The effective identities must resolve successfully with nonempty names and emails; if they do not, explain what is missing and ask the user to supply it. Never silently change Git identity settings.
- Infer co-authorship from the agent that contributed to the changes and report the trailer with the identity summary:
  - Codex: `Co-Authored-By: Codex <noreply@openai.com>`
  - Claude: `Co-Authored-By: Claude <noreply@anthropic.com>`
  - If the agent is unknown, omit the trailer and explain why; do not invent an identity.
- Use a feature branch; never commit directly to the default branch. Name a new branch `<user-name>-<short-description>` in kebab-case, using `git config user.name` or the authenticated `gh` login. Ask if neither is available. Reuse an appropriate existing feature branch.
- Keep history linear. Fetch and rebase when needed; do not amend existing commits, create merge commits, or overwrite unrelated work.

## Commit and submit the PR

- After authorization, stage only the intended files. Write English Angular Conventional Commit messages, adding a concise scope when useful. Append the inferred `Co-Authored-By` trailer after a blank line in the commit body.
- Push the feature branch and manage PRs with `gh`. For a non-fast-forward rejection, fetch and rebase, resolve conflicts within the task's scope, then retry a normal push. Use `--force-with-lease` only when an intentional history rewrite requires it; never fall back to `--force` without explicit authorization.
- Determine the PR target from `upstream` when present; otherwise use `gh repo view --json isFork,parent,nameWithOwner`. For a fork, push to the fork and open the PR against the original repository with `gh pr create --repo <upstream-owner>/<upstream-repo> --head <fork-owner>:<feature-branch>`.
- Update the branch's existing PR when present; otherwise create one. Use an English Conventional Commit title and an English description covering the problem, resulting behavior, relevant validation, and related issues. State the preference for rebase merge and feature branch deletion. Keep inferred co-author trailers in commits.
- Attach created or updated PRs to the current task when the host supports it, and provide the PR link. If any step is blocked, preserve the work and report the cause and remaining steps.

## Follow through

- Check CI and review status with `gh pr checks` and `gh pr view`. Fix task-related failures and valid blocking review issues, creating new commits with the same identity reporting and co-author rules. Ask for direction when a review requires a material scope change or its resolution is unclear.
- Merge only when required checks pass, no unresolved blocking review issues remain, and the user has authorized merging. Honor existing standing authorization without asking again; otherwise ask before merging.
- Prefer the project's merge queue when enabled, and rebase merge with branch deletion. Preserve commit messages and co-author trailers; if squash is required, retain all co-author trailers in the squash commit body.
- Confirm the merge and remote branch deletion, check closure of any issue the PR should close, and provide an available preview link.
