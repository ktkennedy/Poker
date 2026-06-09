# 포커 어드바이저 (Poker Advisor) — Phase 1 설계 문서

- 작성일: 2026-06-09
- 상태: 사용자 승인 완료 (NLHE 캐시 / 전부 클라이언트 JS / GitHub Pages)

---

## 1. 개요 (Overview)

홈게임·플레이머니 **NLHE 캐시게임**에서, 현재 상황을 입력하면
**폴드 / 체크 / 콜 / 레이즈(+권장 사이즈)** 추천을 **화면과 음성**으로 알려주는 개인용 도구.

- 아이폰 사파리에서 **PWA**로 동작 ("홈 화면에 추가" → 앱처럼)
- **전부 클라이언트 사이드 JavaScript** → 서버 없음 → **GitHub Pages 무료 배포**
- 두뇌는 이미 검증된 몬테카를로 에쿼티 엔진(`poker_equity.py`)을 JavaScript로 포팅해 재사용
  (검증값: AA vs 랜덤 85.2%, AA vs KK 82.6%, 플러시드로우 vs 셋 27% — 교과서값 일치)

---

## 2. 사용 맥락과 합법성 (중요)

- **대상**: 홈게임 / 플레이머니 — 전원 동의된 판. 합법.
- **명시적 비대상 (Non-goal)**: 온라인 포커사이트·카지노의 **실제 머니게임 중 실시간 조언(RTA, Real-Time Assistance)**.
  이는 모든 사이트·카지노에서 금지된 부정행위이며, **본 프로젝트는 이를 지원하지 않는다.**

---

## 3. 범위 (Scope) — Phase 1

| 항목 | 내용 |
|------|------|
| 게임 | No-Limit Texas Hold'em **캐시게임**, 2~9인 |
| 입력 | 홀카드 2장 · 보드 0/3/4/5장 · 상대 수 · 팟 · 콜 금액 · 내 스택 |
| 출력 | 액션(fold/check/call/raise) + 권장 사이즈 + 승률 + 팟오즈 + 이유 + 음성 |
| 플랫폼 | 아이폰 사파리 PWA (홈 화면 추가, 오프라인 동작) |
| 배포 | GitHub Pages (정적 파일) |

### 한계 (정직하게 명시)

- v1은 상대를 **랜덤 레인지**로 가정하고 **칩 EV 최대화**로 조언한다. **GTO 아님** (밸런스·블러프 빈도 미고려).
- **캐시게임 전용** (칩 EV = 돈 EV). 토너먼트(ICM 보정) 미지원.
- 포지션·블라인드 크기·상대 성향 미반영 → Phase 2.

---

## 4. 단계 로드맵

- **Phase 1 (본 문서)**: 수동 탭 입력 + EV 엔진 + 음성 출력
- **Phase 2**: 음성 입력(Web Speech 인식) + 상대 레인지 모델링(타이트/루즈) + 포지션
- **Phase 3**: 카메라 카드 자동 인식 (roboflow.js / TensorFlow.js, `blackjack-basic-strategy` 패턴)
  - 포커 한계: 보드(공유카드) 인식은 쉬움, 홀카드·상대 벳은 어려움 → "보드는 카메라, 내 패는 탭" 하이브리드 현실적

---

## 5. 아키텍처

```
[아이폰 사파리 = PWA]
 ┌──────────────────────────────────────────────┐
 │  index.html   탭 입력 UI                       │
 │      │                                         │
 │      ▼                                         │
 │  app.js       입력 → GameState 객체            │
 │      │                                         │
 │      ▼                                         │
 │  decide.js    GameState → Recommendation       │
 │      │   └ engine.js : eval7 + 몬테카를로 에쿼티 │
 │      ▼                                         │
 │  출력 ─┬─ 화면(액션·승률·이유)                  │
 │        └─ 음성: speechSynthesis                 │
 │                                                │
 │  manifest.json + sw.js → 오프라인·홈화면 설치    │
 └──────────────────────────────────────────────┘
   전부 정적 → GitHub Pages 무료·항상켜짐·오프라인·콜드스타트 없음
```

**데이터 흐름**: 탭 입력 → GameState → `decide()` → Recommendation → 화면 렌더 + 음성 합성

---

## 6. 구성요소 & 파일 구조

```
poker-advisor/                  ← 깃허브 레포 = 그대로 GitHub Pages
├─ index.html                   UI 골격
├─ css/style.css                스타일
├─ js/
│  ├─ engine.js                 card() · eval7() · equity()  (poker_equity.py 포팅)
│  ├─ decide.js                 decide(GameState) → Recommendation  (순수 함수)
│  └─ app.js                    DOM 이벤트 · 입력수집 · 렌더 · 음성출력
├─ manifest.json                PWA 메타(이름·아이콘)
├─ sw.js                        서비스워커(오프라인 캐시)
├─ tests/
│  ├─ engine.test.js            엔진 회귀 테스트 (Node 실행)
│  └─ decide.test.js            결정 로직 경계 테스트
└─ docs/superpowers/specs/      본 설계 문서
```

