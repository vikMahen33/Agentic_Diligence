"""
Eval Engine — Quantitative comparison of original vs. benchmark analysis workbooks.
Computes scoring metrics, sensitivity analysis, and impact propagation.
No LLM dependency — pure Python computation.

Usage:
    python3 eval.py <original_workbook> <benchmark_workbook> [case_toggle]

    case_toggle defaults to "Today Low". Options:
      "Today Low", "Today High", "2–3y Low", "2–3y High", "5–10y Low", "5–10y High"

Output:
    JSON to stdout with scores, grades, sensitivity analysis, and reliability metrics.
"""

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError:
    print(json.dumps({"error": "openpyxl is not installed. Run: pip install openpyxl"}))
    sys.exit(1)


# ── Appendix A: House View Automation Ceilings ──────────────────────────────
# Source: Sheet5 of template workbook (do not change without updating template)
# Format: 12 atoms per case, ordered Atom 1 → Atom 12

ATOM_NAMES = [
    "Information discovery & retrieval",
    "Extraction & structuring",
    "Normalization, reconciliation & integration",
    "Deterministic execution & transaction processing",
    "Structured triage & decision support",
    "Authority-bearing judgment & decisioning",
    "Drafting, synthesis & artifact assembly",
    "Stakeholder interaction & influence",
    "Workflow orchestration & exception resolution",
    "Assurance, compliance & traceability",
    "Physical execution — structured/predictable",
    "Physical execution — variable/unstructured",
]

CEILINGS = {
    # v2 Section 10 \u2014 Asset-Light / Capex-Constrained view
    # Atom 11 (structured physical) and Atom 12 (unstructured physical) collapse vs. v1.5.0
    # because robotics/equipment deployment is excluded; software-only levers only
    "Today Low":  [0.50, 0.55, 0.25, 0.45, 0.50, 0.10, 0.50, 0.15, 0.15, 0.20, 0.08, 0.03],
    "Today High": [0.75, 0.80, 0.55, 0.70, 0.75, 0.30, 0.75, 0.35, 0.40, 0.45, 0.20, 0.10],
    "\u2013".join(["2", "3y Low"]):   [0.65, 0.70, 0.45, 0.60, 0.65, 0.20, 0.65, 0.25, 0.30, 0.30, 0.12, 0.05],
    "\u2013".join(["2", "3y High"]):  [0.90, 0.92, 0.75, 0.88, 0.90, 0.45, 0.88, 0.50, 0.60, 0.60, 0.25, 0.13],
    "\u2013".join(["5", "10y Low"]):  [0.80, 0.85, 0.60, 0.75, 0.80, 0.30, 0.75, 0.35, 0.50, 0.45, 0.15, 0.07],
    "\u2013".join(["5", "10y High"]): [0.95, 0.98, 0.90, 0.95, 0.95, 0.65, 0.95, 0.70, 0.85, 0.80, 0.30, 0.15],
}

# Fix the ceiling keys to use proper en-dash
CEILINGS["2\u20133y Low"] = CEILINGS.pop("\u2013".join(["2", "3y Low"]))
CEILINGS["2\u20133y High"] = CEILINGS.pop("\u2013".join(["2", "3y High"]))
CEILINGS["5\u201310y Low"] = CEILINGS.pop("\u2013".join(["5", "10y Low"]))
CEILINGS["5\u201310y High"] = CEILINGS.pop("\u2013".join(["5", "10y High"]))


# ── Workbook Reader ─────────────────────────────────────────────────────────

