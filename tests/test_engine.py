from app.engine import equity


def test_nut_royal_is_certain():
    # 히어로가 이미 로열플러시(As Ks + Qs Js Ts) → 무조건 승리
    eq = equity(["As", "Ks"], ["Qs", "Js", "Ts"], num_opponents=3, trials=2000)
    assert eq == 1.0


def test_board_royal_is_chop():
    # 보드가 로열플러시 → 전원 보드로 챱. 히어로 지분 = 1/(상대수+1)
    assert equity(["2c", "3d"], ["As", "Ks", "Qs", "Js", "Ts"], num_opponents=1, trials=500) == 0.5
    assert abs(equity(["2c", "3d"], ["As", "Ks", "Qs", "Js", "Ts"], num_opponents=2, trials=500) - 1 / 3) < 1e-9


def test_aa_vs_random_one_opponent():
    eq = equity(["As", "Ah"], [], num_opponents=1, trials=20000)
    assert 0.83 < eq < 0.87   # 교과서값 ≈ 0.852


def test_72o_vs_random_one_opponent():
    eq = equity(["7s", "2h"], [], num_opponents=1, trials=20000)
    assert 0.30 < eq < 0.40   # 교과서값 ≈ 0.35
