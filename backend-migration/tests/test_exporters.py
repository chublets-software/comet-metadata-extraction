import json
from pathlib import Path

import pytest

from app.exporters.statements import EmptyExtractionError, build_record, merge_records
from app.exporters.writers import (
    chublet_turtle,
    local_quickstatements,
    wikidata_quickstatements,
)

FIXTURE = Path(__file__).parent / "fixtures" / "unicorn.connoss.json"
RETRIEVED = "2026-11-02"


@pytest.fixture
def record():
    return build_record(json.loads(FIXTURE.read_text(encoding="utf-8")), RETRIEVED)


def reasons(record, prop):
    return [entry["reason"] for entry in record.review if entry["property"] == prop]


def test_statements_for_the_unicorn(record):
    pairs = {(s.prop, s.value) for s in record.statements}
    assert pairs == {
        ("P1324", "https://github.com/sparqlunicorn/sparqlunicornGoesGIS"),
        ("P275", "Q10513450"),
        ("P277", "Q28865"),
        ("P348", "0.17.4"),
        ("P1401", "https://github.com/sparqlunicorn/sparqlunicornGoesGIS/issues"),
    }


def test_uncertain_values_go_to_review(record):
    assert reasons(record, "softwareVersion") == ["differs from release tag 0.17.4"]
    assert "several DOIs" in reasons(record, "identifier")[0]
    assert reasons(record, "copyrightHolder")
    assert reasons(record, "dateCreated")
    assert reasons(record, "author")


def test_existing_item_is_not_created(record):
    text = wikidata_quickstatements(record, "Q74005133")
    assert "CREATE" not in text
    assert all(line.startswith(("#", "Q74005133\t")) for line in text.splitlines())


def test_new_item_carries_the_identity_block(record):
    text = wikidata_quickstatements(record, None)
    assert "CREATE" in text
    for line in ("LAST\tP31\tQ141115627", "LAST\tP6104\tQ141169143", "LAST\tP2561\ten:"):
        assert line in text


def test_known_statements_are_skipped(record):
    known = {
        ("P125", "https://github.com/sparqlunicorn/sparqlunicorngoesgis"),
        ("P123", "q370"),
        ("P148", "0.17.4"),
    }
    lines = local_quickstatements(record, "Q360", known).splitlines()[1:]
    assert [line.split("\t")[1] for line in lines] == ["P107", "P138"]


def test_turtle_has_statement_nodes(record):
    text = chublet_turtle(record, "Q360", "Q74005133")
    assert "chbt:P107 chb:Q934" in text
    assert 'chbt:P4 "Q74005133"' in text
    assert text.count("a wikibase:Statement") == 8


def amt_records():
    return [
        build_record(
            json.loads((FIXTURE.parent / name).read_text(encoding="utf-8")), RETRIEVED
        )
        for name in ("amt-engine.connoss.json", "amt-runner.connoss.json")
    ]


def test_repositories_of_one_tool_are_merged():
    merged = merge_records(amt_records(), "Academic Meta Tool (AMT)")
    pairs = [(s.prop, s.value) for s in merged.statements]
    assert merged.label == "Academic Meta Tool (AMT)"
    assert pairs.count(("P275", "Q334661")) == 1
    assert pairs.count(("P277", "Q28865")) == 1
    assert [p for p, _ in pairs].count("P1324") == 2
    assert not {"P348", "P356"} & {p for p, _ in pairs}
    assert len([e for e in merged.review if e["property"] == "P348"]) == 2
    assert [e for e in merged.review if "moved" in e["reason"]]


def test_rate_limited_extraction_is_refused():
    with pytest.raises(EmptyExtractionError):
        build_record({"results": {"name": None}, "enriched_metadata": {}}, RETRIEVED)