def read_workbook(path):
    """Read analysis data from a workbook. Returns dict with step_1, step_2, step_3, step_4, final_output."""
    try:
        wb = load_workbook(path, data_only=True)
    except Exception as e:
        return {"error": f"Cannot open workbook: {e}"}

    result = {}

    # Step 1: Labor %
    try:
        s1 = wb["Step 1"]
        result["step_1"] = {
            "subsegment": s1["B3"].value,
            "sources": [
                {"name": s1[f"C{r}"].value, "estimate": s1[f"D{r}"].value, "commentary": s1[f"E{r}"].value}
                for r in range(7, 10)
            ],
            "triangulated_avg": s1["D10"].value,
        }
    except Exception as e:
        result["step_1"] = {"error": str(e)}

    # Step 2: Tasks
    try:
        s2 = wb["Step 2"]
        result["step_2"] = {
            "tasks": [s2[f"C{r}"].value for r in range(7, 19)],
        }
    except Exception as e:
        result["step_2"] = {"error": str(e)}

    # Step 3: Atom allocations
    try:
        s3 = wb["Step 3"]
        atom_cols = "DEFGHIJKLMNO"
        result["step_3"] = {
            "allocations": [
                [s3[f"{c}{r}"].value for c in atom_cols]
                for r in range(7, 19)
            ],
            "validation": [s3[f"P{r}"].value for r in range(7, 19)],
        }
    except Exception as e:
        result["step_3"] = {"error": str(e)}

    # Step 4: Weights
    try:
        s4 = wb["Step 4 Weighted Calc"]
        result["step_4"] = {
            "weights": [s4[f"D{r}"].value for r in range(7, 19)],
            "sources": [s4[f"E{r}"].value for r in range(7, 19)],
            "case_toggle": s4["C21"].value,
        }
    except Exception as e:
        result["step_4"] = {"error": str(e)}

    # Final Output
    try:
        fo = wb["Final Output"]
        result["final_output"] = {
            "d25": fo["D25"].value,
            "d26": fo["D26"].value,
            "d27": fo["D27"].value,
        }
    except Exception as e:
        result["final_output"] = {"error": str(e)}

    wb.close()
    return result


# ── Formula Chain (Python replication) ───────────────────────────────────────

def compute_d27(weights, atom_matrix, case="Today Low"):
    """
    Replicate the Excel formula chain to compute D27 (hours automated out of 100).

    D27 = 100 × Σ_i(weight_i × Σ_j(alloc_ij × ceiling_j))

    Where:
      - weight_i = Step 4 task weight for task i
      - alloc_ij = Step 3 atom allocation for task i, atom j
      - ceiling_j = Appendix A automation ceiling for atom j under the given case
    """
    if case not in CEILINGS:
        raise ValueError(f"Unknown case toggle: {case}. Options: {list(CEILINGS.keys())}")

    ceilings = CEILINGS[case]
    total_automated = 0.0

    for i in range(min(len(weights), 12)):
        w = weights[i] or 0.0
        allocs = atom_matrix[i] if i < len(atom_matrix) else [0.0] * 12
        blended_ceiling = sum((allocs[j] or 0.0) * ceilings[j] for j in range(12))
        total_automated += w * blended_ceiling

    return round(total_automated * 100, 2)


# ── Scoring Functions ────────────────────────────────────────────────────────

def grade_absolute_error_pp(error_pp):
    """Letter grade based on percentage-point error."""
    if error_pp < 3:
        return "A"
    elif error_pp < 5:
        return "B"
    elif error_pp < 8:
        return "C"
    elif error_pp < 12:
        return "D"
    return "F"


def grade_cosine(cosine):
    """Letter grade based on cosine similarity."""
    if cosine > 0.95:
        return "A"
    elif cosine > 0.90:
        return "B"
    elif cosine > 0.85:
        return "C"
    elif cosine > 0.75:
        return "D"
    return "F"


def grade_to_score(grade):
    """Convert letter grade to numeric score for composite calculation."""
    return {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "F": 0.2}.get(grade, 0.0)


def score_to_grade(score):
    """Convert numeric score back to letter grade."""
    if score >= 0.9:
        return "A"
    elif score >= 0.7:
        return "B"
    elif score >= 0.5:
        return "C"
    elif score >= 0.3:
        return "D"
    return "F"


def cosine_similarity(a, b):
    """Cosine similarity between two vectors."""
    a = [x or 0.0 for x in a]
    b = [x or 0.0 for x in b]
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def mean_absolute_error(a, b):
    """Mean absolute error between two vectors."""
    a = [x or 0.0 for x in a]
    b = [x or 0.0 for x in b]
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


# ── Step 1 Evaluation ───────────────────────────────────────────────────────

def eval_step1(original, benchmark):
    """Compare Step 1 labor % estimates."""
    orig_avg = original.get("step_1", {}).get("triangulated_avg")
    bench_avg = benchmark.get("step_1", {}).get("triangulated_avg")

    if orig_avg is None or bench_avg is None:
        return {"skipped": True, "reason": "Missing labor % data in one or both workbooks"}

    abs_error = abs(orig_avg - bench_avg)
    abs_error_pp = round(abs_error * 100, 2)
    direction = "over" if orig_avg > bench_avg else "under" if orig_avg < bench_avg else "exact"

    return {
        "agent": round(orig_avg, 4),
        "benchmark": round(bench_avg, 4),
        "absolute_error_pp": abs_error_pp,
        "relative_error": round(abs_error / bench_avg, 4) if bench_avg != 0 else None,
        "direction": direction,
        "grade": grade_absolute_error_pp(abs_error_pp),
        "agent_sources": original.get("step_1", {}).get("sources", []),
        "benchmark_sources": benchmark.get("step_1", {}).get("sources", []),
    }


