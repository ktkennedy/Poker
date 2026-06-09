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
