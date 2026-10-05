# AI-supported refactoring

Use any AI assistant you like. Time: 10–15 minutes.

## Context

`notifier.py` sends SLA notifications about support cases to chat channels.
`dedup.py` decides whether a notification goes out again. Today the decision lives in
`CacheItem.need_to_emit(cache, channel)`: it reads the cache itself, hides the rules in
a class hierarchy, and can only answer "send" or "don't send".

`InMemoryCache` stands in for Redis. No infrastructure is needed.

## Task

Refactor so that:

1. **The decision is a pure function** in `dedup.py`:

   ```python
   def decide(old: dict | None, new: dict, intervals: list[AlertInterval]) -> Create | Update | Skip
   ```

   `old` is what was last sent to the channel (or `None`), `new` is the current state.
   No cache, channel or sender inside.

2. **A real change posts, a cosmetic one edits.** Entering a new SLA interval is worth a
   new message. Any other change (e.g. the status) edits the message already in the
   channel via `sender.update(...)` instead of posting a new one. Nothing changed: send
   nothing.

3. **Each channel is deduplicated on its own.** Adding a channel later must not make it
   miss the notification the other channels already got.

## Run

```bash
uv run pytest -q          # or: pip install pytest && pytest -q
```

Tests under "current behaviour" are green now and must stay green. Make the rest green.
Be ready to explain what the AI suggested that you did not take, and why.
