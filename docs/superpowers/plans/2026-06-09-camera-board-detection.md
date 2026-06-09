# 카메라 보드 인식 (Camera Board Detection) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카메라로 보드(공유카드)를 실시간 인식해 보드 칸을 자동으로 채우는 기능을 기존 poker-advisor 프론트엔드에 추가한다.

**Architecture:** 순수 프론트엔드 추가. roboflow.js로 기기 내에서 카드 탐지 → 라벨을 우리 카드코드로 변환 → `setBoard()`로 기존 보드 상태에 주입. 백엔드(FastAPI)는 전혀 건드리지 않는다.

**Tech Stack:** 바닐라 JS, roboflow.js(CDN, 브라우저 내 추론), getUserMedia, Node(순수함수 유닛테스트 + 문법검증)

---

## 파일 구조

```
poker-advisor/
├─ static/
│  ├─ cards.js        ← 신규: 순수 변환 함수(labelToCode·pickBoardCards·sanitizeBoard), 브라우저+Node 공용
│  ├─ camera.js       ← 신규: 카메라·roboflow 추론·오버레이·확정
│  ├─ index.html      ← 수정: 카메라 섹션·설정칸·roboflow CDN·script 태그
│  ├─ app.js          ← 수정: setBoard() 추가·전역 노출
│  └─ style.css       ← 수정: 카메라 뷰 스타일
└─ tests/
   └─ cards.test.js   ← 신규: Node 유닛테스트
```

**전제:** Node.js 설치되어 있어야 함(순수함수 테스트 + JS 문법검증용). `node --version`으로 확인.

**인터페이스 계약 (태스크 간 고정):**
- `labelToCode(cls: string) -> string|null` — 모델 클래스("10C") → 카드코드("Tc"), 무효면 null
- `pickBoardCards(predictions: {class,confidence}[], threshold=0.5) -> string[]` — 신뢰도 필터·중복제거·최대 5장
- `sanitizeBoard(codes: string[], hole: string[]) -> string[]` — 홀카드 제외·중복제거·최대 5장
- `window.setBoard(codes: string[]) -> void` — 보드 상태 채우고 UI 갱신
- 카드코드: rank `23456789TJQKA` + suit `shdc` (예: "As","Td","7c") — Phase 1과 동일

---

## Task 1: 순수 변환 함수 `cards.js` (TDD, Node)

**Files:**
- Create: `static/cards.js`, `tests/cards.test.js`

- [ ] **Step 1: Node 설치 확인**

Run: `node --version`
Expected: v18 이상 버전 출력. (없으면 BLOCKED로 보고)

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/cards.test.js`:
```javascript
const { test } = require("node:test");
const assert = require("node:assert");
const { labelToCode, pickBoardCards, sanitizeBoard } = require("../static/cards.js");

test("labelToCode: 모델 클래스 → 카드코드", () => {
  assert.strictEqual(labelToCode("10C"), "Tc");
  assert.strictEqual(labelToCode("AS"), "As");
  assert.strictEqual(labelToCode("KH"), "Kh");
  assert.strictEqual(labelToCode("2D"), "2d");
  assert.strictEqual(labelToCode("jc"), "Jc");   // 소문자 허용
});

test("labelToCode: 무효 입력 → null", () => {
  assert.strictEqual(labelToCode("Joker"), null);
  assert.strictEqual(labelToCode(""), null);
  assert.strictEqual(labelToCode(null), null);
});

test("pickBoardCards: 신뢰도 필터·중복제거·신뢰도순·최대 5장", () => {
  const preds = [
    { class: "AS", confidence: 0.90 },
    { class: "AS", confidence: 0.80 },   // 중복
    { class: "KH", confidence: 0.70 },
    { class: "2D", confidence: 0.30 },   // 임계 미만 → 제외
    { class: "Joker", confidence: 0.95 },// 무효 → 제외
    { class: "QC", confidence: 0.60 },
    { class: "JD", confidence: 0.55 },
    { class: "10H", confidence: 0.85 },
    { class: "9S", confidence: 0.51 },   // 6번째 → 잘림
  ];
  assert.deepStrictEqual(pickBoardCards(preds, 0.5), ["As", "Th", "Kh", "Qc", "Jd"]);
});

