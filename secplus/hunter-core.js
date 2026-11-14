'use strict';
// Rules for Sec+ Hunter, the terminal RPG (secplus/hunt.js). Pure functions over a
// plain save object so they can be unit-tested; no I/O here.
const E = require('./engine.js');

// Hunter ranks by level. Reaching the top level of a rank caps you until you pass
// that rank's trial (10 scenario questions, 8 to pass).
const RANKS = [
  { r: 'E', min: 1 }, { r: 'D', min: 10 }, { r: 'C', min: 20 },
  { r: 'B', min: 35 }, { r: 'A', min: 50 }, { r: 'S', min: 70 },
];
const MAX_LEVEL = 99;

// One stat per exam domain. The base value is your real mastery of that domain
// (0-100); points you allocate on level-up add gameplay perks on top.
const STATS = [
  { key: 'INT', domain: 1, name: 'Intellect', perk: '+5% XP per point' },
  { key: 'PER', domain: 2, name: 'Perception', perk: '+5% per point to sense and strike out a wrong option' },
  { key: 'VIT', domain: 3, name: 'Vitality', perk: '+10 max HP per point' },
  { key: 'AGI', domain: 4, name: 'Agility', perk: '+1s answer time per point' },
  { key: 'WIL', domain: 5, name: 'Willpower', perk: '+4% per point to land a critical hit on bosses' },
];

// Rift difficulty per rank: monster count, damage per hit taken, XP per kill, boss HP.
const RIFTS = {
  E: { monsters: 5, dmg: 12, xp: 10, bossHp: 2 },
  D: { monsters: 6, dmg: 15, xp: 14, bossHp: 2 },
  C: { monsters: 7, dmg: 18, xp: 20, bossHp: 3 },
  B: { monsters: 8, dmg: 22, xp: 28, bossHp: 3 },
  A: { monsters: 9, dmg: 26, xp: 38, bossHp: 4 },
  S: { monsters: 10, dmg: 30, xp: 50, bossHp: 5 },
};

const MONSTERS = {
  1: ['Cipher Wraith', 'Hash Specter', 'Key Phantom', 'Cert Revenant'],
  2: ['Phishing Goblin', 'Botnet Swarm', 'Rootkit Lurker', 'Worm Hound', 'Injection Imp'],
  3: ['Rogue Proxy', 'Flat-Network Golem', 'Backdoor Shade', 'Open-Port Serpent'],
  4: ['Log Ghoul', 'Patchless Ogre', 'Alert Banshee', 'Stale-Account Zombie'],
  5: ['Audit Lich', 'Compliance Hydra', 'Risk Basilisk', 'Vendor Mimic'],
};
const BOSSES = {
  E: 'The Default Password Warden', D: 'The Unpatched King', C: 'Lord of Lateral Movement',
  B: 'The Exfiltration Queen', A: 'The Zero-Day Wyrm', S: 'The Ransom Tyrant',
};

const DAILY = [
  { key: 'answer', goal: 30, text: 'Answer 30 questions' },
  { key: 'scenario', goal: 8, text: 'Win 8 scenario questions' },
  { key: 'rift', goal: 1, text: 'Clear 1 rift' },
  { key: 'training', goal: 15, text: 'Finish 15 training reps' },
];

const TITLES = [
  { id: 'first-rift', name: 'Rift Closer', how: 'Clear your first rift', test: (s) => s.stats.rifts >= 1 },
  { id: 'flawless', name: 'Untouched', how: 'Clear a rift without taking damage', test: (s) => s.stats.flawless >= 1 },
  { id: 'centurion', name: 'Centurion', how: 'Answer 100 questions correctly', test: (s) => s.stats.correct >= 100 },
  { id: 'boss-5', name: 'Boss Breaker', how: 'Defeat 5 rift bosses', test: (s) => s.stats.bosses >= 5 },
  { id: 'rank-c', name: 'Rising Hunter', how: 'Reach rank C', test: (s) => rankIndex(s.rank) >= 2 },
  { id: 'streak-7', name: 'Relentless', how: 'Study 7 days in a row', test: (s, ctx) => ctx.streak >= 7 },
  { id: 'ready', name: 'Exam Ready', how: 'Reach 80% exam readiness', test: (s, ctx) => ctx.readiness >= 0.8 },
  { id: 'rank-s', name: 'S-Rank Hunter', how: 'Reach rank S', test: (s) => s.rank === 'S' },
];

function rankIndex(r) { return RANKS.findIndex((x) => x.r === r); }
function nextRank(save) { return RANKS[rankIndex(save.rank) + 1] || null; }
function levelCap(save) { const n = nextRank(save); return n ? n.min - 1 : MAX_LEVEL; }
function xpToNext(level) { return Math.round(40 * Math.pow(level, 1.3)); }

function newSave(name) {
  return {
    v: 1, name, level: 1, xp: 0, rank: 'E', points: 0, title: '',
    alloc: { INT: 0, PER: 0, VIT: 0, AGI: 0, WIL: 0 },
    progress: {}, days: {}, daily: null, titles: [],
    stats: { rifts: 0, bosses: 0, kills: 0, deaths: 0, answered: 0, correct: 0, flawless: 0, trials: 0 },
  };
}

