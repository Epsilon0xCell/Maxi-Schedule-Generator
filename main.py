#!/usr/bin/env python3
"""Maxi: a personalized CLI schedule generator.

Maxi interviews you about the ten factors in the README (age, habits,
situation, sleep/wake times, adaptability, template, health, conflicts,
adaptive eating, adaptive breaks) and builds a day schedule from them.
Generation is local and rule-based: no API key and no network needed.
Your answers and the generated schedule are saved to scheduleai.txt.
"""

import argparse
import os
import sys

OUTPUT_FILE = "scheduleai.txt"

QUESTIONS = [
    ("age", "Your age"),
    ("habits", "Habits you want to achieve (comma separated)"),
    ("situation", "Your situation and what you require"),
    ("wake", "Wake time (HH:MM, 24h)"),
    ("sleep", "Sleep time (HH:MM, 24h)"),
    ("adaptability", "Adaptability, how flexible the schedule should be (0-10)"),
    ("health", "What is healthy for you (goals or limits, blank for none)"),
    ("conflicts", "Conflicts to avoid, for example micromanaging (blank for none)"),
    ("adaptive_eating", "Adaptive eating times? (y/n)"),
    ("break_style", "Break style: pomodoro, flowmodoro, or large"),
]

DEFAULTS = {
    "age": "18",
    "habits": "",
    "situation": "",
    "wake": "07:00",
    "sleep": "23:00",
    "adaptability": "5",
    "health": "",
    "conflicts": "",
    "adaptive_eating": "y",
    "break_style": "pomodoro",
    "template": "",
}


def parse_time(text):
    # I check the shape and the range here, at the one place every
    # wake and sleep value passes through. Before this check "25:99"
    # parsed like any other time and fmt() wrapped it, so the printed
    # schedule quietly started at 02:39 for an answer nobody typed.
    # int() sits in a try because a value like a superscript digit
    # passes a digit test and still fails to convert.
    parts = text.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"invalid time {text!r}: expected HH:MM in 24 hour time")
    try:
        hours, minutes = int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError(f"invalid time {text!r}: expected HH:MM in 24 hour time") from None
    if not 0 <= hours <= 23 or not 0 <= minutes <= 59:
        raise ValueError(
            f"invalid time {text!r}: hour must be 0 to 23 and minute 0 to 59")
    return hours * 60 + minutes


def fmt(minutes):
    # The modulo is what makes an overnight day readable: a block at
    # minute 1500 prints as 01:00, not 25:00. It also means the printed
    # schedule never shows which side of midnight a block sits on.
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def interview():
    answers = {}
    print("Maxi: personalized schedule generator")
    print("Answer the questions below. Press Enter to keep a default.\n")
    for key, label in QUESTIONS:
        suffix = f" [{DEFAULTS[key]}]" if DEFAULTS[key] else ""
        raw = input(f"{label}{suffix}: ").strip()
        answers[key] = raw if raw else DEFAULTS[key]
    # I ask for the template outside the QUESTIONS loop on purpose.
    # It has no default to fall back to, and it is a file path, not a
    # fact about the user, so it does not belong in the rendered list.
    template = input("Custom template file (blank for the built-in template): ").strip()
    answers["template"] = template
    return answers


def load_answers_file(path):
    # Starting from a copy of DEFAULTS means a partial answers file
    # still builds a full day. The user only writes the lines they
    # want to change.
    answers = dict(DEFAULTS)
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            # Split on the first colon only. The values themselves
            # contain colons, starting with the wake and sleep times,
            # so a plain split would cut "07:00" down to "07".
            key, value = line.split(":", 1)
            answers[key.strip()] = value.strip()
    return answers


