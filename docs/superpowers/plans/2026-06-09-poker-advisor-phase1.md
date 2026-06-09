# 포커 어드바이저 Phase 1 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈게임 NLHE 캐시에서 상황을 탭으로 입력하면 폴드/체크/콜/레이즈를 화면+음성으로 알려주는, 아이폰서 도는 웹앱(Python 백엔드)을 만든다.

**Architecture:** FastAPI 백엔드가 `treys`+몬테카를로로 에쿼티를 계산하고 EV/팟오즈로 결정을 내린다. 같은 서버가 정적 프론트(탭 UI + Web Speech 음성)도 서빙한다. GitHub→Render 자동배포, 아이폰 사파리로 접속.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, treys, pytest, 바닐라 JS(Web Speech API), Render(무료)

---

## 파일 구조

```
poker-advisor/
├─ app/
│  ├─ __init__.py            (빈 파일 — 패키지 표시)
│  ├─ engine.py              treys + 몬테카를로 equity()
│  ├─ decide.py              validate() + decide(state) → recommendation
│  └─ main.py                FastAPI: POST /advise + 정적 서빙
├─ static/
│  ├─ index.html             탭 입력 UI
│  ├─ style.css              모바일 스타일
│  ├─ app.js                 입력수집·fetch·음성출력
│  ├─ manifest.json          PWA 메타
│  └─ sw.js                  서비스워커(셸 캐시)
├─ tests/
│  ├─ __init__.py
│  ├─ test_engine.py
│  ├─ test_decide.py
│  └─ test_api.py
├─ requirements.txt
├─ render.yaml
└─ README.md
```

**인터페이스 계약 (태스크 간 고정):**
- `engine.equity(hole: list[str], board: list[str], num_opponents: int, trials: int = 20000, seed: int = 0) -> tuple[float, float]` → `(win_rate, tie_rate)`
- `decide.InvalidState(ValueError)` — 검증 실패 예외
- `decide.validate(state: dict) -> None` — 실패 시 `InvalidState`
- `decide.decide(state: dict, trials: int = 20000) -> dict` — `{action,size,equity,potOdds,evCall,reason,speech}`
- 카드 표기: rank `23456789TJQKA` + suit `shdc` (예: `"As"`, `"Td"`, `"7c"`) — treys `Card.new` 호환

---

## Task 1: 프로젝트 스캐폴딩 & 의존성

**Files:**
- Create: `requirements.txt`, `app/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: requirements.txt 작성**

`requirements.txt`:
```
fastapi
uvicorn[standard]
treys
pytest
httpx
```
(`httpx`는 FastAPI `TestClient`에 필요)

- [ ] **Step 2: 빈 패키지 파일 생성**

`app/__init__.py` — 빈 파일.
`tests/__init__.py` — 빈 파일.

- [ ] **Step 3: 가상환경 생성 & 설치** (PowerShell)

Run:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
(bash면: `python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt`)
Expected: 설치 성공, 에러 없음.

- [ ] **Step 4: treys 동작 스모크 체크**

Run:
```powershell
python -c "from treys import Card, Evaluator; e=Evaluator(); b=[Card.new('Ah'),Card.new('Kd'),Card.new('Jc'),Card.new('5s'),Card.new('2d')]; h=[Card.new('As'),Card.new('Ac')]; print(e.evaluate(b,h))"
```
Expected: 정수 하나 출력(예: `3567` 비슷한 값). treys가 `evaluate(board, hand)` 순서로 동작함을 확인.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding and dependencies"
```

---

## Task 2: 엔진 — equity() (treys + 몬테카를로)

**Files:**
- Create: `app/engine.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_engine.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.engine'`

- [ ] **Step 3: engine.py 구현**

`app/engine.py`:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_engine.py -v`
Expected: PASS (3 passed). 통계 테스트는 seed 고정이라 재현됨.

- [ ] **Step 5: Commit**

```bash
git add app/engine.py tests/test_engine.py
git commit -m "feat: treys-based monte carlo equity engine"
```

---

## Task 3: 결정 로직 — validate() + decide()

**Files:**
- Create: `app/decide.py`
- Test: `tests/test_decide.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_decide.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_decide.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.decide'`

- [ ] **Step 3: decide.py 구현**

