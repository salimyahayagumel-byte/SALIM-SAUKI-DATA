from pathlib import Path

from services import dashboard_report


def test_dashboard_report_counts_and_resets_after_24_hours(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_report, "DB_PATH", Path(tmp_path) / "dashboard_report.db")

    dashboard_report.record_scan(5)
    dashboard_report.record_scan(2)
    dashboard_report.record_signal("STRONG GEM")
    dashboard_report.record_signal("GEM SIGNAL")
    dashboard_report.record_signal("EARLY GEM")

    assert dashboard_report.report_if_due() is None
    with dashboard_report._connect() as conn:
        dashboard_report._ensure(conn)
        conn.execute("UPDATE report_cycle SET started_at=started_at-90000 WHERE id=1")
        conn.commit()

    report = dashboard_report.report_if_due()
    assert report is not None
    assert report["scans"] == 2
    assert report["candidates_found"] == 7
    assert report["signals_sent"] == 3
    assert report["strong_gem"] == 1
    assert report["gem_signal"] == 1
    assert report["early_gem"] == 1
    assert dashboard_report.report_if_due() is None


def test_failed_report_can_restore_aggregate_counters(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_report, "DB_PATH", Path(tmp_path) / "dashboard_report.db")
    dashboard_report.record_scan(3)
    with dashboard_report._connect() as conn:
        dashboard_report._ensure(conn)
        conn.execute("UPDATE report_cycle SET started_at=started_at-90000 WHERE id=1")
        conn.commit()
    report = dashboard_report.report_if_due()
    assert report is not None
    dashboard_report.restore_report(report)
    retried = dashboard_report.report_if_due()
    assert retried is not None
    assert retried["candidates_found"] == 3
