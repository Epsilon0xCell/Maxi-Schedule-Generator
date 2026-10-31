![banner](assets/banner.png)

# Maxi-Schedule-Generator
Maxi is a personalized CLI based schedule generator.

# What makes Maxi-Schedule-Generator Different?
Maxi takes into account several different factors and places an emphasis on a flexible schedule to avoid micromanaging and other unhealthy or unmanageable habits.

# What does Maxi-Schedule-Generator use?
1. Age
2. Habits (You wish to achieve)
3. Situation (Your personal situation and what you require)
4. Sleep/Wake Time (When you sleep/wake has an emphasis on when the schedule should manage the day)
5. Adaptability (How adaptive you want your schedule on a scale of 0-10)
6. Our custom schedule template (Or you can provide your own if a power user)
7. What is healthy (What is healthy for you to do for your age personally and based on your requirements)
8. Conflicts (Previous conflicts in a schedule for example, micromanaging, demotivated, etc.)
9. Adaptive Eating Times (Whether you need adaptive eating times or not, for instance, you cannot decide when to eat or it is difficult for you to have food when you want to)
10. Adaptive Breaks (Whether you want one large break or pomodoro/flowmodoro breaks)

All of your responses to this will be saved to a document titled "scheduleai.txt" as well as the schedule generated, unless you pick a different output file with `--output`.

# How to run

Requires Python 3 only (standard library, nothing to install, no API key).

```
python3 main.py
```

Maxi asks the ten questions above, prints your schedule, and saves the answers plus the schedule to `scheduleai.txt`. Generation is local and rule-based: wake/sleep times anchor the day, meals are placed adaptively or at fixed times, habits and a health block are woven between focus blocks, breaks follow the style you pick (pomodoro 25/5, flowmodoro 50/10, or one large break), the adaptability score sets how much buffer sits between blocks, and a 30 minute wind-down block closes the day at the sleep time. Sleep times at or before the wake time are treated as the next day.

Input I cannot use gets a short error message and exit 1, never a traceback: a time that is not `HH:MM` in 24 hour time or is out of range (hour 0 to 23, minute 0 to 59), an unknown break style, an invalid template number, a missing or non-UTF-8 answers file, a template path that is not a readable file, and an output path that cannot be written. Ending the interview early with EOF or Ctrl-C also exits 1 with a short note, and no schedule file is written. Two answers are read leniently on purpose: an adaptability value outside 0 to 10 is clamped to that range, and a non-numeric adaptability falls back to 5.

Non-interactive use, and custom templates:

```
python3 main.py --answers answers.txt
python3 main.py --answers answers.txt --output my-schedule.txt
```

where `answers.txt` holds one `key: value` line per factor (keys: age, habits, situation, wake, sleep, adaptability, health, conflicts, adaptive_eating, break_style, template). A template file lists your own blocks, one per line as `minutes | label`, and replaces the built-in block sequence. Template lines with a duration of zero or less are skipped. A template file that does not exist is reported by name and the program exits without writing a schedule.

Run `python3 main.py --help` for the full option list.

## Tests

```
python3 -m unittest
```

21 tests in `test_main.py`: time parsing and range checks, the three
break styles and the unknown style error, schedule building (day
boundaries, habit order, the single large break, overnight days), the
answers file reader, and the command line paths (missing and non-UTF-8
answers files, out of range times, an interview ended by EOF, output
and template paths that are directories, a normal run, and a template
run).

## Files

- `main.py`: the program.
- `test_main.py`: the test suite.
- `assets/logo.png` and `assets/banner.png`: project branding.

## License

MIT; see `LICENSE`.
