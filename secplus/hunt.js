#!/usr/bin/env node
'use strict';
// Sec+ Hunter: a terminal RPG over the Sec+ Drill cards. Every fight is a real
// Security+ question. Run: npm run hunt   (or: node secplus/hunt.js)
// Save file: ~/.secplus-hunter.json (override with SECPLUS_SAVE=path).
// Flags: --reset  start a new hunter.
const fs = require('fs');
const os = require('os');
const path = require('path');
const readline = require('readline');
const E = require('./engine.js');
const H = require('./hunter-core.js');

const DECK = E.buildDeck(require('./cards.js'));
const SCN = E.buildScenarios(require('./scenarios.js'));
const QUIZ_POOL = DECK.filter((c) => !c.clue);
const ALL = DECK.concat(SCN);
const BY_ID = new Map(ALL.map((c) => [c.id, c]));
const SAVE_PATH = process.env.SECPLUS_SAVE || path.join(os.homedir(), '.secplus-hunter.json');

// ---------- terminal output ----------
const TTY = !!process.stdout.isTTY;
const FAST = !!process.env.HUNT_FAST || !TTY;
const COLOR = TTY && !process.env.NO_COLOR;
const paint = (code) => (s) => (COLOR ? '\x1b[' + code + 'm' + s + '\x1b[0m' : String(s));
const C = {
  sys: paint('38;5;75'), bold: paint('1'), dim: paint('2'), red: paint('38;5;203'), green: paint('38;5;114'),
  gold: paint('38;5;221'), purple: paint('38;5;141'), cyan: paint('38;5;80'), white: paint('97'),
};
const W = Math.max(44, Math.min((process.stdout.columns || 80) - 2, 76));
const IN = W - 4;
const strip = (s) => String(s).replace(/\x1b\[[0-9;]*m/g, '');
const pad = (s, n) => s + ' '.repeat(Math.max(0, n - strip(s).length));
const sleep = (ms) => (FAST ? Promise.resolve() : new Promise((r) => setTimeout(r, ms)));

function wrap(text, width = IN) {
  const out = [];
  for (const para of String(text).split('\n')) {
    let line = '';
    const words = [];
    for (const w of para.split(/\s+/)) for (let i = 0; i < w.length; i += width) words.push(w.slice(i, i + width));
    for (const word of words) {
      if (!word) continue;
      if (line && (line + ' ' + word).length > width) { out.push(line); line = word; }
      else line = line ? line + ' ' + word : word;
    }
    out.push(line);
  }
  return out;
}
// Lines may be plain text (wrapped to fit) or pre-colored short strings.
function box(title, lines, color = C.sys) {
  const rows = [];
  for (const l of lines) {
    if (l === '---') rows.push(null);
    else if (strip(l) === l && l.length > IN) rows.push(...wrap(l));
    else rows.push(l);
  }
  const out = [color('╔' + '═'.repeat(W - 2) + '╗'), color('║ ') + pad(C.bold(color(title)), IN) + color(' ║'), color('╟' + '─'.repeat(W - 2) + '╢')];
  for (const r of rows) out.push(r === null ? color('╟' + '─'.repeat(W - 2) + '╢') : color('║ ') + pad(r, IN) + color(' ║'));
  out.push(color('╚' + '═'.repeat(W - 2) + '╝'));
  return out.join('\n');
}
async function show(text, delay = 0) {
  console.log(text);
  await sleep(delay);
}
function bar(frac, n, color = C.sys) {
  const k = Math.max(0, Math.min(n, Math.round(frac * n)));
  return color('█'.repeat(k)) + C.dim('░'.repeat(n - k));
}

// ---------- input ----------
class Quit extends Error {}
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: TTY });
const lines = [];
let waiting = null, closed = false;
rl.on('line', (l) => { if (waiting) { const w = waiting; waiting = null; w(l); } else lines.push(l); });
rl.on('close', () => { closed = true; if (waiting) { const w = waiting; waiting = null; w(null); } });
rl.on('SIGINT', () => { rl.close(); });
async function ask(prompt) {
  process.stdout.write(C.cyan(prompt));
  let l;
  if (lines.length) l = lines.shift();
  else if (closed) l = null;
  else l = await new Promise((r) => { waiting = r; });
  if (l === null) throw new Quit();
  if (!TTY) process.stdout.write(l + '\n');
  return l.trim();
}
async function pause() { await ask('  [Enter] '); }

