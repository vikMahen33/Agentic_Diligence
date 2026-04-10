---
name: review-step
description: "Adversarial review of any completed analysis step. Challenges conclusions, flags weak assumptions, and identifies blind spots. Usage: /ai-labor-risk:review-step [1-5] [workbook path]"
---

# Adversarial Step Review

You are running an independent adversarial review of a completed analysis step.

Arguments received: **$ARGUMENTS**

Parse the arguments:
- First token: step number (1, 2, 3, 4, or 5)
- Remaining: the workbook path

**Validation**: If either argument is missing or invalid, respond:

    Usage: /ai-labor-risk:review-step [1-5] [workbook path]
    Example: /ai-labor-risk:review-step 3 /path/to/workbook.xlsx

If valid, announce:

    Running adversarial review of Step [N] in: [workbook path]

Then delegate to the `adversarial-reviewer` agent with:
- The step number
- The workbook path

Present the full adversarial review output to the user exactly as returned by the agent.

After presenting, add:

    To rerun any step after making edits: /ai-labor-risk:review-step [step] [workbook]
