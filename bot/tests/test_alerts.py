from vpn.alerts import AlertState, Check, format_status


def test_alert_dedup():
    st = AlertState(fail_threshold=1)
    assert st.update([Check("xray", True, "ok")]) == []
    msgs = st.update([Check("xray", False, "container exited")])
    assert len(msgs) == 1 and "xray" in msgs[0] and "container exited" in msgs[0]
    assert st.update([Check("xray", False, "container exited")]) == []
    rec = st.update([Check("xray", True, "ok")])
    assert len(rec) == 1 and "восстановлено" in rec[0].lower()


def test_threshold_filters_flaps():
    st = AlertState(fail_threshold=2)
    assert st.update([Check("latency", False, "300 ms")]) == []
    assert st.update([Check("latency", True, "40 ms")]) == []  # flap: no alert, no recovery
    assert st.update([Check("latency", False, "300 ms")]) == []
    assert len(st.update([Check("latency", False, "310 ms")])) == 1


def test_failing_names():
    st = AlertState(fail_threshold=1)
    st.update([Check("a", False, "x"), Check("b", True, "y")])
    assert st.failing() == {"a"}


def test_format_status_marks():
    text = format_status([Check("xray", True, "running"), Check("disk", False, "95%")])
    assert "✅ xray: running" in text and "❌ disk: 95%" in text
