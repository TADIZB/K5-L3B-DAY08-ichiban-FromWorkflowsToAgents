from __future__ import annotations

import json

from lab8.db import connect
from lab8.shapes.workflow import run_claim
from tests.conftest import BY_ID


def test_workflow_uses_order_facts_instead_of_ticket_and_writes_safe_trace(public_db):
    result = run_claim("C-002", seed=11, store_path=str(public_db))

    # C-002's ticket claims five days of delay; the order row says two.
    assert "5" in BY_ID["C-002"]["ticket"]
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert result.refund_effects == []

    trace = json.loads(open(result.trace_path, encoding="utf-8").read())
    assert trace["run_id"] == result.run_id
    assert isinstance(trace["events"], list)
    serialized = json.dumps(trace, ensure_ascii=False)
    assert "CANARY_SECRET_" not in serialized
    assert "phone" not in serialized
    assert "address" not in serialized
    assert "internal_note" not in serialized


def test_workflow_passes_full_quote_to_host_for_per_order_cap(public_db):
    result = run_claim("C-014", seed=11, store_path=str(public_db))
    assert result.status == "resolved"
    assert result.proposal_amount == 150_000
    assert result.refund_effects[0]["amount_vnd"] == 120_000


def test_workflow_forwards_crash_and_retry_resumes_once(public_db):
    from lab8.durability import InjectedCrash

    try:
        run_claim("C-012", seed=11, store_path=str(public_db),
                  crash_at="after_effect_before_checkpoint")
    except InjectedCrash:
        pass
    else:
        raise AssertionError("workflow did not forward the crash point")

    result = run_claim("C-012", seed=11, store_path=str(public_db))
    assert result.status == "resolved"
    assert len(result.refund_effects) == 1
    conn = connect(str(public_db))
    try:
        audits = conn.execute(
            "SELECT COUNT(*) AS n FROM audit_events WHERE claim_id=? AND event_type='refund_committed'",
            ("C-012",),
        ).fetchone()["n"]
        assert audits == 1
    finally:
        conn.close()
