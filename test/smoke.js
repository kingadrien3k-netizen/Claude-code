// End-to-end smoke test: boots the server on a temp data file and exercises the protocol.
const assert = require('assert');
const path = require('path');
const os = require('os');
const fs = require('fs');
const WebSocket = require('ws');

process.env.PORT = '3911';
process.env.DATA_FILE = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'avt-')), 'users.json');
const server = require('../server.js');

function client() {
  const ws = new WebSocket('ws://localhost:3911');
  const queue = [], waiters = [];
  ws.on('message', (d) => {
    const m = JSON.parse(d);
    const i = waiters.findIndex((w) => w.t === m.t);
    if (i >= 0) waiters.splice(i, 1)[0].res(m); else queue.push(m);
  });
  return {
    ws,
    send: (m) => ws.send(JSON.stringify(m)),
    next: (t) => new Promise((res, rej) => {
      const i = queue.findIndex((m) => m.t === t);
      if (i >= 0) return res(queue.splice(i, 1)[0]);
      waiters.push({ t, res });
      setTimeout(() => rej(new Error('timeout waiting for ' + t)), 3000);
    }),
    open: () => new Promise((r) => ws.on('open', r)),
  };
}

(async () => {
  const a = client(), b = client();
  await Promise.all([a.open(), b.open()]);

  a.send({ t: 'register', user: 'x', pass: 'abcd' });
  assert.strictEqual((await a.next('auth')).ok, false, 'short name rejected');

  a.send({ t: 'register', user: 'alice', pass: 'secret1' });
  const authA = await a.next('auth');
  assert.ok(authA.ok); assert.strictEqual(authA.profile.coins, 250);

  b.send({ t: 'register', user: 'bob', pass: 'secret2' });
  assert.ok((await b.next('auth')).ok);

  a.send({ t: 'join', room: 'plaza' });
  const roomA = await a.next('room');
  assert.strictEqual(roomA.room, 'plaza');
  assert.ok(roomA.players.some((p) => p.npc), 'NPCs present');

  b.send({ t: 'join', room: 'plaza' });
  await b.next('room');
  const enter = await a.next('enter');
  assert.strictEqual(enter.player.name, 'bob');

  b.send({ t: 'chat', text: 'hello <b>world</b>' });
  let chat; do { chat = await a.next('chat'); } while (chat.name !== 'bob');
  assert.strictEqual(chat.text, 'hello <b>world</b>', 'text relayed verbatim (client renders as text)');

  b.send({ t: 'move', x: 99999, y: 0 });
  const mv = await a.next('move');
  assert.ok(mv.x <= 930 && mv.y >= 330, 'movement clamped');

  // locked item can't be worn, then buy + wear
  const look = { ...authA.profile.avatar, hat: 'crown' };
  a.send({ t: 'avatar', avatar: look });
  assert.match((await a.next('error')).text, /own/);
  a.send({ t: 'buy', slot: 'hat', id: 'crown' });
  assert.match((await a.next('error')).text, /coins/);
  a.send({ t: 'buy', slot: 'hat', id: 'cap' });
  const prof = await a.next('profile');
  assert.strictEqual(prof.profile.coins, 200);
  a.send({ t: 'avatar', avatar: { ...authA.profile.avatar, hat: 'cap' } });
  assert.strictEqual((await b.next('look')).avatar.hat, 'cap');
  await a.next('profile');

  a.send({ t: 'daily' });
  assert.strictEqual((await a.next('profile')).profile.coins, 300);
  a.send({ t: 'daily' });
  await a.next('error');

  a.send({ t: 'gameScore', score: 9999 });
  assert.strictEqual((await a.next('profile')).profile.coins, 360, 'game payout capped at 60');

  a.send({ t: 'friend', name: 'bob' });
  await a.next('profile');
  a.send({ t: 'whereis' });
  assert.strictEqual((await a.next('friends')).where.bob, 'plaza');

  // login with wrong + right password
  const c = client(); await c.open();
  c.send({ t: 'login', user: 'alice', pass: 'nope' });
  assert.strictEqual((await c.next('auth')).ok, false);
  c.send({ t: 'login', user: 'ALICE', pass: 'secret1' });
  assert.ok((await c.next('auth')).ok);
  await a.next('kicked');

  console.log('✅ smoke test passed');
  for (const x of [a, b, c]) x.ws.close();
  server.close(); process.exit(0);
})().catch((e) => { console.error('❌', e); process.exit(1); });
