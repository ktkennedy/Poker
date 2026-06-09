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
  const btn = document.getElementById("adviseBtn");
  btn.disabled = true;
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
    if (!res.ok) {
      const msg = data.error || (data.detail && data.detail[0]?.msg) || res.status;
      out.textContent = "오류: " + msg; return;
    }
    render(data);
  } catch (e) { out.textContent = "네트워크 오류: " + e.message; }
  finally { btn.disabled = false; }
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
