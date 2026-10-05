"""The dedup decision as a pure function: no cache, no channel, no sender."""

from dedup import DEFAULT_INTERVALS, Create, Skip, Update, decide

OLD = {"title": "Backup fails", "status": "In progress", "minutes_left": 45}


def test_nothing_sent_before_creates():
    assert decide(None, OLD, DEFAULT_INTERVALS) == Create()


def test_a_new_interval_creates():
    assert decide(OLD, {**OLD, "minutes_left": 20}, DEFAULT_INTERVALS) == Create()


def test_a_change_within_one_interval_updates():
    assert decide(OLD, {**OLD, "status": "Waiting for customer"}, DEFAULT_INTERVALS) == Update()


def test_only_the_minutes_moved_skips():
    assert decide(OLD, {**OLD, "minutes_left": 40}, DEFAULT_INTERVALS) == Skip()
