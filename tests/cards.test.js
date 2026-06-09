const { test } = require("node:test");
const assert = require("node:assert");
const { labelToCode, pickBoardCards, sanitizeBoard } = require("../static/cards.js");

test("labelToCode: 모델 클래스 → 카드코드", () => {
  assert.strictEqual(labelToCode("10C"), "Tc");
  assert.strictEqual(labelToCode("AS"), "As");
  assert.strictEqual(labelToCode("KH"), "Kh");
  assert.strictEqual(labelToCode("2D"), "2d");
  assert.strictEqual(labelToCode("jc"), "Jc");
});

test("labelToCode: 무효 입력 → null", () => {
  assert.strictEqual(labelToCode("Joker"), null);
  assert.strictEqual(labelToCode(""), null);
  assert.strictEqual(labelToCode(null), null);
});

test("pickBoardCards: 신뢰도 필터·중복제거·신뢰도순·최대 5장", () => {
  const preds = [
    { class: "AS", confidence: 0.90 },
    { class: "AS", confidence: 0.80 },
    { class: "KH", confidence: 0.70 },
    { class: "2D", confidence: 0.30 },
    { class: "Joker", confidence: 0.95 },
    { class: "QC", confidence: 0.60 },
    { class: "JD", confidence: 0.55 },
    { class: "10H", confidence: 0.85 },
    { class: "9S", confidence: 0.51 },
  ];
  assert.deepStrictEqual(pickBoardCards(preds, 0.5), ["As", "Th", "Kh", "Qc", "Jd"]);
});

test("sanitizeBoard: 홀카드 제외·중복제거·최대 5장", () => {
  assert.deepStrictEqual(
    sanitizeBoard(["As", "Kh", "As", "2d", "3c", "4s", "5h"], ["2d"]),
    ["As", "Kh", "3c", "4s", "5h"]
  );
});
