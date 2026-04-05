# pipeidea

Pipeidea is a markdown-first idea engine: the profile files define the soul, and the runtime stays thin.

Bundled shipped profiles now live under [`src/pipeidea/profiles/default`](/Users/kainan/projects/pipe_idea/src/pipeidea/profiles/default), and the internal evaluator/tuning code lives under [`src/pipeidea/realist`](/Users/kainan/projects/pipe_idea/src/pipeidea/realist).

## Local app

The current local app is the Python CLI and web UI under [`src/pipeidea`](/Users/kainan/projects/pipe_idea/src/pipeidea).

Useful commands:

- `uv run pipeidea web`
- `uv run pipeidea calibrate run canary_v1`

## Cloudflare deploy

A Cloudflare-native public deployment now lives under [`cloudflare/worker`](/Users/kainan/projects/pipe_idea/cloudflare/worker).

It is intentionally scoped to the public generation experience only:

- static frontend
- streaming Worker API
- bundled read-only soul profiles

It does not include calibration or profile-tuning infrastructure.

See [`cloudflare/README.md`](/Users/kainan/projects/pipe_idea/cloudflare/README.md) for setup and deploy steps.