// Fill in anything an older save is missing.
function migrate(save) {
  const fresh = newSave(save.name || 'Hunter');
  for (const k of Object.keys(fresh)) if (save[k] === undefined) save[k] = fresh[k];
  save.alloc = Object.assign(fresh.alloc, save.alloc);
  save.stats = Object.assign(fresh.stats, save.stats);
  return save;
}

const xpMult = (s) => 1 + 0.05 * s.alloc.INT;
const senseChance = (s) => Math.min(0.5, 0.05 * s.alloc.PER);
const maxHp = (s) => 100 + 10 * s.alloc.VIT;
const critChance = (s) => Math.min(0.4, 0.04 * s.alloc.WIL);
function timeLimit(s, kind) { return ({ card: 15, typed: 25, scn: 45 }[kind] || 15) + s.alloc.AGI; }

// XP with level-ups. At the rank's level cap, XP banks up to one full bar and
// waits for the rank-up trial.
function addXp(save, amount) {
  const gained = Math.max(0, Math.round(amount * xpMult(save)));
  save.xp += gained;
  const before = save.level;
  while (save.level < levelCap(save) && save.xp >= xpToNext(save.level)) {
    save.xp -= xpToNext(save.level);
    save.level++;
    save.points += 3;
  }
  if (save.level >= levelCap(save)) save.xp = Math.min(save.xp, xpToNext(save.level));
  return { gained, ups: save.level - before, capped: save.level >= levelCap(save) && !!nextRank(save) };
}

function trialReady(save) { return !!nextRank(save) && save.level >= levelCap(save); }
function passTrial(save) {
  const n = nextRank(save);
  if (!n) return null;
  save.rank = n.r;
  save.points += 5;
  save.stats.trials++;
  const flush = addXp(save, 0);
  return { rank: n.r, ups: flush.ups };
}

const levelOf = (save) => (id) => (save.progress[id] && save.progress[id].l) || 0;

function dayKey(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function dayStreak(save, now = new Date()) {
  const d = new Date(now);
  if (!save.days[dayKey(d)]) d.setDate(d.getDate() - 1);
  let n = 0;
  while (save.days[dayKey(d)]) { n++; d.setDate(d.getDate() - 1); }
  return n;
}
function daily(save, now = new Date()) {
  const k = dayKey(now);
  if (!save.daily || save.daily.date !== k) save.daily = { date: k, answer: 0, scenario: 0, rift: 0, training: 0, claimed: false };
  return save.daily;
}
function dailyComplete(d) { return DAILY.every((q) => d[q.key] >= q.goal); }
// Returns the reward if the daily quest just completed, else null.
function claimDaily(save, now = new Date()) {
  const d = daily(save, now);
  if (d.claimed || !dailyComplete(d)) return null;
  d.claimed = true;
  save.points += 3;
  const xp = addXp(save, 60 * (rankIndex(save.rank) + 1));
  return { points: 3, xp };
}

// Record one answer: card mastery level, activity day, counters, daily progress.
function record(save, item, ok, now = new Date()) {
  const p = save.progress[item.id] || { l: 0, s: 0, m: 0 };
  const before = p.l;
  p.l = E.grade(p.l, ok); p.s++; if (!ok) p.m++;
  save.progress[item.id] = p;
  const k = dayKey(now);
  save.days[k] = (save.days[k] || 0) + 1;
  save.stats.answered++;
  if (ok) save.stats.correct++;
  const d = daily(save, now);
  d.answer++;
  if (ok && item.kind === 'scn') d.scenario++;
  return before < E.MASTERED && p.l >= E.MASTERED; // newly mastered
}

function domainStats(save, items) {
  const r = E.readiness(items, levelOf(save));
  return {
    overall: r.overall,
    focus: r.focus,
    stats: STATS.map((st) => {
      const d = r.domains[st.domain - 1];
      return Object.assign({}, st, { base: Math.round(d.score * 100), bonus: save.alloc[st.key], weight: d.w, domainName: d.name, count: d.count });
    }),
  };
}

function checkTitles(save, ctx) {
  const fresh = [];
  for (const t of TITLES) {
    if (save.titles.includes(t.id) || !t.test(save, ctx)) continue;
    save.titles.push(t.id);
    save.title = t.name;
    fresh.push(t);
  }
  return fresh;
}

// A multiple-choice question for a card (definition -> term) or a scenario.
function makeQuestion(item, quizPool, rnd = Math.random) {
  if (item.kind === 'scn') {
    return { prompt: item.q, options: E.shuffle(item.opts.map((label, i) => ({ label, correct: i === item.c })), rnd) };
  }
  const opts = [item].concat(E.pickDistractors(item, quizPool, 3, rnd));
  return { prompt: item.def, options: E.shuffle(opts.map((o) => ({ label: o.term, correct: o.id === item.id, card: o })), rnd) };
}

function monsterFor(item, rnd = Math.random) {
  const list = MONSTERS[item.domain] || MONSTERS[2];
  return list[Math.floor(rnd() * list.length)];
}

module.exports = {
  RANKS, STATS, RIFTS, MONSTERS, BOSSES, DAILY, TITLES, MAX_LEVEL,
  rankIndex, nextRank, levelCap, xpToNext, newSave, migrate,
  xpMult, senseChance, maxHp, critChance, timeLimit, addXp, trialReady, passTrial,
  levelOf, dayKey, dayStreak, daily, dailyComplete, claimDaily, record, domainStats, checkTitles,
  makeQuestion, monsterFor,
};
