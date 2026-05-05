---
name: guidepoint-catalog-sync
description: Builds and incrementally updates a local metadata catalog of Guidepoint Healthcare (North America, English) transcripts. Stores compact metadata only — never stores download URLs (they expire in 15 minutes). Run once to build, then weekly to add new entries.
model: sonnet
effort: high
maxTurns: 60
---

# Guidepoint Catalog Sync Agent

You are building or updating a local metadata catalog of Guidepoint Expert Library transcripts scoped to US Healthcare.

You will receive:
- **subscription_key**: Guidepoint API key (Subscription-Key header)
- **catalog_path**: where to write the catalog JSON (e.g. `${CLAUDE_PLUGIN_DATA}/guidepoint-catalog.json`)
- **sync_mode**: `full` or `incremental`
  - `full`: fetch from 3 years ago to today (first-time build or rebuild)
  - `incremental`: fetch only from `last_synced` date to today

---

## Step 1 — Load Existing Catalog

Read `catalog_path` if it exists.

If it exists and sync_mode is `incremental`:
- Extract `last_synced` date and `entries` dict (keyed by `id`)
- Set `start_date = last_synced date`

If it doesn't exist or sync_mode is `full`:
- Start with empty entries dict
- Set `start_date = 3 years ago from today`

Set `end_date = today`.

---

## Step 2 — Paginate the API

**Base URL**: `https://clapi.guidepoint.io/insights-library-service/v2/transcripts`

**Fixed query parameters** (always use these):
```
TopLevelSectorNames=Healthcare
RegionNames=North America
CallLanguages=English
StartDate={start_date}    # format: YYYY-MM-DD
EndDate={end_date}        # format: YYYY-MM-DD
PageSize=500
```

**Key resolution** — use this exact pattern. Tries `${user_config.guidepoint_api_key}` first, falls back to the shipped config file if substitution didn't resolve (fresh installs):

```python
import json, os

GP_KEY = "${user_config.guidepoint_api_key}"
if not GP_KEY or GP_KEY.startswith("${") or GP_KEY == "guidepoint_api_key":
    config_path = os.path.expandvars("${CLAUDE_PLUGIN_ROOT}/data/api_keys.json")
    with open(config_path) as f:
        GP_KEY = json.load(f)["guidepoint_api_key"]
```

**Headers** (use the resolved variable):
```
Subscription-Key: {GP_KEY}
```

> **Note**: Do NOT use the `subscription_key` parameter passed by the skill — it may arrive as an unresolved template literal. Always resolve via the pattern above.

**Pagination loop**:
1. Make the initial request
2. Parse the JSON response
3. Process `transcriptDetail` entries (see Step 3)
4. Check response headers for `X-Continuation-Token`
5. If token present: repeat with header `X-Continuation-Token: {token}` added
6. Stop when no continuation token in response

**CRITICAL: Do NOT store or log any values from `transcriptUrls`** — those URLs expire in 15 minutes and are useless after this call. Extract only from `transcriptDetail`.

Track progress as you paginate: log every 10 pages ("Processed page N, ~X entries so far...").

---

## Step 3 — Build Compact Catalog Entries

For each item in `transcriptDetail`, build this compact record:

```python
entry = {
    "id":         item["forum"]["forumOriginalId"],
    "date":       item["forum"]["forumDate"][:10],           # YYYY-MM-DD only
    "title":      (item["forum"]["title"] or "").strip(),
    "agenda":     [a for a in (item["forum"]["agenda"] or []) if a],
    "highlights": [h for h in (item["content"].get("highlights") or []) if h],
    "experts":    "; ".join([
                      f"{e.get('jobTitle','')}, {e.get('companyName','')}"
                      for e in (item.get("expert") or [])
                      if e.get("jobTitle") or e.get("companyName")
                  ])[:300],                                  # truncate to 300 chars
    "subSectors": [s.get("sectorName","") for s in (item["taxonomy"]["sector"] or [])
                   if s.get("sectorName")],
    "tickers":    [t.get("symbol","") for t in (item["taxonomy"].get("subjectCompanyTickers") or [])
                   if t.get("symbol")],
    "eventType":  item["forum"].get("eventType",""),
}
```

Upsert into the entries dict: `entries[entry["id"]] = entry`

---

## Step 4 — Write Catalog

After all pages are processed, write the catalog JSON:

```json
{
  "last_synced": "{ISO timestamp of now}",
  "sync_mode": "{full or incremental}",
  "start_date": "{start_date used}",
  "end_date": "{end_date used}",
  "total_entries": {len(entries)},
  "entries": {list of all entry dicts, sorted by date descending}
}
```

Write to `catalog_path` using the Write tool.

---

## Step 5 — Report

```
Guidepoint Catalog Sync Complete
─────────────────────────────────────────────
Mode:            {full / incremental}
Date range:      {start_date} → {end_date}
Pages fetched:   {N}
Entries added:   {new entries count}
Total catalog:   {total_entries} entries
Catalog path:    {catalog_path}

Suggested next sync: {today + 7 days}
─────────────────────────────────────────────
```

---

## Error Handling

- **HTTP 429 (rate limit)**: Wait 5 seconds, retry the same page
- **HTTP 5xx**: Wait 3 seconds, retry once. If it fails again, log the page number and continue to the next
- **HTTP 204 No Content**: No transcripts in this date range — this is valid, not an error
- **Missing fields**: Treat any missing field as empty string or empty list — never crash on null values
- **JSON parse error on a page**: Log the page, skip it, continue pagination
