import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--workspace", type=Path, required=True)
parser.add_argument("--case", choices=["basic", "changed-input", "existing-target"], required=True)
args = parser.parse_args()
name = "input with spaces" if args.case == "changed-input" else "input"
source, target = args.workspace / name, args.workspace / "output"
(source / "nested" / "empty").mkdir(parents=True)
(source / "alpha.txt").write_text("alpha\n" if args.case != "changed-input" else "different input\n")
(source / "nested" / "résumé.txt").write_text("portable example\n", encoding="utf-8")
(source / ".hidden").write_text("hidden file\n")
if args.case == "existing-target":
    target.mkdir()
    (target / "keep.txt").write_text("keep this existing content\n")

def tree(root):
    return {p.relative_to(root).as_posix(): "directory" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))} if root.exists() else None

(args.workspace.parent / "oracle.json").write_text(json.dumps({"source": tree(source), "target": tree(target)}))
print(json.dumps({"source": str(source), "target": str(target)}))
