# 포커 어드바이저 (Poker Advisor) — Phase 1 설계 문서

- 작성일: 2026-06-09
- 상태: 사용자 승인 완료
- 스택 확정: **Python / FastAPI / treys / Render** (Python 백엔드 + 정적 프론트, 한 레포)

---

## 1. 개요 (Overview)

홈게임·플레이머니 **NLHE 캐시게임**에서, 현재 상황을 입력하면
**폴드 / 체크 / 콜 / 레이즈(+권장 사이즈)** 추천을 **화면과 음성**으로 알려주는 개인용 웹앱.

- **백엔드**: Python **FastAPI** — 두뇌(`treys` 평가기 + 몬테카를로) 실행 + 정적 프론트 서빙
- **프론트**: 정적 HTML/JS (탭 입력 + 음성 출력), 백엔드와 **같은 주소**(CORS 없음)
- **배포**: **Render** 무료 — GitHub push → 자동 배포 → HTTPS 주소
- **폰**: 아이폰 사파리로 주소 접속 → "홈 화면에 추가" (PWA)

두뇌 엔진은 **[treys](https://github.com/ihendley/treys)**(검증된 순수 파이썬 평가기, 1~7462 랭킹) +
우리의 **"vs N 랜덤" 몬테카를로 래퍼**(검증값: AA 85%, AA vs KK 82.6%)를 결합한다.

---

## 2. 사용 맥락과 합법성 (중요)

- **대상**: 홈게임 / 플레이머니 — 전원 동의된 판. 합법.
- **명시적 비대상 (Non-goal)**: 온라인 사이트·카지노 **실제 머니게임 중 실시간 조언(RTA)**.
  모든 사이트·카지노에서 금지된 부정행위이며 **본 프로젝트는 지원하지 않는다.**

---

## 3. 범위 (Scope) — Phase 1

| 항목 | 내용 |
|------|------|
| 게임 | No-Limit Texas Hold'em **캐시게임**, 2~9인 |
| 입력 | 홀카드 2장 · 보드 0/3/4/5장 · 상대 수 · 팟 · 콜 금액 · 내 스택 |
| 출력 | 액션(fold/check/call/raise) + 권장 사이즈 + 승률 + 팟오즈 + 이유 + 음성 |
| 폰 | 아이폰 사파리 → 홈 화면 추가 (PWA) |
| 배포 | Render (GitHub 자동배포, HTTPS) |

### 한계 (정직하게 명시)

- v1은 상대를 **랜덤 레인지**로 가정하고 **칩 EV 최대화**로 조언한다. **GTO 아님**.
- **캐시게임 전용** (칩 EV = 돈 EV). 토너먼트(ICM) 미지원.
- 포지션·블라인드·상대 성향 미반영 → Phase 2.

---

## 4. 단계 로드맵

- **Phase 1 (본 문서)**: 수동 탭 입력 + treys/MC 엔진 + 음성 출력
- **Phase 2**: 음성 입력(Web Speech) + 상대 레인지 모델링 + 포지션
- **Phase 3**: 카메라 카드 자동 인식 (브라우저 CV: roboflow.js/tfjs, 또는 백엔드 추론)

---

## 5. 아키텍처

```
[아이폰 사파리 = PWA]            HTTPS / JSON           [Render: FastAPI 서버]
 정적 프론트 (같은 주소)   ─── POST /advise ──►   app/main.py
 - index.html 탭 입력 UI                            │  ├ 정적 프론트 서빙(StaticFiles)
 - app.js 상태수집·음성출력  ◄── Recommendation ──   │  └ /advise 엔드포인트
 - speechSynthesis "폴드해"                          ▼
                                                  app/decide.py  (상태→추천, 순수)
                                                     └ app/engine.py
                                                          treys 평가 + 몬테카를로 equity
```

**데이터 흐름**: 탭 입력 → GameState(JSON) → `POST /advise` → `decide()` → Recommendation(JSON) → 화면 + 음성
프론트·백엔드가 **같은 origin**(FastAPI가 정적 파일도 서빙) → CORS 불필요.

---

## 6. 구성요소 & 파일 구조

```
poker-advisor/                  ← GitHub 레포 = Render 자동배포 대상
├─ app/
│  ├─ __init__.py
│  ├─ main.py                   FastAPI: POST /advise + 정적 프론트 서빙
│  ├─ engine.py                 treys + 몬테카를로 equity()  (순수)
│  └─ decide.py                 decide(GameState) → Recommendation  (순수)
├─ static/
│  ├─ index.html                탭 입력 UI
│  ├─ app.js                    입력수집 · fetch(/advise) · 음성출력
│  ├─ style.css
│  ├─ manifest.json             PWA 메타
│  └─ sw.js                     서비스워커(오프라인 셸 캐시)
├─ tests/
│  ├─ test_engine.py            엔진 회귀 (검증값 고정)
│  ├─ test_decide.py            결정 로직 경계
│  └─ test_api.py               /advise 엔드포인트 (TestClient)
├─ requirements.txt             fastapi · uvicorn · treys · pytest
├─ render.yaml                  Render 배포 설정
├─ README.md
└─ docs/superpowers/specs/      본 설계 문서
```

**유닛 경계 & 인터페이스** (각 파일 한 가지 일만):

| 유닛 | 책임 | 인터페이스 | 의존 |
|------|------|-----------|------|
| `engine.py` | 카드 평가·에쿼티 | `equity(hole, board, num_opp, trials)` → `(win, tie)` | treys |
| `decide.py` | 상황 → 추천 | `decide(state: dict)` → `dict` | engine |
| `main.py` | HTTP·서빙 | `POST /advise` (GameState→Recommendation), 정적서빙 | fastapi, decide |
| `app.js` | UI·음성 | 입력→state, fetch, recommendation→DOM+음성 | Web Speech, fetch |

---

## 7. 데이터 계약 (Contract)

**카드 표기**: `"As"`, `"Td"`, `"7c"` — rank ∈ {2..9,T,J,Q,K,A}, suit ∈ {s,h,d,c} (treys `Card.new` 호환)

```jsonc
// 요청 POST /advise  (GameState)
{
  "hole": ["As", "Kd"],            // 내 홀카드 2장 (필수)
  "board": ["Qs", "7h", "2c"],     // 0·3·4·5장
  "numOpponents": 2,               // 아직 안 죽은 상대 수 (1~8)
  "pot": 100,                      // 현재 팟
  "toCall": 30,                    // 콜에 필요한 금액 (0이면 체크 가능)
  "myStack": 500                   // 내 스택 (올인·사이징 판단)
}

// 응답 (Recommendation)
{
  "action": "call",                // "fold" | "check" | "call" | "raise"
  "size": null,                    // raise일 때 권장 금액, 아니면 null
  "equity": 0.42,                  // 내 승률 추정 (0~1)
  "potOdds": 0.25,                 // 필요 승률
  "evCall": 12.5,                  // 콜의 기댓값 (칩)
  "reason": "에쿼티 42% > 필요 25%, +EV 콜",
  "speech": "콜. 승률 42퍼센트."     // 음성으로 읽을 문장
}
```

---

## 8. 엔진 로직 (engine.py — treys + 몬테카를로)

treys: `evaluate(board, hand)` → 랭크 정수(**낮을수록 강함**, 1=로열, 7462=최약).
몬테카를로는 매판 **보드를 5장까지 채워** 7장(보드5+홀2)으로 평가 → 프리플롭도 동일 처리.

```
equity(hole, board, num_opp, trials=20000):
    dead = hole + board
    deck = 52장 − dead
    need = 5 - len(board)
    win = tie = 0
    repeat trials:
        sample = random.sample(deck, 2*num_opp + need)
        opp_holes  = sample 앞쪽을 2장씩
        full_board = board + sample 뒤쪽 need장
        hero = evaluate(full_board, hole)            # 낮을수록 강함
        best_opp = min(evaluate(full_board, oh) for oh in opp_holes)
        if   hero < best_opp: win += 1
        elif hero == best_opp: tie += 1
    return win/trials, tie/trials
```

---

## 9. 결정 로직 (decide.py)

모든 스트리트에서 에쿼티 라이브 계산(프리플롭 포함). 임계값은 v1 휴리스틱(조정 가능).

```
decide(state):
    validate(state)                                  # 카드 중복/장수/음수
    win, tie = equity(hole, board, numOpponents, 20000)
    eq = win + tie/2

    RAISE_EQ = 0.65
    if toCall == 0:                                  # 벳 없음
        if eq >= RAISE_EQ: action=raise, size=round(0.6*pot)   # 밸류벳
        else:              action=check
    else:                                            # 벳 받음
        required = toCall / (pot + toCall)           # 팟오즈
        evCall   = eq*pot - (1-eq)*toCall
        if   eq <  required: action=fold
        elif eq <  RAISE_EQ: action=call
        else:                action=raise, size=round(pot + 2*toCall)

    # 스택 보정: size >= myStack → 올인 캡
    reason·speech 문장 생성
    return recommendation
```

---

## 10. 에러 처리

- **입력 검증 실패**(카드 중복·장수 오류·음수·보드 4장 불가 등) → `400` + 한글 메시지, 추천 안 함.
- **음성 미지원/차단** 브라우저 → 화면 출력만(graceful degrade).
- 몬테카를로 시드 고정 → 같은 입력 = 같은 출력(재현성).
- Render 콜드스타트(첫 접속 ~30초) → 프론트에 "깨우는 중" 로딩 표시.

---

## 11. 테스트 전략 (pytest)

- **test_engine.py** (회귀): AA vs 랜덤 ≈ 0.85(±0.01) · AA vs KK(상대고정) ≈ 0.826 · 플러시드로우 vs 셋 ≈ 0.27
- **test_decide.py** (경계): 에쿼티 0.9인데 fold면 실패 · toCall=0→check/raise만 · eq<potOdds→fold · size>myStack→올인 캡
- **test_api.py**: FastAPI `TestClient`로 `POST /advise` 정상/검증실패 응답
- 실행: `pytest`

---

## 12. 배포 (Render)

- `requirements.txt`: fastapi, uvicorn, treys, pytest
- 시작 명령: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `render.yaml`로 설정, GitHub 레포 연결 → push마다 자동 배포, **HTTPS 자동**
- 아이폰 사파리 접속 → 공유 → "홈 화면에 추가" → 앱 아이콘
- 캐비엇: 무료 티어 15분 비활성 시 슬립(첫 접속 ~30초 웨이크). 거슬리면 Railway/HF Spaces로 이전(코드 동일)

---

## 13. 재사용 오픈소스 (참고)

| 영역 | 오픈소스 | 비고 |
|------|----------|------|
| 핸드평가 | **treys** (Phase 1 채택), eval7, PokerKit | treys = 순수 파이썬·검증·빠름 |
| 카드 비전 (Phase 3) | Roboflow "Playing Cards", geaxgx/playing-card-detection, roboflow/blackjack-basic-strategy | 브라우저 CV 패턴 |
| GTO 솔버 (이후) | wasm-postflop, bupticybee/TexasSolver | AGPL-v3 주의 |
| 음성 | Web Speech API (브라우저 내장) | 입력·출력 |

---

## 14. 추후 결정 (Phase 1 구현 중/이후)

- PWA 아이콘·앱 이름
- 베팅 사이즈 휴리스틱 미세조정
- (Phase 2) 상대 레인지 프리셋(타이트/루즈), 포지션 반영
