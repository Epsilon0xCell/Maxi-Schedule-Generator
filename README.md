![banner](assets/banner.png)

# Maxi
Maxi is a personalized CLI based schedule generator.

# What makes Maxi Different?
Maxi takes into account several different factors and places an emphasis on a flexible schedule to avoid micromanaging and other unhealthy or unmanageable habits.

# What does Maxi use?
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

Maxi asks the ten questions above, prints your schedule, and saves the answers plus the schedule to `scheduleai.txt`. Generation is local and rule-based: wake/sleep times anchor the day, meals are placed adaptively or at fixed times, habits and a health block are woven between focus blocks, breaks follow the style you pick (pomodoro 25/5, flowmodoro 50/10, or one large break), the adaptability score sets how much buffer sits between blocks, and a 30 minute wind-down block closes the day at the sleep time. Sleep times at or before the wake time are treated as the next day. Invalid times or invalid template numbers are reported with a short error message instead of a traceback.

Non-interactive use, and custom templates:

```
python3 main.py --answers answers.txt
python3 main.py --answers answers.txt --output my-schedule.txt
```

where `answers.txt` holds one `key: value` line per factor (keys: age, habits, situation, wake, sleep, adaptability, health, conflicts, adaptive_eating, break_style, template). A template file lists your own blocks, one per line as `minutes | label`, and replaces the built-in block sequence. Template lines with a duration of zero or less are skipped. A template file that does not exist is reported by name and the program exits without writing a schedule.

Run `python3 main.py --help` for the full option list.

## Files

- `main.py`: the program.
- `assets/logo.png` and `assets/banner.png`: project branding.

## License

MIT; see `LICENSE`.
