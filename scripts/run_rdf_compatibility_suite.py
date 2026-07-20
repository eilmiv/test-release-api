#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

RDFLIB_VERSION = "7.6.0"
JENA_VERSION = "5.3.0"
RDF4J_VERSION = "5.1.3"
RDF_DEREFERENCE_VERSION = "5.0.0"


@dataclass
class UrlCase:
    key: str
    label: str
    url: str


@dataclass
class UrlProbe:
    original_url: str
    final_url: str
    content_type: str


@dataclass
class LibraryRun:
    success: bool
    exit_code: int
    elapsed_seconds: float
    triples: int | None
    summary: str
    stdout: str
    stderr: str


def run_command(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=True,
        text=True,
    )


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def probe_url(url: str) -> UrlProbe:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/rdf+xml, text/turtle;q=0.9, */*;q=0.1",
            "User-Agent": "test-release-api-rdf-compatibility-suite",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        response.read(0)
        return UrlProbe(
            original_url=url,
            final_url=response.geturl(),
            content_type=response.headers.get("Content-Type", "").strip() or "unknown",
        )


def parse_triples(stdout: str, stderr: str) -> int | None:
    for stream in (stdout, stderr):
        for line in reversed([line.strip() for line in stream.splitlines() if line.strip()]):
            if line.isdigit():
                return int(line)
            match = re.search(r"returned\s+(\d+)\s+triples", line)
            if match:
                return int(match.group(1))
    return None


def summarize_failure(stdout: str, stderr: str) -> str:
    lines = [line.strip() for line in (stderr + "\n" + stdout).splitlines() if line.strip()]
    for line in lines:
        if any(token in line for token in ("Exception", "Error", "failed", "Unsupported", "PluginException")):
            return line
    return lines[0] if lines else "Command failed without output"


def summarize_success(triples: int | None) -> str:
    return f"{triples} triples parsed" if triples is not None else "Parsed successfully"


class LibraryRunner:
    id: str
    name: str
    language: str
    version: str

    def setup(self, root: Path) -> None:
        raise NotImplementedError

    def invoke(self, url: str) -> subprocess.CompletedProcess[str]:
        raise NotImplementedError

    def run(self, url: str) -> LibraryRun:
        started = time.monotonic()
        result = self.invoke(url)
        elapsed = time.monotonic() - started
        triples = parse_triples(result.stdout, result.stderr)
        if result.returncode == 0:
            return LibraryRun(
                success=True,
                exit_code=result.returncode,
                elapsed_seconds=round(elapsed, 3),
                triples=triples,
                summary=summarize_success(triples),
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return LibraryRun(
            success=False,
            exit_code=result.returncode,
            elapsed_seconds=round(elapsed, 3),
            triples=triples,
            summary=summarize_failure(result.stdout, result.stderr),
            stdout=result.stdout,
            stderr=result.stderr,
        )


class RdflibRunner(LibraryRunner):
    id = "rdflib"
    name = "RDFLib"
    language = "Python"
    version = RDFLIB_VERSION

    def setup(self, root: Path) -> None:
        self.workdir = root / self.id
        self.venv = self.workdir / "venv"
        run_command([sys.executable, "-m", "venv", str(self.venv)], cwd=root)
        python = self.venv / "bin" / "python"
        run_command([str(python), "-m", "pip", "install", "--quiet", f"rdflib=={self.version}"], cwd=root)
        self.python = python

    def invoke(self, url: str) -> subprocess.CompletedProcess[str]:
        code = (
            "from rdflib import Graph; "
            "import sys; "
            "graph = Graph(); "
            "graph.parse(sys.argv[1]); "
            "print(len(graph))"
        )
        return run_command([str(self.python), "-c", code, url], check=False)


class JenaRunner(LibraryRunner):
    id = "apache-jena"
    name = "Apache Jena"
    language = "Java"
    version = JENA_VERSION

    def setup(self, root: Path) -> None:
        self.workdir = root / self.id
        self.workdir.mkdir(parents=True, exist_ok=True)
        write_file(
            self.workdir / "pom.xml",
            f"""\
            <project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
              <modelVersion>4.0.0</modelVersion>
              <groupId>local</groupId>
              <artifactId>jena-compat-check</artifactId>
              <version>1.0.0</version>
              <dependencies>
                <dependency>
                  <groupId>org.apache.jena</groupId>
                  <artifactId>apache-jena-libs</artifactId>
                  <version>{self.version}</version>
                  <type>pom</type>
                </dependency>
              </dependencies>
            </project>
            """,
        )
        write_file(
            self.workdir / "CheckUrl.java",
            """\
            import org.apache.jena.rdf.model.Model;
            import org.apache.jena.rdf.model.ModelFactory;
            import org.apache.jena.riot.RDFParser;

            public class CheckUrl {
              public static void main(String[] args) {
                Model model = ModelFactory.createDefaultModel();
                RDFParser.source(args[0]).parse(model);
                System.out.println(model.size());
              }
            }
            """,
        )
        run_command(["mvn", "-q", "dependency:build-classpath", "-Dmdep.outputFile=cp.txt"], cwd=self.workdir)
        classpath = (self.workdir / "cp.txt").read_text(encoding="utf-8").strip()
        run_command(["javac", "-cp", classpath, "CheckUrl.java"], cwd=self.workdir)
        self.classpath = f".:{classpath}"

    def invoke(self, url: str) -> subprocess.CompletedProcess[str]:
        return run_command(["java", "-cp", self.classpath, "CheckUrl", url], cwd=self.workdir, check=False)


class Rdf4jRunner(LibraryRunner):
    id = "eclipse-rdf4j"
    name = "Eclipse RDF4J"
    language = "Java"
    version = RDF4J_VERSION

    def setup(self, root: Path) -> None:
        self.workdir = root / self.id
        self.workdir.mkdir(parents=True, exist_ok=True)
        write_file(
            self.workdir / "pom.xml",
            f"""\
            <project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
              <modelVersion>4.0.0</modelVersion>
              <groupId>local</groupId>
              <artifactId>rdf4j-compat-check</artifactId>
              <version>1.0.0</version>
              <dependencies>
                <dependency>
                  <groupId>org.eclipse.rdf4j</groupId>
                  <artifactId>rdf4j-repository-api</artifactId>
                  <version>{self.version}</version>
                </dependency>
                <dependency>
                  <groupId>org.eclipse.rdf4j</groupId>
                  <artifactId>rdf4j-rio-rdfxml</artifactId>
                  <version>{self.version}</version>
                </dependency>
                <dependency>
                  <groupId>org.eclipse.rdf4j</groupId>
                  <artifactId>rdf4j-rio-turtle</artifactId>
                  <version>{self.version}</version>
                </dependency>
              </dependencies>
            </project>
            """,
        )
        write_file(
            self.workdir / "CheckUrl.java",
            """\
            import java.net.URL;
            import org.eclipse.rdf4j.model.impl.SimpleValueFactory;
            import org.eclipse.rdf4j.repository.util.RDFLoader;
            import org.eclipse.rdf4j.rio.ParserConfig;
            import org.eclipse.rdf4j.rio.helpers.StatementCollector;

            public class CheckUrl {
              public static void main(String[] args) throws Exception {
                RDFLoader loader = new RDFLoader(new ParserConfig(), SimpleValueFactory.getInstance());
                StatementCollector collector = new StatementCollector();
                loader.load(new URL(args[0]), null, null, collector);
                System.out.println(collector.getStatements().size());
              }
            }
            """,
        )
        run_command(["mvn", "-q", "dependency:build-classpath", "-Dmdep.outputFile=cp.txt"], cwd=self.workdir)
        classpath = (self.workdir / "cp.txt").read_text(encoding="utf-8").strip()
        run_command(["javac", "-cp", classpath, "CheckUrl.java"], cwd=self.workdir)
        self.classpath = f".:{classpath}"

    def invoke(self, url: str) -> subprocess.CompletedProcess[str]:
        return run_command(["java", "-cp", self.classpath, "CheckUrl", url], cwd=self.workdir, check=False)


class RdfDereferenceRunner(LibraryRunner):
    id = "rdf-dereference"
    name = "rdf-dereference"
    language = "JavaScript"
    version = RDF_DEREFERENCE_VERSION

    def setup(self, root: Path) -> None:
        self.workdir = root / self.id
        self.workdir.mkdir(parents=True, exist_ok=True)
        run_command(["npm", "init", "-y"], cwd=self.workdir)
        run_command(["npm", "install", f"rdf-dereference@{self.version}"], cwd=self.workdir)
        write_file(
            self.workdir / "check.mjs",
            """\
            import { rdfDereferencer } from "rdf-dereference";

            const response = await rdfDereferencer.dereference(process.argv[2]);
            let count = 0;
            await new Promise((resolve, reject) => {
              response.data.on("data", () => { count += 1; });
              response.data.on("error", reject);
              response.data.on("end", resolve);
            });
            console.log(count);
            """,
        )

    def invoke(self, url: str) -> subprocess.CompletedProcess[str]:
        return run_command(["node", "check.mjs", url], cwd=self.workdir, check=False)


class RedlandRunner(LibraryRunner):
    id = "redland-librdf"
    name = "Redland librdf (rapper)"
    language = "C"
    version = "system package"

    def setup(self, root: Path) -> None:
        del root
        if shutil.which("rapper") is None:
            raise RuntimeError("rapper is not installed. Install raptor2-utils before running this suite.")
        result = run_command(["dpkg-query", "-W", "-f=${Version}", "raptor2-utils"], check=False)
        if result.returncode == 0 and result.stdout.strip():
            self.version = result.stdout.strip()

    def invoke(self, url: str) -> subprocess.CompletedProcess[str]:
        return run_command(["rapper", "-i", "guess", "-c", url], check=False)


def classify(results: dict[str, LibraryRun]) -> str:
    release_keys = [key for key in results if key.startswith("release-")]
    pages_keys = [key for key in results if key.startswith("pages-")]
    release_success = all(results[key].success for key in release_keys)
    pages_success = all(results[key].success for key in pages_keys)
    any_release_success = any(results[key].success for key in release_keys)
    if release_success:
        return "Supports GitHub Release download URLs with generic MIME type"
    if not any_release_success and pages_success:
        return "Requires GitHub Pages URL with correct MIME type"
    return "Mixed behavior across tested URLs"


def format_cell(result: LibraryRun) -> str:
    if result.success:
        return f"✅ {result.summary}"
    return f"❌ {result.summary.replace('|', '\\|')}"


def build_report(
    cases: list[UrlCase],
    probes: dict[str, UrlProbe],
    results: list[dict[str, object]],
) -> str:
    supports = [entry["name"] for entry in results if entry["verdict"].startswith("Supports")]
    requires_pages = [entry["name"] for entry in results if entry["verdict"].startswith("Requires")]
    mixed = [entry["name"] for entry in results if entry["verdict"].startswith("Mixed")]
    lines = [
        "# RDF library compatibility report",
        "",
        "This report compares GitHub Release download URLs that resolve to a generic MIME type with GitHub Pages URLs that keep the RDF MIME type.",
        "",
        "## URL probes",
        "",
        "| Case | Content-Type after redirects | Final URL |",
        "| --- | --- | --- |",
    ]
    for case in cases:
        probe = probes[case.key]
        lines.append(f"| {case.label} | `{probe.content_type}` | `{probe.final_url}` |")

    lines.extend(
        [
            "",
            "## Compatibility summary",
            "",
            f"- Supports GitHub Release download URLs with generic MIME type: {', '.join(supports) if supports else 'none'}",
            f"- Requires GitHub Pages URL with correct MIME type: {', '.join(requires_pages) if requires_pages else 'none'}",
            f"- Mixed behavior across tested URLs: {', '.join(mixed) if mixed else 'none'}",
            "",
            "## Library results",
            "",
            "| Library | Language | Version | Release OWL | Pages OWL | Release TTL | Pages TTL | Verdict |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for entry in results:
        by_case = entry["results"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(entry["name"]),
                    str(entry["language"]),
                    f"`{entry['version']}`",
                    format_cell(by_case["release-owl"]),
                    format_cell(by_case["pages-owl"]),
                    format_cell(by_case["release-ttl"]),
                    format_cell(by_case["pages-ttl"]),
                    str(entry["verdict"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def build_cases(args: argparse.Namespace) -> list[UrlCase]:
    return [
        UrlCase("release-owl", "Release example.owl", args.release_url_owl),
        UrlCase("pages-owl", "Pages example.owl", args.pages_url_owl),
        UrlCase("release-ttl", "Release example.ttl", args.release_url_ttl),
        UrlCase("pages-ttl", "Pages example.ttl", args.pages_url_ttl),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RDF library URL compatibility checks.")
    parser.add_argument("--release-url-owl", required=True)
    parser.add_argument("--pages-url-owl", required=True)
    parser.add_argument("--release-url-ttl", required=True)
    parser.add_argument("--pages-url-ttl", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = build_cases(args)
    probes = {case.key: probe_url(case.url) for case in cases}
    libraries: list[LibraryRunner] = [
        RdflibRunner(),
        JenaRunner(),
        Rdf4jRunner(),
        RdfDereferenceRunner(),
        RedlandRunner(),
    ]

    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="rdf-compat-suite-") as root_name:
        root = Path(root_name)
        for library in libraries:
            library.setup(root)
            case_results = {case.key: library.run(case.url) for case in cases}
            results.append(
                {
                    "id": library.id,
                    "name": library.name,
                    "language": library.language,
                    "version": library.version,
                    "verdict": classify(case_results),
                    "results": case_results,
                }
            )

    report = build_report(cases, probes, results)
    (output_dir / "rdf-library-compatibility-report.md").write_text(report, encoding="utf-8")
    (output_dir / "rdf-library-compatibility-results.json").write_text(
        json.dumps(
            {
                "cases": [asdict(case) for case in cases],
                "probes": {key: asdict(value) for key, value in probes.items()},
                "libraries": [
                    {
                        **{key: value for key, value in entry.items() if key != "results"},
                        "results": {key: asdict(value) for key, value in entry["results"].items()},
                    }
                    for entry in results
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