test("sanitizeBoard: 홀카드 제외·중복제거·최대 5장", () => {
  assert.deepStrictEqual(
    sanitizeBoard(["As", "Kh", "As", "2d", "3c", "4s", "5h"], ["2d"]),
    ["As", "Kh", "3c", "4s", "5h"]
  );
});
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `node --test tests/cards.test.js` (poker-advisor 디렉터리에서)
Expected: FAIL — Cannot find module '../static/cards.js'

- [ ] **Step 4: `cards.js` 구현**

`static/cards.js`:
```javascript
// 카드 라벨/탐지결과 → 우리 카드코드 변환 (순수 함수, 브라우저+Node 공용)
const _SUIT_MAP = { C: "c", D: "d", H: "h", S: "s" };

function labelToCode(cls) {
  if (typeof cls !== "string") return null;
  const m = cls.trim().toUpperCase().match(/^(10|[2-9]|[TJQKA])([CDHS])$/);
  if (!m) return null;
  const rank = m[1] === "10" ? "T" : m[1];
  return rank + _SUIT_MAP[m[2]];
}

function pickBoardCards(predictions, threshold = 0.5) {
  const seen = new Set();
  const out = [];
  const sorted = (predictions || [])
    .filter((p) => p && typeof p.confidence === "number" && p.confidence >= threshold)
    .sort((a, b) => b.confidence - a.confidence);
  for (const p of sorted) {
    const code = labelToCode(p.class);
    if (code && !seen.has(code)) {
      seen.add(code);
      out.push(code);
      if (out.length === 5) break;
    }
  }
  return out;
}

function sanitizeBoard(codes, hole) {
  const block = new Set(hole || []);
  const seen = new Set();
  const out = [];
  for (const c of (codes || [])) {
    if (!block.has(c) && !seen.has(c)) {
      seen.add(c);
      out.push(c);
      if (out.length === 5) break;
    }
  }
  return out;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { labelToCode, pickBoardCards, sanitizeBoard };
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `node --test tests/cards.test.js`
Expected: PASS (4 tests pass)

- [ ] **Step 6: Commit**

```bash
git add static/cards.js tests/cards.test.js
git commit -m "feat: pure card label/board helpers with node tests"
```

---

## Task 2: `app.js` — `setBoard()` 통합

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: `setBoard` 추가**

`static/app.js`의 `reset` 함수 **바로 아래**에 다음을 추가:
```javascript
function setBoard(codes) {
  state.board = sanitizeBoard(codes, state.hole);
  refresh();
}
window.setBoard = setBoard;
```
(`sanitizeBoard`는 `cards.js`에서 전역 제공 — index.html에서 cards.js를 app.js보다 먼저 로드함. Task 3에서 처리.)

- [ ] **Step 2: 문법 검증**

Run: `node --check static/app.js`
Expected: 출력 없음(성공). 오류 출력 시 수정.

- [ ] **Step 3: Commit**

```bash
git add static/app.js
git commit -m "feat: expose setBoard() for camera integration"
```

---

## Task 3: `index.html` + `style.css` — 카메라 UI·설정·CDN

**Files:**
- Modify: `static/index.html`, `static/style.css`

- [ ] **Step 1: `index.html` 전체를 아래로 교체**

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
  <script src="https://cdn.roboflow.com/0.2.26/roboflow.js"></script>
</head>
<body>
  <h1>♠ 포커 어드바이저</h1>

  <details class="camera">
    <summary>📷 보드 카메라</summary>
    <div class="cam-settings">
      <input id="rfKey" type="text" placeholder="Roboflow publishable 키">
      <input id="rfModel" type="text" placeholder="모델 id (예: playing-cards-xxx)">
      <input id="rfVersion" type="number" placeholder="버전" min="1" value="1">
      <button id="rfSave">설정 저장</button>
    </div>
    <div class="cam-view">
      <video id="cam" playsinline muted></video>
      <canvas id="overlay"></canvas>
    </div>
    <div id="camCards" class="sel">인식: (없음)</div>
    <div class="btns">
      <button id="camStart" class="primary">카메라 켜기</button>
      <button id="camConfirm">이 보드로 확정</button>
      <button id="camStop">끄기</button>
    </div>
  </details>

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

  <script src="/cards.js"></script>
  <script src="/app.js"></script>
  <script src="/camera.js"></script>
</body>
</html>
```

- [ ] **Step 2: `style.css` 끝에 카메라 스타일 추가**

