# pipeidea

pipeidea is a markdown-driven idea engine. The core design keeps creative taste in profile files and keeps the runtime focused on prompt assembly, provider dispatch, and evaluation.

## CLI usage

The main entry point is the `pipeidea` CLI:

```bash
uv run pipeidea bloom "new kinds of urban food rituals"
uv run pipeidea collide "public libraries" "time banking"
uv run pipeidea profile list
uv run pipeidea calibrate run canary_v1
```

Useful command groups:

- `bloom`: generate ideas from a single seed
- `collide`: force two inputs into the same mechanism space
- `profile`: inspect or create profile overrides
- `calibrate`: run internal evaluation against seed packs and rubrics

## Sample usage

```bash
uv run pipeidea bloom "a social product that makes waiting in line meaningful"
```


