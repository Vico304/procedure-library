#!/usr/bin/env python3
"""Copy a regular directory once, refuse conflicts, and compare contents."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symbolic links are outside this procedure")
        relative = path.relative_to(root).as_posix()
        result[relative] = ("directory" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    source, target = args.source.resolve(), args.target.resolve()
    try:
        if not source.is_dir():
            raise ValueError("Source must be a directory")
        if source == target or source.is_relative_to(target) or target.is_relative_to(source):
            raise ValueError("Source and target must be separate, non-nested directories")
        before = snapshot(source)
        if target.exists():
            if not target.is_dir() or snapshot(target) != before:
                raise ValueError("Target already exists with different content; no changes made")
        else:
            shutil.copytree(source, target)
        if snapshot(target) != before or snapshot(source) != before:
            raise RuntimeError("Source or target content changed during copying")
    except ValueError as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}))
        return 2
    print(json.dumps({"status": "success", "entries_verified": len(before)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
