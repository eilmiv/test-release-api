# test-release-api

Tests whether GitHub Release assets preserve a custom MIME type for OWL/RDF files.

The workflow uploads `example.owl` with `application/rdf+xml`, but the final download is still served as `application/octet-stream`.

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
