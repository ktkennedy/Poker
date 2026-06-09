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

  (function initSettings() {
    const s = loadSettings();
    document.getElementById("rfKey").value = s.key;
    document.getElementById("rfModel").value = s.model;
    document.getElementById("rfVersion").value = s.version;
    document.getElementById("rfSave").onclick = () => {
      localStorage.setItem("rfKey", document.getElementById("rfKey").value.trim());
      localStorage.setItem("rfModel", document.getElementById("rfModel").value.trim());
      localStorage.setItem("rfVersion", document.getElementById("rfVersion").value.trim());
      model = null;
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
      const b = p.bbox || p;
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
