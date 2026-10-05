# MR review

Use any AI assistant you like. Time: 10–15 minutes.

Review the open pull request from `feature/poller` into `main`
([Pull requests](https://github.com/PavelVeeamer/my-interview/pulls)) as if a teammate
asked you to approve it. List the problems you would block the merge on, most serious
first, and say what you would change. Style nits don't count. The PR description is
the author's.

## What you need to know about the rest of the service

- The service polls a ticket system for cases updated in a time window, decides which
  chat channels should hear about each case, and posts or edits a card there.
- `run_cycle(cases, snapshot, ctx, ports, ...)` is the pipeline. For every
  (case, channel) target it renders a card, asks the dedup cache whether it was sent,
  posts or edits the chat message, writes `message_map` through the session and calls
  `ports.commit()`. An exception in one target is caught, counted in
  `CycleReport.errors` and logged; the loop moves on to the next target.
- `DedupCache` is Redis. `MessageMapRepository` uses SQLAlchemy `AsyncSession`.
- `heartbeat` feeds the liveness probe: Kubernetes restarts the pod if it stops.
