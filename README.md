# test-release-api

Tests whether GitHub Release assets and GitHub Pages preserve a custom MIME type for OWL/RDF files.

The single source of truth for the ontology is `example.owl` in the repository root.
On every release the CI generates an additional `example.ttl` (Turtle format) and publishes
both formats as release assets and to GitHub Pages under a versioned path.

**GitHub Releases:** The workflow uploads `example.owl` with `application/rdf+xml`, but the final download is still served as `application/octet-stream`.

**GitHub Pages:** The same files are deployed via GitHub Pages where the MIME type is correct.

## Setup overview

- Canonical source: [`example.owl`](example.owl) is the only file you edit by hand.
- Release build: on a pushed tag matching `v*`, [`release.yml`](.github/workflows/release.yml) installs `rdflib`, converts OWL (RDF/XML) to Turtle, and generates `example.ttl`.
- Release assets: the same workflow creates the GitHub Release and uploads both `example.owl` and `example.ttl` as assets with explicit content types.
- Pages deployment trigger: [`pages.yml`](.github/workflows/pages.yml) runs after the `Release` workflow completes successfully (`workflow_run`) and can also run on `main` pushes/manual dispatch.
   - Pages are rebuilt from GitHub Release assets (downloaded with `gh release download`)
- Version layout: for each release tag, files are placed at `/{version}/example.owl` and `/{version}/example.ttl`; the release marked as latest is also copied to `/latest/...`.
- Pages entry page: [`docs/index.html`](docs/index.html) is copied to the site root as `_site/index.html` during deployment.
- Library compatibility report: [`rdf-library-compatibility-report.yml`](.github/workflows/rdf-library-compatibility-report.yml) runs after a successful Pages deployment (or manually) and uploads a Markdown/JSON artifact comparing RDF library behavior for Release URLs vs Pages URLs.

This keeps release downloads and GitHub Pages content aligned from one source while providing stable, versioned URLs.

## How to create a release

1. Clone the repository:
   ```bash
   git clone https://github.com/eilmiv/test-release-api.git
   cd test-release-api
   ```

2. Create and push a version tag (the workflow triggers on tags matching `v*`):
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. GitHub Actions will automatically:
   - Generate `example.ttl` (Turtle) from `example.owl` (RDF/XML).
   - Create a GitHub Release for the tag.
   - Upload `example.owl` (content type `application/rdf+xml`) and `example.ttl` (content type `text/turtle`) as release assets.
   - Trigger a GitHub Pages deployment workflow that rebuilds the site from release assets.

## Download URL patterns

### GitHub Releases

Content is always served as `application/octet-stream` even though api confirms the `content_type` is `application/rdf+xml`.

| File | Versioned URL | Latest URL |
|------|--------------|------------|
| `example.owl` | `https://github.com/eilmiv/test-release-api/releases/download/{version}/example.owl` | `https://github.com/eilmiv/test-release-api/releases/latest/download/example.owl` |
| `example.ttl` | `https://github.com/eilmiv/test-release-api/releases/download/{version}/example.ttl` | `https://github.com/eilmiv/test-release-api/releases/latest/download/example.ttl` |

Replace `{version}` with the tag name, e.g. `v2.0.0`.

### GitHub Pages

Content is served with correct mime type. [Go to pages index.html.](https://eilmiv.github.io/test-release-api/)

| File | Versioned URL | Latest URL |
|------|--------------|------------|
| `example.owl` | `https://eilmiv.github.io/test-release-api/{version}/example.owl` | `https://eilmiv.github.io/test-release-api/latest/example.owl` |
| `example.ttl` | `https://eilmiv.github.io/test-release-api/{version}/example.ttl` | `https://eilmiv.github.io/test-release-api/latest/example.ttl` |

Replace `{version}` with the tag name, e.g. `v2.0.0`.

## rdflib example

```python
from rdflib import Graph

# Expected: fails for Release download URL.
Graph().parse("https://github.com/eilmiv/test-release-api/releases/download/v2.0.1/example.owl")

# Expected: succeeds for GitHub Pages URL.
Graph().parse("https://eilmiv.github.io/test-release-api/v2.0.1/example.owl")
```

## Library compatibility report

The repository includes a workflow-driven compatibility suite for these libraries:

- RDFLib (Python)
- Apache Jena (Java)
- Eclipse RDF4J (Java)
- rdf-dereference (JavaScript)
- Redland librdf via `rapper` (C)

Each run checks both `example.owl` and `example.ttl` against:

- GitHub Release download URLs, which redirect to a generic `application/octet-stream` response
- GitHub Pages URLs, which keep the RDF-specific MIME type

The workflow uploads an artifact named `rdf-library-compatibility-report-{tag}` containing:

- `rdf-library-compatibility-report.md`
- `rdf-library-compatibility-results.json`

