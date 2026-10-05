import pytest

from dedup import AlertInterval, InMemoryCache
from notifier import Channel, Notification, process_notification


class FakeSender:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def post(self, channel, case_id, text):
        self.calls.append(("post", channel, case_id))

    def update(self, channel, case_id, text):
        self.calls.append(("update", channel, case_id))


@pytest.fixture
def sender():
    return FakeSender()


@pytest.fixture
def notify(sender):
    cache = InMemoryCache()

    def run(minutes_left=45, status="In progress", channels=(Channel("ops"),)):
        sender.calls.clear()
        process_notification(Notification("CS-1", "Backup fails", status, minutes_left), cache, list(channels), sender)
        return sender.calls

    return run


# --- current behaviour: must stay green ---


def test_the_first_notification_is_posted(notify):
    assert notify() == [("post", "ops", "CS-1")]


def test_the_same_notification_is_not_sent_again(notify):
    notify()
    assert notify() == []


def test_entering_a_new_interval_posts_again(notify):
    notify(minutes_left=45)
    assert notify(minutes_left=20) == [("post", "ops", "CS-1")]


def test_minutes_ticking_within_one_interval_send_nothing(notify):
    notify(minutes_left=45)
    assert notify(minutes_left=40) == []


def test_a_channel_can_have_its_own_intervals(notify):
    channel = Channel("ops", intervals=[AlertInterval(120, 0)])
    notify(minutes_left=45, channels=[channel])
    assert notify(minutes_left=20, channels=[channel]) == []


# --- the task: make these green ---


def test_a_change_within_one_interval_edits_the_message_instead_of_posting(notify):
    notify(status="In progress")
    assert notify(status="Waiting for customer") == [("update", "ops", "CS-1")]


def test_after_an_edit_the_same_notification_is_not_sent_again(notify):
    notify(status="In progress")
    notify(status="Waiting for customer")
    assert notify(status="Waiting for customer") == []


def test_channels_are_deduplicated_independently(notify):
    notify(channels=[Channel("ops")])
    assert notify(channels=[Channel("ops"), Channel("managers")]) == [("post", "managers", "CS-1")]
