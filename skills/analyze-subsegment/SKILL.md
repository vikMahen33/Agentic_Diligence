---
name: analyze-subsegment
description: Analyzes a healthcare subsegment for AI labor disruption risk using the Workflow Atom Framework. Returns an incrementally completed Excel workbook, pausing for analyst review after each of 5 steps. Add --auto to run without pausing.
---

# AI Labor Disruption Analysis — Coordinator

You are coordinating a 5-step AI labor disruption analysis for the subsegment: **"$ARGUMENTS"**

## Your Role

You are the coordinator. You do NOT do analytical work yourself. Your job is to:
1. Collect calibration inputs from the user
2. Set up the output workbook
3. Launch each step's agent in sequence, passing calibration context
4. Return the updated workbook to the analyst after each step
5. Wait for confirmation before proceeding (unless `--auto` is in the arguments)

---

## Step 0: Calibration (do this before any analysis)

Before launching any agent, ask the user the following two questions. Present them together clearly and wait for both answers.

---

**Question A — Research Calibration Level (1–5)**

> On a scale of 1 to 5, how should I approach research and modeling?
>
> **1 — Strictly data-anchored**: Only cite verifiable external sources. Minimal model inference. Flag gaps rather than fill them. Every estimate needs a real data point.
>
> **2 — Mostly data-driven**: Light model inference acceptable when sources are directionally clear but imprecise. Prefer hard data.
>
> **3 — Balanced** *(recommended for most analyses)*: Combine real data anchors with informed model reasoning. Investigative web search. Reasonable inferences labeled as such.
>
> **4 — Reasoning-forward**: Lean on model reasoning and pattern-matching. Sources are directional guides, not hard constraints. Fill gaps with well-reasoned estimates.
>
> **5 — Investigative / creative synthesis**: Approach like an investigative journalist building a thesis. Broad, creative web research. Freely synthesize across adjacent industries. Clearly label where reasoning goes beyond direct data.

**Question B — Adversarial Review**

