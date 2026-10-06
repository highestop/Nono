"""Offline integration tests using disposable Git repositories."""

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


REPOSITORY = Path(__file__).resolve().parent.parent
MODULE_SPEC = importlib.util.spec_from_file_location("skill_sync", REPOSITORY / "scripts/sync-skills.py")
SYNC = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(SYNC)


class SkillSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name).resolve()
        self.root = base / "home with spaces" / ".codex"
        self.root.mkdir(parents=True)
        self.source = base / "upstream"
        self.source.mkdir()
        self.cwd = base / "work project"
        self.cwd.mkdir()
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        shutil.copytree(REPOSITORY / "scripts", self.root / "scripts")
        shutil.copyfile(REPOSITORY / ".gitignore", self.root / ".gitignore")
        for path in (self.root, self.source):
            self.git(path, "init", "--quiet", "--initial-branch=main")
        self.write_manifest({})
        self.write_json(self.root / "skills-lock.json", {"version": 1, "skills": {}})
        self.make_skill("example-skill", "first")
        self.make_skill("other-skill", "unselected")
        script = self.source / "skills/example-skill/scripts/run.sh"
        script.parent.mkdir()
        script.write_text("#!/bin/sh\nprintf 'fixture\\n'\n")
        script.chmod(0o755)
        self.commit_source()
        (self.root / "skills").mkdir()
        local = self.root / "skills/local-skill"
        local.mkdir()
        (local / "SKILL.md").write_text("Local skill: keep this file.\n")
        self.git(self.root, "add", ".")
        self.git(self.root, "-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "--quiet", "-m", "Initial fixture")

    def git(self, cwd, *args):
        return subprocess.check_output(
            ["git", "-C", str(cwd), *args], env=self.env, stderr=subprocess.STDOUT, text=True
        ).strip()

    def write_json(self, path, data):
        path.write_text(json.dumps(data, indent=2) + "\n")

    def write_manifest(self, skills):
        self.write_json(self.root / "skills.json", {"version": 1, "skills": skills})

    def dependency(self, name="example-skill"):
        return {"source": str(self.source), "ref": "main", "path": f"skills/{name}"}

    def configure(self):
        self.write_manifest({"example-skill": self.dependency()})

    def make_skill(self, name, content):
        folder = self.source / "skills" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test skill.\n---\n\n{content}\n"
        )
        (folder / "LICENSE").write_text("Fixture license.\n")

    def commit_source(self):
        self.git(self.source, "add", ".")
        self.git(self.source, "-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "--quiet", "-m", "Update fixture")
        return self.git(self.source, "rev-parse", "HEAD")

    def command(self, *args, expected=0, env=None):
        result = subprocess.run(
            [sys.executable, str(self.root / "scripts/sync-skills.py"), *args],
            cwd=self.cwd, env=env or self.env, text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def lock_bytes(self):
        return (self.root / "skills-lock.json").read_bytes()

    def installed_text(self):
        return (self.root / "skills/example-skill/SKILL.md").read_text()

    def test_empty_dependency_list_needs_no_git_or_network(self):
        original = self.lock_bytes()
        for mode in ("setup", "update"):
            self.command(mode, env={**self.env, "PATH": ""})
        self.assertEqual(self.lock_bytes(), original)
        self.assertFalse((self.root / ".cache").exists())
        self.assertFalse((self.root / ".agents").exists())

    def test_codex_runtime_and_system_skills_stay_local(self):
        runtime_paths = [
            "auth.json", "config.toml", "state_5.sqlite", "state_5.sqlite-wal",
            "sessions/example.jsonl", "plugins/cache/example.json",
            "skills/.system/builtin/SKILL.md", "future-runtime/data.json",
        ]
        for relative in runtime_paths:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Disposable runtime fixture.\n")
        custom = self.root / "skills/new-personal-skill/SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("Shared personal skill.\n")
        # A normal git add must include the shared skill and leave all runtime data out.
        self.git(self.root, "add", ".")
        staged = self.git(self.root, "diff", "--cached", "--name-only").splitlines()
        self.assertEqual(staged, ["skills/new-personal-skill/SKILL.md"])
        ignored = self.git(self.root, "check-ignore", *runtime_paths).splitlines()
        self.assertEqual(set(ignored), set(runtime_paths))

    def test_selective_install_flat_layout_and_git_ignore(self):
        self.configure()
        self.command("setup")
        self.assertIn("first", self.installed_text())
        self.assertTrue((self.root / "skills/example-skill").is_symlink())
        self.assertFalse((self.root / "skills/other-skill").exists())
        self.assertFalse((self.root / ".agents").exists())
        self.assertEqual((self.root / "skills/local-skill/SKILL.md").read_text(),
                         "Local skill: keep this file.\n")
        self.assertTrue(os.access(self.root / "skills/example-skill/scripts/run.sh", os.X_OK))
        self.assertEqual((self.root / "skills/example-skill/LICENSE").read_text(), "Fixture license.\n")
        status = self.git(self.root, "status", "--porcelain", "--untracked-files=all")
        self.assertNotIn("skills/example-skill", status)
        self.assertNotIn("skills/.gitignore", status)
        self.assertNotIn(".cache", status)

    def test_update_changes_only_the_selected_skill_and_is_idempotent(self):
        self.configure()
        self.command("update")
        first_lock = self.lock_bytes()
        first_target = (self.root / "skills/example-skill").resolve()
        self.command("update")
        self.assertEqual(self.lock_bytes(), first_lock)
        self.make_skill("other-skill", "unrelated change")
        self.commit_source()
        self.command("update")
        self.assertEqual(self.lock_bytes(), first_lock)
        self.make_skill("example-skill", "second")
        revision = self.commit_source()
        self.command("update")
        self.assertIn("second", self.installed_text())
        self.assertIn("first", (first_target / "SKILL.md").read_text())
        self.assertNotEqual((self.root / "skills/example-skill").resolve(), first_target)
        entry = json.loads(self.lock_bytes())["skills"]["example-skill"]
        self.assertEqual(entry["commit"], revision)

    def test_setup_restores_locked_revision_before_explicit_update(self):
        self.configure()
        self.command("setup")
        first_lock = self.lock_bytes()
        (self.root / "skills/example-skill").unlink()
        self.make_skill("example-skill", "second")
        self.commit_source()
        self.command("setup")
        self.assertIn("first", self.installed_text())
        self.assertEqual(self.lock_bytes(), first_lock)
        self.command("update")
        self.assertIn("second", self.installed_text())

    def test_setup_rejects_content_that_disagrees_with_the_lock(self):
        self.configure()
        self.command("setup")
        (self.root / "skills/example-skill").unlink()
        lock = json.loads(self.lock_bytes())
        lock["skills"]["example-skill"]["contentHash"] = "0" * 64
        self.write_json(self.root / "skills-lock.json", lock)
        original = self.lock_bytes()
        result = self.command("setup", expected=1)
        self.assertIn("does not match the lock", result.stderr)
        self.assertFalse(os.path.lexists(self.root / "skills/example-skill"))
        self.assertEqual(self.lock_bytes(), original)

    def test_root_skill_and_internal_symlink_are_supported(self):
        spec = self.dependency()
        spec["path"] = "."
        self.write_manifest({"example-skill": spec})
        (self.source / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: Root skill.\n---\nRoot instructions.\n"
        )
        (self.source / "reference.md").write_text("Shared reference.\n")
        (self.source / "reference-link.md").symlink_to("reference.md")
        self.commit_source()
        self.command("setup")
        self.assertIn("Root instructions", self.installed_text())
        self.assertEqual((self.root / "skills/example-skill/reference-link.md").read_text(),
                         "Shared reference.\n")

    def test_upstream_failure_preserves_installation_and_agent_can_use_it(self):
        self.configure()
        self.command("setup")
        original = self.lock_bytes()
        self.source.rename(self.source.with_name("offline"))
        self.command("update", expected=1)
        self.assertEqual(self.lock_bytes(), original)
        self.assertIn("first", self.installed_text())
        result = self.command("run", "--", sys.executable, "-c", "raise SystemExit(7)", expected=7)
        self.assertIn("last usable", result.stderr)

    def test_missing_required_skill_prevents_agent_launch(self):
        self.configure()
        self.source.rename(self.source.with_name("offline"))
        marker = self.cwd / "started"
        self.command("run", "--", sys.executable, "-c",
                     f"from pathlib import Path; Path({str(marker)!r}).touch()", expected=1)
        self.assertFalse(marker.exists())

    def test_authored_skill_is_not_overwritten_even_if_missing_on_disk(self):
        self.write_manifest({"local-skill": self.dependency("local-skill")})
        self.command("update", expected=1)
        self.assertEqual((self.root / "skills/local-skill/SKILL.md").read_text(),
                         "Local skill: keep this file.\n")
        shutil.rmtree(self.root / "skills/local-skill")
        result = self.command("update", expected=1)
        self.assertIn("version-controlled", result.stderr)
        self.assertFalse((self.root / "skills/local-skill").exists())

    def test_local_changes_to_generated_skill_are_preserved(self):
        self.configure()
        self.command("setup")
        path = self.root / "skills/example-skill/SKILL.md"
        path.write_text(path.read_text() + "\nLocal edit.\n")
        original = self.lock_bytes()
        result = self.command("update", expected=1)
        self.assertIn("locally modified", result.stderr)
        self.assertIn("Local edit", path.read_text())
        self.assertEqual(self.lock_bytes(), original)

    def test_invalid_path_and_escaping_symlink_are_rejected(self):
        spec = self.dependency()
        spec["path"] = "../outside"
        self.write_manifest({"example-skill": spec})
        self.command("update", expected=1)
        self.assertFalse((self.root / ".cache").exists())
        self.configure()
        (self.source / "skills/example-skill/escape").symlink_to("../../other-skill")
        self.commit_source()
        self.command("update", expected=1)
        self.assertFalse(os.path.lexists(self.root / "skills/example-skill"))

    def test_concurrent_update_is_skipped(self):
        self.configure()
        self.command("setup")
        original = self.lock_bytes()
        with (self.root / ".cache/external-skills/sync.lock").open("a") as mutex:
            fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.command("update", expected=1)
            self.assertIn("Another skill sync", result.stderr)
        self.assertEqual(self.lock_bytes(), original)

    def test_lock_write_failure_rolls_back_the_installed_link(self):
        self.configure()
        self.command("setup")
        original = self.lock_bytes()
        self.make_skill("example-skill", "second")
        self.commit_source()
        with mock.patch.dict(os.environ, self.env), mock.patch.object(
            SYNC, "write_json", side_effect=OSError("Simulated lock write failure")
        ):
            self.assertFalse(SYNC.sync(self.root))
        self.assertEqual(self.lock_bytes(), original)
        self.assertIn("first", self.installed_text())

    def test_shell_launcher_preserves_working_directory_arguments_and_exit_code(self):
        result = subprocess.run(
            ["bash", str(self.root / "scripts/agent.sh"), sys.executable, "-c",
             "import os, sys; print(os.getcwd()); print(sys.argv[1]); raise SystemExit(9)",
             "argument with spaces"],
            cwd=self.cwd, env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [str(self.cwd), "argument with spaces"])
        self.assertFalse((self.root / ".cache").exists())

    def test_launcher_updates_during_a_running_agent_session(self):
        self.configure()
        self.command("setup")
        marker = self.cwd / "agent-started"
        child = (
            "import pathlib,time\n"
            f"pathlib.Path({str(marker)!r}).touch()\n"
            f"skill=pathlib.Path({str(self.root / 'skills/example-skill/SKILL.md')!r})\n"
            "deadline=time.monotonic()+8\n"
            "while time.monotonic()<deadline:\n"
            "    if 'second' in skill.read_text(): raise SystemExit(0)\n"
            "    time.sleep(0.05)\n"
            "raise SystemExit(1)\n"
        )
        process = subprocess.Popen(
            [sys.executable, str(self.root / "scripts/sync-skills.py"), "run",
             "--interval", "0.1", "--", sys.executable, "-c", child],
            cwd=self.cwd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline and process.poll() is None:
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            self.make_skill("example-skill", "second")
            self.commit_source()
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


if __name__ == "__main__":
    unittest.main()
