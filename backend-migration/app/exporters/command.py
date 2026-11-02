"""The ``comet-rs export`` command."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from app.exporters.statements import (
    DEFAULT_THRESHOLD,
    EmptyExtractionError,
    build_record,
    merge_records,
)
from app.exporters.writers import (
    chublet_turtle,
    known_statements,
    local_quickstatements,
    wikidata_quickstatements,
    write_review,
)


def add_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "export",
        help="Turn a saved extraction into QuickStatements or chublet Turtle.",
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="+",
        help="JSON file(s) written by 'comet-rs extract'; several files describe one tool.",
    )
    parser.add_argument(
        "--format", required=True, choices=["wikidata", "chublet-qs", "chublet-ttl"]
    )
    parser.add_argument("--output", type=Path, help="Target file (default: stdout).")
    parser.add_argument("--review", type=Path, help="CSV of values left for curation.")
    parser.add_argument("--item", help="Existing Wikidata item; without it a chublet is created.")
    parser.add_argument("--local-item", help="Existing item in the chublets Wikibase.")
    parser.add_argument(
        "--known",
        type=Path,
        help="statements.csv of the demo; chublet-qs then skips what the item already has.",
    )
    parser.add_argument("--label", help="Name of the tool, overrides the extracted one.")
    parser.add_argument("--description", help="Description, overrides the extracted one.")
    parser.add_argument("--retrieved", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    records = []
    for path in args.input:
        document = json.loads(path.read_text(encoding="utf-8"))
        try:
            records.append(build_record(document, args.retrieved, args.threshold))
        except EmptyExtractionError as error:
            sys.exit(f"{path}: {error}")
    record = merge_records(records, args.label, args.description)

    if args.format == "wikidata":
        text = wikidata_quickstatements(record, args.item)
    elif args.format == "chublet-ttl":
        text = chublet_turtle(record, args.local_item, args.item)
    else:
        if not args.local_item:
            sys.exit("--format chublet-qs needs --local-item.")
        known = known_statements(args.known, args.local_item) if args.known else set()
        text = local_quickstatements(record, args.local_item, known)

    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    if args.review:
        write_review(record, args.review)
    print(
        f"{len(record.statements)} statements, {len(record.review)} values for review",
        file=sys.stderr,
    )
