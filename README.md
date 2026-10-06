# Nono

Personal agent instructions, rules, and reusable skills for Claude Code, Codex, and other AI agents.

## Usage

Recommended setup:

- Keep this checkout at `~/.codex`. The Git root contains `AGENTS.md`, `skills.json`, `skills-lock.json`, `scripts/`, and `skills/` alongside Codex's existing local state. When migrating an existing checkout, merge its files and `.git` into the existing directory; preserve local configuration, credentials, sessions, caches, databases, and built-in skills.
- The root `.gitignore` tracks only Nono's shared files and explicitly excludes `skills/.system/`. Codex runtime data remains local, including new runtime paths outside the tracked allowlist. Do not force-add those files.
- Use Python 3.9+ and Git on macOS or Linux. Keep personal skills directly in `~/.codex/skills`, where the installed Codex client discovers them. Connect other clients to that directory as needed. Project-scoped `.agents/skills` directories remain independent of this user-level layout.
- Codex reads `~/.codex/AGENTS.md` directly as global guidance; no instruction symlink is needed. Keep shared preferences here so other clients can use the same file. See the [official instruction discovery guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- In the directory where you usually keep projects, such as `~/Workspace`, create a `nono` symlink pointing to `~/.codex` for quick access to the Git project. The old user-level `~/.agents` directory is no longer needed.
- If you use zsh, add commonly used agent and workspace shortcuts to `~/.zshrc`:

  ```zsh
  # claude
  alias cc='~/.codex/scripts/agent.sh claude --dangerously-skip-permissions'
  alias ccu="npm i -g @anthropic-ai/claude-code@latest"

  # codex
  alias cdx='~/.codex/scripts/agent.sh codex --sandbox danger-full-access --ask-for-approval never'
  alias cdxu="npm i -g @openai/codex@latest"

  # zsh
  alias zshrc="code ~/.zshrc"

  # workspace
  alias ws="cd ~/Workspace"
  ```

## Source extraction skills

- [extract-wechat](skills/extract-wechat/SKILL.md): extract WeChat Official Account content and selected original images.
- [extract-xiaohongshu](skills/extract-xiaohongshu/SKILL.md): extract Xiaohongshu note content and selected original media.

These skills return source content and selected media without creating Markdown archives.

## External skills

The dependency list starts empty. Setup and update commands then succeed without network access or generated files; existing skills remain locally maintained.

Declare only the skills you want in [@skills.json](/skills.json). For example, after replacing the example source with a real repository:

```json
{
  "version": 1,
  "skills": {
    "article-extractor": {
      "source": "https://github.com/<owner>/<repo>.git",
      "ref": "main",
      "path": "skills/article-extractor"
    }
  }
}
```

- Each key must match the skill's `name` in `SKILL.md`. Use `"path": "."` for a single-skill repository with `SKILL.md` at its root. Sources use Git URLs (with normal Git authentication) or absolute local Git paths.
- `ref` selects a branch, tag, or commit. Updates follow that exact ref; tracking `main` follows new commits, while a fixed tag does not automatically advance to a new release.
- A skill must be self-contained, including supporting files and license notices. Links outside its directory are rejected. An installed skill can be read through `~/.codex/skills/<name>`.
- [@skills-lock.json](/skills-lock.json) records the resolved commit and installed content hash. These are Nono's own manifest and lock formats; the scripts manage them without an npm dependency. Review and commit lock changes when you want to share updated revisions.

```bash
# Restore missing skills from the lock; resolve new dependencies from their refs.
~/.codex/scripts/setup-skills.sh

# Install missing skills and update declared dependencies to their current refs.
~/.codex/scripts/update-skills.sh

# Run a foreground updater, checking every 300 seconds until interrupted.
~/.codex/scripts/update-skills.sh --watch --interval 300

# Sync before launch, then check every 300 seconds until the agent exits.
~/.codex/scripts/agent.sh codex
```

The launcher preserves the agent's working directory, arguments, and exit status. Calling `codex` or `claude` directly bypasses the launcher; the aliases above opt into automatic synchronization. Nothing installs a system service or runs after the agent exits. This is polling, with up to one interval of delay, rather than a webhook subscription.

External skill snapshots live in the ignored `.cache/external-skills/` directory and are exposed through relative links directly under `skills/`. The updater maintains an ignored `skills/.gitignore` for those links. Custom skills remain version-controlled. Sync refuses to overwrite tracked, unmanaged, or locally modified skills; a process lock serializes updates. Failed downloads leave the current version intact, and installation switches each skill's link only after validation. Previous snapshots remain available locally.

When startup cannot update, the launcher uses the last usable installation and reports the failure. If a required skill has never been installed or has been locally modified, launch stops with an error. A client must reload changed instructions at a task boundary; restart it if it does not detect the changed files. For clients that do not follow skill-directory symlinks, configure a supported discovery path before using the launcher.

Removing a manifest entry stops its updates but does not uninstall it. To uninstall explicitly, remove only its generated `skills/<name>` link and its lock entry; cached snapshots can be removed separately. Keep customizations in an owned skill or fork, rather than editing generated snapshots.

Run the offline integration tests with `python3 scripts/test_skill_sync.py -v`.
