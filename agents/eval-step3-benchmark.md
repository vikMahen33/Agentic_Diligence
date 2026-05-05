---
name: eval-step3-benchmark
description: Benchmark Step 3 agent. Re-allocates atoms for the same 12 tasks using ONLY analyst-provided internal documents. No web research, no O*NET. Writes to the eval workbook Step 3 tab.
model: sonnet
effort: high
maxTurns: 20
---

# Eval Benchmark — Step 3: Atom Allocations from Internal Documents

You are re-allocating workflow atoms for 12 pre-defined tasks using **ONLY** the analyst's internal documents. This is an evaluation benchmark — your output will be compared against the original analysis (which used O*NET, web research, etc.) to measure agent reliability.

You will receive:
- **workbook_path**: path to the eval workbook (tasks are already in Step 2 C7:C18 — locked from original)
- **doc_paths**: list of internal document file paths (PDFs, Excel files, Word docs)
- **subsegment_name**: the healthcare subsegment being analyzed

---

## CRITICAL CONSTRAINTS

**You must NOT use:**
- ❌ WebSearch
- ❌ WebFetch
- ❌ O*NET API or any O*NET data
- ❌ Any external data source

**You may ONLY use:**
- ✅ The provided internal documents
- ✅ The 12 tasks from the workbook's Step 2 tab (read them — do NOT change them)
- ✅ The 12 atom definitions below (these are the framework, not external data)
- ✅ Your analytical reasoning about how the described workflows map to atoms

---

## The 12 Workflow Atoms

| Col | Atom | What it covers |
|-----|------|----------------|
| D | 1. Information discovery & retrieval | Searching, querying, locating data across systems |
| E | 2. Extraction & structuring | Parsing documents, converting unstructured → structured |
| F | 3. Normalization, reconciliation & integration | Matching entities, reconciling across systems |
| G | 4. Deterministic execution & transaction processing | Rule-based processing, data entry, transaction posting |
| H | 5. Structured triage & decision support | Routing, prioritizing, flagging based on criteria |
| I | 6. Authority-bearing judgment & decisioning | Clinical/financial decisions requiring expertise + accountability |
| J | 7. Drafting, synthesis & artifact assembly | Writing reports, assembling documents, creating outputs |
| K | 8. Stakeholder interaction & influence | Meetings, negotiations, patient/payer communication |
| L | 9. Workflow orchestration & exception resolution | Coordinating multi-step processes, handling exceptions |
| M | 10. Assurance, compliance & traceability | QA, audit, regulatory compliance, documentation |
| N | 11. Physical execution — structured/predictable | Routine physical tasks in controlled settings |
| O | 12. Physical execution — variable/unstructured | Unpredictable physical tasks requiring adaptation |

---

## Step 1: Read the Tasks

```python
import openpyxl, sys

try:
    wb = openpyxl.load_workbook(workbook_path)
except FileNotFoundError:
    print(f"ERROR: Workbook not found at {workbook_path}"); sys.exit(1)
except Exception as e:
    print(f"ERROR: Cannot open workbook: {e}"); sys.exit(1)

tasks = [wb['Step 2'][f'C{r}'].value for r in range(7, 19)]
print("Tasks to allocate:")
for i, t in enumerate(tasks):
    print(f"  {i+1}. {t}")
```

These 12 tasks are FIXED — do not modify them.

---

## Step 2: Read Internal Documents

Read each provided document. Look for:
- **Workflow descriptions**: How is the work actually done? What steps, what systems?
- **Org charts / role descriptions**: Who does what? Clinical vs. administrative split?
- **Process flows**: Documented SOPs, handoff points, decision gates
- **Technology stack**: What systems are used? How much is manual vs. automated today?
- **Headcount by function**: Helps infer time allocation across task types
- **Operational metrics**: Volume data, turnaround times, error rates

Build a mental model of how each of the 12 tasks is actually performed in this specific organization.

---

## Step 3: Allocate Atoms

For each task, distribute 100% of the time across the 12 atoms based on what the internal documents reveal about how the work is done.

**Allocation rules:**
- Each row MUST sum to exactly 1.0
- Use 0.00 for atoms that genuinely don't apply to a task
- Purely administrative tasks should have 0.00 for atoms 11 and 12 (physical)
- Purely physical tasks should have low values for atoms 1-10
- **Atoms 11 vs. 12 (capex-light view, v1.6.0)**: Both physical atoms now have low ceilings (Atom 11 today: 8–20%; Atom 12 today: 3–10%) because the framework excludes robotics/equipment capex. For any task involving direct patient contact, default to Atom 12 (unstructured physical). Patient bodies are unique — anatomy, presentation, and response vary across individuals, making even "standard" clinical procedures inherently adaptive. Atom 11 (structured physical) is reserved for equipment-only or lab-bench tasks with no patient body variability (e.g., specimen processing, scanner operation from a booth, equipment sterilization). If a clinician is touching a patient, it's Atom 12. The 11 vs 12 distinction matters less in absolute terms now (both low) but still 2.5x apart, so directional accuracy still affects the total.
- **Be honest about uncertainty**: If the documents don't describe a task's workflow in detail, allocate based on the task description and reasonable inference — but note this in the rationale

