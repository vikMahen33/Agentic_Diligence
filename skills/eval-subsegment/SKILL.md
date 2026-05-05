---
name: eval-subsegment
description: "Evaluates a completed analysis by re-running Step 1 (labor %), Step 3 (atom allocations), and Step 4 (task weights) against analyst-provided internal documents, then quantitatively comparing the results. Produces a scored reliability report with investment impact analysis. Usage: /ai-labor-risk:eval-subsegment [workbook path]"
---

# Eval — Backtest Analysis Against Internal Data

You are orchestrating an evaluation that backtests a completed analysis against the firm's internal proofpoints. You do NOT do analytical work yourself — you coordinate the benchmark agents and eval script.

## Arguments

`$ARGUMENTS` should contain the path to a completed analysis workbook (`.xlsx`).

If no path is provided, ask the analyst for the workbook path.

---

## Step 0: Setup & Document Collection

1. **Parse the workbook path** from arguments.

2. **Verify the workbook exists and has completed data:**
   ```python
   import openpyxl, sys
   try:
       wb = openpyxl.load_workbook("WORKBOOK_PATH", data_only=True)
       s1 = wb['Step 1']
       s2 = wb['Step 2']
       s3 = wb['Step 3']
       s4 = wb['Step 4 Weighted Calc']
       # Check Step 1 has data
       labor_pct = s1['D7'].value
       # Check Step 2 has tasks
       tasks = [s2[f'C{r}'].value for r in range(7, 19)]
       task_count = sum(1 for t in tasks if t)
       # Check Step 3 has allocations
       alloc_check = s3['D7'].value
       # Check Step 4 has weights
       weight_check = s4['D7'].value
       print(f"Subsegment: {s1['B3'].value}")
       print(f"Step 1 labor % (D7): {labor_pct}")
       print(f"Step 2 tasks populated: {task_count}")
       print(f"Step 3 has allocations: {alloc_check is not None}")
       print(f"Step 4 has weights: {weight_check is not None}")
       wb.close()
   except Exception as e:
       print(f"ERROR: {e}")
       sys.exit(1)
   ```
   If Step 1, Step 2, Step 3, or Step 4 are empty, stop: "This workbook does not have completed analysis data. Run the full analysis first."

3. **Ask the analyst for internal documents:**
   ```
   To benchmark this analysis, I need internal company documents. Please provide:

   • P&L statements or financial summaries (for labor % benchmarking)
   • Headcount breakdowns, org charts, or FTE-by-department data (for task weight benchmarking — most impactful)
   • CIM sections on operations, org structure, or workflows (for atom allocation benchmarking)
   • Any internal ops decks, process flow docs, or headcount breakdowns

   Drag and drop files or paste file paths.
   Best sources for each benchmark:
     Step 1 (labor %):    P&L with compensation line items
     Step 3 (atoms):      Process flow docs, SOPs, ops decks
     Step 4 (weights):    Headcount by department, org charts, labor cost by function
   ```

   Wait for the analyst to provide documents. Collect all file paths.

4. **Derive the analysis directory and create the benchmark workbook:**
   ```bash
   # Get the directory from the original workbook path
   ANALYSIS_DIR=$(dirname "WORKBOOK_PATH")
   EVAL_DATE=$(date +%Y-%m-%d)
   EVAL_WORKBOOK="${ANALYSIS_DIR}/eval-${EVAL_DATE}.xlsx"

   # Capture analyst's current working directory for workbook delivery
   workspace_dir=$(pwd)

   # Copy the original workbook as the benchmark copy
   cp "WORKBOOK_PATH" "${EVAL_WORKBOOK}"
   ```

---

## CRITICAL — Workbook Path Discipline

The `EVAL_WORKBOOK` path set in Step 0 is the **single canonical path** for the benchmark workbook. When delegating to benchmark agents:
- Pass the **exact full path** — do not let agents derive, relocate, or rename the workbook
- After each agent returns, **verify the file still exists at the canonical path** before proceeding
- If an agent reports saving to a different location, copy the file back to the canonical path

---

## Step 1: Benchmark Labor % (Step 1)

Invoke `eval-step1-benchmark` with:
- **workbook_path**: the eval workbook path `${EVAL_WORKBOOK}` — exact full path, NOT the original
- doc_paths: list of all internal document paths the analyst provided
- subsegment_name: from the original workbook B3

Wait for the agent to complete. It will write benchmark labor % estimates to the eval workbook's Step 1 tab.