`static/style.css` 파일 맨 끝에 추가:
```css
.camera { margin-bottom:12px; background:#14543f; border-radius:10px; padding:8px 12px; }
.camera summary { cursor:pointer; font-size:15px; }
.cam-settings { display:flex; flex-direction:column; gap:6px; margin:8px 0; }
.cam-settings input { padding:8px; border-radius:6px; border:none; font-size:14px; }
.cam-view { position:relative; width:100%; margin:8px 0; }
.cam-view video, .cam-view canvas { width:100%; border-radius:8px; display:block; }
.cam-view canvas { position:absolute; top:0; left:0; }
```

- [ ] **Step 3: 서빙 확인**

Run:
```
C:\Users\USER-\Downloads\poker-advisor\.venv\Scripts\python.exe -c "import os,sys; os.chdir(r'C:\Users\USER-\Downloads\poker-advisor'); sys.path.insert(0,'.'); from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); r=c.get('/'); print('index', r.status_code, '보드 카메라' in r.text); print('cards.js', c.get('/cards.js').status_code)"
```
Expected: `index 200 True`, `cards.js 200`.
(`/camera.js`는 Task 4에서 생성하므로 아직 404일 수 있음 — 정상.)

- [ ] **Step 4: Commit**

```bash
git add static/index.html static/style.css
git commit -m "feat: camera section UI, settings, roboflow CDN"
```

---

## Task 4: `camera.js` — 카메라 + roboflow 추론

**Files:**
- Create: `static/camera.js`