// ---------- save ----------
let save = null;
function persist() {
  if (!save) return;
  const tmp = SAVE_PATH + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(save));
  fs.renameSync(tmp, SAVE_PATH);
}
function loadSave() {
  try { return H.migrate(JSON.parse(fs.readFileSync(SAVE_PATH, 'utf8'))); } catch { return null; }
}
const levelOf = () => H.levelOf(save);
const ctx = () => ({ streak: H.dayStreak(save), readiness: H.domainStats(save, ALL).overall });

// ---------- shared screens ----------
async function announceXp(res) {
  if (res.ups) {
    await show(box('[ SYSTEM ]  LEVEL UP', [
      C.gold('Level ' + (save.level - res.ups) + '  ->  Level ' + save.level),
      '+' + 3 * res.ups + ' stat points. Spend them under Status.',
    ], C.gold), 250);
  }
  if (res.capped && res.ups) {
    await show(box('[ SYSTEM ]  LEVEL CAP', [
      'Rank ' + save.rank + ' hunters cannot grow past level ' + H.levelCap(save) + '.',
      'Pass the Rank-up Trial to become rank ' + H.nextRank(save).r + '.',
    ], C.purple));
  }
}
async function afterActivity() {
  const reward = H.claimDaily(save);
  if (reward) {
    await show(box('[ SYSTEM ]  DAILY QUEST COMPLETE', [
      C.gold('+' + reward.points + ' stat points   +' + reward.xp.gained + ' XP'),
      'Come back tomorrow for a new quest. Your streak: ' + H.dayStreak(save) + ' days.',
    ], C.gold), 250);
    await announceXp(reward.xp);
  }
  for (const t of H.checkTitles(save, ctx())) {
    await show(box('[ SYSTEM ]  TITLE EARNED', [C.purple('"' + t.name + '"'), t.how + '.'], C.purple), 250);
  }
  persist();
}

function statusLines() {
  const ds = H.domainStats(save, ALL);
  const need = H.xpToNext(save.level);
  const d = H.daily(save);
  const nr = H.nextRank(save);
  const L = [
    C.white(save.name) + (save.title ? C.purple('  "' + save.title + '"') : ''),
    'Level ' + C.bold(String(save.level)) + '   Rank ' + C.gold(save.rank) + '   HP ' + H.maxHp(save) +
      (nr ? C.dim('   cap ' + H.levelCap(save)) : ''),
    'XP  ' + bar(save.xp / need, 24) + ' ' + save.xp + '/' + need,
    '---',
  ];
  for (const st of ds.stats) {
    const isFocus = ds.focus && ds.focus.n === st.domain;
    L.push(pad(C.bold(st.key), 5) + pad(String(st.base), 4) + C.gold(st.bonus ? '+' + st.bonus : '  ') + '  ' +
      bar(st.base / 100, 12, C.cyan) + ' ' + C.dim(st.domainName.split(',')[0]) + (isFocus ? C.red(' <- focus') : ''));
  }
  L.push(C.dim('Stats grow as you master each exam domain.') + (save.points ? C.gold('  ' + save.points + ' points to spend') : ''));
  L.push('---');
  L.push(C.bold('Daily quest') + (d.claimed ? C.green('  complete') : ''));
  for (const q of H.DAILY) {
    const v = Math.min(d[q.key], q.goal);
    L.push((v >= q.goal ? C.green('[x] ') : '[ ] ') + pad(q.text, 34) + C.dim(v + '/' + q.goal));
  }
  L.push(C.dim('Exam readiness ' + Math.round(ds.overall * 100) + '%   Streak ' + H.dayStreak(save) + ' days'));
  return L;
}

