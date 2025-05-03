import argparse
import json
import os
import sys
from pathlib import Path


def load_coverage(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)

        return data.get("files", {})
    except FileNotFoundError:
        print(f"[Error] Coverage file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[Error] Invalid JSON in coverage file: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[Error] Failed to load coverage file: {e}", file=sys.stderr)
        sys.exit(1)


def print_context_group(group_lines, all_lines, context, missing_set):
    if not group_lines:
        return

    min_line = min(group_lines)
    max_line = max(group_lines)
    start = max(1, min_line - context)
    end = min(len(all_lines), max_line + context)

    print("***-----***")
    for i in range(start, end + 1):
        prefix = "XX" if i in missing_set else "  "
        content = all_lines[i - 1].rstrip("\n")
        print(f"{prefix} {i:4d}: {content}")


def show_missing_lines(files_data, context, base_dir=None):
    if base_dir is None:
        base_dir = Path.cwd()
    else:
        base_dir = Path(base_dir)

    if not isinstance(base_dir, Path):
        base_dir = Path(base_dir)

    print(f"Searching for source files relative to: {base_dir.resolve()}")

    for filename_rel, info in files_data.items():
        missing = info.get("missing_lines", info.get("missing", []))
        if not missing:
            continue

        source_path = base_dir / filename_rel
        if not source_path.exists():
            source_path_alt = Path(filename_rel)
            if source_path_alt.exists():
                source_path = source_path_alt
            else:
                print(f"\nFile: {filename_rel}")
                print("  [Error] Source file not found.")
                print(f"  Tried: {source_path.resolve()}")
                if source_path_alt != source_path:
                    print(f"  Tried: {source_path_alt.resolve()}")
                continue

        print(f"\nFile: {filename_rel} (Found: {source_path.resolve()})")

        try:
            with open(source_path, "r", encoding="utf-8") as src:
                lines = src.readlines()
        except Exception as e:
            print(f"  [Error] Could not read source file: {e}")
            continue

        total_lines = len(lines)
        missing_sorted = sorted(set(m for m in missing if 1 <= m <= total_lines))
        missing_set = set(missing_sorted)

        if not missing_sorted:
            if missing:
                print(
                    f"  [Warning] All missing lines {missing} are outside the file bounds (1-{total_lines})."
                )
            continue

        current_group: list[int] = []
        last_line_in_group_context_end = -1

        for lineno in missing_sorted:
            current_line_context_start = max(1, lineno - context)

            if (
                not current_group
                or current_line_context_start > last_line_in_group_context_end + 1
            ):
                print_context_group(current_group, lines, context, missing_set)

                current_group = [lineno]
            else:
                current_group.append(lineno)

            last_line_in_group_context_end = min(total_lines, lineno + context)

        print_context_group(current_group, lines, context, missing_set)


def parse_args():
    p = argparse.ArgumentParser(
        description="Show missing coverage lines from coverage JSON data."
    )
    p.add_argument("coverage", help="Path to coverage JSON file (e.g., coverage.json)")
    p.add_argument(
        "-C",
        "--context",
        type=int,
        default=2,
        help="Show N lines of context around missing lines (default: 2)",
    )
    p.add_argument(
        "-B",
        "--base-dir",
        type=str,
        default=None,
        help="Base directory where source files are located (defaults to current directory)",
    )
    return p.parse_args()


def main():
    args = parse_args()
    files_data = load_coverage(args.coverage)
    if not files_data:
        print("No file coverage data found in the JSON.", file=sys.stderr)

    show_missing_lines(files_data, args.context, args.base_dir)


if __name__ == "__main__":
    main()
