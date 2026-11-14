'use strict';
// Sec+ Hunter rules and a scripted terminal playthrough: node test/hunter.js
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const E = require('../secplus/engine.js');
const H = require('../secplus/hunter-core.js');

// Levels, caps and trials.
let s = H.newSave('Tester');
assert.strictEqual(H.levelCap(s), 9);
let r = H.addXp(s, H.xpToNext(1));
assert.deepStrictEqual([s.level, s.points, r.ups], [2, 3, 1]);
H.addXp(s, 1e6);
assert.strictEqual(s.level, 9, 'rank E caps at level 9');
assert.strictEqual(s.xp, H.xpToNext(9), 'XP banks one full bar at the cap');
assert.ok(H.trialReady(s));
const t = H.passTrial(s);
assert.strictEqual(t.rank, 'D');
assert.ok(s.level > 9, 'banked XP flows into levels after the trial');
assert.strictEqual(H.levelCap(s), 19);

// Perks.
s = H.newSave('P');
s.alloc.VIT = 3; s.alloc.AGI = 4; s.alloc.PER = 20; s.alloc.INT = 2; s.alloc.WIL = 20;
assert.strictEqual(H.maxHp(s), 130);
assert.strictEqual(H.timeLimit(s, 'card'), 19);
assert.strictEqual(H.senseChance(s), 0.5, 'sense chance caps at 50%');
assert.strictEqual(H.critChance(s), 0.4);
assert.strictEqual(H.addXp(s, 100).gained, 110);

// Daily quest, records, streaks, titles.
s = H.newSave('D');
const now = new Date(2026, 10, 14, 12);
const scn = E.buildScenarios(require('../secplus/scenarios.js'));
const deck = E.buildDeck(require('../secplus/cards.js'));
for (let i = 0; i < 30; i++) H.record(s, i < 8 ? scn[i] : deck[i], true, now);
const d = H.daily(s, now);
assert.deepStrictEqual([d.answer, d.scenario], [30, 8]);
assert.strictEqual(H.claimDaily(s, now), null, 'rift and training still open');
d.rift = 1; d.training = 15;
const reward = H.claimDaily(s, now);
assert.ok(reward && reward.points === 3 && reward.xp.gained === 60);
assert.strictEqual(s.points, 3 + 3 * reward.xp.ups, "daily points plus level-up points");
assert.strictEqual(H.claimDaily(s, now), null, 'claimed once only');
assert.notStrictEqual(H.daily(s, new Date(2026, 10, 15)).date, d.date, 'new day, new quest');
s.days = { '2026-11-12': 1, '2026-11-13': 2, '2026-11-14': 5 };
assert.strictEqual(H.dayStreak(s, now), 3);
s.stats.rifts = 1;
assert.deepStrictEqual(H.checkTitles(s, { streak: 0, readiness: 0 }).map((x) => x.id), ['first-rift']);
assert.strictEqual(s.title, 'Rift Closer');
assert.strictEqual(H.checkTitles(s, { streak: 0, readiness: 0 }).length, 0);
assert.deepStrictEqual([1, 2, 3].map(() => H.record(s, deck[0], true, now)), [false, false, true], 'third right answer masters a card');

// Questions.
const pool = deck.filter((c) => !c.clue);
for (const item of [pool[0], scn[0]]) {
  const q = H.makeQuestion(item, pool);
  assert.strictEqual(q.options.length, 4);
  assert.strictEqual(q.options.filter((o) => o.correct).length, 1);
}
assert.ok(H.MONSTERS[2].includes(H.monsterFor(pool.find((c) => c.domain === 2))));

// Old saves get new fields.
const old = H.migrate({ name: 'Old', level: 4, xp: 3, rank: 'E', alloc: { VIT: 2 }, progress: {}, stats: { rifts: 2 } });
assert.deepStrictEqual([old.alloc.VIT, old.alloc.INT, old.stats.rifts, old.stats.bosses], [2, 0, 2, 0]);

// Scripted playthrough: new hunter, a rank E rift answered with "1"s, training, codex, status, quit.
const save = path.join(os.tmpdir(), 'secplus-hunter-test-' + process.pid + '.json');
const input = ['Tester', '1', 'E', '0'].concat(Array(60).fill('1')).join('\n') + '\n';
let run = spawnSync(process.execPath, [path.join(__dirname, '../secplus/hunt.js')], { input, env: Object.assign({}, process.env, { SECPLUS_SAVE: save, HUNT_FAST: '1' }), encoding: 'utf8', timeout: 20000 });
assert.strictEqual(run.status, 0, run.stderr);
assert.ok(/RANK E RIFT OPENED/.test(run.stdout), 'rift opened');
assert.ok(/RIFT CLEARED|YOU HAVE FALLEN/.test(run.stdout), 'rift finished');
assert.ok(/Progress saved/.test(run.stdout));
let saved = JSON.parse(fs.readFileSync(save, 'utf8'));
assert.strictEqual(saved.name, 'Tester');
assert.ok(saved.stats.answered >= 6, 'answers recorded: ' + saved.stats.answered);

const input2 = ['2', '0'].concat(Array(15).fill('1'), ['5', '', '4', '', 'q']).join('\n') + '\n';
run = spawnSync(process.execPath, [path.join(__dirname, '../secplus/hunt.js')], { input: input2, env: Object.assign({}, process.env, { SECPLUS_SAVE: save, HUNT_FAST: '1' }), encoding: 'utf8', timeout: 20000 });
assert.strictEqual(run.status, 0, run.stderr);
assert.ok(/Welcome back, Tester/.test(run.stdout));
assert.ok(/TRAINING DONE/.test(run.stdout) && /\[ CODEX \]/.test(run.stdout));
saved = JSON.parse(fs.readFileSync(save, 'utf8'));
assert.ok(saved.daily.training >= 15);
fs.unlinkSync(save);
console.log('hunter: rules and terminal playthrough ok (' + saved.stats.answered + ' answers, level ' + saved.level + ')');
