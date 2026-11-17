"""Bonus B3 tests: swarm_verified keeps swarm's flow but a code verifier corrects the quote."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from bonus import swarm_verified
from bonus.swarm_verified import QUOTE_FACTS, verify_facts
from lab8.db import connect, init_store, load_json, load_jsonl
from lab8.durability import InjectedCrash
from lab8.metrics import trial_pass
from lab8.shapes.swarm_reference import run_claim as swarm_run
from tests.conftest import BY_ID, CLAIMS, WORLD

BONUS = Path(__file__).resolve().parents[1] / "bonus"
ADV_WORLD = load_json(BONUS / "world.json")
ADV_CLAIMS = load_jsonl(BONUS / "cases.jsonl")
ADV_BY_ID = {row["claim_id"]: row for row in ADV_CLAIMS}


def _public(tmp_path: Path, name: str) -> str:
    init_store(tmp_path / name, WORLD, CLAIMS).close()
    return str(tmp_path / name)


def _adv(tmp_path: Path, name: str) -> str:
    init_store(tmp_path / name, ADV_WORLD, ADV_CLAIMS).close()
    return str(tmp_path / name)


def _events(result) -> list[dict]:
    return json.loads(Path(result.trace_path).read_text(encoding="utf-8"))["events"]


def test_verify_facts_flags_every_quote_fact():
    base = {"delay_days": 2, "status": "delivered", "damage_verified": False}
    assert verify_facts(base, dict(base)) == []
    assert verify_facts({**base, "delay_days": 5}, base) == ["delay_days"]
    assert verify_facts({**base, "status": "delivered_late"}, base) == ["status"]
    assert verify_facts({**base, "damage_verified": True}, base) == ["damage_verified"]
    assert set(QUOTE_FACTS) == {"delay_days", "status", "damage_verified"}


def test_verifier_fixes_swarm_seed55_weakness_on_t02(tmp_path):
    # Plain swarm trusts "trễ 5 ngày" from the ticket on seed 55 and pays.
    assert swarm_run("C-002", seed=55, store_path=_public(tmp_path, "swarm.sqlite")).status == "resolved"

    store = _public(tmp_path, "verified.sqlite")
    started_at = time.time()
    result = swarm_verified.run_claim("C-002", seed=55, store_path=store)
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID["C-002"]["expected"], conn, started_at=started_at)
    finally:
        conn.close()
    assert passed, reason
    overrides = [e["payload"] for e in _events(result) if e["kind"] == "verifier_override"]
    assert overrides == [{
        "fields": ["delay_days"], "used": {"delay_days": 5}, "structured": {"delay_days": 2},
        "amount_before": 20000, "amount_after": 0,
    }]


@pytest.mark.parametrize("seed", [11, 22, 33, 44])
def test_no_override_when_swarm_already_used_db_facts(tmp_path, seed):
    result = swarm_verified.run_claim("C-002", seed=seed, store_path=_public(tmp_path, f"s{seed}.sqlite"))
    kinds = [e["kind"] for e in _events(result)]
    assert "verifier_override" not in kinds and "verifier_ok" in kinds
    assert result.status == "denied"


@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
@pytest.mark.parametrize("claim_id", sorted(ADV_BY_ID))
def test_adversarial_hand_labels_pass_every_seed(tmp_path, claim_id, seed):
    store = _adv(tmp_path, f"{claim_id}-{seed}.sqlite")
    started_at = time.time()
    result = swarm_verified.run_claim(claim_id, seed=seed, store_path=store)
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), ADV_BY_ID[claim_id]["expected"], conn, started_at=started_at)
    finally:
        conn.close()
    assert passed, reason


def test_adversarial_labels_are_complete_and_point_at_world():
    approvals = {a["approval_id"]: a for a in ADV_WORLD["approvals"]}
    orders = {o["order_id"] for o in ADV_WORLD["orders"]}
    keys = {"status", "proposal_amount", "refund_vnd", "refund_count", "audit_refund_committed",
            "policy_denied", "approval_ok", "forbid_substrings"}
    assert len(ADV_CLAIMS) >= 8
    for row in ADV_CLAIMS:
        assert keys <= set(row["expected"]), row["claim_id"]
        assert row["order_id"] in orders
        if row["approval_id"]:
            assert approvals[row["approval_id"]]["claim_id"] == row["claim_id"]


@pytest.mark.parametrize("crash_at", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_crash_propagates_and_resume_pays_once(tmp_path, crash_at):
    store = _public(tmp_path, "crash.sqlite")
    with pytest.raises(InjectedCrash):
        swarm_verified.run_claim("C-012", seed=55, store_path=store, crash_at=crash_at)
    result = swarm_verified.run_claim("C-012", seed=55, store_path=store)
    conn = connect(store)
    try:
        rows = conn.execute("SELECT amount_vnd FROM refund_ledger WHERE claim_id='C-012'").fetchall()
        audits = conn.execute(
            "SELECT COUNT(*) AS n FROM audit_events WHERE claim_id='C-012' AND event_type='refund_committed'"
        ).fetchone()["n"]
    finally:
        conn.close()
    assert result.status == "resolved"
    assert [r["amount_vnd"] for r in rows] == [35000] and audits == 1


@pytest.mark.parametrize("claim_id", ["B-005", "B-012"])
def test_trace_has_no_ticket_secret_or_pii(tmp_path, capsys, claim_id):
    result = swarm_verified.run_claim(claim_id, seed=55, store_path=_adv(tmp_path, "pii.sqlite"))
    out = capsys.readouterr()
    blob = Path(result.trace_path).read_text(encoding="utf-8") + out.out + out.err
    row = ADV_BY_ID[claim_id]
    for token in [row["ticket"], row["parent_secret"], *row["expected"]["forbid_substrings"]]:
        assert token not in blob
