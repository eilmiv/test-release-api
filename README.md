# test-release-api

Demonstrates how to set the MIME type of release assets on GitHub so that OWL/RDF files can be parsed directly by tools such as [rdflib](https://rdflib.readthedocs.io/) without receiving an `application/octet-stream` response.

The workflow uploads `example.owl` with the content type `application/rdf+xml`, which rdflib recognises natively.

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

Because the asset is served with the `application/rdf+xml` content type, rdflib can parse it without errors:

```python
from rdflib import Graph

g = Graph()
g.parse("https://github.com/eilmiv/test-release-api/releases/download/v1.0.0/example.owl")
print(list(g))
```
