import pytest
from app.decide import decide, validate, InvalidState


def _state(**kw):
    base = {"hole": ["As", "Kd"], "board": [], "numOpponents": 1,
            "pot": 100, "toCall": 0, "myStack": 500}
    base.update(kw)
    return base


def test_validate_rejects_duplicate_card():
    with pytest.raises(InvalidState):
        validate(_state(hole=["As", "As"]))


def test_validate_rejects_bad_board_length():
    with pytest.raises(InvalidState):
        validate(_state(board=["Qs", "Jh"]))


def test_validate_rejects_bad_opponent_count():
    with pytest.raises(InvalidState):
        validate(_state(numOpponents=0))


def test_strong_hand_never_folds():
    rec = decide(_state(hole=["As", "Ah"], toCall=10), trials=5000)
    assert rec["action"] != "fold"


def test_check_when_no_bet_and_weak():
    rec = decide(_state(hole=["7s", "2h"], board=["As", "Kd", "Qc"],
                        numOpponents=3, toCall=0), trials=5000)
    assert rec["action"] == "check"


def test_fold_when_equity_below_potodds():
    rec = decide(_state(hole=["7s", "2h"], board=["As", "Kd", "Qc"],
                        numOpponents=3, pot=50, toCall=200), trials=5000)
    assert rec["action"] == "fold"


def test_call_when_equity_between_potodds_and_raise_threshold():
    rec = decide(_state(hole=["Js", "Ts"], board=[], numOpponents=1,
                        pot=100, toCall=30), trials=5000)
    assert rec["action"] == "call"


def test_raise_when_strong_and_facing_bet():
    rec = decide(_state(hole=["As", "Ah"], pot=100, toCall=30), trials=5000)
    assert rec["action"] == "raise"
    assert rec["size"] == round(100 + 2 * 30)


def test_stack_cap_limits_raise_size():
    rec = decide(_state(hole=["As", "Ah"], pot=100, toCall=30, myStack=10), trials=2000)
    assert rec["size"] == 10


def test_recommendation_shape():
    rec = decide(_state(hole=["As", "Ah"]), trials=2000)
    assert set(rec) == {"action", "size", "equity", "potOdds", "evCall", "reason", "speech"}
