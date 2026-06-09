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
        validate(_state(board=["Qs", "Jh"]))  # 2장은 불가(0/3/4/5만)


def test_validate_rejects_bad_opponent_count():
    with pytest.raises(InvalidState):
        validate(_state(numOpponents=0))


def test_strong_hand_never_folds():
    rec = decide(_state(hole=["As", "Ah"], toCall=10), trials=5000)
    assert rec["action"] != "fold"          # AA는 폴드 금지


def test_check_when_no_bet_and_weak():
    rec = decide(_state(hole=["7s", "2h"], board=["As", "Kd", "Qc"],
                        numOpponents=3, toCall=0), trials=5000)
    assert rec["action"] == "check"


def test_fold_when_equity_below_potodds():
    rec = decide(_state(hole=["7s", "2h"], board=["As", "Kd", "Qc"],
                        numOpponents=3, pot=50, toCall=200), trials=5000)
    assert rec["action"] == "fold"


def test_recommendation_shape():
    rec = decide(_state(hole=["As", "Ah"]), trials=2000)
    assert set(rec) == {"action", "size", "equity", "potOdds", "evCall", "reason", "speech"}
