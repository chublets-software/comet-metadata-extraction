# Export examples

Real results of CoMET-RS from 2 and 3 November 2026. They show one tool with one repository and one tool with two
repositories, each as ConnOSS and CodeMeta metadata and as the output of `comet-rs export`.

| Folder | Tool | Wikidata item | Chublet | Statements | Values for review |
|---|---|---|---|---|---|
| [`unicorn`](unicorn) | SPARQLing Unicorn QGIS Plugin | Q74005133 | Q360 | 5 | 11 |
| [`amt`](amt) | Academic Meta Tool | Q74003194 | Q358 | 6 | 21 |

Each folder holds these files, with one extraction per repository:

| File | Content |
|---|---|
| `*.connoss.json` | Extraction with the ConnOSS schema, from `comet-rs extract` |
| `*.codemeta.json` | Extraction with the CodeMeta schema, from `comet-rs extract`, without e-mail addresses |
| `*.qs` | QuickStatements v1 with Wikidata ids, references and retrieval dates |
| `*.ttl` | The chublet in Turtle: direct claims, statement nodes and references, in the RDF shape of the [chublets demo](https://github.com/n4o-rse/chublets-wikibase-demo) |
| `*.review.csv` | Values that were not exported, with the reason |

The review file is part of the result. It holds persons, publications and conflicts, such as a CITATION.cff that
lags behind the latest release, and differing versions of the two AMT repositories.

These files have not been applied to Wikidata or to the demo. The statements in them are proposals for curation.

## Reproducing

Install the fork as described in the main [README](../README.md) and set `GITHUB_TOKEN`: a rate-limited extraction
ends normally with missing values.

```cmd
comet-rs extract https://github.com/sparqlunicorn/sparqlunicornGoesGIS connoss --with-enrichment > unicorn.connoss.json
comet-rs extract https://github.com/sparqlunicorn/sparqlunicornGoesGIS codemeta --schema-class SoftwareSourceCode --with-enrichment > unicorn.codemeta.json
comet-rs export unicorn.connoss.json --format wikidata --item Q74005133 --retrieved 2026-11-02 --review unicorn.review.csv --output unicorn.qs
comet-rs export unicorn.connoss.json --format chublet-ttl --local-item Q360 --item Q74005133 --retrieved 2026-11-02 --output unicorn.ttl
```

For AMT, both extractions go into one export:

```cmd
comet-rs extract https://github.com/alpaca-fair-framework/amt-engine connoss --with-enrichment > amt-engine.connoss.json
comet-rs extract https://github.com/n4o-rse/amt-runner connoss --with-enrichment > amt-runner.connoss.json
comet-rs extract https://github.com/alpaca-fair-framework/amt-engine codemeta --schema-class SoftwareSourceCode --with-enrichment > amt-engine.codemeta.json
comet-rs extract https://github.com/alpaca-fair-framework/amt-runner codemeta --schema-class SoftwareSourceCode --with-enrichment > amt-runner.codemeta.json
comet-rs export amt-engine.connoss.json amt-runner.connoss.json --format wikidata --item Q74003194 --label "Academic Meta Tool (AMT)" --retrieved 2026-11-02 --review amt.review.csv --output amt.qs
comet-rs export amt-engine.connoss.json amt-runner.connoss.json --format chublet-ttl --local-item Q358 --item Q74003194 --label "Academic Meta Tool (AMT)" --description "ontology and webapp for modelling vagueness in graphs including reasoning" --retrieved 2026-11-02 --output amt.ttl
```

Values from a new extraction can differ when a repository has changed. The rules behind the export are in
[`backend-migration/app/exporters/README.md`](../backend-migration/app/exporters/README.md).

## AI usage

Parts of the export code were written with the assistance of Claude (Anthropic) and are supervised by Florian Thiery.
