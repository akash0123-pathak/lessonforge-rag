"""LessonForge: generate, evaluate, repair, and remember beginner lessons."""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Protocol

MAX_RETRIES = 2
ROOT = Path(__file__).parent
MEMORY_PATH = ROOT / "data" / "memory.json"
OUTPUT_DIR = ROOT / "outputs"
FAILURE_GUIDANCE = {
    "grounded accuracy": "Explain retrieval, supplied context, and generation; never promise a correct answer.",
    "key coverage": "Include definition, value, steps, example, limits, and recap.",
    "beginner language": "Use short sentences and simple words for a first-time learner.",
    "jargon clarity": "Define retrieval, context, and language model in a key-words section.",
    "teaches by example": "Include a real question and show which document answers it.",
    "coherent flow": "Teach in this order: what, why, how, example, limits, key words, recap.",
}


@dataclass
class Check:
    name: str
    passed: bool
    reason: str


@dataclass
class Evaluation:
    passed: bool
    checks: List[Check]

    @property
    def failures(self) -> List[str]:
        return [f"{c.name}: {c.reason}" for c in self.checks if not c.passed]


class Generator(Protocol):
    def generate(self, topic: str, feedback: List[str], memory: Dict, attempt: int) -> str: ...


def load_memory() -> Dict:
    if not MEMORY_PATH.exists():
        return {"runs": [], "failure_counts": {}, "guidance": []}
    return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))


def save_memory(memory: Dict) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")


class DemoGenerator:
    """Reproducible RAG fixture used to exercise the evaluator and retry loop."""

    def __init__(self, inject_error: bool = False) -> None:
        self.inject_error = inject_error

    def generate(self, topic: str, feedback: List[str], memory: Dict, attempt: int) -> str:
        if "rag" not in topic.lower() and "retrieval-augmented generation" not in topic.lower():
            raise ValueError("The offline demo supports RAG only. Use --model for another topic.")
        if attempt > 0 and not feedback:
            raise ValueError("Retry feedback is required before repairing the demo lesson.")
        learned = FAILURE_GUIDANCE["grounded accuracy"] in memory.get("guidance", [])
        if attempt == 0 and (self.inject_error or not learned):
            sound_lesson = self.generate(topic, ["grounded accuracy: repair false guarantee"], memory, 1)
            return sound_lesson.replace(
                "RAG does not magically make every answer true",
                "RAG guarantees every answer is true",
            )
        return """# Introduction to RAG\n\n## What you will learn\nRAG (Retrieval-Augmented Generation) helps an AI answer using useful information supplied at question time. It is for beginners: think of it as an AI that first looks in a trusted folder, then writes an answer.\n\n## What is RAG?\nRAG is a method with two parts: retrieval means finding relevant text; generation means writing a response. The found text is called context. RAG does not magically make every answer true, so the documents and the final answer still need checking.\n\n## Why does it matter?\nA normal language model may not know a company's new policy or your school's handbook. RAG can bring that information into the conversation without retraining the whole model. This can make answers more useful and easier to trace back to a document.\n\n## How it works: three steps\n1. **Retrieve:** turn the question into a search and find the most relevant passages in a document store (a searchable collection of documents).\n2. **Augment:** place those passages, called context, beside the user's question. Augment means “add useful information.”\n3. **Generate:** the language model uses the question and context to write an answer. A good system can show the source passages too.\n\n## A simple example\nImagine a school stores its attendance rules in a handbook. A student asks, “How many days can I be absent?” RAG searches the handbook, finds the attendance paragraph, gives that paragraph to the language model, and asks it to answer from that paragraph. If the paragraph does not contain the answer, the system should say it cannot find the answer instead of guessing.\n\n## What RAG cannot do\nRAG can retrieve the wrong passage, use an old document, or write an answer that is not supported by the context. It does not remove hallucinations (made-up information). Use trusted, updated documents and check important answers.\n\n## Key words\n- **Language model:** software trained to understand and produce text.\n- **Retrieval:** finding useful information.\n- **Context:** information given to the model for this answer.\n- **Hallucination:** an answer that sounds real but is made up or unsupported.\n\n## Quick recap\nRAG retrieves relevant information, adds it as context, and then generates an answer. It matters because the model can use changing or private documents. It is helpful, but its sources and answers still need checking.\n"""


