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