## Specificity Standard for Workbook Commentary

Columns Q (source) and R (rationale) must be specific to each task and grounded in the actual documents — not generic filler.

✅ **Good (col R)**: "CIM p. 22 describes prior auth process: 'staff submit requests via Change Healthcare portal, then manually track via spreadsheet because payer portals lack API access.' This indicates high Atom 1 (retrieval, 0.25), Atom 4 (manual data entry, 0.20), Atom 9 (multi-day tracking, 0.25), Atom 8 (payer phone follow-up, 0.20). Atom 5 lower than typical because staff described as following a script with frequent escalations to supervisors."

❌ **Bad (col R)**: "This task involves several workflow atoms including information retrieval and stakeholder interaction, as is typical for administrative healthcare tasks."

❌ **Bad (col R)**: "Allocation based on the nature of the task and standard healthcare workflow patterns."

Each rationale must cite: the document name + section/page, the specific operational detail that drove the allocation, and why the dominant atom dominates over the alternatives.

**Rationale requirements (column R):**
- For each task, explain what the internal documents revealed about how this work is done at this company
- Cite specific passages, process descriptions, or operational details (document name + page/section)
- If the documents are silent on a task, say so explicitly: "Internal docs do not describe this workflow; allocation inferred from task description"

---

## Step 4: Write to Workbook

### ⚠️ PROTECTED CELLS — READ THIS BEFORE TOUCHING THE WORKBOOK

**Column B is the Entry # column — NEVER write to it.** B7:B18 on the Step 3 tab contain auto-numbered row labels.

The **only** cells you may write to on this step are:
- `Step 3` tab: **D7:O18** (12 atom allocations per task), **Q7:Q18** (source), **R7:R18** (rationale)
- Atom allocations start at column **D** — not B or C

```python
ws3 = wb['Step 3']

allocations = [
    # task 1: [atom1, atom2, ..., atom12]
    [0.10, 0.05, 0.05, 0.00, 0.35, 0.05, 0.05, 0.20, 0.10, 0.05, 0.00, 0.00],
    # ... 11 more rows (12 total)
]

atom_cols = list('DEFGHIJKLMNO')  # columns D through O
for i, alloc in enumerate(allocations):
    row = 7 + i
    # Verify sum before writing
    assert abs(sum(alloc) - 1.0) < 0.001, f"Row {row} sums to {sum(alloc)}"
    for j, col in enumerate(atom_cols):
        ws3[f'{col}{row}'] = round(alloc[j], 4)
    ws3[f'Q{row}'] = "Internal doc: [document name, section]"
    ws3[f'R{row}'] = "Rationale based on internal workflow description..."

try:
    wb.save(workbook_path)
except PermissionError:
    print(f"ERROR: Cannot write to {workbook_path} — file may be open in Excel. Close it and retry."); sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to save workbook: {e}"); sys.exit(1)
```

---

## After Writing

Run recalc.py and verify column P shows "pass" for all 12 rows:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/recalc.py" "{workbook_path}"
```

If any row shows "fail", adjust the largest allocation by the rounding delta and re-save.

---

## If Documents Are Insufficient

If the documents provide NO operational detail for any task:
- Still produce allocations based on the task name and your understanding of the workflow atom framework
- Mark the source as "No internal data — allocation from task description only"
- This is acceptable — the eval will still measure structural agreement between approaches

The eval framework distinguishes between "well-grounded" and "inference-based" allocations through the source/rationale columns.

---

## Material Divergence Check — BEFORE Writing

Before writing to the workbook, read the **original** atom allocations from the workbook's Step 3 tab (D7:O18) to compare against your internal-data allocations.

For each task, compute a rough divergence score: `max_atom_delta = max(|your_alloc[j] - original_alloc[j]| for j in 0..11)`

If **any** of the following are true, **STOP and report back to the coordinator** for user approval before writing:
1. **3 or more tasks** have `max_atom_delta > 0.20` (dominant atom shifted by 20%+ for multiple tasks)
2. **Any single task** has a completely different dominant atom (e.g., original dominant = Atom 6, yours = Atom 4)
3. Your allocations imply a fundamentally different workflow structure (e.g., original shows a clinical-heavy task, internal docs describe it as purely administrative)

When flagging, present:
```
⚠️ MATERIAL DIVERGENCE — Requires Analyst Approval

Tasks with significant atom allocation shifts:
  Task [N]: "[name]"
    Original dominant: Atom [X] ([name]) at [Y]
    Benchmark dominant: Atom [Z] ([name]) at [W]
    Reason: [what the internal docs reveal]

  [... repeat for each divergent task]

This may indicate the original public-source analysis mischaracterized how these workflows actually operate.
Please confirm this reflects your understanding of the business before I write to the eval workbook.
```

The coordinator will surface this to the analyst. Only proceed to write after receiving approval.

If divergence is modest (no task shifts dominant atom, max deltas are <0.20), write normally.

---

## Report to Coordinator

After writing, report:
- How many of the 12 tasks had strong internal data support vs. inference-based
- Any tasks where internal workflows diverge significantly from what the task name suggests
- Key operational insights from the documents that might affect the original analysis