class OpenAIGenerator:
    def __init__(self) -> None:
        from urllib.request import Request, urlopen
        self.request = Request
        self.urlopen = urlopen
        self.url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions"

    def generate(self, topic: str, feedback: List[str], memory: Dict, attempt: int) -> str:
        instruction = f"""Write a standalone beginner lesson for a 12th-grade Indian learner about {topic}. Use simple English. Include: definition, why it matters, three-step how-it-works flow, concrete example, limitations, glossary, recap. Define every technical word. Never claim the method guarantees truth.\nPrevious evaluator failures to fix: {feedback}\nRecurring guidance: {memory.get('guidance', [])}"""
        payload = {"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "messages": [{"role": "user", "content": instruction}], "temperature": 0.2}
        req = self.request(self.url, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}, method="POST")
        with self.urlopen(req, timeout=60) as response:
            return json.loads(response.read())['choices'][0]['message']['content']


def evaluate(lesson: str) -> Evaluation:
    low = lesson.lower()
    headings = list(re.finditer(r"^##\s+(.+?)\s*$", lesson, re.MULTILINE))
    sections = {}
    for index, match in enumerate(headings):
        title = match.group(1).lower()
        body_end = headings[index + 1].start() if index + 1 < len(headings) else len(lesson)
        body = lesson[match.end():body_end]
        role = next((name for name, pattern in [
            ("what", r"^what is"), ("why", r"^why"), ("how", r"^how"),
            ("example", r"example"), ("limits", r"limitation|cannot do"),
            ("terms", r"glossary|key words"), ("recap", r"recap"),
        ] if re.search(pattern, title)), None)
        if role and role not in sections:
            sections[role] = (index, body)
    required = ["what", "why", "how", "example", "limits", "terms", "recap"]
    words = re.findall(r"\b[\w'-]+\b", lesson)
    prose = re.sub(r"^#+.*$|^\s*[-\d]+[.)]?\s*\*\*[^*]+\*\*:?", "", lesson, flags=re.MULTILINE)
    sentences = [len(re.findall(r"\b[\w'-]+\b", part)) for part in re.split(r"[.!?]+", prose) if len(part.split()) >= 3]
    bad_claim = re.search(r"\b(guarantees? (every |all |a )?(answer|response)|always (true|correct|accurate)|never hallucinates|eliminates? hallucinations)\b", low)
    caution = re.search(r"\b(does not|cannot|can be wrong|need checking|still need checking|check important answers)\b", low)
    grounded = all(x in low for x in ["retriev", "context", "generat", "augment"]) and caution is not None and bad_claim is None
    coverage = all(role in sections and len(sections[role][1].split()) >= 20 for role in ["what", "why", "how", "example", "limits", "recap"])
    language = 220 <= len(words) <= 700 and len(sentences) >= 8 and sum(sentences) / len(sentences) <= 28 and max(sentences) <= 55 if sentences else False
    terms = sections.get("terms", (0, ""))[1].lower()
    jargon = all(re.search(r"^\s*-\s*\*\*" + re.escape(term) + r":\*\*\s+\w+", terms, re.MULTILINE) for term in ["language model", "retrieval", "context"])
    example = sections.get("example", (0, ""))[1].lower()
    concrete_example = "?" in example and ("handbook" in example or "document" in example) and "rag" in example
    flow = all(role in sections for role in required) and [sections[role][0] for role in required] == sorted(sections[role][0] for role in required)
    checks = [
        Check("grounded accuracy", grounded, "must explain retrieval, context, and generation; mention uncertainty; and avoid false guarantees"),
        Check("key coverage", coverage, "must give substantive what, why, how, example, limitations, and recap sections"),
        Check("beginner language", language, "must be 220–700 words with at least eight sentences, average sentence <=28 words, and longest <=55 words"),
        Check("jargon clarity", jargon, "must define language model, retrieval, and context in the key-words section"),
        Check("teaches by example", concrete_example, "example must include a real question and a handbook or document source"),
        Check("coherent flow", flow, "headings must follow: what, why, how, example, limits, terms, recap"),
    ]
    return Evaluation(all(c.passed for c in checks), checks)