`app/decide.py`:
```python
"""게임 상태 → 추천 결정. 에쿼티(라이브) + 팟오즈 + EV 기반(EV 최대화, GTO 아님)."""
from app.engine import equity

RAISE_EQ = 0.65
DEFAULT_TRIALS = 20000

_RANKS = "23456789TJQKA"
_SUITS = "shdc"
_VALID_CARDS = {r + s for r in _RANKS for s in _SUITS}


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

    win, tie = equity(hole, board, n, trials=trials)
    eq = win + tie / 2

    size = None
    if to_call == 0:
        required, ev_call = 0.0, 0.0
        if eq >= RAISE_EQ:
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_decide.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add app/decide.py tests/test_decide.py
git commit -m "feat: decision logic with validation"
```

---

## Task 4: API — FastAPI /advise + 정적 서빙

**Files:**
- Create: `app/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_api.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_advise_returns_recommendation():
    r = client.post("/advise", json={
        "hole": ["As", "Ah"], "board": [], "numOpponents": 1,
        "pot": 100, "toCall": 0, "myStack": 500})
    assert r.status_code == 200
    data = r.json()
    assert data["action"] in ("check", "raise")   # AA 강함
    assert 0.0 <= data["equity"] <= 1.0


def test_advise_rejects_invalid():
    r = client.post("/advise", json={
        "hole": ["As", "As"], "board": [], "numOpponents": 1,
        "pot": 100, "toCall": 0, "myStack": 500})
    assert r.status_code == 400
    assert "error" in r.json()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: main.py 구현**

`app/main.py`:
```python
"""FastAPI: POST /advise + 정적 프론트 서빙(같은 origin)."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.decide import decide, InvalidState

app = FastAPI(title="Poker Advisor")


class GameState(BaseModel):
    hole: list[str]
    board: list[str] = []
    numOpponents: int
    pot: float
    toCall: float
    myStack: float


@app.post("/advise")
def advise(state: GameState):
    try:
        return decide(state.model_dump())
    except InvalidState as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# 정적 프론트 서빙. check_dir=False → static/이 아직 없어도 import 가능(프론트는 Task 5).
app.mount("/", StaticFiles(directory="static", html=True, check_dir=False), name="static")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 테스트 확인**

Run: `pytest -v`
Expected: PASS (전부 12 passed)

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_api.py
git commit -m "feat: FastAPI /advise endpoint with static mount"
```

---

## Task 5: 프론트엔드 — 탭 UI + 음성

**Files:**
- Create: `static/index.html`, `static/style.css`, `static/app.js`

검증은 수동(브라우저). pytest 대상 아님.

- [ ] **Step 1: index.html 작성**

`static/index.html`:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <title>Poker Advisor</title>
  <link rel="manifest" href="/manifest.json">
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <h1>♠ 포커 어드바이저</h1>

  <div class="targets">
    <button class="tgl" data-t="hole">내 패 (2)</button>
    <button class="tgl" data-t="board">보드 (5)</button>
  </div>
  <div class="sel">내 패: <span id="holeSel"></span></div>
  <div class="sel">보드: <span id="boardSel"></span></div>

  <div id="grid" class="grid"></div>

  <div class="nums">
    <label>상대 수 <input id="opp" type="number" value="1" min="1" max="8"></label>
    <label>팟 <input id="pot" type="number" value="100" min="0"></label>
    <label>콜 금액 <input id="toCall" type="number" value="0" min="0"></label>
    <label>내 스택 <input id="stack" type="number" value="500" min="0"></label>
  </div>

  <label class="voiceopt"><input id="voice" type="checkbox" checked> 음성으로 읽기</label>

  <div class="btns">
    <button id="adviseBtn" class="primary">추천 받기</button>
    <button id="resetBtn">초기화</button>
  </div>

  <div id="out" class="out"></div>

  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: style.css 작성**

`static/style.css`:
```css
* { box-sizing: border-box; }
body { margin:0 auto; padding:16px; max-width:520px;
       font-family:-apple-system,system-ui,sans-serif; background:#0b3d2e; color:#fff; }
h1 { font-size:20px; text-align:center; }
.targets { display:flex; gap:8px; margin-bottom:8px; }
.tgl { flex:1; padding:10px; border:none; border-radius:8px; background:#14543f; color:#fff; font-size:15px; }
.tgl.active { background:#f0c419; color:#000; font-weight:700; }
.sel { font-size:14px; margin:2px 0; }
.grid { display:grid; grid-template-columns:repeat(13,1fr); gap:3px; margin:10px 0; }
.card { padding:6px 0; border:none; border-radius:4px; background:#fff; font-size:12px; font-weight:700; }
.card.r { color:#c0392b; }
.card.b { color:#000; }
.card.picked { outline:3px solid #f0c419; }
.nums { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:10px 0; }
.nums label { font-size:13px; display:flex; flex-direction:column; gap:3px; }
.nums input { padding:8px; border-radius:6px; border:none; font-size:15px; }
.voiceopt { display:block; margin:8px 0; font-size:14px; }
.btns { display:flex; gap:8px; }
.btns button { flex:1; padding:14px; border:none; border-radius:8px; font-size:16px; }
.primary { background:#f0c419; color:#000; font-weight:700; }
.out { margin-top:14px; padding:14px; background:#14543f; border-radius:10px; min-height:40px; }
.action { font-size:26px; font-weight:800; color:#f0c419; }
.detail { font-size:13px; opacity:.85; margin:4px 0; }
.reason { font-size:14px; }
```

- [ ] **Step 3: app.js 작성**

`static/app.js`:
```javascript
const RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"];
const SUITS = [["s","♠","b"],["h","♥","r"],["d","♦","r"],["c","♣","b"]];
const state = { hole: [], board: [], target: "hole" };

function buildGrid() {
  const grid = document.getElementById("grid");
  for (const [s, sym, color] of SUITS) {
    for (const r of RANKS) {
      const code = r + s;
      const b = document.createElement("button");
      b.className = "card " + color;
      b.textContent = r + sym;
      b.dataset.code = code;
      b.onclick = () => toggleCard(code);
      grid.appendChild(b);
    }
  }
}

function toggleCard(code) {
  if (state.hole.includes(code)) { state.hole = state.hole.filter(c => c !== code); return refresh(); }
  if (state.board.includes(code)) { state.board = state.board.filter(c => c !== code); return refresh(); }
  if (state.target === "hole") { if (state.hole.length < 2) state.hole.push(code); }
  else { if (state.board.length < 5) state.board.push(code); }
  refresh();
}

function setTarget(t) { state.target = t; refresh(); }

function refresh() {
  document.getElementById("holeSel").textContent = state.hole.join(" ") || "(없음)";
  document.getElementById("boardSel").textContent = state.board.join(" ") || "(없음)";
  document.querySelectorAll(".tgl").forEach(el => el.classList.toggle("active", el.dataset.t === state.target));
  document.querySelectorAll(".card").forEach(el => {
    const c = el.dataset.code;
    el.classList.toggle("picked", state.hole.includes(c) || state.board.includes(c));
  });
}

async function advise() {
  const out = document.getElementById("out");
  out.textContent = "계산 중... (서버가 자고 있으면 최대 ~30초)";
  const body = {
    hole: state.hole, board: state.board,
    numOpponents: +document.getElementById("opp").value,
    pot: +document.getElementById("pot").value,
    toCall: +document.getElementById("toCall").value,
    myStack: +document.getElementById("stack").value,
  };
  try {
    const res = await fetch("/advise", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) { out.textContent = "오류: " + (data.error || res.status); return; }
    render(data);
  } catch (e) { out.textContent = "네트워크 오류: " + e.message; }
}

function render(d) {
  const labels = { fold: "폴드", check: "체크", call: "콜", raise: "레이즈" };
  const sizeTxt = d.size != null ? " " + d.size : "";
  document.getElementById("out").innerHTML =
    `<div class="action">${labels[d.action]}${sizeTxt}</div>` +
    `<div class="detail">승률 ${Math.round(d.equity*100)}% · 필요 ${Math.round(d.potOdds*100)}% · EV ${d.evCall}</div>` +
    `<div class="reason">${d.reason}</div>`;
  if (document.getElementById("voice").checked) speak(d.speech);
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "ko-KR";
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

function reset() {
  state.hole = []; state.board = [];
  document.getElementById("out").textContent = "";
  refresh();
}

window.onload = () => {
  buildGrid();
  document.getElementById("adviseBtn").onclick = advise;
  document.getElementById("resetBtn").onclick = reset;
  document.querySelectorAll(".tgl").forEach(el => el.onclick = () => setTarget(el.dataset.t));
  refresh();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
};
```

- [ ] **Step 4: 수동 검증 — 로컬 실행**

Run: `uvicorn app.main:app --reload`
브라우저에서 `http://127.0.0.1:8000` 열기.
확인:
1. 13×4 카드 그리드가 보인다.
2. "내 패 (2)" 누르고 As, Ah 탭 → "내 패: As Ah" 표시.
3. 상대 수 1, "추천 받기" → "레이즈 ..." + 승률 ~85% 표시, 음성으로 읽힘.
4. "보드 (5)" 누르고 카드 3장 탭 → 보드 반영, 다시 추천 → 값 갱신.

- [ ] **Step 5: Commit**

```bash
git add static/index.html static/style.css static/app.js
git commit -m "feat: tap-input frontend with voice output"
```

---

## Task 6: PWA — manifest + 서비스워커

**Files:**
- Create: `static/manifest.json`, `static/sw.js`

검증은 수동. 오프라인은 '셸만' 캐시됨(추천 계산은 서버 필요 → 인터넷 있어야 동작).

- [ ] **Step 1: manifest.json 작성**

`static/manifest.json` (커스텀 아이콘은 후순위 — iOS는 없으면 페이지 스냅샷 사용):
```json
{
  "name": "Poker Advisor",
  "short_name": "Poker",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0b3d2e",
  "theme_color": "#0b3d2e"
}
```

- [ ] **Step 2: sw.js 작성**

`static/sw.js`:
```javascript
const CACHE = "poker-advisor-v1";
const ASSETS = ["/", "/index.html", "/style.css", "/app.js", "/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
});

self.addEventListener("fetch", (e) => {
  if (e.request.url.includes("/advise")) return;          // 추천은 항상 네트워크
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
```

- [ ] **Step 3: 수동 검증**

Run: `uvicorn app.main:app --reload`
크롬 DevTools → Application → Manifest: "Poker Advisor" 인식 확인.
Application → Service Workers: `sw.js` 등록(activated) 확인.
(아이폰 실기기 배포 후) 사파리 → 공유 → "홈 화면에 추가" 작동 확인.

- [ ] **Step 4: Commit**

```bash
git add static/manifest.json static/sw.js
git commit -m "feat: PWA manifest and service worker"
```

---

## Task 7: 배포 설정 — render.yaml + README

**Files:**
- Create: `render.yaml`, `README.md`

- [ ] **Step 1: render.yaml 작성**

`render.yaml`:
```yaml
services:
  - type: web
    name: poker-advisor
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 2: README.md 작성**

`README.md`:
```markdown
# 포커 어드바이저 (Phase 1)

홈게임 NLHE 캐시용 EV 기반 어드바이저. 탭으로 상황 입력 → 폴드/체크/콜/레이즈 + 음성.

> ⚠️ 홈게임·플레이머니 전용. 실제 머니게임(온라인/카지노) 중 실시간 사용은 RTA(부정행위)이며 지원하지 않습니다.

## 로컬 실행
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
→ http://127.0.0.1:8000

## 테스트
```
pytest -v
```

## 배포 (Render)
1. 이 레포를 GitHub에 push
2. render.com → New → Web Service → 이 레포 연결
3. `render.yaml` 자동 인식 → Deploy
4. 받은 `https://...onrender.com` 주소를 아이폰 사파리에서 열고 "홈 화면에 추가"

## 한계 (v1)
- 상대를 랜덤 레인지로 가정한 EV 조언 (GTO 아님)
- 캐시게임 전용 (토너먼트 ICM 미지원)
- 포지션·상대 레인지 미반영 → Phase 2
```

- [ ] **Step 3: 최종 전체 테스트 & 실행 확인**

Run: `pytest -v`
Expected: 전부 통과 (12 passed)
Run: `uvicorn app.main:app --reload` → http://127.0.0.1:8000 에서 한 핸드 추천 동작 확인.

- [ ] **Step 4: Commit**

```bash
git add render.yaml README.md
git commit -m "chore: Render deploy config and README"
```

---

## 완료 기준 (Definition of Done)

- [ ] `pytest -v` 전부 통과 (engine 3 + decide 7 + api 2 = 12)
- [ ] 로컬 `uvicorn`에서 탭 입력 → 추천 + 음성 동작
- [ ] PWA manifest·SW 등록 확인
- [ ] (사용자) Render 배포 → 아이폰서 접속 → 홈화면 추가
