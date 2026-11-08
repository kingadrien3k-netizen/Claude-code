// "Star Catch" mini-game: 30 seconds, catch stars with your basket, dodge bombs.
(function (root) {
  function start(host, onEnd) {
    const W = 640, H = 480, DURATION = 30;
    host.innerHTML = '<h2 class="center">⭐ Star Catch</h2><canvas id="gameCanvas" width="640" height="480"></canvas>' +
      '<p class="center label">Move with mouse / touch / ← →. ★ = 1, 🌟 = 3, 💣 = −5. Coins = score (max 60).</p>';
    const cv = host.querySelector('#gameCanvas'), ctx = cv.getContext('2d');
    let px = W / 2, score = 0, time = DURATION, items = [], spawnT = 0, last = performance.now(), running = true, keys = {};
    const pops = [];

    function toLocal(e) { const r = cv.getBoundingClientRect(); return ((e.clientX - r.left) / r.width) * W; }
    cv.addEventListener('pointermove', (e) => { px = toLocal(e); });
    cv.addEventListener('pointerdown', (e) => { px = toLocal(e); });
    const kd = (e) => { keys[e.key] = true; }, ku = (e) => { keys[e.key] = false; };
    addEventListener('keydown', kd); addEventListener('keyup', ku);

    function spawn() {
      const r = Math.random();
      const kind = r < 0.12 ? 'gold' : r < 0.32 ? 'bomb' : 'star';
      items.push({ kind, x: 30 + Math.random() * (W - 60), y: -20, vy: 140 + Math.random() * 120 + (DURATION - time) * 6, rot: 0 });
    }

    function frame(now) {
      if (!running) return;
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      time -= dt;
      if (keys.ArrowLeft || keys.a) px -= 480 * dt;
      if (keys.ArrowRight || keys.d) px += 480 * dt;
      px = Math.max(50, Math.min(W - 50, px));
      spawnT -= dt;
      if (spawnT <= 0) { spawn(); spawnT = Math.max(0.18, 0.55 - (DURATION - time) * 0.012); }
      for (const it of items) { it.y += it.vy * dt; it.rot += dt * 3; }
      items = items.filter((it) => {
        if (it.y > H - 70 && it.y < H - 30 && Math.abs(it.x - px) < 55) {
          const d = it.kind === 'gold' ? 3 : it.kind === 'bomb' ? -5 : 1;
          score = Math.max(0, score + d);
          pops.push({ x: it.x, y: it.y, txt: (d > 0 ? '+' : '') + d, life: 0.8, col: d > 0 ? '#ffd93d' : '#ff5d73' });
          return false;
        }
        return it.y < H + 30;
      });

      // draw
      const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#120840'); g.addColorStop(1, '#3a1c7a');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      for (let i = 0; i < 40; i++) { ctx.fillStyle = 'rgba(255,255,255,.4)'; ctx.fillRect((i * 151) % W, (i * 97 + now / 30) % H, 2, 2); }
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      for (const it of items) {
        ctx.save(); ctx.translate(it.x, it.y); ctx.rotate(it.kind === 'bomb' ? 0 : it.rot);
        ctx.font = it.kind === 'gold' ? '38px sans-serif' : '30px sans-serif';
        ctx.fillStyle = '#ffd93d';
        ctx.fillText(it.kind === 'bomb' ? '💣' : it.kind === 'gold' ? '🌟' : '★', 0, 0);
        ctx.restore();
      }
      // basket
      ctx.fillStyle = '#ff9f43'; ctx.beginPath(); ctx.moveTo(px - 55, H - 70); ctx.lineTo(px + 55, H - 70); ctx.lineTo(px + 40, H - 25); ctx.lineTo(px - 40, H - 25); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = '#c56a12'; ctx.lineWidth = 3; ctx.stroke();
      for (const p of pops) { p.life -= dt; p.y -= 60 * dt; ctx.globalAlpha = Math.max(0, p.life); ctx.fillStyle = p.col; ctx.font = 'bold 24px Fredoka, sans-serif'; ctx.fillText(p.txt, p.x, p.y); }
      ctx.globalAlpha = 1;
      for (let i = pops.length - 1; i >= 0; i--) if (pops[i].life <= 0) pops.splice(i, 1);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 22px Fredoka, sans-serif'; ctx.textAlign = 'left'; ctx.fillText('Score: ' + score, 16, 24);
      ctx.textAlign = 'right'; ctx.fillText('⏱ ' + Math.max(0, Math.ceil(time)), W - 16, 24);

      if (time <= 0) return finish();
      requestAnimationFrame(frame);
    }
    function finish() {
      running = false; cleanup();
      ctx.fillStyle = 'rgba(0,0,0,.6)'; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.font = 'bold 40px Fredoka, sans-serif'; ctx.fillText('Time!', W / 2, H / 2 - 30);
      ctx.font = '26px Fredoka, sans-serif'; ctx.fillText('Score ' + score + '  →  🪙 ' + Math.min(60, score), W / 2, H / 2 + 20);
      onEnd(score);
    }
    function cleanup() { removeEventListener('keydown', kd); removeEventListener('keyup', ku); }
    requestAnimationFrame((t) => { last = t; frame(t); });
    return { stop() { running = false; cleanup(); } };
  }
  root.StarCatch = { start };
})(this);