**If the agent flags a MATERIAL DIVERGENCE**: present the divergence details to the analyst and ask for approval before telling the agent to proceed. The analyst may provide additional context (e.g., "that's expected — the P&L includes corporate overhead" or "use only the segment-level figures on page 3").

If the agent reports "Internal documents do not contain labor cost data": note this and continue — Step 1 eval will be skipped in scoring.

---

## Step 2: Benchmark Atom Allocations (Step 3)

Invoke `eval-step3-benchmark` with:
- **workbook_path**: the eval workbook path `${EVAL_WORKBOOK}` — exact full path (tasks already locked in Step 2 from the copy)
- doc_paths: same internal document paths
- subsegment_name: from the original workbook B3

Wait for the agent to complete. It will write benchmark atom allocations to the eval workbook's Step 3 tab.

**If the agent flags a MATERIAL DIVERGENCE**: present the divergence details to the analyst and ask for approval before telling the agent to proceed. The analyst may clarify how specific workflows actually operate at the portfolio company, which may inform whether the divergence is correct or reflects a misread of the internal documents.

---

## Step 2.5: Benchmark Task Weights (Step 4)

Invoke `eval-step4-benchmark` with:
- **workbook_path**: the eval workbook path `${EVAL_WORKBOOK}` — exact full path (tasks already locked in Step 2 from the copy)
- doc_paths: same internal document paths
- subsegment_name: from the original workbook B3

Wait for the agent to complete. It will write benchmark task weights to the eval workbook's Step 4 tab (D7:D18, E7:E18, F7:F18), overwriting the original agent's weights in the eval copy.

**If the agent flags a MATERIAL DIVERGENCE**: present the divergence details to the analyst and ask for approval before telling the agent to proceed. This often surfaces cases where the agent's public-source headcount assumptions diverge from the company's actual staffing mix.

If the agent reports "Internal documents do not contain functional headcount or cost breakdowns": note this and continue — Step 4 eval will be scored with low confidence weighting.

---

## Step 2.7: Stamp Final Output Tab

After both benchmark agents (Step 2 and Step 2.5) have completed, update the Final Output tab in the eval workbook to mark the rationales as stale. The original Step 5 rationales (G7:G18) and sources (H7:H18) were written against the original atom allocations and weights — they no longer describe the benchmark numbers.

```python
import openpyxl

wb = openpyxl.load_workbook("EVAL_WORKBOOK_PATH")
wf = wb['Final Output']

for r in range(7, 19):
    original_rationale = wf[f'G{r}'].value or ""
    original_source    = wf[f'H{r}'].value or ""
    wf[f'G{r}'] = f"[BENCHMARK EVAL — rationale reflects original analysis; see Step 3 tab col R and Step 4 tab col F for benchmark sources] {original_rationale}"
    wf[f'H{r}'] = f"[BENCHMARK] {original_source}"

wb.save("EVAL_WORKBOOK_PATH")
```

This preserves the original rationale text for reference while making it unambiguous that the D/E column values now reflect benchmark data, not the original analysis.

---

## Step 3: Quantitative Comparison

Run the eval script:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/eval.py" "ORIGINAL_WORKBOOK_PATH" "EVAL_WORKBOOK_PATH"
```

Capture the JSON output. Save it:
```bash
# Save eval JSON alongside the workbooks
EVAL_JSON="${ANALYSIS_DIR}/eval-${EVAL_DATE}.json"
```

Write the JSON output to the eval JSON path using the Write tool.

---

## Step 4: Report

Invoke `eval-reporter` with:
- eval_json_path: path to the saved eval JSON

The reporter will produce a structured markdown report. Present it to the analyst.

---

## Completion Message

Before printing the completion message, copy both workbooks to the analyst's workspace:
```bash
eval_filename=$(basename "${EVAL_WORKBOOK}")
orig_filename=$(basename "WORKBOOK_PATH")
cp "${EVAL_WORKBOOK}" "{workspace_dir}/${eval_filename}"
cp "WORKBOOK_PATH"    "{workspace_dir}/${orig_filename}"
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Eval complete: [Subsegment Name]

Composite Grade: [LETTER]  |  Reliability Score: [X.XX]

📁 Original workbook:  {workspace_dir}/{orig_filename}
📁 Benchmark workbook: {workspace_dir}/{eval_filename}
   Eval results JSON:  [JSON path]

To re-run the original analysis: /ai-labor-risk:analyze-subsegment [subsegment]
To review a specific step:       /ai-labor-risk:review-step [1-5] [workbook path]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