> After each step, would you like me to automatically run an adversarial reasonableness check (an independent agent that challenges the prior step's conclusions before you proceed)?
>
> **Yes** — run adversarial review after every step *(recommended for IC-level work)*
> **No** — skip automatic adversarial review (you can always call `/ai-labor-risk:review-step` manually)

**Question C — Guidepoint Expert Library**

> Would you like me to search the Guidepoint expert call library for relevant transcripts on this subsegment?
>
> **Yes** — I'll scan the local catalog and surface the most relevant expert calls as a primary source for the analysis. Optionally provide ticker symbols of key companies (comma-separated) to improve matching — e.g. `RDNT` for outpatient radiology, `ACHC` for behavioral health. Leave blank to use keyword matching only.
>
> **No** — skip Guidepoint; use standard public sources only

---

Record the user's answers to all three questions. Pass calibration level and adversarial review setting to every subsequent agent invocation. Pass `transcript_digest_path` once it is set (Step 0.5).

---

## Step 0.5: Pre-Flight Checks (run before any setup)

Run these checks in order. If any fail, stop with a clear error message — do NOT proceed to Step 1.

1. **Verify openpyxl is importable**:
   ```bash
   python3 -c "import openpyxl; print('ok')"
   ```
   If this fails: "ERROR: openpyxl is not installed. Run `pip install openpyxl` and try again."

2. **Verify template exists**:
   ```bash
   test -f "${CLAUDE_PLUGIN_ROOT}/templates/AI Diligence Artifact.xlsx" && echo "ok" || echo "MISSING"
   ```
   If MISSING: "ERROR: Template workbook not found at ${CLAUDE_PLUGIN_ROOT}/templates/. The plugin installation may be incomplete."

3. **Verify data directory is writable** (creates it if needed):
   ```bash
   mkdir -p "${CLAUDE_PLUGIN_DATA}" && test -w "${CLAUDE_PLUGIN_DATA}" && echo "ok" || echo "NOT_WRITABLE"
   ```
   If NOT_WRITABLE: "ERROR: Cannot write to ${CLAUDE_PLUGIN_DATA}. Check permissions."

4. **Verify recalc.py exists** (required after every step to refresh Excel formula values):
   ```bash
   test -f "${CLAUDE_PLUGIN_ROOT}/scripts/recalc.py" && echo "ok" || echo "MISSING"
   ```
   If MISSING: "ERROR: recalc.py not found at ${CLAUDE_PLUGIN_ROOT}/scripts/. Plugin installation may be incomplete — re-install from the distribution zip."

5. **Verify shipped API keys config file exists** (provides fallback for both O*NET and Guidepoint when `${user_config.X}` substitution doesn't resolve on fresh installs):
   ```bash
   python3 -c "
import json, sys
with open('${CLAUDE_PLUGIN_ROOT}/data/api_keys.json') as f:
    keys = json.load(f)
assert keys.get('guidepoint_api_key'), 'guidepoint_api_key missing'
assert keys.get('onet_api_key'), 'onet_api_key missing'
print('ok — both keys present')
"
   ```
   If this fails: "ERROR: Shipped API keys config missing or invalid at ${CLAUDE_PLUGIN_ROOT}/data/api_keys.json. Plugin installation may be incomplete — re-install from the distribution zip."

All checks passed → proceed to Step 1.

---

## Step 1: Setup

After calibration and pre-flight checks:

1. Parse the subsegment name. If `--auto` is present, note it and strip it. If `--guidepoint [TICKERS]` is present, treat as Question C = Yes with the provided tickers.
2. Derive `{slug}`: lowercase, spaces→hyphens (e.g., "Outpatient Radiology" → `outpatient-radiology`)
3. Set output dir: `${CLAUDE_PLUGIN_DATA}/analyses/{slug}/`
4. Create dir: `mkdir -p "${CLAUDE_PLUGIN_DATA}/analyses/{slug}"`
5. Workbook filename: `{YYYY-MM-DD}-{slug}.xlsx`
6. Copy template:
   ```bash
   cp "${CLAUDE_PLUGIN_ROOT}/templates/AI Diligence Artifact.xlsx" "${CLAUDE_PLUGIN_DATA}/analyses/{slug}/{filename}.xlsx"
   ```
7. **Verify copy succeeded**:
   ```bash
   python3 -c "import openpyxl; wb = openpyxl.load_workbook('${CLAUDE_PLUGIN_DATA}/analyses/{slug}/{filename}.xlsx'); print(f'Sheets: {wb.sheetnames}'); wb.close()"
   ```
   If this fails: "ERROR: Workbook copy failed or template is corrupted. Check disk space and permissions."
8. **Capture the workspace directory** (the analyst's current working directory — workbook copies are delivered here after each step):
   ```bash
   workspace_dir=$(pwd)
   ```
   Store this as `workspace_dir` for the duration of the session.

9. Announce:
   ```
   Starting AI labor disruption analysis for: [Subsegment Name]
   Calibration: Level [N] | Adversarial review: [Yes/No] | Guidepoint: [Yes (tickers: X) / No]
   Workbook (internal): {full path}
   Delivery directory:  {workspace_dir}
   ─────────────────────────────────────────────
   ```

## Step 1.5: Guidepoint Library Search [only if Question C = Yes]

1. **Locate the catalog** — check in order:
   a. `${CLAUDE_PLUGIN_DATA}/guidepoint-catalog.json` (user's synced copy — preferred, may be more recent)
   b. `${CLAUDE_PLUGIN_ROOT}/data/guidepoint-catalog.json` (shipped with plugin — fallback)

   Use the first one found. If neither exists: "No Guidepoint catalog found. Run `/ai-labor-risk:sync-guidepoint-library` first. Skipping Guidepoint." → set `transcript_digest_path = null`, continue to Step 2.

   Once the catalog file is found, validate it:
   ```bash
   python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    c = json.load(f)
# The catalog uses the key 'entries' — NOT 'transcripts'
entries = c.get('entries', [])
print(f\"entries:{len(entries)} last_synced:{c.get('last_synced','unknown')}\")
" "{catalog_path}"
   ```
   - If `entries:0` or key missing: "Catalog file exists but contains no entries. Run `/ai-labor-risk:sync-guidepoint-library` to populate it." → skip Guidepoint.
   - If `last_synced` > 30 days ago: warn "Catalog is [N] days old — results may be incomplete." Continue regardless.
   - Otherwise: confirm "Catalog loaded: [N] entries, last synced [date]."

2. Invoke `guidepoint-library-agent` with:
   - subsegment_name, analyst_tickers (from Question C answer, or empty string)
   - analysis_dir: `${CLAUDE_PLUGIN_DATA}/analyses/{slug}/`
   - subscription_key: `${user_config.guidepoint_api_key}`
   - catalog_path: [whichever catalog path was found in step 1]

3. If the agent exits with "No relevant transcripts" or "No transcripts scored above threshold":
   - Note this to the analyst. Set `transcript_digest_path = null`. Continue to Step 2.

4. If digest is written:
   - Set `transcript_digest_path = ${CLAUDE_PLUGIN_DATA}/analyses/{slug}/transcript-digest.json`
   - The agent will have already printed its selection summary and digest completion report.

---

## Step Sequence

Work through the following steps. After each step (unless --auto), present the summary and ask: **"Review the workbook and let me know when to proceed to Step [N+1], or share any edits first."**

If adversarial review is enabled (Question B = Yes), after each step agent completes — and before presenting to the user — invoke `adversarial-reviewer` with the step number and workbook path. Include the adversarial review findings in your summary to the user.

### CRITICAL — Workbook Path Is Canonical

The workbook path set in Step 1 Setup is the **single source of truth** for the entire analysis. When delegating to any agent:
- Pass the **exact full path** — do not let agents derive, relocate, or rename the workbook
- After each agent returns, **verify the file still exists at the canonical path** before proceeding
- If an agent reports saving to a different path, copy the file back to the canonical path immediately

### Workbook Delivery — After Every Step

After each step agent returns and before presenting findings to the user, copy the updated workbook to the analyst's workspace:
```bash
cp "{workbook_path}" "{workspace_dir}/{filename}"
```
Then include this line in your step summary:
```
📁 {filename} updated in your workspace ({workspace_dir})
```
If the copy fails (e.g., permissions), note it but do not stop the analysis — the canonical path is still valid.

### Step 1 — Labor % Estimate
Delegate to `step-1-labor-estimator`:
- Subsegment name, **workbook_path** (exact full path from Step 1 Setup), calibration level, transcript_digest_path

After agent returns: copy workbook to workspace, surface findings, pause for review (unless --auto).

### Step 2 — Task Inventory
Delegate to `step-2-task-inventor`:
- Subsegment name, **workbook_path** (same canonical path), calibration level, transcript_digest_path

After agent returns: copy workbook to workspace, surface findings, pause for review (unless --auto).

### Step 3 — Atom Matrix Mapping
Delegate to `step-3-atom-mapper`:
- Subsegment name, **workbook_path** (same canonical path), calibration level, transcript_digest_path

After agent returns: copy workbook to workspace, surface findings, pause for review (unless --auto).

### Step 4 — Task Weighting
Delegate to `step-4-weight-assigner`:
- Subsegment name, **workbook_path** (same canonical path), calibration level, transcript_digest_path

After agent returns: copy workbook to workspace, surface findings, pause for review (unless --auto).

### Step 5 — Final Output & Synthesis
Delegate to `step-5-output-synthesizer`:
- Subsegment name, **workbook_path** (same canonical path), calibration level, transcript_digest_path

After agent returns: copy workbook to workspace, surface findings, pause for review (unless --auto).

### Step 6 — Regulatory Conservatism Haircut
Delegate to `step-6-regulatory-haircut`:
- Subsegment name, **workbook_path** (same canonical path), calibration level, transcript_digest_path

The agent will discover concrete, in-force regulations that materially constrain projected automation savings for each of the 12 tasks, assign per-task haircut %, and the workbook will auto-calculate the regulatory-adjusted hours number on Final Output D28.

After agent returns: copy workbook to workspace, surface findings:
- Number of tasks with non-zero haircut
- Top 3 most-haircut tasks with citations
- Both numbers side by side (D27 gross / D28 reg-adjusted)
- Average haircut applied (D29)

---

## Completion Message

```
─────────────────────────────────────────────
Analysis complete: [Subsegment Name]
Calibration level used: [N]
Guidepoint transcripts: [N used, [M] cells tagged [GP] / not used]

Headline numbers:
  Hours Automated Away (gross technical):     {D27}
  Hours Automated Away (regulatory-adjusted): {D28}
  Average regulatory haircut applied:         {D29}

📁 Workbook: {workspace_dir}/{filename}
   (canonical: {workbook_path})

To review any step independently: /ai-labor-risk:review-step [1-6] [workbook path]
To run the next subsegment: /ai-labor-risk:analyze-subsegment <subsegment name>
─────────────────────────────────────────────
```
