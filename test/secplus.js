'use strict';
// Checks the Sec+ Drill card data and study logic: node test/secplus.js
const assert = require('assert');
const SETS = require('../secplus/cards.js');
const E = require('../secplus/engine.js');

// Data: the four Quizlet sets, complete and well formed.
assert.deepStrictEqual(SETS.map((s) => s.cards.length), [86, 61, 72, 85]);
const deck = E.buildDeck(SETS);
assert.strictEqual(deck.length, 304);
assert.strictEqual(new Set(deck.map((c) => c.id)).size, 304, 'card ids are unique');
for (const c of deck) {
  assert.ok(c.term.trim() && c.def.trim(), 'card ' + c.id + ' has both sides');
  assert.strictEqual(c.term, c.term.trim());
}

// Clue / mnemonic detection.
const clue = (t) => deck.find((c) => c.term === t).clue;
assert.ok(clue('XSS memory trick'));
assert.ok(clue('Biometrics + Passwordless + Public Key Cryptography'));
assert.ok(clue('VPN vs. E2EE'));
assert.ok(clue("Why aren't performance metrics sufficient?"));
assert.ok(!clue('Risk Transference'));
assert.ok(!clue('802.1X'));
assert.ok(!clue('Secure Erase / Sanitize'));

// Typed answers.
const card = (t) => deck.find((c) => c.term === t);
const ok = (t, input) => E.checkAnswer(card(t), input).ok;
assert.ok(ok('Role-Based Access Control (RBAC)', 'rbac'));
assert.ok(ok('Role-Based Access Control (RBAC)', 'role based access control'));
assert.ok(ok('Single Loss Expectancy (SLE)', 'Single Loss Expectancy'));
assert.ok(ok('Secure Erase / Sanitize', 'sanitize'));
assert.ok(ok('802.1X', '802.1x'));
assert.ok(ok('S/MIME', 'smime'));
assert.ok(ok('Credential Stuffing', 'credential stufing'), 'one typo allowed on longer terms');
assert.ok(ok('Annualized Loss Expectancy (ALE)', 'anualized loss expectency'), 'two typos on long terms');
assert.ok(!ok('RBAC', 'abac'), 'acronyms must match exactly');
assert.ok(!ok('RTO', 'rpo'));
assert.ok(!ok('Honeypot', ''));
assert.ok(!ok('Honeypot', 'honeynet'));

// Multiple-choice distractors: three, distinct, never the same concept as the answer.
const pool = deck.filter((c) => !c.clue);
let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
for (const c of pool) {
  const d = E.pickDistractors(c, pool, 3, rnd);
  assert.strictEqual(d.length, 3, 'three distractors for ' + c.term);
  for (const x of d) {
    assert.ok(!x.clue);
    assert.ok(!E.sameConcept(c, x), c.term + ' vs ' + x.term);
    assert.notStrictEqual(E.norm(x.term), E.norm(c.term));
  }
  assert.strictEqual(new Set(d.map((x) => E.norm(x.term))).size, 3);
}
// "RBAC" and "Role-Based Access Control (RBAC)" are the same concept.
assert.ok(E.sameConcept(card('RBAC'), card('Role-Based Access Control (RBAC)')));

// Mastery levels and ordering.
assert.strictEqual(E.grade(0, true), 1);
assert.strictEqual(E.grade(3, true), 3);
assert.strictEqual(E.grade(2, false), 0);
const levels = { 's1-1': 3, 's1-2': 1 };
const ordered = E.order(deck.slice(0, 5), (id) => levels[id] || 0, rnd);
assert.strictEqual(ordered[ordered.length - 1].id, 's1-1', 'mastered cards come last');

console.log('secplus: all checks passed (' + deck.length + ' cards)');
