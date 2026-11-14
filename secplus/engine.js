// Study logic shared by the page and the Node tests: deck building, answer
// checking for typed answers, distractor choice for multiple choice, and the
// mastery levels (0 new, 1-2 learning, 3 mastered).
(function (root) {
  'use strict';

  const MASTERED = 3;
  // CompTIA Security+ SY0-701 domains and their share of the exam.
  const DOMAINS = [
    { n: 1, name: 'General Security Concepts', short: 'Concepts', w: 12 },
    { n: 2, name: 'Threats, Vulnerabilities, and Mitigations', short: 'Threats', w: 22 },
    { n: 3, name: 'Security Architecture', short: 'Architecture', w: 18 },
    { n: 4, name: 'Security Operations', short: 'Operations', w: 28 },
    { n: 5, name: 'Security Program Management and Oversight', short: 'Oversight', w: 20 },
  ];
  const STOP = new Set(('a an and are as at be by for from has in into is it its of on or such that the ' +
    'their them then to used uses using via was when where which while with without not only after before ' +
    'than other another can may more most one two three').split(' '));

  function norm(s) {
    return String(s).toLowerCase()
      .replace(/&/g, ' and ')
      .replace(/[‐-―]/g, '-')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  // A term like "Role-Based Access Control (RBAC)" is answered correctly by the
  // full term, by "Role-Based Access Control", or by "RBAC". "Secure Erase / Sanitize"
  // accepts either side of the slash.
  function variants(term) {
    const out = new Set();
    const add = (s) => { const n = norm(s); if (n) out.add(n); };
    add(term);
    const paren = term.match(/^(.*?)\s*\(([^)]+)\)\s*(.*)$/);
    if (paren) {
      add(paren[1] + ' ' + paren[3]);
      add(paren[2]);
    }
    if (term.includes(' / ')) term.split(' / ').forEach(add);
    // "SQL Injection (SQLi)" and "SQL Injection" both normalise to "sql injection".
    return out;
  }

  // Cards whose "term" is an exam clue, mnemonic or comparison rather than a
  // concept name. They are great flashcards but poor multiple-choice answers.
  function isClue(term) {
    return /exam clue|exam tip|memory trick/i.test(term) || /\s\+\s/.test(term) ||
      /\svs\.?\s/i.test(term) || /\?\s*$/.test(term);
  }

  function buildDeck(sets) {
    const cards = [];
    for (const set of sets) {
      set.cards.forEach(([term, def], i) => {
        cards.push({
          id: set.id + '-' + (i + 1),
          setId: set.id,
          setTitle: set.title,
          pos: i + 1,
          setSize: set.cards.length,
          term,
          def,
          clue: isClue(term),
          domain: Number((set.domains || '')[i]) || 0,
          keys: variants(term),
        });
      });
    }
    return cards;
  }

  // Scenario questions share the card shape (term = correct answer, def = question)
  // so the quiz, results and browse code can show either.
  function buildScenarios(list) {
    return list.map((s, i) => ({
      id: s.id, kind: 'scn', q: s.q, opts: s.opts, c: s.c, why: s.why, domain: s.d,
      term: s.opts[s.c], def: s.q, setId: 'scn', setTitle: 'Scenarios', pos: i + 1, setSize: list.length,
      clue: false, keys: new Set(),
    }));
  }

  // Per-domain readiness: mastered items count fully, learning items by level.
  // Overall readiness is weighted by each domain's share of the exam.
  function readiness(items, levelOf) {
    const per = DOMAINS.map((d) => Object.assign({ count: 0, score: 0 }, d));
    for (const it of items) {
      const d = per[it.domain - 1];
      if (!d) continue;
      d.count++;
      d.score += Math.min(levelOf(it.id) || 0, MASTERED) / MASTERED;
    }
    let total = 0, wsum = 0, focus = null;
    for (const d of per) {
      d.score = d.count ? d.score / d.count : 0;
      total += d.w * d.score; wsum += d.w;
      if (!focus || d.w * (1 - d.score) > focus.w * (1 - focus.score)) focus = d;
    }
    return { domains: per, overall: wsum ? total / wsum : 0, focus };
  }

  function sameConcept(a, b) {
    for (const k of a.keys) if (b.keys.has(k)) return true;
    return norm(a.def) === norm(b.def);
  }

  function lev(a, b) {
    if (a === b) return 0;
    const m = a.length, n = b.length;
    if (!m || !n) return m || n;
    let prev = Array.from({ length: n + 1 }, (_, j) => j);
    for (let i = 1; i <= m; i++) {
      const cur = [i];
      for (let j = 1; j <= n; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = cur;
    }
    return prev[n];
  }

  // Typed answers: exact match on any variant (ignoring case, punctuation and
  // spacing), or a small typo allowance on longer words. Short acronyms must match.
  function checkAnswer(card, input) {
    const n = norm(input);
    if (!n) return { ok: false, close: false };
    if (card.keys.has(n)) return { ok: true, close: false };
    const squash = (s) => s.replace(/ /g, '');
    for (const k of card.keys) {
      if (squash(k) === squash(n)) return { ok: true, close: false };
      const allow = k.length >= 12 ? 2 : k.length >= 6 ? 1 : 0;
      if (allow && lev(squash(k), squash(n)) <= allow) return { ok: true, close: true };
    }
    return { ok: false, close: false };
  }

  function words(s) {
    return norm(s).split(' ').filter((w) => w.length > 2 && !STOP.has(w));
  }

  function similarity(a, b) {
    const wa = new Set(words(a.term + ' ' + a.def));
    const wb = new Set(words(b.term + ' ' + b.def));
    let shared = 0;
    for (const w of wa) if (wb.has(w)) shared++;
    const termA = new Set(words(a.term));
    let termShared = 0;
    for (const w of words(b.term)) if (termA.has(w)) termShared++;
    return shared / Math.sqrt((wa.size || 1) * (wb.size || 1)) + termShared * 0.6 + (a.setId === b.setId ? 0.1 : 0);
  }

  function shuffle(arr, rnd = Math.random) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  // Three wrong options that look plausible: rank the pool by word overlap with
  // the answer, then draw from the closest few so repeats don't always match.
  function pickDistractors(card, pool, count = 3, rnd = Math.random) {
    const seenLabels = new Set([norm(card.term), norm(card.def)]);
    const candidates = [];
    for (const c of pool) {
      if (c.id === card.id || c.clue || sameConcept(card, c)) continue;
      candidates.push({ c, score: similarity(card, c) + rnd() * 0.25 });
    }
    candidates.sort((x, y) => y.score - x.score);
    const near = shuffle(candidates.slice(0, Math.max(count * 3, 8)), rnd);
    const out = [];
    for (const { c } of near.concat(candidates)) {
      if (out.length >= count) break;
      if (out.includes(c)) continue;
      if (seenLabels.has(norm(c.term)) || seenLabels.has(norm(c.def))) continue;
      if (out.some((o) => sameConcept(o, c))) continue;
      seenLabels.add(norm(c.term));
      seenLabels.add(norm(c.def));
      out.push(c);
    }
    return out;
  }

  // Weakest cards first, random order within a level.
  function order(cards, levelOf, rnd = Math.random) {
    return shuffle(cards, rnd).sort((a, b) => levelOf(a.id) - levelOf(b.id));
  }

  function grade(level, correct) {
    return correct ? Math.min(MASTERED, (level || 0) + 1) : 0;
  }

  const api = { MASTERED, DOMAINS, buildScenarios, readiness, norm, variants, isClue, buildDeck, sameConcept, checkAnswer, pickDistractors, shuffle, order, grade };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SecEngine = api;
})(this);