# ── Step 3 Evaluation ───────────────────────────────────────────────────────

def eval_step3(original, benchmark):
    """Compare Step 3 atom allocations task-by-task."""
    orig_allocs = original.get("step_3", {}).get("allocations", [])
    bench_allocs = benchmark.get("step_3", {}).get("allocations", [])
    tasks = original.get("step_2", {}).get("tasks", [])

    if not orig_allocs or not bench_allocs:
        return {"skipped": True, "reason": "Missing atom allocation data"}

    per_task = []
    cosines = []
    maes = []

    for i in range(min(len(orig_allocs), len(bench_allocs), 12)):
        orig_vec = [x or 0.0 for x in orig_allocs[i]]
        bench_vec = [x or 0.0 for x in bench_allocs[i]]

        cos_sim = cosine_similarity(orig_vec, bench_vec)
        mae = mean_absolute_error(orig_vec, bench_vec)

        # Find max deviation
        deviations = [(j, abs(orig_vec[j] - bench_vec[j])) for j in range(12)]
        max_dev = max(deviations, key=lambda x: x[1])

        # Dominant atom match
        orig_dominant = max(range(12), key=lambda j: orig_vec[j])
        bench_dominant = max(range(12), key=lambda j: bench_vec[j])

        task_result = {
            "task_index": i,
            "task_name": tasks[i] if i < len(tasks) else f"Task {i + 1}",
            "cosine_similarity": round(cos_sim, 4),
            "mae": round(mae, 4),
            "max_deviation": {
                "atom_index": max_dev[0],
                "atom_name": ATOM_NAMES[max_dev[0]],
                "agent_value": round(orig_vec[max_dev[0]], 4),
                "benchmark_value": round(bench_vec[max_dev[0]], 4),
                "delta": round(max_dev[1], 4),
            },
            "dominant_atom_match": orig_dominant == bench_dominant,
            "agent_dominant": {"index": orig_dominant, "name": ATOM_NAMES[orig_dominant]},
            "benchmark_dominant": {"index": bench_dominant, "name": ATOM_NAMES[bench_dominant]},
        }

        per_task.append(task_result)
        cosines.append(cos_sim)
        maes.append(mae)

    mean_cos = sum(cosines) / len(cosines) if cosines else 0.0
    mean_mae_val = sum(maes) / len(maes) if maes else 0.0

    # Detect systematic biases — average deviation per atom across all tasks
    atom_biases = []
    for j in range(12):
        deltas = []
        for i in range(min(len(orig_allocs), len(bench_allocs), 12)):
            orig_val = (orig_allocs[i][j] or 0.0)
            bench_val = (bench_allocs[i][j] or 0.0)
            deltas.append(orig_val - bench_val)
        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
        if abs(avg_delta) > 0.02:  # Flag if systematic bias > 2pp
            atom_biases.append({
                "atom_index": j,
                "atom_name": ATOM_NAMES[j],
                "avg_delta": round(avg_delta, 4),
                "direction": "over-allocated" if avg_delta > 0 else "under-allocated",
            })

    return {
        "tasks_compared": len(per_task),
        "per_task": per_task,
        "aggregate": {
            "mean_cosine_similarity": round(mean_cos, 4),
            "mean_mae": round(mean_mae_val, 4),
            "grade": grade_cosine(mean_cos),
        },
        "systematic_biases": atom_biases,
    }


# ── Step 4 Evaluation ───────────────────────────────────────────────────────

