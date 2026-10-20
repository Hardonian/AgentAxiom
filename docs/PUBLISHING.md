# PyPI publishing runbook

1. Confirm the desired version in `pyproject.toml`, `CHANGELOG.md`, and a signed Git tag match.
2. In both PyPI and TestPyPI, configure this repository’s release workflow as a Trusted Publisher. Do not create or store API tokens.
3. Run **Publish to TestPyPI** from a protected `testpypi` environment.
4. In a new virtual environment, install the TestPyPI artifact with its dependency index and run `agentaxiom --help` plus the offline fixture smoke check.
5. Approve the 100-item gate, create a GitHub release from the immutable tag, and let **Publish to PyPI** build, SBOM, attest, and publish.
6. Verify the PyPI artifact hash, provenance attestation, package metadata, and clean install. Announce only after verification.

The release workflows require a GitHub environment, a configured Trusted Publisher, and an authorized release owner. They intentionally cannot publish from a developer workstation.
