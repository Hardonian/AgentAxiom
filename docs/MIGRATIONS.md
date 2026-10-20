# Evidence schema migration policy

`schema_version` is a compatibility boundary. A producer must never silently reinterpret an older transcript. A breaking change requires:

1. A new `schemas/transcript.vN.schema.json` file.
2. A fixture for every supported prior version.
3. A pure migration function from each supported version to the current version.
4. Tests proving migrated fixtures retain prompt hashes when turn semantics do not change.
5. A changelog note and one full minor release of overlap before deprecation.

Current status: `v1` is the only released format, so no migration is necessary yet.
