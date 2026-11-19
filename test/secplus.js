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

// Domains: every card tagged 1-5, and every domain has cards.
for (const s of SETS) assert.strictEqual(s.domains.length, s.cards.length, s.id + ' domain tags line up');
for (const c of deck) assert.ok(c.domain >= 1 && c.domain <= 5, 'domain for ' + c.id);
const perDomain = [1, 2, 3, 4, 5].map((d) => deck.filter((c) => c.domain === d).length);
assert.ok(perDomain.every((n) => n >= 20), 'each domain has cards: ' + perDomain);
assert.strictEqual(card('Annualized Loss Expectancy (ALE)').domain, 5);
assert.strictEqual(card('Directory Traversal').domain, 2);
assert.strictEqual(card('Honeyfile').domain, 1);
assert.strictEqual(E.DOMAINS.reduce((a, d) => a + d.w, 0), 100);

// Scenarios: well formed, unique ids and options, all domains covered.
const SCN = E.buildScenarios(require('../secplus/scenarios.js'));
assert.strictEqual(new Set(SCN.map((q) => q.id)).size, SCN.length);
for (const q of SCN) {
  assert.strictEqual(q.opts.length, 4, q.id);
  assert.strictEqual(new Set(q.opts).size, 4, q.id + ' options unique');
  assert.ok(q.c >= 0 && q.c < 4 && q.why && q.q.length > 20, q.id);
  assert.ok(q.domain >= 1 && q.domain <= 5, q.id);
}
for (let d = 1; d <= 5; d++) assert.ok(SCN.filter((q) => q.domain === d).length >= 8, 'scenarios in domain ' + d);

// Readiness: weighted by exam share; the weakest heavy domain is flagged.
const all = deck.concat(SCN);
assert.strictEqual(E.readiness(all, () => 0).overall, 0);
assert.strictEqual(E.readiness(all, () => 3).overall, 1);
const r = E.readiness(all, (id) => (all.find((x) => x.id === id).domain === 4 ? 0 : 3));
assert.strictEqual(r.focus.n, 4);
assert.ok(Math.abs(r.overall - 0.72) < 1e-9, 'domain 4 is 28% of the exam');
console.log('secplus: domains ' + perDomain.join('/') + ', ' + SCN.length + ' scenarios ok');

// Labs: every answer key passes its own checker; firewall labs start broken.
const LB = require('../secplus/labs.js');
for (const lab of LB.LABS) {
  assert.ok(LB.TYPES[lab.type] && lab.d >= 1 && lab.d <= 5 && lab.why, lab.id);
  if (lab.type === 'hunt') {
    assert.ok(LB.checkHunt(lab, new Set(lab.bad), lab.answer).ok, lab.id);
    assert.ok(!LB.checkHunt(lab, new Set([...lab.bad, ...lab.lines.keys()]), lab.answer).linesOk || lab.bad.length === lab.lines.length, lab.id + ' has normal lines');
  } else if (lab.type === 'order') {
    assert.ok(LB.checkOrder(lab, lab.items.map((_, i) => i)).ok, lab.id);
  } else if (lab.type === 'sort') {
    assert.ok(LB.checkSort(lab, lab.items.map((it) => it[1])).ok, lab.id);
    assert.ok(lab.buckets.every((_, b) => lab.items.some((it) => it[1] === b)), lab.id + ' every bucket used');
  } else if (lab.type === 'calc') {
    assert.ok(LB.checkCalc(lab, lab.fields.map((f) => String(f.answer))).ok, lab.id);
  } else if (lab.type === 'firewall') {
    assert.ok(!LB.checkFirewall(lab, lab.rules).ok, lab.id + ' starts broken');
    const solved = lab.solution.order.map((i, k) => Object.assign({}, lab.rules[i], { action: lab.solution.actions[i] }));
    assert.ok(LB.checkFirewall(lab, solved).ok, lab.id + ' solution works');
  }
}
assert.strictEqual(LB.parseNumber('$100,000'), 100000);
assert.strictEqual(LB.parseNumber('1/20'), 0.05);
assert.ok(LB.ipMatch('10.0.9.0/24', '10.0.9.15') && !LB.ipMatch('10.0.9.0/24', '10.0.4.20'));

// Lessons: terms exist and every packet/link points at a real node.
const LESSONS = require('../secplus/lessons.js');
const termSet = new Set(deck.map((c) => c.term));
for (const l of LESSONS) {
  for (const t of l.terms) assert.ok(termSet.has(t), l.id + ' term ' + t);
  l.scenes.forEach((sc, i) => {
    assert.ok(sc.caption && sc.think, l.id + ' scene ' + (i + 1));
    const ids = new Set((sc.nodes || []).map((n) => n.id));
    for (const x of [...(sc.packets || []), ...(sc.links || [])]) for (const e of [x.from, x.to]) assert.ok(typeof e !== 'string' || ids.has(e), l.id + ' scene ' + (i + 1) + ' node ' + e);
  });
}
console.log('secplus: ' + LB.LABS.length + ' labs and ' + LESSONS.length + ' lessons ok');

// One thing a day: plan refers to real lesson scenes and cards; calendar math.
const DY = require('../secplus/daily.js');
for (const e of DY.PLAN) {
  const l = LESSONS.find((x) => x.id === e.lesson);
  assert.ok(l && l.scenes[e.scene], 'daily ' + e.title + ' scene');
  const quiz = new Set(e.terms.filter((t) => termSet.has(t) && !deck.find((c) => c.term === t).clue));
  assert.strictEqual(quiz.size, e.terms.length, 'daily ' + e.title + ' terms are real, non-clue cards');
  assert.ok(quiz.size >= 1);
}
assert.strictEqual(DY.PLAN.length, LESSONS.reduce((a, l) => a + l.scenes.length, 0), 'one day per scene');
assert.strictEqual(DY.dayNumber(new Date(2026, 10, 19, 23, 59)), 1);
assert.strictEqual(DY.dayNumber(new Date(2026, 10, 20, 0, 1)), 2);
assert.strictEqual(DY.forDay(1).title, 'The CIA triad');
assert.strictEqual(DY.forDay(DY.PLAN.length + 1), DY.forDay(1), 'plan repeats after the last day');
console.log('secplus: ' + DY.PLAN.length + '-day plan ok');
