'use strict';
// Avaterra server: static files + WebSocket world (accounts, rooms, chat, shop, coins).
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { WebSocketServer } = require('ws');
const Catalog = require('./public/catalog.js');

const PORT = Number(process.env.PORT) || 3000;
const DATA_FILE = process.env.DATA_FILE || path.join(__dirname, 'data', 'users.json');
const PUBLIC = path.join(__dirname, 'public');
const START_COINS = 250;
const DAILY_COINS = 100;
const DAILY_MS = 20 * 3600 * 1000;

// ---------- persistence ----------
let users = {};
try { users = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8')); } catch { users = {}; }
let saveTimer = null;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
    const tmp = DATA_FILE + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(users, null, 1));
    fs.renameSync(tmp, DATA_FILE);
  }, 300);
}
function hashPass(pass, salt) { return crypto.scryptSync(pass, salt, 32).toString('hex'); }
function publicProfile(u) {
  return { name: u.name, avatar: u.avatar, coins: u.coins, owned: u.owned, friends: u.friends || [],
           dailyReady: Date.now() - (u.lastDaily || 0) >= DAILY_MS };
}

// ---------- static http ----------
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent((req.url || '/').split('?')[0]);
  if (p === '/') p = '/index.html';
  if (p === '/healthz') { res.writeHead(200, { 'content-type': 'text/plain' }); return res.end('ok'); }
  const file = path.normalize(path.join(PUBLIC, p));
  if (!file.startsWith(PUBLIC + path.sep)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-cache' });
    res.end(buf);
  });
});

// ---------- world state ----------
const rooms = {};          // roomId -> Map(id -> player)
for (const r of Object.keys(Catalog.ROOMS)) rooms[r] = new Map();
const sessions = new Map(); // token -> username
let nextId = 1;

function roomCounts() {
  const out = {};
  for (const [r, m] of Object.entries(rooms)) out[r] = [...m.values()].filter((p) => !p.npc).length;
  return out;
}
function playerView(p) { return { id: p.id, name: p.name, avatar: p.avatar, x: p.x, y: p.y, npc: !!p.npc }; }
function send(ws, msg) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(msg)); }
function broadcast(room, msg, exceptId) {
  const s = JSON.stringify(msg);
  for (const p of rooms[room].values()) if (p.ws && p.id !== exceptId && p.ws.readyState === 1) p.ws.send(s);
}
function clampToRoom(room, x, y) {
  const r = Catalog.ROOMS[room];
  return [Math.max(30, Math.min(930, x)), Math.max(r.walk[0], Math.min(r.walk[1], y))];
}

// simple word filter for a friendly space
const BLOCKED = /\b(fuck|shit|bitch|cunt|nigg\w*|fag\w*|retard\w*)\b/gi;
function cleanText(t) {
  return String(t).replace(/[\u0000-\u001f\u007f]/g, '').slice(0, 140).trim().replace(BLOCKED, (w) => '*'.repeat(w.length));
}

// ---------- NPCs to keep the world lively ----------
const NPC_LINES = {
  plaza: ['Welcome to Avaterra!', 'Try the Arcade for coins ✨', 'Nice outfit!', 'The Rooftop is bumping tonight 🎶'],
  cafe: ['One oat latte, please ☕', 'This café has the best vibes', 'Anyone want to chat?'],
  beach: ['Surf\'s up! 🌊', 'The sand sparkles here', 'I love sunsets'],
  arcade: ['Star Catch high score is mine!', 'Click a cabinet to play 🎮', 'Dodge the bombs!'],
  rooftop: ['Dance with me! 💃', 'This track slaps', 'Hit the dance emote!'],
};
const NPC_NAMES = ['Pip', 'Juno', 'Mochi', 'Rex', 'Lumi', 'Kai', 'Nova', 'Bix', 'Sol', 'Tali'];
function randAvatar() {
  const pick = (a) => a[Math.floor(Math.random() * a.length)];
  const a = {};
  for (const s of Catalog.SLOTS) a[s] = pick(Catalog.ITEMS[s]).id;
  for (const [f, pal] of Object.entries(Catalog.COLOR_FIELDS)) a[f] = pick(Catalog.PALETTES[pal]);
  return a;
}
let npcIdx = 0;
for (const room of Object.keys(rooms)) {
  for (let i = 0; i < 2; i++) {
    const r = Catalog.ROOMS[room];
    const id = 'npc' + nextId++;
    const [x, y] = clampToRoom(room, 150 + Math.random() * 660, r.walk[0] + Math.random() * (r.walk[1] - r.walk[0]));
    rooms[room].set(id, { id, name: NPC_NAMES[npcIdx++ % NPC_NAMES.length], avatar: randAvatar(), x, y, npc: true, room });
  }
}
setInterval(() => {
  for (const [room, m] of Object.entries(rooms)) {
    for (const p of m.values()) {
      if (!p.npc) continue;
      const roll = Math.random();
      if (roll < 0.25) {
        const r = Catalog.ROOMS[room];
        [p.x, p.y] = clampToRoom(room, p.x + (Math.random() - 0.5) * 300, r.walk[0] + Math.random() * (r.walk[1] - r.walk[0]));
        broadcast(room, { t: 'move', id: p.id, x: p.x, y: p.y });
      } else if (roll < 0.31) {
        const lines = NPC_LINES[room];
        broadcast(room, { t: 'chat', id: p.id, name: p.name, text: lines[Math.floor(Math.random() * lines.length)] });
      } else if (roll < 0.36) {
        broadcast(room, { t: 'emote', id: p.id, emote: Catalog.EMOTES[Math.floor(Math.random() * 4)] });
      }
    }
  }
}, 3000);

