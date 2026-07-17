# test-release-api

Tests whether GitHub Release assets and GitHub Pages preserve a custom MIME type for OWL/RDF files.

The single source of truth for the ontology is `example.owl` in the repository root.
On every release the CI generates an additional `example.ttl` (Turtle format) and publishes
both formats as release assets and to GitHub Pages under a versioned path.

**GitHub Releases:** The workflow uploads `example.owl` with `application/rdf+xml`, but the final download is still served as `application/octet-stream`.

**GitHub Pages:** The same file is deployed via GitHub Pages (see [GitHub Pages section](#github-pages-alternative)) to test whether the correct MIME type is preserved there.

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
   - Fail the Pages deployment if required assets for `latest/` are missing.

## Download URL patterns

### GitHub Releases

| File | Versioned URL | Latest URL |
|------|--------------|------------|
| `example.owl` | `https://github.com/eilmiv/test-release-api/releases/download/{version}/example.owl` | `https://github.com/eilmiv/test-release-api/releases/latest/download/example.owl` |
| `example.ttl` | `https://github.com/eilmiv/test-release-api/releases/download/{version}/example.ttl` | `https://github.com/eilmiv/test-release-api/releases/latest/download/example.ttl` |

Replace `{version}` with the tag name, e.g. `v1.0.0`.

### GitHub Pages

| File | Versioned URL | Latest URL |
|------|--------------|------------|
| `example.owl` | `https://eilmiv.github.io/test-release-api/{version}/example.owl` | `https://eilmiv.github.io/test-release-api/latest/example.owl` |
| `example.ttl` | `https://eilmiv.github.io/test-release-api/{version}/example.ttl` | `https://eilmiv.github.io/test-release-api/latest/example.ttl` |

Replace `{version}` with the tag name, e.g. `v1.0.0`.

## Test Result (v1.0.0)

Status: **Failed** (GitHub Releases) / **Passed** (GitHub Pages)

Observed behavior for release `v1.0.0`:

- GitHub Release API asset metadata reports `content_type: application/rdf+xml`.
- The actual download response header is `content-type: application/octet-stream`.

Conclusion:

GitHub currently does not preserve or serve custom MIME types for release asset downloads in this flow, and serves the file as `application/octet-stream`.

## GitHub Pages Alternative

As an alternative to GitHub Releases, the same `example.owl` file is deployed to GitHub Pages.
The GitHub Pages workflow (`.github/workflows/pages.yml`) rebuilds and deploys from release assets
after the `Release` workflow completes successfully (`workflow_run`).

The same Pages workflow is also available for manual rebuilds (`workflow_dispatch`) and pushes to `main`.

### GitHub Pages Test Result

Status: **Passed**

Observed behavior:

- GitHub Pages serves `example.owl` with `content-type: application/rdf+xml`.
- `rdflib` can parse the URL directly without requiring an alternate extension.

Conclusion:

GitHub Pages currently serves `.owl` files in this repository with the correct
`application/rdf+xml` MIME type, so an additional `.rdf` copy is not needed.
