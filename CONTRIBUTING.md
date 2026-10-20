# Contributing to AgentAxiom

## Local development

```bash
python -m pip install -e '.[test,lint]'
python -m pytest
python -m ruff check src tests
```

All behavior changes need a regression test. Keep all default execution offline. A test that invokes a live model must be opt-in, use an isolated project, declare a bounded maximum cost, and never run in pull-request CI.

## Evidence compatibility

Treat the transcript format and evidence manifest as public compatibility surfaces. Add a `schema_version` migration and fixture whenever changing their semantics. Do not log raw prompts, model responses, secrets, or customer identifiers in tests or issue reports.
