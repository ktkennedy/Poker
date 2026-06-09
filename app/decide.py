"""게임 상태 → 추천 결정. 에쿼티(라이브) + 팟오즈 + EV 기반(EV 최대화, GTO 아님)."""
from app.engine import equity, FULL_DECK

RAISE_EQ = 0.65
DEFAULT_TRIALS = 20000

_VALID_CARDS = set(FULL_DECK)


class InvalidState(ValueError):
    pass


def validate(state):
    hole = state.get("hole", [])
    board = state.get("board", [])
    if len(hole) != 2:
        raise InvalidState("홀카드는 정확히 2장이어야 합니다.")
    if len(board) not in (0, 3, 4, 5):
        raise InvalidState("보드는 0·3·4·5장만 가능합니다.")
    cards = list(hole) + list(board)
    for c in cards:
        if c not in _VALID_CARDS:
            raise InvalidState(f"잘못된 카드 표기: {c}")
    if len(set(cards)) != len(cards):
        raise InvalidState("중복된 카드가 있습니다.")
    if not (1 <= state.get("numOpponents", 0) <= 8):
        raise InvalidState("상대 수는 1~8명이어야 합니다.")
    for key in ("pot", "toCall", "myStack"):
        if state.get(key, 0) < 0:
            raise InvalidState(f"{key}는 음수일 수 없습니다.")


def _explain(action, eq, required, size):
    pct = round(eq * 100)
    req = round(required * 100)
    if action == "fold":
        return f"에쿼티 {pct}% < 필요 {req}%, 폴드", f"폴드. 승률 {pct}퍼센트."
    if action == "check":
        return f"벳 없음, 에쿼티 {pct}%로 체크", f"체크. 승률 {pct}퍼센트."
    if action == "call":
        return f"에쿼티 {pct}% > 필요 {req}%, 콜", f"콜. 승률 {pct}퍼센트."
    return f"에쿼티 {pct}%로 레이즈 {size}", f"레이즈 {size}. 승률 {pct}퍼센트."


def decide(state, trials=DEFAULT_TRIALS):
    validate(state)
    hole, board = state["hole"], state.get("board", [])
    n, pot, to_call, my_stack = (state["numOpponents"], state["pot"],
                                 state["toCall"], state["myStack"])

    eq = equity(hole, board, n, trials=trials)

    size = None
    if to_call == 0:
        required, ev_call = 0.0, 0.0
        if eq >= RAISE_EQ and pot > 0:
            action, size = "raise", round(0.6 * pot)
        else:
            action = "check"
    else:
        required = to_call / (pot + to_call)
        ev_call = eq * pot - (1 - eq) * to_call
        if eq < required:
            action = "fold"
        elif eq < RAISE_EQ:
            action = "call"
        else:
            action, size = "raise", round(pot + 2 * to_call)

    if size is not None and size >= my_stack:   # 스택 보정
        size = my_stack

    reason, speech = _explain(action, eq, required, size)
    return {
        "action": action,
        "size": size,
        "equity": round(eq, 4),
        "potOdds": round(required, 4),
        "evCall": round(ev_call, 2),
        "reason": reason,
        "speech": speech,
    }