def focus_cycle(style):
    """(focus_minutes, break_minutes) for the repeating focus cycle."""
    # An unknown style raises instead of falling back to pomodoro
    # without a word. The fallback hid typos: "pomodoroo" in an
    # answers file built a pomodoro day and the user never learned
    # their answer was not read. main() reports the ValueError with
    # the style named, the same as for a bad time.
    # large has a break length of 0 because its break is a separate
    # one time 90 minute block in build_schedule, not part of the cycle.
    cycles = {
        "pomodoro": (25, 5),
        "flowmodoro": (50, 10),
        "large": (120, 0),
    }
    if style not in cycles:
        raise ValueError(
            f"unknown break style {style!r}: use pomodoro, flowmodoro, or large")
    return cycles[style]


def build_schedule(answers):
    wake = parse_time(answers.get("wake") or "07:00")
    sleep = parse_time(answers.get("sleep") or "23:00")
    # A sleep time at or before wake means the day runs past midnight,
    # so I push sleep into the next day and let fmt() wrap the clock
    # back around. Equal wake and sleep therefore means a 24 hour day,
    # which is what the arithmetic gives, odd as that input is.
    if sleep <= wake:
        sleep += 24 * 60
    try:
        adaptability = max(0, min(10, int(answers.get("adaptability") or "5")))
    except ValueError:
        adaptability = 5
    # This buffer is added after every single block in add(), meals
    # and breaks included, not just after work. A high adaptability
    # day drifts later than the block lengths alone suggest.
    buffer_min = adaptability  # 0 = rigid back-to-back, 10 = loose spacing
    style = (answers.get("break_style") or "pomodoro").strip().lower()
    focus_len, break_len = focus_cycle(style)
    adaptive_eating = (answers.get("adaptive_eating") or "y").strip().lower().startswith("y")
    habits = [h.strip() for h in (answers.get("habits") or "").split(",") if h.strip()]

    blocks = []  # (start, end, label)
    cursor = wake

    def add(duration, label):
        # Everything that places a block goes through here, so cursor
        # is the one source of truth for "where the day has got to".
        # Code that appends to blocks directly, like the wind-down at
        # the end, has to get its times right on its own.
        nonlocal cursor
        blocks.append((cursor, cursor + duration, label))
        cursor += duration + buffer_min

    add(30, "Wake routine")
    add(30, "Breakfast" + (" (adaptive)" if adaptive_eating else ""))

    # Adaptive lunch tracks the middle of the actual day, so a late
    # wake moves it. Fixed lunch is always five hours after wake.
    # Dinner is pinned three hours before sleep either way.
    day_mid = wake + (sleep - wake) // 2
    lunch_at = day_mid if adaptive_eating else wake + 5 * 60
    dinner_at = sleep - 3 * 60
    lunch_done = dinner_done = False
    habit_queue = list(habits)
    health_done = False
    large_break_done = False

    def maybe_meals():
        # Meals are only checked between blocks, never inside one. A
        # long template block or focus block that starts before
        # lunch_at pushes lunch to whenever that block ends.
        nonlocal lunch_done, dinner_done
        if not lunch_done and cursor >= lunch_at:
            add(45, "Lunch" + (" (adaptive)" if adaptive_eating else ""))
            lunch_done = True
        if not dinner_done and cursor >= dinner_at:
            add(45, "Dinner")
            dinner_done = True

    if answers.get("template"):
        with open(answers["template"], encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or "|" not in line:
                    continue
                minutes, label = line.split("|", 1)
                minutes = int(minutes)
                if minutes <= 0:
                    continue
                maybe_meals()
                # This is a break, not a skip. The first block that
                # would run into the last half hour ends the whole
                # template, and any lines after it are never read as
                # schedule blocks at all.
                if cursor + minutes > sleep - 30:
                    break
                add(minutes, label.strip())
    else:
        cycle = 0
        while cursor + focus_len <= sleep - 30:
            maybe_meals()
            # Habits get the odd cycles and the health block is only
            # considered on cycles where no habit is waiting. With
            # habits still queued late in the day, the health block
            # can be pushed into the leftover pass after this loop.
            if habit_queue and cycle % 2 == 1:
                add(30, f"Habit: {habit_queue.pop(0)}")
            elif not health_done and cursor >= wake + (sleep - wake) * 2 // 3:
                note = answers.get("health", "")
                add(30, "Health block" + (f" ({note})" if note else ""))
                health_done = True
            else:
                add(focus_len, "Focus block")
                # The large break happens once, straight after the
                # first focus block. large_break_done is what stops a
                # day of 120 minute blocks from earning a 90 minute
                # break after every one of them.
                if style == "large" and not large_break_done:
                    add(90, "Large break")
                    large_break_done = True
                elif break_len and cursor + break_len <= sleep - 30:
                    add(break_len, "Break")
            cycle += 1

    # Leftover pass. Habits and a health block that never got a cycle
    # are placed here if half an hour still fits before the wind-down.
    # If it does not fit, they are dropped without a note in the
    # output. The user asked for them and the schedule just omits them.
    maybe_meals()
    while habit_queue and cursor + 30 <= sleep - 30:
        add(30, f"Habit: {habit_queue.pop(0)}")
    if not health_done and answers.get("health") and cursor + 30 <= sleep - 30:
        add(30, f"Health block ({answers['health']})")
    if cursor <= sleep - 30:
        # Wind-down belongs at the end of the day, not straight after
        # the last block when a short custom template ends early.
        blocks.append((sleep - 30, sleep, "Wind-down"))
    # Safety clamp. Nothing above should end past sleep, but if a
    # future change lets a block overrun, I cut it at sleep instead
    # of printing a day that ends after the user is in bed.
    if blocks and blocks[-1][1] > sleep:
        blocks[-1] = (blocks[-1][0], sleep, blocks[-1][2])
    return blocks


def render(answers, blocks):
    lines = ["Maxi schedule", "=" * 40, "", "Your answers:"]
    for key, label in QUESTIONS:
        lines.append(f"- {label}: {answers.get(key, '')}")
    if answers.get("template"):
        lines.append(f"- Template: {answers['template']}")
    if answers.get("conflicts"):
        # Honest limit: the conflicts answer is only printed back
        # here. No rule in build_schedule reads it, and the same is
        # true of the age and situation answers. They are a record of
        # what the user said, not inputs the builder acts on.
        lines.append(f"- Avoid (from your conflicts answer): {answers['conflicts']}")
    lines += ["", "Schedule:"]
    for start, end, label in blocks:
        lines.append(f"{fmt(start)} - {fmt(end)}  {label}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Maxi: personalized CLI schedule generator")
    parser.add_argument("--answers", help="file of 'key: value' answers; skips the interview")
    parser.add_argument("--output", default=OUTPUT_FILE, help="output file (default scheduleai.txt)")
    args = parser.parse_args()

    # The answers step is wrapped like the build step below it. A
    # missing --answers file, a file that is not UTF-8 text, and an
    # interview cut off by EOF or Ctrl-C each get a short message and
    # exit 1. Before this wrap all three died with a traceback.
    try:
        if args.answers:
            answers = load_answers_file(args.answers)
        else:
            answers = interview()
    except OSError as error:
        print(f"Could not read answers file {args.answers}: {error}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as error:
        print(f"Answers file {args.answers} is not valid UTF-8 text: {error}",
              file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nNo schedule built: the interview ended before it finished.",
              file=sys.stderr)
        return 1
    # I check the template path here, before building, so a missing
    # file gets named in its own message. Inside build_schedule the
    # same failure would surface as a bare file error with no context.
    if answers.get("template") and not os.path.exists(answers["template"]):
        print(f"Template file not found: {answers['template']}", file=sys.stderr)
        return 1
    # OSError is in this catch because build_schedule opens the
    # template file itself. A template path that exists but cannot be
    # read as a file, a directory for example, failed the existence
    # check above in the sense that it exists, and then died here
    # with a traceback before this catch named it.
    try:
        blocks = build_schedule(answers)
    except (ValueError, KeyError, OSError) as error:
        print(f"Could not build a schedule from those answers: {error}", file=sys.stderr)
        return 1
    text = render(answers, blocks)
    print()
    print(text)
    try:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as error:
        print(f"Could not write output file {args.output}: {error}", file=sys.stderr)
        return 1
    print(f"Saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