def eval_step4(original, benchmark):
    """Compare Step 4 task weight distributions."""
    orig_weights = original.get("step_4", {}).get("weights", [])
    bench_weights = benchmark.get("step_4", {}).get("weights", [])
    tasks = original.get("step_2", {}).get("tasks", [])

    if not orig_weights or not bench_weights:
        return {"skipped": True, "reason": "Missing task weight data in one or both workbooks"}

    # Sanitize
    orig_w = [w or 0.0 for w in orig_weights]
    bench_w = [w or 0.0 for w in bench_weights]
    n = min(len(orig_w), len(bench_w), 12)

    cos_sim = cosine_similarity(orig_w[:n], bench_w[:n])
    mae = mean_absolute_error(orig_w[:n], bench_w[:n])

    # Per-task comparison
    per_task = []
    for i in range(n):
        delta = orig_w[i] - bench_w[i]
        per_task.append({
            "task_index": i,
            "task_name": tasks[i] if i < len(tasks) else f"Task {i + 1}",
            "agent_weight": round(orig_w[i], 4),
            "benchmark_weight": round(bench_w[i], 4),
            "delta_pp": round(delta * 100, 2),
            "direction": "over-weighted" if delta > 0 else "under-weighted" if delta < 0 else "exact",
        })

    # Sort by absolute delta to surface biggest misses
    per_task_sorted = sorted(per_task, key=lambda x: abs(x["delta_pp"]), reverse=True)

    # Top-3 heaviest tasks comparison
    orig_top3 = set(sorted(range(n), key=lambda i: orig_w[i], reverse=True)[:3])
    bench_top3 = set(sorted(range(n), key=lambda i: bench_w[i], reverse=True)[:3])
    top3_overlap = len(orig_top3 & bench_top3)

    # Systematic bias: which tasks are consistently over/under-weighted
    material_shifts = [t for t in per_task if abs(t["delta_pp"]) > 5.0]

    return {
        "tasks_compared": n,
        "cosine_similarity": round(cos_sim, 4),
        "mae": round(mae, 4),
        "grade": grade_cosine(cos_sim),
        "per_task": per_task,
        "largest_deviations": per_task_sorted[:3],
        "top3_overlap": top3_overlap,
        "top3_overlap_note": (
            f"{top3_overlap}/3 of the heaviest tasks agree between agent and benchmark"
        ),
        "material_shifts": material_shifts,
    }


# ── Sensitivity Analysis ────────────────────────────────────────────────────

