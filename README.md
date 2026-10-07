# Nono

Personal agent instructions, rules, and reusable skills for Claude Code, Codex, and other AI agents.

## Usage

Recommended setup:

- Keep this checkout at `~/.codex`. The Git root contains `AGENTS.md`, `rules/`, and `skills/` alongside Codex's existing local state. When migrating an existing checkout, merge its files and `.git` into the existing directory; preserve local configuration, credentials, sessions, caches, databases, and built-in skills.
- The root `.gitignore` tracks only Nono's shared files and explicitly excludes `skills/.system/`. Codex runtime data remains local, including new runtime paths outside the tracked allowlist. Do not force-add those files.
- Keep personal skills directly in `~/.codex/skills`, where the installed Codex client discovers them. Connect other clients to that directory as needed. Project-scoped `.agents/skills` directories remain independent of this user-level layout.
- Codex reads `~/.codex/AGENTS.md` directly as global guidance; no instruction symlink is needed. Keep shared preferences here so other clients can use the same file. See the [official instruction discovery guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- In the directory where you usually keep projects, such as `~/Workspace`, create a `nono` symlink pointing to `~/.codex` for quick access to the Git project. The old user-level `~/.agents` directory is no longer needed.
- If you use zsh, add commonly used agent and workspace shortcuts to `~/.zshrc`:

  ```zsh
  # claude
  alias cc='claude --dangerously-skip-permissions'
  alias ccu="npm i -g @anthropic-ai/claude-code@latest"

  # codex
  alias cdx='codex --sandbox danger-full-access --ask-for-approval never'
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
