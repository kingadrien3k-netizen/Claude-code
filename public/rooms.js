// Procedural room backdrops (960x540). Each painter receives (ctx, t).
(function (root) {
  const W = 960, H = 540;
  const R = () => root.AvatarRenderer.rr;

  function sky(ctx, top, bottom, h) {
    const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, top); g.addColorStop(1, bottom);
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, h);
  }
  function cloud(ctx, x, y, s) {
    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    for (const [dx, dy, r] of [[0, 0, 22], [24, -10, 26], [50, 0, 20], [26, 6, 22]]) { ctx.beginPath(); ctx.arc(x + dx * s, y + dy * s, r * s, 0, 7); ctx.fill(); }
  }
  function doorSign(ctx, d) {
    const rr = R();
    ctx.save();
    ctx.font = 'bold 14px Fredoka, system-ui, sans-serif'; ctx.textAlign = 'center';
    const w = ctx.measureText(d.label).width + 34;
    rr(ctx, d.x - w / 2, d.y - 80, w, 26, 13); ctx.fillStyle = 'rgba(30,20,60,0.75)'; ctx.fill();
    ctx.fillStyle = '#fff'; ctx.fillText('➜ ' + d.label, d.x, d.y - 62);
    ctx.restore();
  }
  function building(ctx, x, y, w, h, color, roof) {
    const rr = R();
    ctx.fillStyle = color; ctx.fillRect(x, y, w, h);
    ctx.fillStyle = roof; ctx.fillRect(x - 8, y - 12, w + 16, 14);
    ctx.fillStyle = 'rgba(255,255,255,0.55)';
    for (let wy = y + 18; wy < y + h - 70; wy += 40) for (let wx = x + 16; wx < x + w - 30; wx += 42) { rr(ctx, wx, wy, 26, 24, 3); ctx.fill(); }
  }

  const painters = {
    plaza(ctx, t) {
      sky(ctx, '#7fd3ff', '#d7f3ff', 320);
      cloud(ctx, ((t * 12) % 1200) - 120, 70, 1); cloud(ctx, ((t * 8 + 600) % 1200) - 120, 120, 0.7);
      building(ctx, 0, 140, 190, 200, '#ffb4a2', '#e5989b');
      building(ctx, 220, 170, 160, 170, '#9b5de5', '#6a3fb5');
      building(ctx, 580, 160, 170, 180, '#00bbf9', '#0081a7');
      building(ctx, 780, 130, 180, 210, '#fee440', '#f2b705');
      // arcade + rooftop doors
      const rr = R();
      ctx.fillStyle = '#2b2d42'; rr(ctx, 270, 250, 60, 85, 8); ctx.fill();
      ctx.fillStyle = '#ff5d73'; ctx.font = 'bold 16px Fredoka, sans-serif'; ctx.textAlign = 'center'; ctx.fillText('ARCADE', 300, 205);
      ctx.fillStyle = '#2b2d42'; rr(ctx, 630, 250, 60, 85, 8); ctx.fill();
      // ground
      ctx.fillStyle = '#e9d8a6'; ctx.fillRect(0, 320, W, H - 320);
      ctx.fillStyle = '#dcc48f';
      for (let y = 330; y < H; y += 34) for (let x = (y / 34 % 2) * 30; x < W; x += 60) ctx.fillRect(x, y, 56, 30);
      // fountain
      ctx.fillStyle = '#8ecae6'; ctx.beginPath(); ctx.ellipse(480, 380, 90, 26, 0, 0, 7); ctx.fill();
      ctx.strokeStyle = '#adb5bd'; ctx.lineWidth = 8; ctx.stroke();
      for (let i = 0; i < 8; i++) {
        const ph = (t * 1.5 + i / 8) % 1;
        ctx.fillStyle = `rgba(160,220,255,${1 - ph})`;
        ctx.beginPath(); ctx.arc(480 + Math.cos(i) * ph * 40, 340 - Math.sin(ph * Math.PI) * 40, 4, 0, 7); ctx.fill();
      }
      ctx.fillStyle = '#adb5bd'; ctx.fillRect(474, 335, 12, 45);
      // trees
      for (const tx of [40, 920]) {
        ctx.fillStyle = '#8d6e63'; ctx.fillRect(tx - 6, 260, 12, 70);
        ctx.fillStyle = '#52b788'; ctx.beginPath(); ctx.arc(tx, 250, 36, 0, 7); ctx.fill();
      }
    },
    cafe(ctx, t) {
      const rr = R();
      ctx.fillStyle = '#f7e1d7'; ctx.fillRect(0, 0, W, 340);
      ctx.fillStyle = '#edafb8'; for (let x = 0; x < W; x += 40) ctx.fillRect(x, 0, 20, 340);
      ctx.fillStyle = '#4a3428'; ctx.fillRect(0, 330, W, 12);
      // counter
      ctx.fillStyle = '#7f5539'; rr(ctx, 60, 230, 420, 110, 8); ctx.fill();
      ctx.fillStyle = '#9c6644'; ctx.fillRect(60, 230, 420, 18);
      // menu board
      ctx.fillStyle = '#2d3a3a'; rr(ctx, 100, 50, 300, 140, 10); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = 'bold 22px Fredoka, sans-serif'; ctx.textAlign = 'left';
      ctx.fillText('☕ MENU', 130, 88); ctx.font = '16px Fredoka, sans-serif';
      ['Oat Latte .... 3c', 'Pixel Pie .... 5c', 'Byte Tea ..... 2c'].forEach((l, i) => ctx.fillText(l, 130, 120 + i * 24));
      // window
      ctx.fillStyle = '#a2d2ff'; rr(ctx, 560, 60, 300, 170, 12); ctx.fill();
      cloud(ctx, 600 + ((t * 10) % 220), 120, 0.6);
      ctx.strokeStyle = '#7f5539'; ctx.lineWidth = 8; ctx.strokeRect(560, 60, 300, 170); ctx.beginPath(); ctx.moveTo(710, 60); ctx.lineTo(710, 230); ctx.stroke();
      // floor
      ctx.fillStyle = '#b08968'; ctx.fillRect(0, 342, W, H);
      ctx.strokeStyle = '#9c7a5b'; ctx.lineWidth = 2; for (let x = 0; x < W; x += 64) { ctx.beginPath(); ctx.moveTo(x, 342); ctx.lineTo(x - 80, H); ctx.stroke(); }
      // steam
      for (let i = 0; i < 3; i++) {
        const ph = (t * 0.6 + i / 3) % 1;
        ctx.fillStyle = `rgba(255,255,255,${0.7 - ph * 0.7})`; ctx.beginPath(); ctx.arc(200 + i * 18 + Math.sin(t * 3 + i) * 4, 220 - ph * 50, 6, 0, 7); ctx.fill();
      }
      // tables
      for (const [x, y] of [[620, 420], [800, 470]]) {
        ctx.fillStyle = '#6c584c'; ctx.fillRect(x - 4, y - 40, 8, 40);
        ctx.fillStyle = '#a98467'; ctx.beginPath(); ctx.ellipse(x, y - 42, 46, 13, 0, 0, 7); ctx.fill();
      }
    },
    beach(ctx, t) {
      sky(ctx, '#ff9a8b', '#ffd6a5', 260);
      ctx.fillStyle = '#ffe066'; ctx.beginPath(); ctx.arc(720, 200, 60, 0, 7); ctx.fill();
      // sea
      const g = ctx.createLinearGradient(0, 220, 0, 360); g.addColorStop(0, '#1b98e0'); g.addColorStop(1, '#4cc9f0');
      ctx.fillStyle = g; ctx.fillRect(0, 220, W, 140);
      ctx.strokeStyle = 'rgba(255,255,255,0.6)'; ctx.lineWidth = 3;
      for (let row = 0; row < 4; row++) {
        ctx.beginPath();
        for (let x = 0; x <= W; x += 10) ctx.lineTo(x, 250 + row * 28 + Math.sin(x / 40 + t * 2 + row) * 4);
        ctx.stroke();
      }
      // sand
      ctx.fillStyle = '#f6d89a'; ctx.beginPath(); ctx.moveTo(0, 350);
      for (let x = 0; x <= W; x += 20) ctx.lineTo(x, 345 + Math.sin(x / 70 + t) * 5);
      ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.fill();
      // sparkles
      for (let i = 0; i < 25; i++) {
        const a = (Math.sin(t * 3 + i * 7.3) + 1) / 2;
        ctx.fillStyle = `rgba(255,255,255,${a})`; ctx.fillRect((i * 137) % W, 370 + (i * 53) % 160, 3, 3);
      }
      // palm + umbrella
      ctx.strokeStyle = '#8d6e63'; ctx.lineWidth = 14; ctx.beginPath(); ctx.moveTo(880, 400); ctx.quadraticCurveTo(900, 300, 860, 200); ctx.stroke();
      ctx.fillStyle = '#2d6a4f';
      for (let i = 0; i < 6; i++) { ctx.save(); ctx.translate(860, 200); ctx.rotate(i * 1.05 + Math.sin(t) * 0.05); ctx.beginPath(); ctx.ellipse(45, 0, 50, 12, 0, 0, 7); ctx.fill(); ctx.restore(); }
      ctx.fillStyle = '#ddd'; ctx.fillRect(477, 310, 6, 110);
      ctx.fillStyle = '#ff5d73'; ctx.beginPath(); ctx.moveTo(400, 320); ctx.quadraticCurveTo(480, 250, 560, 320); ctx.closePath(); ctx.fill();
    },
    arcade(ctx, t) {
      const rr = R();
      ctx.fillStyle = '#1a1033'; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#26184a'; ctx.fillRect(0, 0, W, 340);
      // neon sign
      ctx.save(); ctx.shadowColor = '#ff4ecd'; ctx.shadowBlur = 20 + Math.sin(t * 4) * 8;
      ctx.fillStyle = '#ff9ff3'; ctx.font = 'bold 54px Fredoka, sans-serif'; ctx.textAlign = 'center'; ctx.fillText('BYTE ARCADE', 480, 100); ctx.restore();
      // cabinets
      const cols = ['#ff5d73', '#4d96ff', '#ffd93d', '#6bcb77', '#9b5de5'];
      for (let i = 0; i < 5; i++) {
        const x = 110 + i * 170;
        const big = i === 0 || i === 4;
        const cx = big ? (i === 0 ? 200 : 760) : x;
        if (big) continue;
        ctx.fillStyle = cols[i]; rr(ctx, cx - 45, 160, 90, 170, 8); ctx.fill();
        ctx.fillStyle = '#000'; rr(ctx, cx - 32, 180, 64, 54, 4); ctx.fill();
        ctx.fillStyle = `hsl(${(t * 80 + i * 60) % 360},90%,60%)`; ctx.fillRect(cx - 26, 186 + ((t * 40 + i * 13) % 40), 10, 10);
      }
      // the two playable Star Catch cabinets
      for (const cx of [200, 760]) {
        ctx.save(); ctx.shadowColor = '#ffd93d'; ctx.shadowBlur = 18;
        ctx.fillStyle = '#ff9f43'; rr(ctx, cx - 55, 140, 110, 200, 10); ctx.fill(); ctx.restore();
        ctx.fillStyle = '#000'; rr(ctx, cx - 40, 165, 80, 66, 5); ctx.fill();
        for (let k = 0; k < 4; k++) { ctx.fillStyle = '#ffd93d'; ctx.font = '14px sans-serif'; ctx.fillText('★', cx - 30 + k * 18, 180 + ((t * 50 + k * 17) % 50)); }
        ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Fredoka, sans-serif'; ctx.textAlign = 'center'; ctx.fillText('STAR CATCH', cx, 158);
        ctx.fillStyle = '#ffd93d'; ctx.fillText('click to play!', cx, 260 + Math.sin(t * 5) * 3);
      }
      // floor grid
      ctx.strokeStyle = 'rgba(255,78,205,0.35)'; ctx.lineWidth = 2;
      for (let y = 345; y < H; y += 26) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
      for (let x = -400; x < W + 400; x += 70) { ctx.beginPath(); ctx.moveTo(480 + (x - 480) * 0.3, 340); ctx.lineTo(x, H); ctx.stroke(); }
    },
    rooftop(ctx, t) {
      sky(ctx, '#0b0033', '#3a0ca3', 330);
      for (let i = 0; i < 60; i++) { ctx.fillStyle = `rgba(255,255,255,${0.4 + 0.6 * Math.abs(Math.sin(t + i))})`; ctx.fillRect((i * 97) % W, (i * 41) % 200, 2, 2); }
      // skyline
      ctx.fillStyle = '#10002b';
      for (let i = 0; i < 16; i++) { const h = 80 + ((i * 67) % 130); ctx.fillRect(i * 62, 330 - h, 56, h); }
      ctx.fillStyle = '#ffd60a';
      for (let i = 0; i < 80; i++) if ((i * 31 + Math.floor(t)) % 7 === 0) ctx.fillRect((i * 53) % W, 220 + (i * 29) % 100, 5, 6);
      // dance floor
      ctx.fillStyle = '#240046'; ctx.fillRect(0, 330, W, H - 330);
      const tile = 48, beat = Math.floor(t * 2.2);
      for (let y = 340, r = 0; y < H; y += tile, r++) for (let x = 150, c = 0; x < 810; x += tile, c++) {
        const hue = ((r + c + beat) * 47) % 360;
        ctx.fillStyle = (r + c + beat) % 3 === 0 ? `hsl(${hue},90%,60%)` : `hsla(${hue},70%,40%,0.6)`;
        ctx.fillRect(x + 2, y + 2, tile - 4, tile - 4);
      }
      // spotlights
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      for (const [x, c] of [[180, 'rgba(255,0,170,0.18)'], [780, 'rgba(0,200,255,0.18)']]) {
        const sw = Math.sin(t * 1.3 + x) * 160;
        ctx.fillStyle = c; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(480 + sw - 70, H); ctx.lineTo(480 + sw + 70, H); ctx.closePath(); ctx.fill();
      }
      ctx.restore();
      // DJ booth
      const rr = R();
      ctx.fillStyle = '#3c096c'; rr(ctx, 400, 250, 160, 80, 10); ctx.fill();
      ctx.fillStyle = '#c77dff'; ctx.font = 'bold 18px Fredoka, sans-serif'; ctx.textAlign = 'center'; ctx.fillText('♪ DJ ♪', 480, 300);
    },
  };

  function paint(ctx, roomId, t) {
    (painters[roomId] || painters.plaza)(ctx, t);
    const def = root.Catalog.ROOMS[roomId];
    if (def) for (const d of def.doors) doorSign(ctx, d);
  }
  root.RoomPainter = { paint, W, H };
})(this);
