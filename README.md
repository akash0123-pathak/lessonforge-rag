# LessonForge: a self-evaluating lesson generator

LessonForge is an agentic content system for the take-home assessment. Given a topic, it:

1. generates a standalone beginner lesson;
2. evaluates it with hard pass/fail rubric checks;
3. feeds every failure back to the generator;
4. retries at most twice; and
5. persists lessons, rejection logs, and recurring failure patterns in `data/memory.json`.

The offline demo is deterministic and runs without an API key. It intentionally starts with a false guarantee on a fresh memory file. The evaluator rejects that draft and the generator repairs it after receiving the accuracy failure. Set `OPENAI_API_KEY` to use an OpenAI-compatible model instead.

## Quick start

```powershell
python lesson_agent.py --topic "Introduction to RAG" --demo --inject-error
```

The command writes:

- `outputs/final_lesson.md` — the lesson that cleared the rubric
- `outputs/attempt_0.md` and `attempt_1.md` — drafts for comparing the rejection and repair
- `outputs/run_report.json` — attempts, feedback sent, checkpoint decisions, rejection log, and memory update
- `data/memory.json` — persistent cross-run learning

Run the automated checks with:

```powershell
python -m unittest discover -s tests -v
```

Use a model instead of the offline generator:

```powershell
$env:OPENAI_API_KEY="your-key"
python lesson_agent.py --topic "Introduction to RAG" --model
```

The model adapter expects `OPENAI_MODEL` (default `gpt-4o-mini`) and `OPENAI_BASE_URL` (default `https://api.openai.com/v1`). No API key is needed for `--demo`. The included factual rubric is specific to RAG; another topic requires its own reference facts and evaluator rules.

## Architecture and decisions

The generator is separate from the evaluator, so a draft cannot grade itself. The evaluator uses deterministic checks for required concepts, section order, examples, jargon definitions, sentence lengths, and false claims. Hard checks have no partial credit: one failure means the draft is rejected.

The lesson contract is intentionally narrow: explain what RAG is, why it matters, the retrieval→augmentation→generation flow, a concrete example, limitations, a glossary, and a short recap. This gives the evaluator observable evidence instead of asking a model for a vague quality score.

The retry loop is bounded by `MAX_RETRIES = 2`, preventing cost or infinite-loop surprises. Each retry receives the precise failure reasons. Memory stores run metadata and failure counts. When a checkpoint has failed twice, its mapped guidance is added to the next run’s generation prompt. In demo mode, learned accuracy guidance makes the next first draft pass; `--inject-error` overrides that learning for the recording.

If all three attempts fail, the report says `FAIL`, the CLI exits with code 1, and no new final lesson is written. The report is the authority for the latest run; an older `final_lesson.md` may still exist from a prior passing run.

## Rubric

Every checkpoint is PASS or FAIL:

| Checkpoint | Hard requirement |
|---|---|
| Grounded accuracy | retrieval, context, augmentation, generation, uncertainty, and no false guarantee |
| Key coverage | substantive definition, value, flow, example, limitations, and recap sections |
| Beginner language | 220–700 words, at least eight sentences, average sentence ≤28 words, longest ≤55 |
| Jargon clarity | language model, retrieval, and context defined in the key-words section |
| Teaching by example | example section includes a real question and document source |
| Coherent flow | headings appear in what → why → how → example → limits → terms → recap order |

## Demo / Loom walkthrough

For a 15–20 minute recording: show the files and architecture (3 min), run the command with `--inject-error` and open `run_report.json` (4 min), compare the two saved drafts and the feedback (4 min), inspect the passing lesson (3 min), then explain the memory file and trade-offs (3 min). Keep the camera face-visible as requested by the assessment.

## Limitations and next steps

The offline generator is a scripted RAG fixture, not a general-purpose language model. The rule-based evaluator catches known false claims and missing structure, but cannot prove every factual statement is true or that a learner will understand it. In production I would add reviewed reference documents, a separate factuality judge with citations, prompt/version tracking, token/cost metrics, human approval for high-risk topics, and a small regression set of lessons to prevent rubric drift.
