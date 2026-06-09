"""treys 기반 몬테카를로 에쿼티 엔진. treys evaluate는 낮을수록 강함(1=로열,7462=최약)."""
import random
from treys import Card, Evaluator

_EVALUATOR = Evaluator()
_RANKS = "23456789TJQKA"
_SUITS = "shdc"
_FULL_DECK = [r + s for r in _RANKS for s in _SUITS]


def _to_treys(cards):
    return [Card.new(c) for c in cards]


def equity(hole, board, num_opponents, trials=20000, seed=0):
    """hero(hole) vs num_opponents명 '랜덤' 상대의 (승률, 무승부율) 추정.
    매판 보드를 5장까지 채워 7장(보드5+홀2)으로 평가 → 프리플롭도 동일 처리."""
    rng = random.Random(seed)
    hole_t = _to_treys(hole)
    board_t = _to_treys(board)
    dead = set(hole) | set(board)
    deck = [c for c in _FULL_DECK if c not in dead]
    need = 5 - len(board)
    draw_count = 2 * num_opponents + need

    win = tie = 0
    for _ in range(trials):
        sample = rng.sample(deck, draw_count)
        opp_holes = [sample[2 * i:2 * i + 2] for i in range(num_opponents)]
        extra = sample[2 * num_opponents:]
        full_board = board_t + _to_treys(extra)
        hero_rank = _EVALUATOR.evaluate(full_board, hole_t)
        best_opp = min(_EVALUATOR.evaluate(full_board, _to_treys(oh)) for oh in opp_holes)
        if hero_rank < best_opp:
            win += 1
        elif hero_rank == best_opp:
            tie += 1
    return win / trials, tie / trials