// ---------- one fight ----------
// Returns { ok, slow, fled }.
async function fight(item, opts) {
  const typed = opts.typed && item.kind !== 'scn';
  const kind = item.kind === 'scn' ? 'scn' : typed ? 'typed' : 'card';
  const limit = H.timeLimit(save, kind);
  const head = C.red(opts.name) + C.dim('  [' + (E.DOMAINS[item.domain - 1] || { short: '?' }).short + ']') +
    (opts.hpLine ? '   ' + opts.hpLine : '');
  console.log('\n' + head);
  for (const l of wrap(item.kind === 'scn' ? item.q : item.def, W - 2)) console.log('  ' + C.white(l));
  const start = Date.now();
  let ok = false, picked = null;
  if (typed) {
    console.log(C.dim('  Elite monster: type the term or acronym (' + limit + 's)' + (opts.canFlee ? ', or f to flee' : '')));
    const a = await ask('  > ');
    if (opts.canFlee && a.toLowerCase() === 'f') return { fled: true };
    ok = E.checkAnswer(item, a).ok;
    picked = a;
  } else {
    const q = H.makeQuestion(item, QUIZ_POOL);
    let struck = -1;
    if (Math.random() < H.senseChance(save)) {
      const wrong = q.options.map((o, i) => (o.correct ? -1 : i)).filter((i) => i >= 0);
      struck = wrong[Math.floor(Math.random() * wrong.length)];
    }
    q.options.forEach((o, i) => {
      const line = '  ' + C.cyan(String(i + 1)) + '  ' + o.label;
      console.log(i === struck ? C.dim('  ' + (i + 1) + '  ' + o.label + '   x sensed false') : line);
    });
    console.log(C.dim('  ' + limit + 's' + (opts.canFlee ? ' · f to flee' : '')));
    let a;
    for (;;) {
      a = (await ask('  > ')).toLowerCase();
      if (opts.canFlee && a === 'f') return { fled: true };
      if (/^[1-4]$/.test(a) && Number(a) - 1 !== struck) break;
      console.log(C.dim('  Pick 1-4' + (opts.canFlee ? ' or f' : '') + '.'));
    }
    picked = q.options[Number(a) - 1];
    ok = picked.correct;
  }
  const secs = (Date.now() - start) / 1000;
  const slow = ok && !FAST && secs > limit;
  const mastered = H.record(save, item, ok);
  if (!ok) {
    console.log(C.red('  Wrong.') + ' Answer: ' + C.bold(item.term));
    if (item.kind === 'scn') for (const l of wrap(item.why, W - 4)) console.log(C.dim('  ' + l));
    else if (picked && picked.card) for (const l of wrap(picked.card.term + ' means: ' + picked.card.def, W - 4)) console.log(C.dim('  ' + l));
  }
  if (mastered) console.log(C.gold('  [SYSTEM] Mastered: ' + item.term));
  persist();
  return { ok, slow, secs };
}

// ---------- rift ----------
async function pickRank() {
  const max = Math.min(H.rankIndex(save.rank) + 1, H.RANKS.length - 1);
  const L = [];
  for (let i = 0; i <= max; i++) {
    const r = H.RANKS[i].r, rf = H.RIFTS[r];
    L.push(C.gold(r) + '  ' + rf.monsters + ' monsters + boss, ' + rf.dmg + ' dmg per hit, ' + rf.xp + ' XP per kill' +
      (i > H.rankIndex(save.rank) ? C.red('  (above your rank)') : ''));
  }
  await show(box('[ SYSTEM ]  RIFTS DETECTED', L));
  for (;;) {
    const a = (await ask('Rift rank (' + H.RANKS.slice(0, max + 1).map((x) => x.r).join('/') + ', b = back): ')).toUpperCase();
    if (a === 'B' || a === '') return null;
    const i = H.RANKS.findIndex((x) => x.r === a);
    if (i >= 0 && i <= max) return a;
  }
}
async function pickDomain(label) {
  const ds = H.domainStats(save, ALL);
  const L = ['0  Mixed: all domains'];
  for (const st of ds.stats) {
    const f = ds.focus && ds.focus.n === st.domain;
    L.push(st.domain + '  ' + st.domainName + C.dim(' (' + st.weight + '% of exam)') + (f ? C.gold('  +25% XP, weakest') : ''));
  }
  await show(box(label, L));
  for (;;) {
    const a = await ask('Domain (0-5): ');
    if (/^[0-5]$/.test(a)) return { domain: Number(a), bonus: ds.focus && ds.focus.n === Number(a) ? 1.25 : 1 };
  }
}
function poolFor(domain, items) { return items.filter((c) => !domain || c.domain === domain); }