// ---------- connections ----------
const wss = new WebSocketServer({ server, maxPayload: 8 * 1024 });

wss.on('connection', (ws) => {
  let user = null;   // users[] record
  let player = null; // in-room player
  let room = null;
  const rate = { chat: [], lastGame: 0 };

  function leave() {
    if (!room || !player) return;
    rooms[room].delete(player.id);
    broadcast(room, { t: 'leave', id: player.id });
    room = null;
  }
  function join(target) {
    if (!Catalog.ROOMS[target]) return;
    const from = room;
    leave();
    room = target;
    const def = Catalog.ROOMS[target];
    const door = def.doors.find((d) => d.to === from);
    const [x, y] = door ? clampToRoom(target, door.x + (door.x < 480 ? 70 : -70), door.y + 40) : def.spawn;
    player = { id: player ? player.id : 'p' + nextId++, name: user.name, avatar: user.avatar, x, y, ws };
    rooms[target].set(player.id, player);
    send(ws, { t: 'room', room: target, you: player.id, players: [...rooms[target].values()].map(playerView) });
    broadcast(target, { t: 'enter', player: playerView(player) }, player.id);
  }
  function authed(u) {
    // kick any older connection of the same account
    for (const m of Object.values(rooms)) for (const p of m.values())
      if (!p.npc && p.name === u.name && p.ws !== ws) { send(p.ws, { t: 'kicked', reason: 'Logged in elsewhere' }); p.ws.close(); }
    user = u;
    const token = crypto.randomBytes(24).toString('hex');
    sessions.set(token, u.name);
    send(ws, { t: 'auth', ok: true, token, profile: publicProfile(u) });
  }
  function profileUpdate() { send(ws, { t: 'profile', profile: publicProfile(user) }); }
  function err(text) { send(ws, { t: 'error', text }); }

  ws.on('message', (raw) => {
    let m;
    try { m = JSON.parse(raw); } catch { return; }
    if (!m || typeof m.t !== 'string') return;

    if (!user) {
      if (m.t === 'register') {
        const name = String(m.user || '');
        const pass = String(m.pass || '');
        if (!/^[A-Za-z0-9_]{3,16}$/.test(name)) return send(ws, { t: 'auth', ok: false, text: 'Name must be 3–16 letters, numbers or _' });
        if (pass.length < 4 || pass.length > 64) return send(ws, { t: 'auth', ok: false, text: 'Password must be 4–64 characters' });
        const key = name.toLowerCase();
        if (users[key] || NPC_NAMES.some((n) => n.toLowerCase() === key)) return send(ws, { t: 'auth', ok: false, text: 'That name is taken' });
        const salt = crypto.randomBytes(16).toString('hex');
        const avatar = Catalog.sanitizeAvatar(m.avatar, Catalog.starterItems()) || { ...Catalog.DEFAULT_AVATAR };
        users[key] = { name, salt, hash: hashPass(pass, salt), avatar, coins: START_COINS, owned: Catalog.starterItems(), lastDaily: 0, friends: [], created: Date.now() };
        save();
        return authed(users[key]);
      }
      if (m.t === 'login') {
        const u = users[String(m.user || '').toLowerCase()];
        if (!u) return send(ws, { t: 'auth', ok: false, text: 'Wrong name or password' });
        const h = hashPass(String(m.pass || ''), u.salt);
        if (!crypto.timingSafeEqual(Buffer.from(h, 'hex'), Buffer.from(u.hash, 'hex'))) return send(ws, { t: 'auth', ok: false, text: 'Wrong name or password' });
        return authed(u);
      }
      if (m.t === 'resume') {
        const name = sessions.get(String(m.token || ''));
        if (!name || !users[name.toLowerCase()]) return send(ws, { t: 'auth', ok: false, silent: true });
        sessions.delete(m.token);
        return authed(users[name.toLowerCase()]);
      }
      return;
    }

    switch (m.t) {
      case 'join': return join(String(m.room));
      case 'move': {
        if (!room) return;
        [player.x, player.y] = clampToRoom(room, Number(m.x) || 0, Number(m.y) || 0);
        return broadcast(room, { t: 'move', id: player.id, x: player.x, y: player.y }, player.id);
      }
      case 'chat': {
        if (!room) return;
        const now = Date.now();
        rate.chat = rate.chat.filter((t) => now - t < 5000);
        if (rate.chat.length >= 5) return err('Slow down a little!');
        rate.chat.push(now);
        const text = cleanText(m.text || '');
        if (!text) return;
        return broadcast(room, { t: 'chat', id: player.id, name: player.name, text });
      }
      case 'emote': {
        if (!room || !Catalog.EMOTES.includes(m.emote)) return;
        return broadcast(room, { t: 'emote', id: player.id, emote: m.emote });
      }
      case 'avatar': {
        const a = Catalog.sanitizeAvatar(m.avatar, user.owned);
        if (!a) return err('You don\'t own one of those items');
        user.avatar = a;
        save();
        if (player) { player.avatar = a; broadcast(room, { t: 'look', id: player.id, avatar: a }); }
        return profileUpdate();
      }
      case 'buy': {
        const it = Catalog.findItem(String(m.slot), String(m.id));
        if (!it) return err('Unknown item');
        const key = Catalog.itemKey(m.slot, it.id);
        if (user.owned.includes(key)) return err('Already owned');
        if (user.coins < it.price) return err('Not enough coins');
        user.coins -= it.price;
        user.owned.push(key);
        save();
        send(ws, { t: 'toast', text: `Bought ${it.name}!` });
        return profileUpdate();
      }
      case 'daily': {
        if (Date.now() - (user.lastDaily || 0) < DAILY_MS) return err('Daily bonus already claimed — come back later!');
        user.lastDaily = Date.now();
        user.coins += DAILY_COINS;
        save();
        send(ws, { t: 'toast', text: `+${DAILY_COINS} coins daily bonus!` });
        return profileUpdate();
      }
      case 'gameScore': {
        // Client-reported, so earnings are capped and rate-limited.
        const now = Date.now();
        if (now - rate.lastGame < 25000) return err('Game finished too quickly to pay out');
        rate.lastGame = now;
        const coins = Math.max(0, Math.min(60, Math.floor(Number(m.score) || 0)));
        user.coins += coins;
        save();
        send(ws, { t: 'toast', text: `You earned ${coins} coins!` });
        return profileUpdate();
      }
      case 'friend': {
        const target = users[String(m.name || '').toLowerCase()];
        if (!target || target === user) return;
        user.friends = user.friends || [];
        if (!user.friends.includes(target.name)) user.friends.push(target.name);
        save();
        send(ws, { t: 'toast', text: `${target.name} added to friends` });
        return profileUpdate();
      }
      case 'whereis': {
        const out = {};
        for (const f of user.friends || []) out[f] = null;
        for (const [r, mm] of Object.entries(rooms)) for (const p of mm.values()) if (!p.npc && p.name in out) out[p.name] = r;
        return send(ws, { t: 'friends', where: out, counts: roomCounts() });
      }
      case 'counts': return send(ws, { t: 'counts', counts: roomCounts() });
    }
  });

  ws.on('close', leave);
});

server.listen(PORT, () => console.log(`Avaterra running at http://localhost:${PORT}`));
module.exports = server;
