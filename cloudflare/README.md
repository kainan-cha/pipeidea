# Cloudflare Deploy

This folder contains the Cloudflare-native public deployment for Pipeidea.

Scope:

- static frontend
- streaming generation Worker
- read-only bundled soul profiles

Not included:

- calibration
- candidate profile tuning
- local profile creation
- local SQLite/stateful tooling

## Layout

- `worker/` — Worker source, static assets, Wrangler config

## Workflow

1. Build the bundled profile module:

   `python3 scripts/build_profiles_bundle.py`

2. Install Worker tooling:

   `cd cloudflare/worker && npm install`

3. Set secrets:

   `npx wrangler secret put DEEPSEEK_API_KEY`

4. Run locally:

   `npm run dev`

5. Deploy:

   `npm run deploy`