async function rift() {
  const r = await pickRank();
  if (!r) return;
  const { domain, bonus } = await pickDomain('[ SYSTEM ]  CHOOSE THE RIFT\'S DOMAIN');
  const rf = H.RIFTS[r];
  const cards = E.order(poolFor(domain, QUIZ_POOL), levelOf()).slice(0, rf.monsters);
  let scns = E.order(poolFor(domain, SCN), levelOf());
  if (!scns.length) scns = E.order(QUIZ_POOL, levelOf()).slice(0, 10);
  const max = H.maxHp(save);
  let hp = max, earned = 0, flawless = true;
  const boss = H.BOSSES[r];
  await show(box('[ SYSTEM ]  RANK ' + r + ' RIFT OPENED', [
    'Domain: ' + (domain ? E.DOMAINS[domain - 1].name : 'Mixed') + (bonus > 1 ? C.gold('   +25% XP') : ''),
    rf.monsters + ' monsters, then ' + C.red(boss) + ' (' + rf.bossHp + ' HP, scenario questions).',
    'Every 4th monster is elite: type the answer. Wrong answers cost ' + rf.dmg + ' HP; slow answers cost half.',
    'Your HP: ' + max,
  ]), 200);
  const hpLine = () => C.green('HP ' + bar(hp / max, 10, hp / max > 0.3 ? C.green : C.red) + ' ' + hp);
  const gain = (n) => { const x = H.addXp(save, n * bonus); earned += x.gained; return x; };

  for (let i = 0; i < cards.length; i++) {
    const item = cards[i];
    const elite = (i + 1) % 4 === 0;
    const name = (elite ? 'Elite ' : '') + H.monsterFor(item) + ' ' + C.dim('(' + (i + 1) + '/' + cards.length + ')');
    const res = await fight(item, { name, typed: elite, canFlee: true, hpLine: hpLine() });
    if (res.fled) { await show(C.dim('You slip back through the rift. XP earned so far is kept.')); return afterActivity(); }
    if (res.ok) {
      save.stats.kills++;
      const x = gain(rf.xp * (elite ? 2 : 1) * (res.slow ? 0.5 : 1));
      let msg = C.green('  Hit! It falls.') + C.gold(' +' + x.gained + ' XP');
      if (res.slow) { hp -= Math.round(rf.dmg / 2); flawless = false; msg += C.red('  You hesitated and took ' + Math.round(rf.dmg / 2) + ' damage.'); }
      console.log(msg);
      await announceXp(x);
    } else {
      hp -= rf.dmg; flawless = false;
      console.log(C.red('  It strikes you for ' + rf.dmg + '.'));
    }
    if (hp <= 0) return died(r, earned);
    await sleep(250);
  }

  await show('\n' + box('[ SYSTEM ]  BOSS', [C.red(boss), 'HP ' + bar(1, rf.bossHp * 3, C.red)], C.red), 300);
  let bossHp = rf.bossHp, j = 0;
  while (bossHp > 0) {
    const item = scns[j++ % scns.length];
    const res = await fight(item, {
      name: boss, canFlee: true,
      hpLine: hpLine() + C.red('   Boss ' + bar(bossHp / rf.bossHp, rf.bossHp * 2, C.red)),
    });
    if (res.fled) { await show(C.dim('You retreat from the boss. XP earned so far is kept.')); return afterActivity(); }
    if (res.ok) {
      const crit = Math.random() < H.critChance(save);
      bossHp -= crit ? 2 : 1;
      console.log(crit ? C.gold('  CRITICAL HIT!') : C.green('  You land a hit.'));
      if (res.slow) { hp -= Math.round(rf.dmg * 0.75); flawless = false; console.log(C.red('  Too slow. It counters for ' + Math.round(rf.dmg * 0.75) + '.')); }
    } else {
      const dmg = Math.round(rf.dmg * 1.5);
      hp -= dmg; flawless = false;
      console.log(C.red('  ' + boss + ' hits you for ' + dmg + '.'));
    }
    if (hp <= 0) return died(r, earned);
  }
  save.stats.bosses++; save.stats.rifts++;
  if (flawless) save.stats.flawless++;
  const x1 = gain(rf.xp * 5);
  const x2 = gain(rf.xp * 3 * (flawless ? 2 : 1));
  H.daily(save).rift++;
  await show('\n' + box('[ SYSTEM ]  RIFT CLEARED', [
    C.green(boss + ' is defeated.'),
    'Boss reward ' + C.gold('+' + x1.gained + ' XP') + '   Clear bonus ' + C.gold('+' + x2.gained + ' XP') + (flawless ? C.gold('  (flawless x2)') : ''),
    'Total this rift: ' + C.gold(earned + ' XP') + '   HP left: ' + hp + '/' + max,
  ], C.gold), 250);
  await announceXp({ ups: x1.ups + x2.ups, capped: x2.capped });
  await afterActivity();
}
async function died(r, earned) {
  save.stats.deaths++;
  await show('\n' + box('[ SYSTEM ]  YOU HAVE FALLEN', [
    C.red('The rank ' + r + ' rift overwhelms you.'),
    'You keep the ' + earned + ' XP you earned. Everything you missed comes back first in Training.',
  ], C.red), 300);
  await afterActivity();
}

