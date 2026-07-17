# test-release-api

Tests whether GitHub Release assets and GitHub Pages preserve a custom MIME type for OWL/RDF files.

The single source of truth for the ontology is `example.owl` in the repository root.
On every release the CI generates an additional `example.ttl` (Turtle format) and publishes
both formats as release assets and to GitHub Pages under a versioned path.

**GitHub Releases:** The workflow uploads `example.owl` with `application/rdf+xml`, but the final download is still served as `application/octet-stream`.

**GitHub Pages:** The same file is deployed via GitHub Pages (see [GitHub Pages section](#github-pages-alternative)) where the MIME type is correct.

## Setup overview

- `example.owl` in the repository root is the canonical source file.
- When you push a release tag (`v*`), CI converts `example.owl` to `example.ttl` and publishes both files as release assets.
- The Pages deployment then copies the same released artifacts into:
   - `/{version}/...` for immutable versioned files
   - `/latest/...` as a moving alias to the newest release

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

Replace `{version}` with the tag name, e.g. `v1.0.0`.


