# Repository for MLDEV team interview

Each task takes up to 15 minutes. Feel free to clone or download the repo to your machine.

> Alternatively, use a codespace in the browser.

To pack all tasks into one archive (committed files only, no `.venv`, caches or IDE files):

```bash
git archive --format=zip -o my-interview.zip HEAD
```

Tasks 2 and 3 need Python 3.11+ and [uv](https://docs.astral.sh/uv/) (or plain `pip install pytest`).
No databases, Redis or other infrastructure.

## Structure

### Warm-up: Blitz

Tech questions about Python, common libs, use-cases, techniques, practicality, anything.
Small question, small answer (1-2 sentences), 1:30 per question.
Open [task-0/blitz.html](./task-0/blitz.html) in a browser.

### Task 1: Classics

No AI copilot. Just code and your knowledge. Go to [task-1](./task-1/TASK.md).

### Task 2: AI-supported refactoring

You can use any AI agent you prefer. Refactor a dedup decision into a pure function and
make the tests green. Go to [task-2](./task-2/TASK.md).

### Task 3: MR review

You can use any AI agent you prefer. Review the open pull request from `feature/poller`
into `main`. Go to [task-3](./task-3/TASK.md).