// ---------- training ----------
async function training() {
  const { domain } = await pickDomain('[ SYSTEM ]  TRAINING: PICK A DOMAIN');
  const items = E.order(poolFor(domain, QUIZ_POOL), levelOf()).slice(0, 15);
  await show(box('[ SYSTEM ]  TRAINING', ['15 reps on your weakest cards. No damage, 4 XP per correct answer. Every 5th rep: type the term.', 'Type f at any answer to stop early.']), 150);
  let right = 0;
  for (let i = 0; i < items.length; i++) {
    const res = await fight(items[i], { name: 'Training dummy ' + C.dim('(' + (i + 1) + '/' + items.length + ')'), typed: (i + 1) % 5 === 0, canFlee: true });
    if (res.fled) break;
    H.daily(save).training++;
    if (res.ok) { right++; const x = H.addXp(save, 4); console.log(C.green('  Correct.') + C.gold(' +' + x.gained + ' XP')); await announceXp(x); }
  }
  await show(box('[ SYSTEM ]  TRAINING DONE', [right + ' correct. Weak cards you missed will come back first.']));
  await afterActivity();
}

// ---------- rank-up trial ----------
async function trial() {
  const n = H.nextRank(save);
  if (!n) return show(box('[ SYSTEM ]', ['You are rank S. There is no higher trial. The only boss left is the real exam.'], C.gold));
  if (!H.trialReady(save)) {
    return show(box('[ SYSTEM ]  TRIAL LOCKED', ['The rank ' + n.r + ' trial opens at level ' + H.levelCap(save) + '. You are level ' + save.level + '.']));
  }
  const qs = E.order(SCN, levelOf()).slice(0, 10);
  await show(box('[ SYSTEM ]  RANK-UP TRIAL: ' + save.rank + ' -> ' + n.r, ['10 scenario questions from across the exam. Answer 8 correctly to rank up. No time pressure.'], C.purple), 200);
  let right = 0;
  for (let i = 0; i < qs.length; i++) {
    const res = await fight(qs[i], { name: 'Trial ' + (i + 1) + '/10' });
    if (res.ok) { right++; console.log(C.green('  Correct.')); }
  }
  if (right >= 8) {
    const res = H.passTrial(save);
    await show('\n' + box('[ SYSTEM ]  RANK UP', [
      C.gold('You are now a rank ' + res.rank + ' hunter.') + '  (' + right + '/10)',
      '+5 stat points. Your level cap is now ' + H.levelCap(save) + '.',
    ], C.gold), 300);
    await announceXp({ ups: res.ups, capped: false });
  } else {
    await show(box('[ SYSTEM ]  TRIAL FAILED', [right + '/10. You need 8. Train the domains marked focus and try again.'], C.red));
  }
  await afterActivity();
}

// ---------- status / points ----------
async function status() {
  for (;;) {
    const L = statusLines();
    L.push('---');
    for (const st of H.STATS) L.push(pad(C.bold(st.key), 5) + C.dim(st.perk));
    if (save.titles.length) L.push('---', 'Titles: ' + H.TITLES.filter((t) => save.titles.includes(t.id)).map((t) => t.name).join(', '));
    await show(box('[ STATUS ]', L));
    if (!save.points) { await pause(); return; }
    const a = (await ask('Spend points like "vit 2" (' + save.points + ' left, Enter = done): ')).toUpperCase().split(/\s+/);
    if (!a[0]) return;
    const st = H.STATS.find((s) => s.key.startsWith(a[0].slice(0, 3)));
    const n = Math.min(save.points, Math.max(1, Number(a[1]) || 1));
    if (!st) { console.log(C.dim('Unknown stat. Use INT, PER, VIT, AGI or WIL.')); continue; }
    save.alloc[st.key] += n; save.points -= n;
    console.log(C.gold('  ' + st.key + ' +' + n));
    persist();
  }
}

