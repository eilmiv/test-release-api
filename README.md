# test-release-api

Tests whether GitHub Release assets and GitHub Pages preserve a custom MIME type for OWL/RDF files.

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
   - Create a GitHub Release for the tag.
   - Upload `example.owl` as a release asset with content type `application/rdf+xml`.

## Downloading the OWL file

After a release has been created you can download the asset directly:

```
https://github.com/eilmiv/test-release-api/releases/download/v1.0.0/example.owl
```

Replace `v1.0.0` with the actual tag you created.

If GitHub served the asset as `application/rdf+xml`, rdflib could parse it directly:

```python
from rdflib import Graph

g = Graph()
g.parse("https://github.com/eilmiv/test-release-api/releases/download/v1.0.0/example.owl")
print(list(g))
```

## Test Result (v1.0.0)

Status: **Failed**

Observed behavior for release `v1.0.0`:

- GitHub Release API asset metadata reports `content_type: application/rdf+xml`.
- The actual download response header is `content-type: application/octet-stream`.

Conclusion:

GitHub currently does not preserve or serve custom MIME types for release asset downloads in this flow, and serves the file as `application/octet-stream`.

## GitHub Pages Alternative

As an alternative to GitHub Releases, the same `example.owl` file is deployed to GitHub Pages.
The GitHub Pages workflow (`.github/workflows/pages.yml`) runs on every push to `main` and publishes
the contents of the `docs/` directory.

### Accessing the file via GitHub Pages

The OWL file is available at:

```
https://eilmiv.github.io/test-release-api/example.owl
```

You can test it with rdflib:

```python
from rdflib import Graph

g = Graph()
g.parse("https://eilmiv.github.io/test-release-api/example.owl")
print(list(g))
```

### GitHub Pages Test Result

Status: **Failed**

Observed behavior:

- GitHub Pages serves `example.owl` with `content-type: application/octet-stream`.
- The `.owl` extension is not mapped to `application/rdf+xml` by the GitHub Pages CDN (Fastly/nginx).
- As a result, rdflib raises a `PluginException` because it cannot determine the RDF format from the
  `application/octet-stream` content type.

Conclusion:

GitHub Pages also does not serve `.owl` files with the correct `application/rdf+xml` MIME type.
The CDN's MIME type mapping does not include an entry for the `.owl` extension.

### Workaround

Rename (or copy) the file with the `.rdf` extension, which is officially registered with IANA for
`application/rdf+xml` and is included in the MIME type table of most web servers and CDNs:

```
https://eilmiv.github.io/test-release-api/example.rdf
```

```python
from rdflib import Graph

g = Graph()
g.parse("https://eilmiv.github.io/test-release-api/example.rdf")
print(list(g))
```
