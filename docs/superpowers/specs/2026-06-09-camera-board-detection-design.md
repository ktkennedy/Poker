# 카메라 보드 인식 (Camera Board Detection) — Phase 3 설계 문서

- 작성일: 2026-06-09
- 기반: Phase 1 (poker-advisor, FastAPI + treys + 정적 프론트)
- 추가 스택: **roboflow.js (브라우저 내 추론)** — 백엔드 변경 없음

---

## 1. 개요

카메라로 테이블의 **공유카드(보드)를 실시간 인식**해 보드 칸을 자동으로 채운다.
탐지는 **기기 안(roboflow.js, tfjs/WebGL)**에서 돌아 서버 왕복이 없고, 잠자는 Render 백엔드와 무관하게 작동한다.
내 홀카드는 기존처럼 탭 입력(사적). 인식 후 기존 `/advise` 추천 흐름은 그대로.

---

## 2. 범위 (Scope)

- **인식 대상**: 보드(공유카드) 3~5장만. 홀카드·상대 벳은 대상 아님.
- **방식**: 실시간 라이브 오버레이 + "이 보드로 확정" 버튼으로 잡기.
- **추론 위치**: 브라우저 내 roboflow.js (기기 온디바이스).
- **백엔드**: 변경 없음.

### 비대상 (Non-goal)
- 홀카드·칩/벳 인식. 토너먼트. 자동 핸드 진행 추적.

---

## 3. 아키텍처

```
[프론트엔드만 추가 — 백엔드 무변경]
 카메라(getUserMedia, 후면) → <video>
        │
        ▼  requestAnimationFrame 루프
 roboflow.js model.detect(video) → predictions[{class,confidence,bbox}]
        │  (신뢰도 필터 + 라벨→카드코드 매핑)
        ▼
 <canvas> 오버레이에 박스 그림 + 현재 인식 카드 표시
        │  [이 보드로 확정] 탭
        ▼
 app.setBoard(cards)  → 기존 보드 상태 채움 → 탭 수정 가능
        │
        ▼
 기존 "추천 받기" → POST /advise (변경 없음)
```

---

## 4. 구성요소 & 파일

| 파일 | 변경 | 책임 |
|------|------|------|
| `static/camera.js` | **신규** | 카메라 스트림·roboflow.js 초기화·추론 루프·오버레이·라벨매핑·확정 |
| `static/index.html` | 수정 | 카메라 섹션(video/canvas/버튼) + Roboflow 설정칸 + roboflow.js CDN `<script>` |
| `static/app.js` | 수정 | `setBoard(cards)` 노출(카메라→보드 상태 반영) |
| `static/style.css` | 수정 | 카메라 뷰·오버레이 스타일 |

**유닛 경계**: `camera.js`는 카메라/추론을 담당하고, 결과를 `app.setBoard()` 한 함수로만 넘긴다(느슨한 결합). `app.js`는 카메라 존재를 몰라도 됨.

---

## 5. Roboflow 의존성 & 설정

- 사용자가 **무료 Roboflow 계정** 생성 → **publishable API 키** 발급 → 공개 "Playing Cards" 모델 선택(model id + version).
- 앱의 **⚙️ 설정칸**에 키·모델 입력 → **localStorage 저장**. 레포에 키 하드코딩 금지.
- `camera.js`는 localStorage에서 읽어 `roboflow.auth({publishable_key}).load({model, version})`로 초기화.
- 키/모델 미설정 시 → 설정 입력을 안내하고 카메라 비활성.

---

## 6. 라벨 매핑 (순수 함수, 테스트 대상)

모델 클래스 → 우리 카드 코드(rank∈`23456789TJQKA`, suit∈`shdc`).

```
labelToCode("10C") = "Tc"   # 10 → T,  C → c
labelToCode("AS")  = "As"
labelToCode("KH")  = "Kh"
labelToCode("2D")  = "2d"
```
규칙: rank `"10"`→`"T"`, 그 외 그대로; suit 대문자→소문자(C/D/H/S→c/d/h/s).
**주의**: 선택한 모델의 클래스 명명 형식을 확인하고 매핑을 맞춘다(모델마다 다름).

---

## 7. UI 통합

- index 상단에 **"📷 보드 카메라"** 접이식 섹션: `[카메라 켜기]` → video+overlay 표시 → 실시간 박스 → `[이 보드로 확정]` / `[끄기]`.
- 확정 시: 현재 신뢰도 임계값(예: 0.5) 통과한 예측을 dedupe·정렬해 최대 5장 → `setBoard()`.
- 그 아래는 기존 탭 그리드·숫자입력·추천 버튼 그대로(보드는 카메라/탭 어느 쪽으로도 채워짐).

---

## 8. 에러 처리

- **카메라 권한 거부** → 안내 메시지, 수동 탭으로 계속 가능.
- **키/모델 미설정** → 설정 입력 안내.
- **인식 결과가 0장/6장↑/중복/저신뢰** → 잡은 것만 표시하고 탭 수정 유도(쓰레기 자동 확정 금지).
- **roboflow.js 로드 실패·오프라인** → 카메라 비활성, 수동 탭 폴백(앱 핵심 기능은 유지).

---

## 9. 테스트

- **`labelToCode` 유닛테스트**(Node 실행, 순수함수): "10C"→"Tc", "AS"→"As", 잘못된 입력 처리 등.
- **수동 검증**: localhost(보안컨텍스트)에서 PC 웹캠으로 실제/인쇄 카드 비춰 박스·보드채움 확인.
- 기존 백엔드 테스트(16개)는 영향 없음(백엔드 무변경).

---

## 10. HTTPS / 배포

- `getUserMedia`는 **보안 컨텍스트 필수**: `localhost`(개발)와 **HTTPS(Render 배포)**(폰)에서 동작.
- 따라서 폰에서 카메라를 쓰려면 **Render 배포가 전제** → 기능 완성 후 배포 단계 진행.

---

## 11. 정직한 한계

- 실시간 카드 인식은 **조명·각도·카드 겹침**에 민감 → 잘 펴고 밝게. "확정+탭 수정" 단계로 오인식 보정.
- 공개 모델 정확도에 의존(완벽하지 않음). 라벨 형식은 모델별로 다름.

---

## 12. 로드맵

- (본 문서) Phase 3 카메라 보드 인식 + Render 배포
- 이후(선택): 홀카드 스캔, 상대 레인지(Phase 2와 합류), GTO 솔버 연동