// ---------- codex ----------
async function codex() {
  const ds = H.domainStats(save, ALL);
  const L = ['Exam readiness ' + C.bold(Math.round(ds.overall * 100) + '%') + C.dim('  (weighted by SY0-701 domain share)'), '---'];
  for (const st of ds.stats) L.push(pad(st.key, 5) + bar(st.base / 100, 16, C.cyan) + ' ' + pad(st.base + '%', 5) + C.dim(st.domainName));
  const seen = ALL.filter((c) => save.progress[c.id]);
  const weak = seen.filter((c) => save.progress[c.id].l < E.MASTERED)
    .sort((a, b) => save.progress[b.id].m - save.progress[a.id].m || save.progress[a.id].l - save.progress[b.id].l).slice(0, 8);
  L.push('---', C.bold('Your toughest monsters'));
  if (!weak.length) L.push(C.dim('Nothing yet. Clear a rift or train first.'));
  for (const c of weak) {
    L.push(C.red(c.term) + C.dim('  missed ' + save.progress[c.id].m + 'x'));
    if (c.kind !== 'scn') L.push(C.dim('  ' + c.def.slice(0, IN - 2)));
  }
  const mastered = ALL.filter((c) => (save.progress[c.id] || {}).l >= E.MASTERED).length;
  L.push('---', 'Mastered ' + mastered + '/' + ALL.length + '   Answered ' + save.stats.answered + '   Rifts ' + save.stats.rifts + '   Falls ' + save.stats.deaths);
  L.push(C.dim('Real exam: up to 90 questions, 90 minutes, pass at 750 on a 100-900 scale.'));
  await show(box('[ CODEX ]', L));
  await pause();
}

// ---------- start ----------
async function intro() {
  await show(box('[ SYSTEM ]  CONNECTION ESTABLISHED', [
    'Rifts are tearing open across the network: unpatched servers, phished inboxes, misconfigured clouds.',
    'You have been registered as a Hunter. Every monster is a Security+ question. Every concept you master makes you stronger.',
    C.gold('Final objective: pass CompTIA Security+ (SY0-701).'),
  ]), 400);
  let name = '';
  while (!name) name = (await ask('Hunter name: ')).slice(0, 24);
  save = H.newSave(name);
  persist();
  await show(box('[ SYSTEM ]', [
    'Welcome, ' + C.white(name) + '. You are a rank ' + C.gold('E') + ' hunter.',
    'Clear rifts to level up. At level 9 the Rank-up Trial opens. Your five stats track your mastery of the five exam domains.',
    'Do the daily quest every day. Save file: ' + SAVE_PATH,
  ]));
}

async function main() {
  if (process.argv.includes('--reset')) {
    if (fs.existsSync(SAVE_PATH)) {
      const a = await ask('Type RESET to erase your hunter at ' + SAVE_PATH + ': ');
      if (a === 'RESET') { fs.unlinkSync(SAVE_PATH); console.log('Erased.'); } else { console.log('Kept.'); return; }
    }
  }
  save = loadSave();
  if (!save) await intro();
  else await show(C.sys('[SYSTEM] Welcome back, ' + save.name + '.'));
  for (;;) {
    H.daily(save);
    await show('\n' + box('[ STATUS ]', statusLines()));
    const trialTag = H.nextRank(save) ? (H.trialReady(save) ? C.gold('  READY') : C.dim('  opens at level ' + H.levelCap(save))) : '';
    console.log([
      '  ' + C.cyan('1') + '  Enter a rift',
      '  ' + C.cyan('2') + '  Training',
      '  ' + C.cyan('3') + '  Rank-up trial' + trialTag,
      '  ' + C.cyan('4') + '  Status and stat points' + (save.points ? C.gold('  (' + save.points + ')') : ''),
      '  ' + C.cyan('5') + '  Codex',
      '  ' + C.cyan('q') + '  Save and quit',
    ].join('\n'));
    const a = (await ask('> ')).toLowerCase();
    if (a === '1') await rift();
    else if (a === '2') await training();
    else if (a === '3') await trial();
    else if (a === '4') await status();
    else if (a === '5') await codex();
    else if (a === 'q') break;
  }
}

main()
  .catch((e) => { if (!(e instanceof Quit)) throw e; })
  .finally(() => {
    persist();
    if (save) console.log('\n' + C.sys('[SYSTEM] Progress saved. Rifts will keep opening, ' + save.name + '.'));
    rl.close();
  });
