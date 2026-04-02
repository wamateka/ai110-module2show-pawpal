# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

PawPal+ goes beyond a basic task list with three scheduling improvements built into `pawpal_system.py`.

**Task sorting** — tasks can be ordered three ways depending on what the owner cares about most: by *urgency* (overdue tasks surface first, then ascending by date), by *care score* (pets with the lowest overall score get attention first), or by *completion gap* (pets furthest from meeting their daily targets are prioritized). All three strategies are pure functions that accept any task list and return a sorted copy, making them easy to compose with filters.

**Status and pet filtering** — `TaskService.get_all_for_pets()` accepts an optional `status` argument (`pending`, `done`, `skipped`) and an arbitrary list of pet IDs, so the UI can slice the task list by a single pet, a species group, or a completion state without loading everything into memory first.

**Recurring task automation** — marking a recurring task done or skipped automatically spawns the next occurrence (linked via `parent_task_id`), so daily walks and weekly grooming sessions regenerate themselves without manual re-entry. Custom intervals are supported alongside `daily` and `weekly`.

**Target auto-reset** — care targets can be given a `reset_period` of `daily` or `weekly`. Once a target is marked achieved, calling `check_and_reset()` (or the bulk `check_and_reset_all()`) on the next qualifying day flips it back to `pending` automatically, keeping recurring goals like daily feeding quotas in sync with the calendar.

**Conflict detection** — `TaskService.detect_conflicts()` scans a configurable day window for four problem patterns: the same non-feeding task type scheduled twice for one pet on the same day, two timed tasks within 30 minutes of each other for the same pet, more than six tasks in one day for a single pet, and — new in this iteration — tasks for *different* pets booked at the exact same time, flagging situations where a solo owner physically cannot be in two places at once. All conflicts return structured `ConflictReport` objects with a plain-English message rather than raising exceptions.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
