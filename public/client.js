(() => {
  const { ITEMS, SLOTS, PALETTES, ROOMS, EMOTES, DEFAULT_AVATAR, itemKey, findItem } = Catalog;
  const $ = (s) => document.querySelector(s);
  const SPEED = 170;
  const SLOT_LABEL = { hair: 'Hair', eyes: 'Eyes', top: 'Tops', bottom: 'Bottoms', shoes: 'Shoes', hat: 'Hats', acc: 'Extras' };
  const SLOT_COLOR = { hair: ['hairColor', 'hair'], top: ['topColor', 'cloth'], bottom: ['bottomColor', 'cloth'], shoes: ['shoesColor', 'cloth'] };
  const EMOTE_ICON = { wave: '👋', dance: '💃', jump: '⤴️', laugh: '😂', heart: '💖', sit: '🪑' };

  let ws, profile = null, roomId = null, myId = null, pending = null, reconnectDelay = 500;
  const players = new Map();
  const stage = $('#stage'), ctx = stage.getContext('2d');

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };

  // ---------------- networking ----------------
  function connect() {
    ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host);
    ws.onopen = () => {
      reconnectDelay = 500;
      const tok = store.get('avt_token');
      if (tok) send({ t: 'resume', token: tok });
    };
    ws.onmessage = (ev) => handle(JSON.parse(ev.data));
    ws.onclose = () => {
      if (profile) sys('Connection lost — reconnecting…');
      setTimeout(connect, reconnectDelay); reconnectDelay = Math.min(8000, reconnectDelay * 2);
    };
  }
  function send(m) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(m)); }

  function handle(m) {
    switch (m.t) {
      case 'auth':
        if (!m.ok) { if (!m.silent) $('#authMsg').textContent = m.text; else store.set('avt_token', null); return; }
        store.set('avt_token', m.token);
        profile = m.profile;
        showWorld();
        send({ t: 'join', room: roomId || store.get('avt_room') || 'plaza' });
        break;
      case 'profile': profile = m.profile; updateHud(); if (modalRefresh) modalRefresh(); break;
      case 'room':
        roomId = m.room; myId = m.you; store.set('avt_room', roomId);
        players.clear();
        for (const p of m.players) addPlayer(p);
        $('#roomName').textContent = '📍 ' + ROOMS[roomId].name;
        sys('You entered ' + ROOMS[roomId].name);
        break;
      case 'enter': addPlayer(m.player); if (!m.player.npc) sys(m.player.name + ' arrived'); break;
      case 'leave': { const p = players.get(m.id); if (p && !p.npc) sys(p.name + ' left'); players.delete(m.id); break; }
      case 'move': { const p = players.get(m.id); if (p) { p.tx = m.x; p.ty = m.y; } break; }
      case 'look': { const p = players.get(m.id); if (p) p.avatar = m.avatar; break; }
      case 'emote': { const p = players.get(m.id); if (p) { p.emote = m.emote; p.emoteStart = now(); } break; }
      case 'chat': {
        const p = players.get(m.id);
        if (p) { p.bubble = m.text; p.bubbleT = now(); }
        logLine(m.name, m.text);
        break;
      }
      case 'toast': toast(m.text); break;
      case 'error': toast('⚠️ ' + m.text); break;
      case 'counts': case 'friends': if (onCounts) onCounts(m); break;
      case 'kicked': store.set('avt_token', null); profile = null; alert(m.reason); location.reload(); break;
    }
  }

  // ---------------- login ----------------
  let authMode = 'login';
  document.querySelectorAll('#authForm button').forEach((b) => b.addEventListener('click', () => { authMode = b.dataset.mode; }));
  $('#authForm').addEventListener('submit', (e) => {
    e.preventDefault();
    $('#authMsg').textContent = '';
    send({ t: authMode, user: $('#authUser').value.trim(), pass: $('#authPass').value, avatar: loginAvatar });
  });
  // random starter look on the login screen
  const loginAvatar = { ...DEFAULT_AVATAR };
  const pick = (a) => a[Math.floor(Math.random() * a.length)];
  for (const s of SLOTS) loginAvatar[s] = pick(ITEMS[s].filter((i) => i.price === 0)).id;
  loginAvatar.skin = pick(PALETTES.skin); loginAvatar.hairColor = pick(PALETTES.hair);
  loginAvatar.topColor = pick(PALETTES.cloth); loginAvatar.bottomColor = pick(PALETTES.cloth);
  const lp = $('#loginPreview').getContext('2d');
  (function loginLoop() {
    if (profile) return;
    const t = now();
    lp.clearRect(0, 0, 200, 220);
    AvatarRenderer.draw(lp, loginAvatar, 100, 200, { scale: 1.5, t, emote: 'wave', emoteT: t });
    requestAnimationFrame(loginLoop);
  })();

  function showWorld() {
    $('#login').classList.add('hidden');
    $('#world').classList.remove('hidden');
    updateHud();
  }
  function updateHud() {
    if (!profile) return;
    $('#coinCount').textContent = profile.coins;
    $('#btnDaily').disabled = !profile.dailyReady;
  }
  $('#btnLogout').onclick = () => { store.set('avt_token', null); store.set('avt_room', null); location.reload(); };

  // ---------------- world ----------------
  function now() { return performance.now() / 1000; }
  function addPlayer(p) {
    players.set(p.id, { ...p, dx: p.x, dy: p.y, tx: p.x, ty: p.y, facing: 1, walk: 0, emote: null, emoteStart: 0, bubble: null, bubbleT: 0 });
  }
  function toCanvas(e) {
    const r = stage.getBoundingClientRect();
    return [((e.clientX - r.left) / r.width) * stage.width, ((e.clientY - r.top) / r.height) * stage.height];
  }
  function playerAt(x, y) {
    let best = null;
    for (const p of players.values()) {
      if (x > p.dx - 26 && x < p.dx + 26 && y > p.dy - 112 && y < p.dy + 4) if (!best || p.dy > best.dy) best = p;
    }
    return best;
  }
  function walkTo(x, y, then) {
    const me = players.get(myId);
    if (!me) return;
    const w = ROOMS[roomId].walk;
    me.tx = Math.max(30, Math.min(930, x)); me.ty = Math.max(w[0], Math.min(w[1], y));
    if (me.emote === 'sit') me.emote = null;
    pending = then || null;
    send({ t: 'move', x: me.tx, y: me.ty });
  }

  stage.addEventListener('click', (e) => {
    hideMenu();
    if (!roomId) return;
    const [x, y] = toCanvas(e);
    const def = ROOMS[roomId];
    const p = playerAt(x, y);
    if (p && p.id !== myId) return showPlayerMenu(p, e);
    for (const d of def.doors) {
      if (Math.abs(x - d.x) < 60 && y > d.y - 95 && y < d.y + 40) return walkTo(d.x, d.y, () => send({ t: 'join', room: d.to }));
    }
    for (const g of def.games || []) {
      if (Math.abs(x - g.x) < 60 && y > 135 && y < g.y + 30) return walkTo(g.x, g.y + 10, () => openGame());
    }
    walkTo(x, y);
  });

  function showPlayerMenu(p, e) {
    const menu = $('#playerMenu');
    const wrap = stage.parentElement.getBoundingClientRect();
    menu.innerHTML = '';
    const h = document.createElement('h4'); h.textContent = p.name + (p.npc ? ' (local)' : ''); menu.append(h);
    const wave = document.createElement('button'); wave.textContent = '👋 Wave at';
    wave.onclick = () => { doEmote('wave'); send({ t: 'chat', text: 'Hi ' + p.name + '!' }); hideMenu(); };
    menu.append(wave);
    if (!p.npc && !(profile.friends || []).includes(p.name)) {
      const fr = document.createElement('button'); fr.className = 'alt'; fr.textContent = '➕ Add friend';
      fr.onclick = () => { send({ t: 'friend', name: p.name }); hideMenu(); };
      menu.append(fr);
    }
    menu.style.left = Math.min(wrap.width - 160, e.clientX - wrap.left) + 'px';
    menu.style.top = Math.max(0, e.clientY - wrap.top - 40) + 'px';
    menu.classList.remove('hidden');
  }
  function hideMenu() { $('#playerMenu').classList.add('hidden'); }

  function wrapText(text, maxW) {
    const words = text.split(' '), lines = []; let cur = '';
    for (const w of words) {
      const test = cur ? cur + ' ' + w : w;
      if (ctx.measureText(test).width > maxW && cur) { lines.push(cur); cur = w; } else cur = test;
    }
    if (cur) lines.push(cur);
    return lines.slice(0, 4);
  }

  let lastT = now();
  function loop() {
    const t = now(), dt = Math.min(0.1, t - lastT); lastT = t;
    if (roomId) {
      RoomPainter.paint(ctx, roomId, t);
      const sorted = [...players.values()].sort((a, b) => a.dy - b.dy);
      for (const p of sorted) {
        const vx = p.tx - p.dx, vy = p.ty - p.dy, dist = Math.hypot(vx, vy);
        const walking = dist > 1.5;
        if (walking) {
          const step = Math.min(dist, SPEED * dt);
          p.dx += (vx / dist) * step; p.dy += (vy / dist) * step;
          if (Math.abs(vx) > 2) p.facing = vx < 0 ? -1 : 1;
          p.walk += dt * 11;
        } else if (p.id === myId && pending) { const f = pending; pending = null; f(); }
        const et = t - p.emoteStart;
        if (p.emote && p.emote !== 'sit' && et > (p.emote === 'dance' ? 6 : 2.2)) p.emote = null;
        if (walking && p.emote === 'sit') p.emote = null;
        AvatarRenderer.draw(ctx, p.avatar, p.dx, p.dy, { scale: 0.95, t: t + p.dx * 0.01, walking, walk: p.walk, facing: p.facing, emote: p.emote, emoteT: et });
        // name tag
        ctx.font = '600 13px Fredoka, sans-serif'; ctx.textAlign = 'center';
        const nw = ctx.measureText(p.name).width + 14;
        ctx.fillStyle = p.id === myId ? 'rgba(255,93,158,.9)' : p.npc ? 'rgba(60,60,80,.75)' : 'rgba(30,20,60,.8)';
        AvatarRenderer.rr(ctx, p.dx - nw / 2, p.dy + 6, nw, 18, 9); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.fillText(p.name, p.dx, p.dy + 19);
      }
      // bubbles on top of everyone
      for (const p of sorted) {
        if (!p.bubble) continue;
        const age = t - p.bubbleT;
        if (age > 7) { p.bubble = null; continue; }
        ctx.globalAlpha = age > 6 ? 7 - age : 1;
        ctx.font = '14px Fredoka, sans-serif';
        const lines = wrapText(p.bubble, 180);
        const w = Math.max(...lines.map((l) => ctx.measureText(l).width)) + 20, h = lines.length * 18 + 12;
        const bx = Math.max(4, Math.min(956 - w, p.dx - w / 2)), by = p.dy - 125 - h;
        ctx.fillStyle = '#fff'; AvatarRenderer.rr(ctx, bx, by, w, h, 12); ctx.fill();
        ctx.beginPath(); ctx.moveTo(p.dx - 7, by + h - 1); ctx.lineTo(p.dx, by + h + 9); ctx.lineTo(p.dx + 7, by + h - 1); ctx.fill();
        ctx.fillStyle = '#222'; ctx.textAlign = 'center';
        lines.forEach((l, i) => ctx.fillText(l, bx + w / 2, by + 21 + i * 18));
        ctx.globalAlpha = 1;
      }
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  // ---------------- chat + emotes ----------------
  $('#chatForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const v = $('#chatInput').value.trim();
    if (!v) return;
    const cmd = v.match(/^\/(\w+)$/);
    if (cmd && EMOTES.includes(cmd[1])) doEmote(cmd[1]); else send({ t: 'chat', text: v });
    $('#chatInput').value = '';
  });
  for (const e of EMOTES) {
    const b = document.createElement('button'); b.type = 'button'; b.title = '/' + e; b.textContent = EMOTE_ICON[e];
    b.onclick = () => doEmote(e);
    $('#emotes').append(b);
  }
  function doEmote(e) { send({ t: 'emote', emote: e }); }
  function logLine(name, text) {
    const d = document.createElement('div');
    const b = document.createElement('b'); b.textContent = name + ': ';
    d.append(b, document.createTextNode(text));
    pushLog(d);
  }
  function sys(text) { const d = document.createElement('div'); d.className = 'sys'; d.textContent = text; pushLog(d); }
  function pushLog(d) {
    const log = $('#chatLog'); log.append(d);
    while (log.children.length > 80) log.firstChild.remove();
    log.scrollTop = log.scrollHeight;
  }
  let toastTimer;
  function toast(text) {
    const el = $('#toast'); el.textContent = text; el.classList.remove('hidden');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.add('hidden'), 2600);
  }

  // ---------------- modals ----------------
  let modalRefresh = null, onCounts = null, activeGame = null;
  function openModal(render) {
    modalRefresh = render; $('#modal').classList.remove('hidden'); render();
  }
  function closeModal() {
    $('#modal').classList.add('hidden'); modalRefresh = null; onCounts = null;
    if (activeGame) { activeGame.stop(); activeGame = null; }
  }
  $('#modalClose').onclick = closeModal;
  $('#modal').addEventListener('click', (e) => { if (e.target.id === 'modal') closeModal(); });
  addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
  const body = () => $('#modalBody');
  function el(tag, props, ...kids) { const n = Object.assign(document.createElement(tag), props || {}); n.append(...kids); return n; }
  function preview(avatar, w, h, scale, opts) {
    const c = el('canvas', { width: w, height: h });
    AvatarRenderer.draw(c.getContext('2d'), avatar, w / 2, h - 8, { scale, t: 0, ...(opts || {}) });
    return c;
  }
  const owns = (slot, id) => profile.owned.includes(itemKey(slot, id));

  // Dress up
  let draft = null, dressTab = 'hair';
  $('#btnDress').onclick = () => { draft = { ...profile.avatar }; openModal(renderDress); };
  function renderDress() {
    const b = body(); b.innerHTML = '';
    const big = preview(draft, 220, 260, 1.9);
    const tabs = el('div', { className: 'tabs' });
    for (const s of ['skin', ...SLOTS]) {
      tabs.append(el('button', { className: dressTab === s ? 'on' : '', textContent: s === 'skin' ? 'Skin' : SLOT_LABEL[s], onclick: () => { dressTab = s; renderDress(); } }));
    }
    const right = el('div', {}, tabs);
    if (dressTab === 'skin') right.append(swatches('skin', 'skin'));
    else {
      if (SLOT_COLOR[dressTab]) { right.append(el('div', { className: 'label', textContent: 'Color' }), swatches(...SLOT_COLOR[dressTab])); }
      const grid = el('div', { className: 'grid' });
      for (const it of ITEMS[dressTab]) {
        const have = owns(dressTab, it.id);
        const look = { ...draft, [dressTab]: it.id };
        const tile = el('div', { className: 'tile' + (draft[dressTab] === it.id ? ' on' : '') + (have ? '' : ' locked') },
          preview(look, 80, 96, 0.78), el('div', { textContent: it.name }), have ? '' : el('div', { className: 'price', textContent: '🔒 🪙' + it.price }));
        tile.onclick = () => { if (have) { draft[dressTab] = it.id; renderDress(); } else toast('Buy it in the Shop first!'); };
        grid.append(tile);
      }
      right.append(grid);
    }
    right.append(el('div', { className: 'actions' },
      el('button', { className: 'ghost', textContent: 'Reset', onclick: () => { draft = { ...profile.avatar }; renderDress(); } }),
      el('button', { textContent: 'Save look ✨', onclick: () => { send({ t: 'avatar', avatar: draft }); closeModal(); } })));
    b.append(el('h2', { textContent: '👕 Dress Up' }), el('div', { className: 'dress' }, big, right));
  }
  function swatches(field, pal) {
    const wrap = el('div', { className: 'swatches' });
    for (const c of PALETTES[pal]) {
      const s = el('div', { className: 'swatch' + (draft[field] === c ? ' on' : ''), title: c });
      s.style.background = c;
      s.onclick = () => { draft[field] = c; renderDress(); };
      wrap.append(s);
    }
    return wrap;
  }

  // Shop
  let shopTab = 'hat';
  $('#btnShop').onclick = () => openModal(renderShop);
  function renderShop() {
    const b = body(); b.innerHTML = '';
    const tabs = el('div', { className: 'tabs' });
    for (const s of SLOTS) tabs.append(el('button', { className: shopTab === s ? 'on' : '', textContent: SLOT_LABEL[s], onclick: () => { shopTab = s; renderShop(); } }));
    const grid = el('div', { className: 'grid' });
    for (const it of ITEMS[shopTab].filter((i) => i.price > 0)) {
      const have = owns(shopTab, it.id);
      const tile = el('div', { className: 'tile' }, preview({ ...profile.avatar, [shopTab]: it.id }, 80, 96, 0.78),
        el('div', { textContent: it.name }), el('div', { className: 'price', textContent: '🪙 ' + it.price }));
      const btn = el('button', { textContent: have ? 'Owned' : 'Buy', disabled: have || profile.coins < it.price });
      btn.onclick = () => send({ t: 'buy', slot: shopTab, id: it.id });
      tile.append(btn);
      grid.append(tile);
    }
    b.append(el('h2', { textContent: '🛍️ Shop — you have 🪙 ' + profile.coins }), tabs, grid,
      el('p', { className: 'label', textContent: 'Tip: play Star Catch in the Byte Arcade and claim your Daily bonus to earn coins.' }));
  }

  // Map
  $('#btnMap').onclick = () => {
    onCounts = (m) => {
      const b = body(); b.innerHTML = '';
      const grid = el('div', { className: 'map' });
      for (const [id, r] of Object.entries(ROOMS)) {
        grid.append(el('button', { disabled: id === roomId, onclick: () => { send({ t: 'join', room: id }); closeModal(); } },
          r.name, el('small', { textContent: (id === roomId ? 'You are here · ' : '') + (m.counts[id] || 0) + ' online' })));
      }
      b.append(el('h2', { textContent: '🗺️ World Map' }), grid);
    };
    openModal(() => { body().textContent = 'Loading…'; send({ t: 'counts' }); });
  };

  // Friends
  $('#btnFriends').onclick = () => {
    onCounts = (m) => {
      const b = body(); b.innerHTML = '';
      b.append(el('h2', { textContent: '👥 Friends' }));
      const names = Object.keys(m.where || {});
      if (!names.length) b.append(el('p', { className: 'label', textContent: 'No friends yet — click another player in a room to add them.' }));
      for (const n of names) {
        const r = m.where[n];
        b.append(el('div', { className: 'tile', style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;text-align:left' },
          el('span', { textContent: (r ? '🟢 ' : '⚪ ') + n + (r ? ' — ' + ROOMS[r].name : ' — offline') }),
          r && r !== roomId ? el('button', { textContent: 'Go', onclick: () => { send({ t: 'join', room: r }); closeModal(); } }) : ''));
      }
    };
    openModal(() => { body().textContent = 'Loading…'; send({ t: 'whereis' }); });
  };

  $('#btnDaily').onclick = () => send({ t: 'daily' });

  // Mini-game
  function openGame() {
    openModal(() => {});
    modalRefresh = null;
    activeGame = StarCatch.start(body(), (score) => {
      send({ t: 'gameScore', score });
      activeGame = null;
      body().append(el('div', { className: 'actions' },
        el('button', { className: 'ghost', textContent: 'Close', onclick: closeModal }),
        el('button', { textContent: 'Play again', onclick: () => openGame() })));
    });
  }

  connect();
})();
