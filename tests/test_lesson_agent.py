import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lesson_agent


class LessonAgentTests(unittest.TestCase):
    def test_demo_retries_and_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(lesson_agent, "MEMORY_PATH", root / "memory.json"), patch.object(lesson_agent, "OUTPUT_DIR", root / "outputs"):
                report = lesson_agent.run("Introduction to RAG", lesson_agent.DemoGenerator())
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["attempts"]), 2)
            self.assertEqual(len(report["rejection_log"]), 1)
            self.assertTrue(report["attempts"][0]["evaluation"]["passed"] is False)
            self.assertTrue(report["attempts"][1]["evaluation"]["passed"] is True)

    def test_evaluator_rejects_unsupported_guarantee(self):
        good = lesson_agent.DemoGenerator().generate("RAG", ["grounded accuracy: repair"], {}, 1)
        bad = good.replace("RAG does not magically make every answer true", "RAG guarantees every answer is true")
        result = lesson_agent.evaluate(bad)
        self.assertFalse(result.passed)
        self.assertTrue(any(c.name == "grounded accuracy" and not c.passed for c in result.checks))
        self.assertTrue(all(c.passed for c in result.checks if c.name != "grounded accuracy"))

    def test_memory_is_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(lesson_agent, "MEMORY_PATH", root / "memory.json"), patch.object(lesson_agent, "OUTPUT_DIR", root / "outputs"):
                lesson_agent.run("RAG", lesson_agent.DemoGenerator())
            saved = json.loads((root / "memory.json").read_text())
            self.assertEqual(len(saved["runs"]), 1)
            self.assertGreater(saved["failure_counts"]["grounded accuracy"], 0)

    def test_repeated_failures_change_next_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(lesson_agent, "MEMORY_PATH", root / "memory.json"), patch.object(lesson_agent, "OUTPUT_DIR", root / "outputs"):
                first = lesson_agent.run("RAG", lesson_agent.DemoGenerator())
                second = lesson_agent.run("RAG", lesson_agent.DemoGenerator())
                third = lesson_agent.run("RAG", lesson_agent.DemoGenerator())
                injected = lesson_agent.run("RAG", lesson_agent.DemoGenerator(inject_error=True))
            self.assertEqual([len(x["attempts"]) for x in [first, second, third, injected]], [2, 2, 1, 2])
            self.assertIn(lesson_agent.FAILURE_GUIDANCE["grounded accuracy"], third["memory"]["guidance"])

    def test_exhausted_retries_report_failure(self):
        class AlwaysBad:
            def generate(self, topic, feedback, memory, attempt):
                return "# RAG\nBad lesson."

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(lesson_agent, "MEMORY_PATH", root / "memory.json"), patch.object(lesson_agent, "OUTPUT_DIR", root / "outputs"):
                report = lesson_agent.run("RAG", AlwaysBad())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(len(report["attempts"]), lesson_agent.MAX_RETRIES + 1)
            self.assertFalse((root / "outputs" / "final_lesson.md").exists())


if __name__ == "__main__":
    unittest.main()
