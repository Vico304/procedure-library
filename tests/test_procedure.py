"""Control-plane tests use synthetic receipts; these are never published as model evidence."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("procedure", ROOT / "tools" / "procedure.py")
procedure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(procedure)


class ProcedureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.library = self.base / "library"
        self.package = procedure.init_draft("test-task", self.library, "routine")
        self.data = procedure.read_json(self.package / "procedure.json")
        self.data["description"] = "Write a test artifact"
        self.data["triggers"] = ["create the requested test artifact"]
        procedure.write_json(self.package / "procedure.json", self.data)
        (self.package / "procedure.md").write_text("Write the requested artifact and verify it.\n")
        (self.package / "checks" / "prepare.py").write_text('print(\'{"input": "value"}\')\n')
        (self.package / "checks" / "verify.py").write_text(
            'import argparse\nfrom pathlib import Path\np=argparse.ArgumentParser()\n'
            'p.add_argument("--workspace",type=Path)\np.add_argument("--parameters")\n'
            'p.add_argument("--result")\np.add_argument("--case")\na=p.parse_args()\n'
            'raise SystemExit(0 if (a.workspace / "artifact.txt").is_file() else 1)\n'
        )

    def receipt(self):
        return {"kind": "procedure-test-report-v1", "tested_at": "2026-01-01T12:34:56Z",
                "content_digest": procedure.fingerprint(self.package), "runtime_digest": procedure.runtime_digest(),
                "executor": self.data["executor"], "environment": {"platform": "synthetic-unit-test"},
                "complete": True, "passed": True,
                "cases": [{"id": "basic", "expected_status": "success", "actual_status": "success",
                           "verified": True, "passed": True}]}

    def publish(self):
        report = self.base / "synthetic-unit-receipt.json"
        procedure.write_json(report, self.receipt())
        return procedure.promote(self.package, report, self.library)

    def test_draft_is_uninstallable_and_template_is_incomplete(self):
        unfinished = procedure.init_draft("unfinished", self.library, "routine")
        with self.assertRaisesRegex(ValueError, "draft description"):
            procedure.manifest(unfinished)
        with self.assertRaises(FileNotFoundError):
            procedure.require_ready(self.package)

    def test_path_traversal_and_unrecognized_parameters_are_rejected(self):
        data = copy.deepcopy(self.data)
        data["verify"] = "../outside.py"
        procedure.write_json(self.package / "procedure.json", data)
        with self.assertRaisesRegex(ValueError, "relative"):
            procedure.manifest(self.package)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            procedure.parameters(self.data, {"unexpected": "value"}, self.base)

    def test_write_parameter_requires_an_explicit_root(self):
        data = {"parameters": {"target": {"type": "directory", "access": "write"}}}
        workspace, outside = self.base / "workspace", self.base / "other"
        workspace.mkdir()
        with self.assertRaisesRegex(ValueError, "outside authorized"):
            procedure.parameters(data, {"target": str(outside)}, workspace)
        bound = procedure.parameters(data, {"target": str(outside)}, workspace, [outside])
        self.assertEqual(bound["target"], str(outside))

    def test_changed_package_or_executor_cannot_use_old_receipt(self):
        report = self.base / "report.json"
        procedure.write_json(report, self.receipt())
        (self.package / "procedure.md").write_text("Changed procedure\n")
        with self.assertRaisesRegex(ValueError, "does not match"):
            procedure.promote(self.package, report, self.library)

    def test_incomplete_or_inconsistent_evidence_cannot_publish(self):
        for mutation in ("incomplete", "unchecked", "wrong-status"):
            with self.subTest(mutation=mutation):
                report = self.receipt()
                if mutation == "incomplete":
                    report["complete"] = False
                elif mutation == "unchecked":
                    report["cases"][0]["verified"] = False
                else:
                    report["cases"][0]["actual_status"] = "blocked"
                path = self.base / "report.json"
                procedure.write_json(path, report)
                with self.assertRaises(ValueError):
                    procedure.promote(self.package, path, self.library)

    def test_installation_is_self_contained_and_preserves_unrelated_skills(self):
        published = self.publish()
        installed = procedure.install(published, self.base / "installed")
        self.assertEqual(procedure.require_ready(installed)["id"], "test-task")
        self.assertTrue((installed / ".runner" / "procedure.py").is_file())
        self.assertNotIn(str(self.package), (installed / "SKILL.md").read_text())
        (installed / "procedure.md").write_text("Changed after installation")
        with self.assertRaisesRegex(ValueError, "revalidation"):
            procedure.require_ready(installed)
        unrelated = self.base / "unrelated" / "procedure-test-task"
        unrelated.mkdir(parents=True)
        (unrelated / "SKILL.md").write_text("User-owned unrelated skill")
        with self.assertRaisesRegex(ValueError, "unrelated"):
            procedure.install(published, unrelated.parent)
        self.assertEqual((unrelated / "SKILL.md").read_text(), "User-owned unrelated skill")

    def test_public_record_has_no_raw_runtime_bindings(self):
        published = self.publish()
        record = (published / "verification.json").read_text()
        self.assertNotIn(str(self.base), record)
        self.assertNotIn("summary", record)
        self.assertNotIn("parameters", record)
        self.assertEqual(procedure.read_json(self.library / "catalog.json")["procedures"][0]["id"], "test-task")

    def test_public_audit_rejects_private_paths_tokens_and_symlinks(self):
        root = self.base / "public"
        root.mkdir()
        path = root / "note.txt"
        for text in ("/" + "Users" + "/example/private/file", "ghp_" + "a" * 40):
            path.write_text(text)
            with self.assertRaisesRegex(ValueError, "Public content check"):
                procedure.audit(root)
        path.unlink()
        path.symlink_to(self.package / "procedure.md")
        with self.assertRaisesRegex(ValueError, "Symbolic"):
            procedure.audit(root)

    def test_model_claim_cannot_replace_an_independent_artifact_check(self):
        original_run = subprocess.run

        def control_run(command, *args, **kwargs):
            if command[:2] == ["codex", "--version"]:
                return SimpleNamespace(stdout="synthetic-test-cli")
            return original_run(command, *args, **kwargs)

        def lying_worker(root, data, values, workspace, state, task, timeout, write_roots=()):
            state.mkdir(parents=True)
            response = {"status": "success", "summary": "claimed success", "outputs": []}
            procedure.write_json(state / "parameters.json", values)
            procedure.write_json(state / "result.json", response)
            return response

        with patch.object(procedure, "require_tools"), patch.object(procedure, "codex_executable", return_value="codex"), patch.object(procedure, "worker", lying_worker), patch.object(procedure.subprocess, "run", control_run):
            self.assertFalse(procedure.test_package(self.package, self.library, 10))
        self.assertFalse((self.library / "procedures" / "test-task").exists())

    def test_complexity_selects_only_requested_models(self):
        self.assertEqual(procedure.executor_profile("routine"), {"model": "gpt-6-luna", "reasoning_effort": "low"})
        self.assertEqual(procedure.executor_profile("complex"), {"model": "gpt-6.1-terra", "reasoning_effort": "medium"})
        self.data["executor"]["model"] = "gpt-5.6-luna"
        procedure.write_json(self.package / "procedure.json", self.data)
        with self.assertRaisesRegex(ValueError, "6 Luna or 6.1 Terra only"):
            procedure.manifest(self.package)

    def test_policy_change_invalidates_old_verification(self):
        published = self.publish()
        with patch.object(procedure, "runtime_digest", return_value="changed-policy-digest"):
            with self.assertRaisesRegex(ValueError, "revalidation"):
                procedure.require_ready(published)

    def test_plugin_build_excludes_private_data_and_uses_shared_packages(self):
        self.publish()
        procedure.write_json(self.library / "plugin.json", {"name": "procedure-library", "version": "0.2.0"})
        import shutil
        for relative in ("tools/procedure.py", "tools/model-policy.json", "skills/procedure-register/SKILL.md"):
            target = self.library / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        procedure.write_json(self.library / ".local/private-parameters.json", {"input": "private-binding"})
        archive = procedure.build_plugin(self.library, self.library / "dist")
        with zipfile.ZipFile(archive) as package:
            names = package.namelist()
            self.assertFalse(any(".local/" in p or ".git/" in p for p in names))
            wrapper = package.read("procedure-library/skills/procedure-test-task/SKILL.md").decode()
            self.assertIn("../../procedures/test-task/procedure.json", wrapper)
            self.assertNotIn(".runner", wrapper)
        self.assertGreater(procedure.audit(self.library), 0)

    def test_explicit_outdated_cli_is_not_silently_replaced(self):
        procedure.codex_executable.cache_clear()
        self.addCleanup(procedure.codex_executable.cache_clear)
        with patch.dict(procedure.os.environ, {"PROCEDURE_CODEX": "old-codex"}), patch.object(procedure.shutil, "which", return_value="old-codex"), patch.object(procedure.subprocess, "run", return_value=SimpleNamespace(stdout="codex-cli 0.146.0")):
            with self.assertRaisesRegex(ValueError, "0.159.0"):
                procedure.codex_executable()


if __name__ == "__main__":
    unittest.main()
