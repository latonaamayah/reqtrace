"""CLI sub-command: annotate — manage notes on captured request records."""
from __future__ import annotations

import argparse
import sys
from typing import List

from reqtrace.annotator import AnnotationStore, format_annotations
from reqtrace.storage import LogStorage

# Module-level store so the CLI session persists annotations in memory.
_store = AnnotationStore()


def build_annotate_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:
    desc = "Add, list, or remove notes on request records."
    if parent is not None:
        parser = parent.add_parser("annotate", help=desc, description=desc)
    else:
        parser = argparse.ArgumentParser(prog="reqtrace annotate", description=desc)

    parser.add_argument("--log", required=True, help="Path to the .jsonl log file.")
    sub = parser.add_subparsers(dest="action", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a note to a record.")
    p_add.add_argument("record_id", help="ID of the request record.")
    p_add.add_argument("note", help="Text of the annotation.")
    p_add.add_argument("--author", default="user", help="Author name (default: user).")

    # list
    p_list = sub.add_parser("list", help="List annotations for a record.")
    p_list.add_argument("record_id", help="ID of the request record.")

    # remove
    p_rm = sub.add_parser("remove", help="Remove an annotation by index.")
    p_rm.add_argument("record_id", help="ID of the request record.")
    p_rm.add_argument("index", type=int, help="Zero-based index of the annotation to remove.")

    return parser


def run_annotate(args: argparse.Namespace, store: AnnotationStore = _store) -> int:
    storage = LogStorage(args.log)
    records = {r.id: r for r in storage.load_all()}

    if args.action == "add":
        if args.record_id not in records:
            print(f"Error: record '{args.record_id}' not found.", file=sys.stderr)
            return 1
        ann = store.add(args.record_id, args.note, author=args.author)
        print(f"Added annotation: {ann}")
        return 0

    if args.action == "list":
        if args.record_id not in records:
            print(f"Error: record '{args.record_id}' not found.", file=sys.stderr)
            return 1
        rec = records[args.record_id]
        annotations = store.get(args.record_id)
        print(format_annotations(rec, annotations))
        return 0

    if args.action == "remove":
        removed = store.remove(args.record_id, args.index)
        if removed is None:
            print(f"Error: no annotation at index {args.index} for '{args.record_id}'.", file=sys.stderr)
            return 1
        print(f"Removed: {removed}")
        return 0

    print(f"Unknown action: {args.action}", file=sys.stderr)
    return 1


def main(argv: List[str] | None = None) -> None:
    parser = build_annotate_parser()
    args = parser.parse_args(argv)
    sys.exit(run_annotate(args))


if __name__ == "__main__":  # pragma: no cover
    main()
