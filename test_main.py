"""Tests for main.py. Run with: python3 -m unittest"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import build_schedule, fmt, focus_cycle, load_answers_file, parse_time, render

ROOT = Path(__file__).resolve().parent


def run_cli(*args, stdin_text=None):
    return subprocess.run(
        [sys.executable, str(ROOT / "main.py"), *args],
        input=stdin_text, capture_output=True, text=True, cwd=ROOT, timeout=30)


def base_answers(**overrides):
    answers = {
        "age": "18", "habits": "", "situation": "", "wake": "07:00",
        "sleep": "23:00", "adaptability": "5", "health": "",
        "conflicts": "", "adaptive_eating": "y",
        "break_style": "pomodoro", "template": "",
    }
    answers.update(overrides)
    return answers


class ParseTimeTests(unittest.TestCase):
    def test_valid_times(self):
        self.assertEqual(parse_time("00:00"), 0)
        self.assertEqual(parse_time("07:30"), 450)
        self.assertEqual(parse_time("23:59"), 23 * 60 + 59)
        self.assertEqual(parse_time(" 08:15 "), 495)

    def test_out_of_range_times_raise_with_value_named(self):
        for bad in ("24:00", "25:99", "12:60", "-1:00", "07:-5"):
            with self.assertRaises(ValueError, msg=bad):
                parse_time(bad)

    def test_malformed_times_raise(self):
        for bad in ("seven", "7", "07:00:00", "", "²:00", "07:"):
            with self.assertRaises(ValueError, msg=bad):
                parse_time(bad)

    def test_fmt_wraps_past_midnight(self):
        self.assertEqual(fmt(0), "00:00")
        self.assertEqual(fmt(1500), "01:00")


class FocusCycleTests(unittest.TestCase):
    def test_known_styles(self):
        self.assertEqual(focus_cycle("pomodoro"), (25, 5))
        self.assertEqual(focus_cycle("flowmodoro"), (50, 10))
        self.assertEqual(focus_cycle("large"), (120, 0))

    def test_unknown_style_raises_and_names_it(self):
        with self.assertRaises(ValueError) as caught:
            focus_cycle("pomodoroo")
        self.assertIn("pomodoroo", str(caught.exception))


class BuildScheduleTests(unittest.TestCase):
    def test_day_starts_at_wake_and_ends_with_wind_down_at_sleep(self):
        blocks = build_schedule(base_answers())
        self.assertEqual(blocks[0], (420, 450, "Wake routine"))
        self.assertEqual(blocks[-1][1], 23 * 60)
        self.assertEqual(blocks[-1][2], "Wind-down")
        for start, end, _label in blocks:
            self.assertLessEqual(end, 23 * 60)
            self.assertGreater(end, start)

    def test_habits_appear_in_order(self):
        blocks = build_schedule(base_answers(habits="read, run"))
        labels = [label for _s, _e, label in blocks]
        self.assertIn("Habit: read", labels)
        self.assertIn("Habit: run", labels)
        self.assertLess(labels.index("Habit: read"), labels.index("Habit: run"))

    def test_large_style_has_one_large_break(self):
        blocks = build_schedule(base_answers(break_style="large"))
        labels = [label for _s, _e, label in blocks]
        self.assertEqual(labels.count("Large break"), 1)

    def test_bad_time_and_bad_style_raise(self):
        with self.assertRaises(ValueError):
            build_schedule(base_answers(wake="25:99"))
        with self.assertRaises(ValueError):
            build_schedule(base_answers(break_style="bogus"))

    def test_overnight_day_wraps_past_midnight(self):
        blocks = build_schedule(base_answers(wake="22:00", sleep="02:00"))
        self.assertEqual(blocks[-1][1], 26 * 60)


class AnswersFileTests(unittest.TestCase):
    def test_partial_file_keeps_defaults_and_time_colons(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "answers.txt"
            path.write_text("# comment\n\nwake: 06:30\nhabits: read\nnocolon\n",
                            encoding="utf-8")
            answers = load_answers_file(str(path))
        self.assertEqual(answers["wake"], "06:30")
        self.assertEqual(answers["habits"], "read")
        self.assertEqual(answers["sleep"], "23:00")

    def test_render_names_conflicts_and_template(self):
        answers = base_answers(conflicts="micromanaging", template="tmpl.txt")
        text = render(answers, build_schedule(base_answers()))
        self.assertIn("Avoid (from your conflicts answer): micromanaging", text)
        self.assertIn("- Template: tmpl.txt", text)


class CliTests(unittest.TestCase):
    def test_missing_answers_file_exits_1_without_traceback(self):
        proc = run_cli("--answers", "no-such-file-xyz.txt")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Could not read answers file", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_non_utf8_answers_file_exits_1_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.txt"
            bad.write_bytes(b"\xff\xfe\x00binary")
            proc = run_cli("--answers", str(bad))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not valid UTF-8", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_out_of_range_time_exits_1_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            answers = Path(tmp) / "a.txt"
            answers.write_text("wake: 25:99\n", encoding="utf-8")
            proc = run_cli("--answers", str(answers), "--output", str(Path(tmp) / "o.txt"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("25:99", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_eof_in_interview_exits_1_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_cli("--output", str(Path(tmp) / "o.txt"), stdin_text="")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("interview ended", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_output_path_is_directory_exits_1_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            answers = Path(tmp) / "a.txt"
            answers.write_text("wake: 07:00\nsleep: 23:00\n", encoding="utf-8")
            proc = run_cli("--answers", str(answers), "--output", tmp)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Could not write output file", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_template_path_is_directory_exits_1_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            answers = Path(tmp) / "a.txt"
            answers.write_text(f"template: {tmp}\n", encoding="utf-8")
            proc = run_cli("--answers", str(answers), "--output", str(Path(tmp) / "o.txt"))
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("Traceback", proc.stderr)

    def test_normal_answers_run_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            answers = Path(tmp) / "a.txt"
            out = Path(tmp) / "schedule.txt"
            answers.write_text("wake: 07:00\nsleep: 23:00\nhabits: read\n",
                               encoding="utf-8")
            proc = run_cli("--answers", str(answers), "--output", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = out.read_text(encoding="utf-8")
            self.assertIn("Habit: read", text)
            self.assertIn("Wind-down", text)
            self.assertIn("Saved to", proc.stdout)

    def test_template_run_uses_template_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpl = Path(tmp) / "tmpl.txt"
            tmpl.write_text("60 | Deep work\n30 | Email\n", encoding="utf-8")
            answers = Path(tmp) / "a.txt"
            answers.write_text(
                f"wake: 08:00\nsleep: 22:00\ntemplate: {tmpl}\n", encoding="utf-8")
            out = Path(tmp) / "schedule.txt"
            proc = run_cli("--answers", str(answers), "--output", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Deep work", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
