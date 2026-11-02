"""Serialise a :class:`Record` as QuickStatements or chublet Turtle."""

from __future__ import annotations

import csv
import hashlib
import uuid
from pathlib import Path
from typing import Iterable, Optional

from app.exporters import vocabulary as vocab
from app.exporters.statements import Record, Statement

BASE = "https://n4o-rse.github.io/chublets-wikibase-demo/"
CANDIDATE = BASE + "candidate/"


def _quote(text: str) -> str:
    return '"' + text.replace('"', "'") + '"'


def _identity(record: Record) -> list[Statement]:
    def fixed(prop: str, value: str) -> Statement:
        return Statement(prop, "item", value, "", "chublets.software", 1.0)

    return [
        fixed("P31", vocab.CHUBLET_CLASS),
        fixed("P6104", vocab.CHUBLETS_WIKIPROJECT),
        fixed("P361", vocab.CHUBLETS_PLATFORM),
    ]


def known_statements(path: Path, subject: str) -> set[tuple[str, str]]:
    """Read the (property, value) pairs of an item from the demo's statements.csv."""
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            (row["property"], row["value"].casefold())
            for row in csv.DictReader(handle)
            if row["subject"] == subject
        }


def _local(statement: Statement) -> tuple[str, str]:
    value = statement.value
    if statement.kind == "item":
        value = vocab.LOCAL_ITEMS[value]
    return vocab.LOCAL_PROPERTIES[statement.prop], value


def _new_only(record: Record, known: set[tuple[str, str]]) -> list[Statement]:
    return [
        statement
        for statement in record.statements
        if (_local(statement)[0], _local(statement)[1].casefold()) not in known
    ]


def _qs_value(statement: Statement, value: str) -> str:
    if statement.kind == "item":
        return value
    if statement.kind == "monolingual":
        return "en:" + _quote(value)
    return _quote(value)


def _qs_time(day: str) -> str:
    return f"+{day}T00:00:00Z/11"


def wikidata_quickstatements(record: Record, item: Optional[str]) -> str:
    """QuickStatements v1 with Wikidata ids; without an item it creates a chublet."""
    subject = item or "LAST"
    lines = [f"# {record.repository}, extracted with CoMET-RS, retrieved {record.retrieved}"]
    statements = list(record.statements)
    if item is None:
        lines += [
            "CREATE",
            f"LAST\tLen\t{_quote(record.label)}",
            f"LAST\tDen\t{_quote(record.description[:250])}",
        ]
        name = Statement(
            "P2561", "monolingual", record.label, record.repository, "CoMET-RS", 1.0
        )
        statements = _identity(record) + [name] + statements
    for statement in statements:
        fields = [subject, statement.prop, _qs_value(statement, statement.value)]
        for qualifier, value in statement.qualifiers:
            fields += [qualifier, value]
        if statement.reference_url:
            fields += [
                "S854", _quote(statement.reference_url),
                "S813", _qs_time(record.retrieved),
            ]
        lines.append("\t".join(fields))
    return "\n".join(lines) + "\n"


def local_quickstatements(record: Record, item: str, known: set[tuple[str, str]]) -> str:
    """QuickStatements with local ids for ``main.py apply-qs`` of the demo."""
    lines = [f"# {record.repository}, extracted with CoMET-RS, retrieved {record.retrieved}"]
    for statement in _new_only(record, known):
        prop, value = _local(statement)
        fields = [item, prop, _qs_value(statement, value)]
        for qualifier, target in statement.qualifiers:
            fields += [vocab.LOCAL_PROPERTIES[qualifier], vocab.LOCAL_ITEMS[target]]
        fields += ["S6", _quote(statement.reference_url)]
        lines.append("\t".join(fields))
    return "\n".join(lines) + "\n"


def _literal(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _ttl_value(statement: Statement, value: str) -> str:
    if statement.kind == "item":
        return f"chb:{value}"
    if statement.kind == "url":
        return f"<{value}>"
    return _literal(value)


def _slug(repository: str) -> str:
    return repository.rsplit("/", 1)[-1]


def chublet_turtle(
    record: Record, local_item: Optional[str], wikidata_item: Optional[str]
) -> str:
    """One chublet in the RDF shape of the demo: direct claims plus statement nodes."""
    subject = f"chb:{local_item}" if local_item else f"<{CANDIDATE}{_slug(record.repository)}>"
    statements = _identity(record) + record.statements
    item_lines = [
        "    a wikibase:Item ;",
        f"    skos:prefLabel {_literal(record.label)}@en ;",
    ]
    if record.description:
        item_lines.append(f"    schema:description {_literal(record.description)}@en ;")
    if wikidata_item:
        item_lines.append(f"    chbt:P4 {_literal(wikidata_item)} ;")

    nodes: list[str] = []
    references: dict[str, str] = {}
    for statement in statements:
        prop, value = _local(statement)
        rendered = _ttl_value(statement, value)
        key = f"{record.repository}|{prop}|{value}"
        node = f"chbs:{uuid.uuid5(uuid.NAMESPACE_URL, key)}"
        item_lines.append(f"    chbt:{prop} {rendered} ;")
        item_lines.append(f"    chbp:{prop} {node} ;")
        block = [node, "    a wikibase:Statement ;", f"    chbps:{prop} {rendered} ;"]
        for qualifier, target in statement.qualifiers:
            block.append(
                f"    chbpq:{vocab.LOCAL_PROPERTIES[qualifier]} chb:{vocab.LOCAL_ITEMS[target]} ;"
            )
        if statement.reference_url:
            reference = hashlib.sha1(
                f"{statement.reference_url}|{record.retrieved}".encode("utf-8")
            ).hexdigest()
            references[reference] = statement.reference_url
            block.append(f"    prov:wasDerivedFrom chbref:{reference} ;")
        block[-1] = block[-1][:-1] + "."
        nodes.append("\n".join(block))

    item_lines[-1] = item_lines[-1][:-1] + "."
    prefixes = [
        f"@prefix chb: <{BASE}entity/> .",
        f"@prefix chbt: <{BASE}prop/direct/> .",
        f"@prefix chbp: <{BASE}prop/> .",
        f"@prefix chbps: <{BASE}prop/statement/> .",
        f"@prefix chbpq: <{BASE}prop/qualifier/> .",
        f"@prefix chbpr: <{BASE}prop/reference/> .",
        f"@prefix chbs: <{BASE}entity/statement/> .",
        f"@prefix chbref: <{BASE}reference/> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix schema: <http://schema.org/> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix wikibase: <http://wikiba.se/ontology#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
    ]
    reference_blocks = [
        "\n".join(
            [
                f"chbref:{key}",
                "    a wikibase:Reference ;",
                f"    chbpr:P6 <{url}> ;",
                f'    chbpr:P7 "{record.retrieved}T00:00:00Z"^^xsd:dateTime .',
            ]
        )
        for key, url in sorted(references.items())
    ]
    header = f"# {record.repository}, extracted with CoMET-RS, retrieved {record.retrieved}"
    sections: Iterable[str] = [
        header + "\n" + "\n".join(prefixes),
        subject + "\n" + "\n".join(item_lines),
        *nodes,
        *reference_blocks,
    ]
    return "\n\n".join(sections) + "\n"


def write_review(record: Record, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repository", "property", "value", "reason"])
        writer.writeheader()
        writer.writerows(record.review)
