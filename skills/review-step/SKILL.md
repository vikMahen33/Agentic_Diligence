---
description: Runs an independent adversarial reasonableness check on any completed step of a labor disruption analysis workbook. Challenges conclusions, flags weak assumptions, and identifies blind spots. Usage: /ai-labor-risk:review-step <step number (1-5)> <path to workbook>. Example: /ai-labor-risk:review-step 3 ~/.claude/plugins/data/ai-labor-risk/analyses/outpatient-radiology/2026-03-31-outpatient-radiology.xlsx
---

# Adversarial Step Review

You are running an independent adversarial review of a completed analysis step.

Arguments received: **$ARGUMENTS**

Parse the arguments:
- First token: step number (1, 2, 3, 4, or 5)
- Remaining: the workbook path

**Validation**: If either argument is missing or invalid, respond:
```
Usage: /ai-labor-risk:review-step <step 1-5> <workbook path>
Example: /ai-labor-risk:review-step 3 ~/.claude/plugins/data/ai-labor-risk/analyses/outpatient-radiology/2026-03-31-outpatient-radiology.xlsx
```

If valid, announce:
```
Running adversarial review of Step [N] in:
[workbook path]
─────────────────────────────────────────────
```

Then delegate to the `adversarial-reviewer` agent with:
- The step number
- The workbook path

Present the full adversarial review output to the user exactly as returned by the agent.

After presenting, add:
```
─────────────────────────────────────────────
To rerun any step after making edits: /ai-labor-risk:review-step <step> <workbook>
```
