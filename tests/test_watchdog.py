import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("watchdog", Path(__file__).parents[1] / "scripts" / "watchdog.py")
wd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd)


def test_alert_once_then_recover():
    st, msgs, rb = wd.decide({}, up=False, server_dead=False, can_reboot=True)
    assert len(msgs) == 1 and "недоступен" in msgs[0] and not rb
    st, msgs, rb = wd.decide(st, up=False, server_dead=False, can_reboot=True)
    assert msgs == [] and not rb
    st, msgs, _ = wd.decide(st, up=True, server_dead=False, can_reboot=True)
    assert len(msgs) == 1 and "снова" in msgs[0] and st["fails"] == 0


def test_reboot_only_when_dead_long_enough_and_once():
    st = {}
    for _ in range(2):
        st, _, rb = wd.decide(st, up=False, server_dead=True, can_reboot=True)
        assert not rb
    st, _, rb = wd.decide(st, up=False, server_dead=True, can_reboot=True)
    assert rb
    st, _, rb = wd.decide(st, up=False, server_dead=True, can_reboot=True)
    assert not rb  # no reboot loop


def test_no_reboot_without_token_or_if_ssh_alive():
    st = {"down": True, "fails": 5}
    assert wd.decide(st, up=False, server_dead=True, can_reboot=False)[2] is False
    assert wd.decide(st, up=False, server_dead=False, can_reboot=True)[2] is False
