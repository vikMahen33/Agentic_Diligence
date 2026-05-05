---
name: sync-guidepoint-library
description: Builds or updates the local Guidepoint transcript metadata catalog scoped to Healthcare, North America, English. Run once after installation, then weekly to add new transcripts. Use --full to rebuild from scratch.
---

# Guidepoint Library Sync

You are syncing the local Guidepoint transcript metadata catalog for the ai-labor-risk plugin.

The catalog stores compact metadata (title, expert roles, agenda, highlights, tickers) for all US Healthcare transcripts — no download URLs, which expire in 15 minutes. The per-analysis library agent reads this catalog to find relevant transcripts without hitting the API on every run.

## Arguments

Parse `$ARGUMENTS`:
- `--full` flag present → sync_mode = `full` (rebuild catalog from 3 years ago)
- No flag → sync_mode = `incremental` (only new entries since last sync)

## Step 1 — Check API Key

Verify the shipped key config file exists at `${CLAUDE_PLUGIN_ROOT}/data/api_keys.json` and contains `guidepoint_api_key`. The sync agent reads from this file directly (with `${user_config.guidepoint_api_key}` as primary attempt and the file as fallback for fresh installs).

```bash
python3 -c "
import json
with open('${CLAUDE_PLUGIN_ROOT}/data/api_keys.json') as f:
    keys = json.load(f)
assert keys.get('guidepoint_api_key'), 'guidepoint_api_key missing'
print('ok')
"
```

If this fails:
```
ERROR: Shipped API keys file not found or missing guidepoint_api_key.
Re-install plugin from the distribution zip.
```
Stop.

## Step 2 — Determine Sync Mode

Read `${CLAUDE_PLUGIN_DATA}/guidepoint-catalog.json` if it exists.

- If `--full` or catalog doesn't exist → sync_mode = `full`
- Otherwise → sync_mode = `incremental`

Show the analyst what you're about to do:
```
Guidepoint Library Sync
─────────────────────────────────────────────
Mode:     {full (first-time build) / incremental (adding new entries)}
Catalog:  ${CLAUDE_PLUGIN_DATA}/guidepoint-catalog.json
{If incremental: "Last synced: {last_synced date} — fetching transcripts since then"}
{If full: "Fetching all Healthcare transcripts from the past 3 years"}

This may take several minutes for a full build. Starting now...
─────────────────────────────────────────────
```

## Step 3 — Run Sync Agent

Invoke `guidepoint-catalog-sync` with:
- subscription_key: `${user_config.guidepoint_api_key}`
- catalog_path: `${CLAUDE_PLUGIN_DATA}/guidepoint-catalog.json`
- sync_mode: `{full or incremental}`

## Step 4 — Done

The sync agent reports its own completion summary. Add:
```
To use in an analysis: answer Yes to Question C when running /ai-labor-risk:analyze-subsegment
To sync again next week: /ai-labor-risk:sync-guidepoint-library
To force a full rebuild:  /ai-labor-risk:sync-guidepoint-library --full
```
