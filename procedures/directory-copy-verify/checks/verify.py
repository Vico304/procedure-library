import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--workspace", type=Path, required=True)
parser.add_argument("--parameters", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
parser.add_argument("--case")
args = parser.parse_args()
values = json.loads(args.parameters.read_text())
result = json.loads(args.result.read_text())
source, target = Path(values["source"]), Path(values["target"])

def tree(root):
    if not root.is_dir():
        return None
    found = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise SystemExit("Unexpected symbolic link")
        found[p.relative_to(root).as_posix()] = "directory" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()
    return found

if args.case:
    oracle = json.loads((args.workspace.parent / "oracle.json").read_text())
    if tree(source) != oracle["source"]:
        raise SystemExit("Source changed")
    if args.case == "existing-target":
        if result["status"] != "blocked" or tree(target) != oracle["target"]:
            raise SystemExit("Conflict did not preserve the original target")
    elif result["status"] != "success" or tree(target) != oracle["source"]:
        raise SystemExit("Copied result differs from the independent oracle")
elif result["status"] != "success" or tree(source) is None or tree(target) != tree(source):
    raise SystemExit("Runtime copy verification failed")
print("Independent content and directory checks passed")
