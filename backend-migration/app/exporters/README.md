# Exporters

`comet-rs export` turns the JSON of `comet-rs extract` into records for Wikidata and for
[chublets.software](https://github.com/n4o-rse/chublets-wikibase-demo). It reads the saved file, needs no
network and uses the standard library only.

| `--format` | Result | Target |
|---|---|---|
| `wikidata` | QuickStatements v1 with Wikidata ids | QuickStatements |
| `chublet-qs` | QuickStatements with local ids | `python main.py apply-qs` of the demo |
| `chublet-ttl` | One chublet in Turtle | packaging, for example with fdo-git-packager |

```cmd
comet-rs export unicorn.connoss.json --format wikidata --item Q74005133 --review unicorn.review.csv --output unicorn.qs
```

Several input files describe one tool with several repositories. Set `--label` and `--description` in that
case, and differing versions and DOIs go to the review file:

```cmd
comet-rs export amt-engine.connoss.json amt-runner.connoss.json --format wikidata --item Q74003194 --label "Academic Meta Tool (AMT)" --output amt.qs
```

Without `--item`, `wikidata` creates a new chublet with its identity block and `--format chublet-ttl`
uses a candidate IRI. Search Wikidata for the repository URL (P1324) first.

## Rules

A value becomes a statement only if it has provenance, is not an LLM value, reaches `--threshold`
(default 0.9) and maps to a checked identifier. Everything else is written to the `--review` file with a
reason. Persons, publications and keywords always go there, because they need reconciliation. The release
tag wins over `softwareVersion`, because a CITATION.cff can lag behind the releases, and only the main
language is exported.

Extend `vocabulary.py` only with identifiers that have been checked. Extractions without a name or
repository are refused, because a rate-limited run ends with a normal exit code and an empty record.
