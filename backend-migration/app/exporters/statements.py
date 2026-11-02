"""Derive reviewed statements from a ``comet-rs extract`` result."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.exporters import vocabulary as vocab

DEFAULT_THRESHOLD = 0.9


class EmptyExtractionError(ValueError):
    """The extraction holds no usable record, typically after a rate limit."""


@dataclass(frozen=True)
class Statement:
    prop: str
    kind: str  # item, url, string or monolingual
    value: str
    reference_url: str
    source: str
    confidence: float
    qualifiers: tuple[tuple[str, str], ...] = ()


@dataclass
class Record:
    repository: str
    label: str
    description: str
    retrieved: str
    statements: list[Statement] = field(default_factory=list)
    review: list[dict[str, str]] = field(default_factory=list)

    def note(self, prop: str, value: Any, reason: str) -> None:
        self.review.append(
            {
                "repository": self.repository,
                "property": prop,
                "value": _text(value),
                "reason": reason,
            }
        )


def _text(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(_text(entry) for entry in value)
    if isinstance(value, dict):
        for key in ("name", "@id", "url", "title"):
            if value.get(key):
                return str(value[key])
        return f"{value.get('givenName', '')} {value.get('familyName', '')}".strip()
    return str(value)


def _person(person: dict[str, Any]) -> str:
    name = f"{person.get('givenName', '')} {person.get('familyName', '')}".strip()
    return f"{name} <{person.get('@id', '')}>"


def _canonical_repository(url: str) -> str:
    return re.sub(r"\.git$", "", url.rstrip("/"))


def _spdx_id(licence: Any) -> Optional[str]:
    url = licence.get("url", "") if isinstance(licence, dict) else str(licence)
    match = re.search(r"spdx\.org/licenses/([^/]+?)(?:\.html)?$", url)
    return re.sub(r"-(only|or-later)$", "", match.group(1)) if match else None


def build_record(
    document: dict[str, Any], retrieved: str, threshold: float = DEFAULT_THRESHOLD
) -> Record:
    """Sort every extracted value into a statement or the review list."""
    results = document.get("results") or {}
    meta = document.get("enriched_metadata") or {}
    if not results.get("name") or not results.get("codeRepository"):
        raise EmptyExtractionError(
            "No name or codeRepository in this extraction; check its log for a "
            "rate limit and run it again with GITHUB_TOKEN set."
        )

    repository = _canonical_repository(results["codeRepository"])
    record = Record(
        repository=repository,
        label=results.get("alternateName") or results["name"],
        description=results.get("description") or "",
        retrieved=retrieved,
    )

    def trusted(prop: str) -> bool:
        info = meta.get(prop)
        if info is None:
            record.note(prop, results.get(prop), "no provenance")
            return False
        if "llm" in str(info.get("source", "")).lower():
            record.note(prop, results.get(prop), "LLM value, needs curation")
            return False
        if float(info.get("confidence", 0)) < threshold:
            record.note(
                prop,
                results.get(prop),
                f"confidence {info.get('confidence')} below {threshold}",
            )
            return False
        return True

    def add(prop: str, kind: str, value: str, origin: str, url: str = repository, **extra):
        record.statements.append(
            Statement(
                prop=prop,
                kind=kind,
                value=value,
                reference_url=url,
                source=str(meta[origin]["source"]),
                confidence=float(meta[origin]["confidence"]),
                **extra,
            )
        )

    requested = _canonical_repository(document.get("code_url", repository))
    if requested.lower() != repository.lower():
        record.note("codeRepository", requested, f"repository moved to {repository}")

    if trusted("codeRepository"):
        add(
            "P1324", "url", repository, "codeRepository",
            qualifiers=(("P8423", vocab.GIT),),
        )

    licence = results.get("license")
    if licence and trusted("license"):
        spdx = _spdx_id(licence)
        if spdx in vocab.LICENCES:
            add("P275", "item", vocab.LICENCES[spdx], "license")
        else:
            record.note("license", licence, "licence without a checked Wikidata item")

    languages = results.get("programmingLanguage") or []
    if languages and trusted("programmingLanguage"):
        if languages[0] in vocab.LANGUAGES:
            add("P277", "item", vocab.LANGUAGES[languages[0]], "programmingLanguage")
        else:
            record.note("programmingLanguage", languages[0], "language without a checked item")
        if languages[1:]:
            record.note(
                "programmingLanguage", languages[1:], "secondary, only the main language is exported"
            )

    _add_version(results, meta, record, add)

    if results.get("issueTracker") and trusted("issueTracker"):
        add("P1401", "url", results["issueTracker"], "issueTracker")

    identifiers = results.get("identifier") or []
    dois = [entry.split("doi.org/")[1] for entry in identifiers if "doi.org/" in entry]
    if len(dois) == 1 and trusted("identifier"):
        add("P356", "string", dois[0].upper(), "identifier")
    elif len(dois) > 1:
        record.note("identifier", identifiers, "several DOIs, CoMET does not link them to versions")

    for prop, reason in (
        ("author", "person needs reconciliation to an item"),
        ("contributor", "person needs reconciliation to an item"),
        ("referencePublication", "publication needs reconciliation to an item"),
        ("copyrightHolder", "taken from the licence text, check the holder"),
        ("dateCreated", "repository creation is not always the inception of the software"),
        ("documentation", "no property chosen yet"),
        ("archivedAt", "no property chosen yet"),
        ("keywords", "keywords need mapping to main subjects"),
    ):
        value = results.get(prop)
        if not value:
            continue
        if prop in ("author", "contributor"):
            value = [_person(person) for person in value]
        record.note(prop, value, reason)

    return record


def merge_records(
    records: list[Record], label: Optional[str] = None, description: Optional[str] = None
) -> Record:
    """Combine the repositories of one tool into one record.

    Versions and DOIs belong to a single repository, so differing values are
    left for curation rather than attributed to the whole tool.
    """
    first = records[0]
    merged = Record(
        repository=first.repository,
        label=label or first.label,
        description=description if description is not None else first.description,
        retrieved=first.retrieved,
    )
    for record in records:
        merged.review.extend(record.review)
    seen: set[tuple[str, str]] = set()
    statements = [statement for record in records for statement in record.statements]
    for statement in statements:
        values = {other.value for other in statements if other.prop == statement.prop}
        if statement.prop in ("P348", "P356") and len(values) > 1:
            merged.review.append(
                {
                    "repository": statement.reference_url,
                    "property": statement.prop,
                    "value": statement.value,
                    "reason": "repositories of this tool differ, decide what the item records",
                }
            )
            continue
        if (statement.prop, statement.value) not in seen:
            seen.add((statement.prop, statement.value))
            merged.statements.append(statement)
    return merged


def _add_version(results, meta, record, add) -> None:
    """Prefer the release tag: a CITATION.cff often lags behind the releases."""
    version = results.get("softwareVersion")
    notes = results.get("releaseNotes") or ""
    tagged = re.search(r"/releases/tag/v?([^/]+)$", notes)
    if tagged:
        add("P348", "string", tagged.group(1), "releaseNotes", url=notes)
        if version and version != tagged.group(1):
            record.note(
                "softwareVersion", version, f"differs from release tag {tagged.group(1)}"
            )
    elif version:
        add("P348", "string", version, "softwareVersion")
