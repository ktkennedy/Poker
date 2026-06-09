from app.engine import equity


def test_nut_royal_is_certain():
    # 히어로가 이미 로열플러시(As Ks + Qs Js Ts) → 무조건 승리
    win, tie = equity(["As", "Ks"], ["Qs", "Js", "Ts"], num_opponents=3, trials=2000)
    assert win == 1.0
    assert tie == 0.0


def test_aa_vs_random_one_opponent():
    win, tie = equity(["As", "Ah"], [], num_opponents=1, trials=20000)
    eq = win + tie / 2
    assert 0.83 < eq < 0.87   # 교과서값 ≈ 0.852


def test_72o_vs_random_one_opponent():
    win, tie = equity(["7s", "2h"], [], num_opponents=1, trials=20000)
    eq = win + tie / 2
    assert 0.30 < eq < 0.40   # 교과서값 ≈ 0.35