def run(topic: str, generator: Generator) -> Dict:
    if "rag" not in topic.lower() and "retrieval-augmented generation" not in topic.lower():
        raise ValueError("This submission includes a grounded rubric for RAG only; add a topic pack before using another topic.")
    memory = load_memory()
    feedback: List[str] = []
    attempts = []
    rejection_log = []
    OUTPUT_DIR.mkdir(exist_ok=True)
    for attempt in range(MAX_RETRIES + 1):
        lesson = generator.generate(topic, feedback, memory, attempt)
        draft_file = f"attempt_{attempt}.md"
        OUTPUT_DIR.joinpath(draft_file).write_text(lesson, encoding="utf-8")
        result = evaluate(lesson)
        attempts.append({"attempt": attempt, "draft_file": draft_file, "feedback_received": feedback, "evaluation": asdict(result)})
        if result.passed:
            break
        rejection_log.append({"attempt": attempt, "failures": result.failures, "change_requested": result.failures, "resolved_on_attempt": None, "checks_resolved": []})
        feedback = result.failures
    status = "PASS" if result.passed else "FAIL"
    for item in rejection_log:
        prior_failures = {failure.split(":", 1)[0] for failure in item["failures"]}
        for later in attempts[item["attempt"] + 1:]:
            passed_names = {check["name"] for check in later["evaluation"]["checks"] if check["passed"]}
            resolved = sorted(prior_failures & passed_names)
            if resolved:
                item["resolved_on_attempt"] = later["attempt"]
                item["checks_resolved"] = resolved
                break
    for item in rejection_log:
        for failure in item["failures"]:
            key = failure.split(":", 1)[0]
            memory["failure_counts"][key] = memory["failure_counts"].get(key, 0) + 1
    memory["guidance"] = [instruction for name, instruction in FAILURE_GUIDANCE.items() if memory["failure_counts"].get(name, 0) >= 2]
    memory["runs"].append({"at": datetime.now(timezone.utc).isoformat(), "topic": topic, "status": status, "attempts": len(attempts), "rejections": len(rejection_log)})
    save_memory(memory)
    report = {"topic": topic, "status": status, "attempts": attempts, "rejection_log": rejection_log, "memory": copy.deepcopy(memory)}
    if result.passed:
        OUTPUT_DIR.joinpath("final_lesson.md").write_text(lesson, encoding="utf-8")
    OUTPUT_DIR.joinpath("run_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="Introduction to RAG")
    parser.add_argument("--demo", action="store_true", help="use deterministic offline generator")
    parser.add_argument("--model", action="store_true", help="use OpenAI-compatible generator")
    parser.add_argument("--inject-error", action="store_true", help="force an erroneous first draft in demo mode")
    args = parser.parse_args()
    if args.model and args.inject_error:
        parser.error("--inject-error is only available in demo mode")
    if args.model and not os.getenv("OPENAI_API_KEY"):
        parser.error("--model requires OPENAI_API_KEY")
    generator = OpenAIGenerator() if args.model else DemoGenerator(inject_error=args.inject_error)
    report = run(args.topic, generator)
    print(f"{report['status']} after {len(report['attempts'])} attempt(s); rejections: {len(report['rejection_log'])}")
    print("Wrote outputs/run_report.json and attempt drafts" + ("; outputs/final_lesson.md passed" if report["status"] == "PASS" else "; no lesson passed"))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
