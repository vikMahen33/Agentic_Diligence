# ai-labor-risk

A Claude Code plugin that quantifies AI disruption risk to the human labor component of healthcare subsegments using the **Appendix A Workflow Atom Framework** (March 2026).

Built for PE diligence workflows. Produces an auditable Excel workbook — one step at a time, returning it to the analyst for review after each step.

---

## What it does

Given a healthcare subsegment (e.g., "outpatient radiology", "late-stage small CROs"), the plugin:

1. Estimates labor as % of total costs from SEC EDGAR, BLS, and CMS sources
2. Defines 11 collectively exhaustive tasks covering 100% of labor in the subsegment
3. Allocates each task across 12 workflow atoms (information retrieval → physical execution)
4. Weights each task by share of total labor hours
5. Synthesizes a final automation ceiling at Today Low, 2–3 year, and 5–10 year horizons

All outputs are written incrementally to an Excel workbook. The analyst reviews and edits after each step before proceeding.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI installed
- An [O*NET Web Services API key](https://services.onetcenter.org/developer/) (free registration)
- Python 3 with `openpyxl` (`pip install openpyxl`)

---

## Installation

```bash
git clone https://github.com/vikMahen33/Agentic_Diligence.git
cd Agentic_Diligence
pip install -r requirements.txt
```

Launch Claude Code pointing at this directory as the plugin:

```bash
claude --plugin-dir .
```

On first load, Claude Code will prompt you for your O*NET API key.

---

## Usage

### Run a full subsegment analysis

```
/ai-labor-risk:analyze-subsegment <subsegment name>
```

Examples:
```
/ai-labor-risk:analyze-subsegment outpatient radiology
/ai-labor-risk:analyze-subsegment late-stage small CROs
/ai-labor-risk:analyze-subsegment home health and personal care
```

You will be asked two questions upfront:
- **Calibration level (1–5)**: controls research rigor vs. creative inference (3 = recommended)
- **Adversarial review (Y/N)**: whether to run an independent challenge agent after each step

Add `--auto` to run all 5 steps without pausing for confirmation.

Output workbook is saved to:
```
~/.claude/plugins/data/ai-labor-risk/analyses/{slug}/{YYYY-MM-DD}-{slug}.xlsx
```

### Review any completed step

```
/ai-labor-risk:review-step <step 1-5> <workbook path>
```

Runs an independent adversarial review of a completed step — surfaces hard errors, analytical weaknesses, and blind spots.

---

## Output workbook structure

| Tab | Contents |
|---|---|
| Step 1 | Labor % estimate — 3 sources + triangulated average |
| Step 2 | 11-task inventory — collectively exhaustive, mutually exclusive |
| Step 3 | Atom matrix — 12-column allocation, each row sums to 1.0 |
| Step 4 Weighted Calc | Task labor time weights + auto-calculated remaining labor by atom |
| Final Output | Automation ceiling per task + synthesized rationale |
| Appendix A | Workflow Atom Framework ceiling ranges — pre-populated, do not edit |

---

## Calibration levels

| Level | Description |
|---|---|
| 1 | Strictly data-anchored — verified sources only, gaps flagged |
| 2 | Mostly data-driven — light inference where sources are directionally clear |
| 3 | Balanced *(recommended)* — data anchors + labeled analyst reasoning |
| 4 | Reasoning-forward — model judgment with directional source support |
| 5 | Investigative synthesis — thesis-driven, broad research, clearly labeled |

---

## Plugin structure

```
.claude-plugin/
  plugin.json          ← manifest + O*NET API key config
skills/
  analyze-subsegment/
    SKILL.md           ← coordinator: sequences all 5 agents
  review-step/
    SKILL.md           ← standalone adversarial review
agents/
  step-1-labor-estimator.md
  step-2-task-inventor.md
  step-3-atom-mapper.md
  step-4-weight-assigner.md
  step-5-output-synthesizer.md
  adversarial-reviewer.md
templates/
  AI Diligence Artifact.xlsx   ← blank workbook template (do not edit)
scripts/
  recalc.py            ← formula recalculation via LibreOffice
hooks/
  hooks.json           ← SessionStart: installs openpyxl
requirements.txt
```

---

## Notes

- Analysis outputs are stored outside this repo at `~/.claude/plugins/data/ai-labor-risk/` and are not tracked in git
- Formula recalculation (`recalc.py`) requires LibreOffice installed — if unavailable, formulas will recalculate automatically when the workbook is opened in Excel
- The Appendix A tab contains the house-view atom ceiling estimates and should not be edited