def eval_sensitivity(original, benchmark, case="Today Low"):
    """Compute impact propagation — how do Step 1 / Step 3 / Step 4 deviations affect D27?"""
    orig_weights = original.get("step_4", {}).get("weights", [])
    orig_allocs = original.get("step_3", {}).get("allocations", [])
    bench_weights = benchmark.get("step_4", {}).get("weights", [])
    bench_allocs = benchmark.get("step_3", {}).get("allocations", [])

    if not orig_weights or not orig_allocs:
        return {"skipped": True, "reason": "Missing weights or allocations"}

    # Sanitize
    orig_weights = [w or 0.0 for w in orig_weights]
    orig_allocs = [[x or 0.0 for x in row] for row in orig_allocs]

    # D27 with original data
    d27_original = compute_d27(orig_weights, orig_allocs, case)

    result = {
        "case_toggle": case,
        "d27_original": d27_original,
    }

    # Step 1 impact (dollar framing)
    orig_labor = original.get("step_1", {}).get("triangulated_avg")
    bench_labor = benchmark.get("step_1", {}).get("triangulated_avg")
    if orig_labor is not None and bench_labor is not None:
        labor_delta = orig_labor - bench_labor
        dollar_impact = round(labor_delta * d27_original / 100, 2)
        result["step1_labor_delta"] = round(labor_delta, 4)
        result["step1_dollar_impact_per_100_revenue"] = dollar_impact
        if labor_delta > 0:
            result["step1_narrative"] = (
                f"Agent estimated labor at {orig_labor:.0%} of costs; benchmark shows {bench_labor:.0%}. "
                f"At {d27_original} hours automated out of 100, the agent overstates the automatable "
                f"cost pool by ${abs(dollar_impact):.2f} per $100 of revenue."
            )
        else:
            result["step1_narrative"] = (
                f"Agent estimated labor at {orig_labor:.0%} of costs; benchmark shows {bench_labor:.0%}. "
                f"At {d27_original} hours automated out of 100, the agent understates the automatable "
                f"cost pool by ${abs(dollar_impact):.2f} per $100 of revenue."
            )

    tasks = original.get("step_2", {}).get("tasks", [])

    # Step 3 impact — per-task atom substitution (hold weights constant)
    if bench_allocs:
        bench_allocs_clean = [[x or 0.0 for x in row] for row in bench_allocs]

        per_task_impact = []
        for i in range(min(len(orig_allocs), len(bench_allocs_clean), 12)):
            mixed = [row[:] for row in orig_allocs]
            mixed[i] = bench_allocs_clean[i]
            d27_substituted = compute_d27(orig_weights, mixed, case)
            delta = round(d27_substituted - d27_original, 2)
            per_task_impact.append({
                "task_index": i,
                "task_name": tasks[i] if i < len(tasks) else f"Task {i + 1}",
                "d27_with_benchmark_atoms": d27_substituted,
                "d27_delta": delta,
            })

        result["step3_per_task_d27_impact"] = per_task_impact

        # Total Step 3 impact — substitute ALL benchmark atoms, keep original weights
        d27_bench_atoms = compute_d27(orig_weights, bench_allocs_clean, case)
        result["d27_with_benchmark_atoms"] = d27_bench_atoms
        result["step3_total_d27_delta"] = round(d27_bench_atoms - d27_original, 2)

    # Step 4 impact — substitute benchmark weights, keep original atoms
    if bench_weights:
        bench_weights_clean = [w or 0.0 for w in bench_weights]
        d27_bench_weights = compute_d27(bench_weights_clean, orig_allocs, case)
        result["d27_with_benchmark_weights"] = d27_bench_weights
        result["step4_total_d27_delta"] = round(d27_bench_weights - d27_original, 2)

        delta_w = d27_bench_weights - d27_original
        pct_w = (delta_w / d27_original * 100) if d27_original != 0 else 0
        if abs(delta_w) < 0.5:
            result["step4_narrative"] = (
                f"Task weight distribution closely matches internal headcount data. "
                f"Substituting benchmark weights moves D27 by only {delta_w:+.1f} hours — negligible."
            )
        else:
            direction_w = "overestimates" if delta_w < 0 else "underestimates"
            result["step4_narrative"] = (
                f"If internal headcount distribution is correct, the agent {direction_w} automation "
                f"potential by {abs(delta_w):.1f} hours ({abs(pct_w):.0f}%) due to task weight errors."
            )

    # Combined impact — benchmark weights AND benchmark atoms
    if bench_weights and bench_allocs:
        d27_full_benchmark = compute_d27(bench_weights_clean, bench_allocs_clean, case)
        result["d27_full_benchmark"] = d27_full_benchmark
        result["combined_d27_delta"] = round(d27_full_benchmark - d27_original, 2)

        delta_total = d27_full_benchmark - d27_original
        pct_change = (delta_total / d27_original * 100) if d27_original != 0 else 0
        if abs(delta_total) < 0.5:
            result["combined_narrative"] = (
                f"Analysis is well-aligned with internal data across atoms and weights. "
                f"Full benchmark substitution moves D27 by only {delta_total:+.1f} hours."
            )
        else:
            direction = "overestimates" if delta_total < 0 else "underestimates"
            result["combined_narrative"] = (
                f"If internal data is correct, automation ceiling is {d27_full_benchmark:.1f} hours "
                f"(not {d27_original:.1f}) — agent {direction} by {abs(delta_total):.1f} hours "
                f"({abs(pct_change):.0f}%) when both atom allocations and task weights are corrected."
            )
    elif bench_allocs:
        # Only atoms available (no weight benchmark)
        d27_bench_atoms_only = compute_d27(orig_weights, bench_allocs_clean, case)
        delta_total = d27_bench_atoms_only - d27_original
        pct_change = (delta_total / d27_original * 100) if d27_original != 0 else 0
        if abs(delta_total) < 0.5:
            result["combined_narrative"] = (
                f"Atom allocations are well-aligned with internal data. "
                f"D27 moves by only {delta_total:+.1f} hours — negligible impact on the thesis."
            )
        else:
            direction = "overestimates" if delta_total < 0 else "underestimates"
            result["combined_narrative"] = (
                f"If internal ops data is correct, automation ceiling is {d27_bench_atoms_only:.1f} hours "
                f"(not {d27_original:.1f}) — agent {direction} by {abs(delta_total):.1f} hours "
                f"({abs(pct_change):.0f}%)."
            )

    return result


# ── Overall Assessment ──────────────────────────────────────────────────────