> **외부 SDK 확인:** roboflow.js는 버전에 따라 CDN URL과 예측 포맷이 다를 수 있다. 구현 후 동작이 이상하면 현재 roboflow.js 문서(https://docs.roboflow.com → web/browser 배포)에서 CDN URL과 `model.detect()` 반환 포맷(특히 bbox)을 확인해 조정한다. 아래 코드는 `roboflow.auth().load()` / `model.detect()` / 예측 `{class, confidence, bbox:{x,y,width,height}}`(또는 평면형) 기준이며 둘 다 처리한다.

- [ ] **Step 1: `camera.js` 구현**

`static/camera.js`:
```javascript
// 카메라 보드 인식 — getUserMedia + roboflow.js(기기내 추론) → setBoard
(function () {
  const video = document.getElementById("cam");
  const canvas = document.getElementById("overlay");
  const ctx = canvas.getContext("2d");
  const camCards = document.getElementById("camCards");

  let model = null, stream = null, running = false, latest = [];

  function loadSettings() {
    return {
      key: (localStorage.getItem("rfKey") || "").trim(),
      model: (localStorage.getItem("rfModel") || "").trim(),
      version: parseInt(localStorage.getItem("rfVersion") || "1", 10),
    };
  }

  // 저장된 설정을 입력칸에 채우고, 저장 버튼 연결
  (function initSettings() {
    const s = loadSettings();
    document.getElementById("rfKey").value = s.key;
    document.getElementById("rfModel").value = s.model;
    document.getElementById("rfVersion").value = s.version;
    document.getElementById("rfSave").onclick = () => {
      localStorage.setItem("rfKey", document.getElementById("rfKey").value.trim());
      localStorage.setItem("rfModel", document.getElementById("rfModel").value.trim());
      localStorage.setItem("rfVersion", document.getElementById("rfVersion").value.trim());
      model = null; // 설정 바뀌면 모델 재로딩
      camCards.textContent = "설정 저장됨";
    };
  })();

  async function start() {
    const s = loadSettings();
    if (!s.key || !s.model) { camCards.textContent = "먼저 Roboflow 키/모델을 저장하세요"; return; }
    if (typeof roboflow === "undefined") { camCards.textContent = "roboflow.js 로드 실패(온라인 확인)"; return; }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    } catch (e) { camCards.textContent = "카메라 권한 거부됨"; return; }
    video.srcObject = stream;
    await video.play();
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    camCards.textContent = "모델 로딩 중...";
    try {
      if (!model) {
        model = await roboflow.auth({ publishable_key: s.key }).load({ model: s.model, version: s.version });
      }
    } catch (e) { camCards.textContent = "모델 로드 실패: 키/모델 확인"; return; }
    running = true;
    loop();
  }

  function loop() {
    if (!running) return;
    model.detect(video).then((preds) => {
      latest = preds || [];
      draw(latest);
      const codes = pickBoardCards(latest, 0.5);
      camCards.textContent = "인식: " + (codes.join(" ") || "(없음)");
      requestAnimationFrame(loop);
    }).catch(() => { if (running) requestAnimationFrame(loop); });
  }

  function draw(preds) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#f0c419";
    ctx.fillStyle = "#f0c419";
    ctx.font = "16px sans-serif";
    for (const p of preds) {
      const b = p.bbox || p;                 // 버전별 포맷 모두 처리
      if (typeof b.x !== "number") continue;
      const x = b.x - b.width / 2, y = b.y - b.height / 2;
      ctx.strokeRect(x, y, b.width, b.height);
      ctx.fillText(String(p.class), x + 2, y - 4);
    }
  }

  function stop() {
    running = false;
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  function confirmBoard() {
    const codes = pickBoardCards(latest, 0.5);
    if (codes.length === 0) { camCards.textContent = "인식된 카드가 없습니다"; return; }
    window.setBoard(codes);
    camCards.textContent = "보드 확정: " + codes.join(" ");
  }

  document.getElementById("camStart").onclick = start;
  document.getElementById("camStop").onclick = stop;
  document.getElementById("camConfirm").onclick = confirmBoard;
})();
```

- [ ] **Step 2: 문법 검증**

Run: `node --check static/camera.js`
Expected: 출력 없음(성공).

- [ ] **Step 3: 서빙 확인**

Run:
```
C:\Users\USER-\Downloads\poker-advisor\.venv\Scripts\python.exe -c "import os,sys; os.chdir(r'C:\Users\USER-\Downloads\poker-advisor'); sys.path.insert(0,'.'); from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); print('camera.js', c.get('/camera.js').status_code)"
```
Expected: `camera.js 200`.

- [ ] **Step 4: Commit**

```bash
git add static/camera.js
git commit -m "feat: camera board detection via roboflow.js"
```

---

## Task 5: README — 카메라 사용법·Roboflow 설정

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README 끝에 카메라 섹션 추가**

`README.md` 맨 끝에 추가:
```markdown

## 📷 보드 카메라 (Phase 3)

카메라로 보드(공유카드)를 실시간 인식해 자동으로 채웁니다. 내 홀카드는 탭으로.

### 1회 설정 (Roboflow)
1. roboflow.com 무료 가입 → Settings → **Publishable API Key** 복사
2. 공개 "Playing Cards" 모델 선택(Roboflow Universe) → 모델 id와 버전 확인
3. 앱의 "📷 보드 카메라" → 키·모델 id·버전 입력 → **설정 저장**

### 사용
1. "카메라 켜기" → 보드를 화면에 맞춤 → 카드에 박스가 뜸
2. "이 보드로 확정" → 보드 칸 자동 채움 → 틀리면 탭으로 수정
3. 내 패 2장 탭 → "추천 받기"

### 주의
- **폰에서 카메라는 HTTPS 필요** → Render 배포 후 사용. PC는 `http://127.0.0.1:8000`(localhost)에서 됨.
- 인식은 조명·각도·겹침에 민감. 잘 펴고 밝게. 확정 후 탭 수정으로 보정.
```

- [ ] **Step 2: 순수함수 테스트 재확인 + 백엔드 테스트 무영향 확인**

Run: `node --test tests/cards.test.js`
Expected: 4 tests pass.
Run: `C:\Users\USER-\Downloads\poker-advisor\.venv\Scripts\python.exe -m pytest -q`
Expected: 16 passed (백엔드 무변경).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: camera usage and Roboflow setup"
```

---

## 완료 기준 (Definition of Done)

- [ ] `node --test tests/cards.test.js` 통과 (4)
- [ ] `node --check static/app.js` / `static/camera.js` 문법 OK
- [ ] `pytest -q` 여전히 16 passed (백엔드 무변경)
- [ ] index/cards.js/camera.js 모두 서빙 200
- [ ] (사용자) localhost 웹캠으로 카드 비춰 박스·보드채움 확인
- [ ] (사용자) Render 배포 → 아이폰서 카메라 동작

## 배포 (구현 후 별도 진행)

폰 카메라용 HTTPS를 위해 Render 배포가 필요. 컨트롤러가 사용자와 대화형으로 진행:
1. GitHub 레포 생성·push
2. render.com → New Web Service → 레포 연결 → `render.yaml` 자동 → Deploy
3. `https://...onrender.com` → 아이폰 사파리 → 홈 화면 추가
