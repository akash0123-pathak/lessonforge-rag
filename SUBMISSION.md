# Submission handoff

## Links to submit

- GitHub repository: add the repository URL after pushing this folder.
- Document link: `outputs/final_lesson.md` is the generated document. Paste its contents into Google Docs or Notion and add the published URL here.
- Loom: record the walkthrough using the script below and paste the URL here.

## Loom script (15–20 minutes)

1. **0:00–3:00 — Context and architecture.** Explain the input, generator, independent evaluator, bounded retry loop, output files, and persistent memory.
2. **3:00–7:00 — Run it.** Execute `python lesson_agent.py --topic "Introduction to RAG" --demo --inject-error`, then open `outputs/run_report.json`.
3. **7:00–11:00 — Deliberate error.** Show attempt 0: it falsely says RAG guarantees every answer is true. The accuracy checkpoint fails while the other five pass. Show that exact feedback reaching retry 1, then compare `attempt_0.md` with `attempt_1.md`.
4. **11:00–14:00 — Passing output.** Open `outputs/final_lesson.md` and map its sections to the rubric: what, why, three steps, school-handbook example, limitations, key words, recap.
5. **14:00–17:00 — Memory and trade-offs.** Open `data/memory.json`. Explain that failure counts and reusable guidance persist across runs. Mention the two-retry cap, deterministic offline mode, and optional model adapter.
6. **17:00–20:00 — Production next steps.** Discuss source citations, factuality evaluation, prompt/version tracking, cost metrics, regression tests, and human review for high-risk lessons.

Keep the camera face-visible as requested. The generated run is reproducible, so the evaluator can follow along without an API key.