**유닛 경계 & 인터페이스** (각 파일은 한 가지 일만):

| 유닛 | 책임 | 인터페이스 | 의존 |
|------|------|-----------|------|
| `engine.js` | 카드 평가·에쿼티 | `equity(hole, board, numOpp, trials)` → `{win, tie}` · `eval7(cards7)` → 점수 | 없음 (순수) |
| `decide.js` | 상황 → 추천 | `decide(state)` → `recommendation` | engine.js |
| `app.js` | UI·음성 | 입력→state, recommendation→DOM+음성 | decide.js, Web Speech API |

---

## 7. 데이터 계약 (Contract)

**카드 표기**: `"As"`, `"Td"`, `"7c"` — rank ∈ {2..9,T,J,Q,K,A}, suit ∈ {s,h,d,c}

```jsonc
// 입력 GameState
{
  "hole": ["As", "Kd"],            // 내 홀카드 2장 (필수)
  "board": ["Qs", "7h", "2c"],     // 0·3·4·5장
  "numOpponents": 2,               // 아직 안 죽은 상대 수 (1~8)
  "pot": 100,                      // 현재 팟
  "toCall": 30,                    // 콜에 필요한 금액 (0이면 체크 가능)
  "myStack": 500                   // 내 스택 (올인·사이징 판단)
}

// 출력 Recommendation
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

## 8. 결정 로직 (decide.js)

모든 스트리트에서 **에쿼티를 라이브 계산**(프리플롭 포함 → 별도 차트 불필요).
임계값은 v1 휴리스틱이며 추후 조정 가능.

```
decide(state):
  validate(state)                                  # 카드 중복/장수/음수 검사
  eq = equity(hole, board, numOpponents, 20000)    # vs 랜덤레인지, 몬테카를로

  RAISE_EQ = 0.65                                   # v1 휴리스틱

  if toCall == 0:                                   # 아무도 벳 안 함
      if eq >= RAISE_EQ:  action=raise, size=round(0.6 * pot)   # 밸류벳
      else:               action=check
  else:                                             # 벳 받음
      required = toCall / (pot + toCall)            # 팟오즈(필요 승률)
      evCall   = eq * pot - (1 - eq) * toCall       # 콜 기댓값
      if   eq <  required:   action=fold
      elif eq <  RAISE_EQ:   action=call
      else:                  action=raise, size=round(pot + 2*toCall)  # 팟사이즈 근사

  # 스택 보정
  if size != null and size >= myStack:  size=myStack, label="올인"
  if action==call and toCall >= myStack: label="콜 올인"

  reason, speech 문장 생성
  return recommendation
```

---

## 9. 에러 처리

- **입력 검증 실패**(카드 중복 "As" 2번 · 장수 오류 · 음수 팟/스택 · 보드 4장 등 불가 상태)
  → 추천을 내지 않고 **한글 안내 메시지** 표시.
- **speechSynthesis 미지원/차단** 브라우저 → 화면 출력만, 음성은 우아하게 생략(graceful degrade).
- 몬테카를로는 결정적 시드 사용 → 같은 입력 = 같은 출력(재현성).

---

## 10. 테스트 전략

- **engine.test.js** (회귀): 검증된 값 고정
  - AA vs 랜덤 = 85% ±0.5
  - AA vs KK = 82.6% ±0.5
  - 플러시드로우 vs 셋 = 27% ±1
- **decide.test.js** (경계):
  - 에쿼티 90%인데 fold 추천 → 실패
  - toCall=0 → check 또는 raise만 가능
  - eq < potOdds → 반드시 fold
  - size > myStack → 올인으로 캡
- **실행 환경**: Node.js (npm 의존성 0, 순수 JS). `node tests/engine.test.js`

---

## 11. 배포 (GitHub Pages)

- 레포 `poker-advisor`의 `main` 브랜치(루트 또는 `/docs`)를 GitHub Pages 소스로 지정
- GitHub Pages는 **HTTPS 자동 제공** → Phase 3 카메라(`getUserMedia`)의 보안 컨텍스트 요건 충족
- 아이폰 사파리에서 URL 접속 → 공유 → **"홈 화면에 추가"** → 앱 아이콘 + 오프라인 동작

---

## 12. 재사용 오픈소스 (참고 — 주로 Phase 2~3)

| 영역 | 오픈소스 | 라이선스 주의 |
|------|----------|--------------|
| 카드 비전 | Roboflow "Playing Cards" 모델, geaxgx/playing-card-detection, **roboflow/blackjack-basic-strategy**(브라우저 CV 패턴 레퍼런스) | 모델별 확인 |
| GTO 솔버 | wasm-postflop(브라우저), bupticybee/TexasSolver | **AGPL-v3** |
| 핸드평가 | treys, eval7 (Python) | — |
| 음성 | Web Speech API (브라우저 내장) | — |

---

## 13. 추후 결정 (Phase 1 구현 중/이후)

- PWA 아이콘·앱 이름
- 베팅 사이즈 휴리스틱 미세조정
- (Phase 2) 상대 레인지 프리셋(타이트/루즈), 포지션 반영