def compute_overall(step1_result, step3_result, step4_result, sensitivity_result):
    """
    Compute composite grade and reliability score.

    Weights:
      Step 1 (labor %):        25%
      Step 3 (atom allocs):    40%
      Step 4 (task weights):   20%
      Sensitivity (D27 delta): 15%
    """
    scores = []
    score_weights = []
    flags = []

    # Step 1 weight: 25%
    if not step1_result.get("skipped"):
        scores.append(grade_to_score(step1_result["grade"]))
        score_weights.append(0.25)
        if step1_result["absolute_error_pp"] > 10:
            flags.append(f"Step 1 labor % off by {step1_result['absolute_error_pp']:.1f}pp — material for investment sizing")

    # Step 3 weight: 40%
    if not step3_result.get("skipped"):
        scores.append(grade_to_score(step3_result["aggregate"]["grade"]))
        score_weights.append(0.40)
        for bias in step3_result.get("systematic_biases", []):
            flags.append(
                f"Atom {bias['atom_index'] + 1} ({bias['atom_name']}) systematically "
                f"{bias['direction']} by {abs(bias['avg_delta']):.2f} avg"
            )

    # Step 4 weight: 20%
    if not step4_result.get("skipped"):
        scores.append(grade_to_score(step4_result["grade"]))
        score_weights.append(0.20)
        for shift in step4_result.get("material_shifts", []):
            if abs(shift["delta_pp"]) > 10:
                flags.append(
                    f"Task '{shift['task_name']}' weight off by {shift['delta_pp']:+.1f}pp "
                    f"({shift['direction']}) — may skew D27"
                )
        if step4_result.get("top3_overlap", 3) < 2:
            flags.append(
                "Top-3 heaviest tasks by weight are materially different between agent and benchmark — "
                "public-source staffing assumptions diverge from internal headcount"
            )

    # Sensitivity (combined D27 delta): 15%
    if not sensitivity_result.get("skipped"):
        total_delta = abs(sensitivity_result.get("combined_d27_delta",
                          sensitivity_result.get("step3_total_d27_delta", 0)))
        if total_delta < 2:
            scores.append(1.0)
        elif total_delta < 5:
            scores.append(0.8)
        elif total_delta < 8:
            scores.append(0.6)
        elif total_delta < 12:
            scores.append(0.4)
        else:
            scores.append(0.2)
        score_weights.append(0.15)

        if total_delta > 5:
            flags.append(
                f"D27 shifts by {sensitivity_result.get('combined_d27_delta', sensitivity_result.get('step3_total_d27_delta', 0)):+.1f} hours "
                f"when using benchmark data — material impact on thesis"
            )

    if not scores:
        return {"composite_grade": "N/A", "reliability_score": None, "flags": ["Insufficient data for scoring"]}

    # Normalize weights (handles skipped steps)
    total_weight = sum(score_weights)
    reliability = sum(s * w for s, w in zip(scores, score_weights)) / total_weight

    return {
        "composite_grade": score_to_grade(reliability),
        "reliability_score": round(reliability, 2),
        "flags": flags if flags else ["No material flags identified"],
    }


# ── Main ────────────────────────────────────────────────────────────────────

def run_eval(original_path, benchmark_path, case="Today Low"):
    """Run full evaluation comparing original vs. benchmark workbooks."""
    original = read_workbook(original_path)
    if "error" in original:
        return original

    benchmark = read_workbook(benchmark_path)
    if "error" in benchmark:
        return benchmark

    step1_result = eval_step1(original, benchmark)
    step3_result = eval_step3(original, benchmark)
    step4_result = eval_step4(original, benchmark)
    sensitivity_result = eval_sensitivity(original, benchmark, case)
    overall = compute_overall(step1_result, step3_result, step4_result, sensitivity_result)

    return {
        "eval_version": "1.2",  # v2 Section 10 asset-light ceilings
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsegment": original.get("step_1", {}).get("subsegment", "Unknown"),
        "original_workbook": str(original_path),
        "benchmark_workbook": str(benchmark_path),
        "case_toggle": case,
        "step_1": step1_result,
        "step_3": step3_result,
        "step_4": step4_result,
        "sensitivity": sensitivity_result,
        "overall": overall,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 eval.py <original_workbook> <benchmark_workbook> [case_toggle]")
        print()
        print("Compares an original analysis workbook against a benchmark workbook")
        print("produced from internal documents. Outputs JSON with scores and sensitivity.")
        print()
        print("Case toggle options (default: 'Today Low'):")
        for case in CEILINGS:
            print(f"  \"{case}\"")
        sys.exit(1)

    original_path = sys.argv[1]
    benchmark_path = sys.argv[2]
    case = sys.argv[3] if len(sys.argv) > 3 else "Today Low"

    if not Path(original_path).exists():
        print(json.dumps({"error": f"Original workbook not found: {original_path}"}))
        sys.exit(1)

    if not Path(benchmark_path).exists():
        print(json.dumps({"error": f"Benchmark workbook not found: {benchmark_path}"}))
        sys.exit(1)

    result = run_eval(original_path, benchmark_path, case)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
