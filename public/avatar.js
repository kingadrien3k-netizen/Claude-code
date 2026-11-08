// Procedural chibi avatar renderer. Origin = feet center. ~110 units tall at scale 1.
(function (root) {
  function shade(hex, amt) {
    const n = parseInt(hex.slice(1), 16);
    let r = (n >> 16) + amt, g = ((n >> 8) & 255) + amt, b = (n & 255) + amt;
    r = Math.max(0, Math.min(255, r)); g = Math.max(0, Math.min(255, g)); b = Math.max(0, Math.min(255, b));
    return '#' + ((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1);
  }
  function rr(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function fillStroke(ctx, fill, stroke) {
    ctx.fillStyle = fill; ctx.fill();
    ctx.strokeStyle = stroke || shade(fill, -60); ctx.lineWidth = 1.6; ctx.stroke();
  }
  function ellipse(ctx, x, y, rx, ry) { ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); }

  const HEAD_Y = -80, HEAD_R = 23;

  function drawHairBack(ctx, a) {
    const c = a.hairColor;
    if (a.hair === 'long') { rr(ctx, -25, HEAD_Y - 8, 50, 58, 16); fillStroke(ctx, shade(c, -15)); }
    if (a.hair === 'bob') { rr(ctx, -27, HEAD_Y - 10, 54, 40, 18); fillStroke(ctx, shade(c, -15)); }
    if (a.hair === 'afro') { ellipse(ctx, 0, HEAD_Y - 6, 36, 32); fillStroke(ctx, c); }
    if (a.hair === 'bun') {
      ellipse(ctx, -20, HEAD_Y - 22, 11, 11); fillStroke(ctx, c);
      ellipse(ctx, 20, HEAD_Y - 22, 11, 11); fillStroke(ctx, c);
    }
  }
  function drawHairFront(ctx, a) {
    const c = a.hairColor;
    ctx.save();
    switch (a.hair) {
      case 'short': case 'bob': case 'long': case 'bun':
        ctx.beginPath();
        ctx.arc(0, HEAD_Y, HEAD_R + 2, Math.PI * 1.05, Math.PI * 1.95);
        ctx.quadraticCurveTo(10, HEAD_Y - 8, -4, HEAD_Y - 10);
        ctx.quadraticCurveTo(-14, HEAD_Y - 4, -24, HEAD_Y - 2);
        ctx.closePath(); fillStroke(ctx, c); break;
      case 'spiky':
        ctx.beginPath(); ctx.moveTo(-24, HEAD_Y - 2);
        for (let i = 0; i <= 6; i++) {
          const ang = Math.PI * (1.05 + i * 0.15);
          const r = i % 2 ? HEAD_R + 12 : HEAD_R + 1;
          ctx.lineTo(Math.cos(ang) * r, HEAD_Y + Math.sin(ang) * r);
        }
        ctx.lineTo(24, HEAD_Y - 2); ctx.quadraticCurveTo(0, HEAD_Y - 14, -24, HEAD_Y - 2);
        fillStroke(ctx, c); break;
      case 'mohawk':
        ctx.beginPath(); ctx.moveTo(-6, HEAD_Y - 16);
        for (let i = 0; i < 5; i++) { ctx.lineTo(-8 + i * 4, HEAD_Y - 38 - (i % 2) * 6); ctx.lineTo(-4 + i * 4, HEAD_Y - 22); }
        ctx.lineTo(8, HEAD_Y - 16); ctx.closePath(); fillStroke(ctx, c); break;
      case 'afro':
        ctx.beginPath(); ctx.arc(0, HEAD_Y - 4, HEAD_R + 4, Math.PI * 1.08, Math.PI * 1.92);
        ctx.quadraticCurveTo(0, HEAD_Y - 6, -24, HEAD_Y - 10); fillStroke(ctx, c); break;
    }
    ctx.restore();
  }

  function drawEyes(ctx, a, blink, emote) {
    const y = HEAD_Y + 2;
    ctx.fillStyle = '#2a2230'; ctx.strokeStyle = '#2a2230'; ctx.lineWidth = 2.4; ctx.lineCap = 'round';
    const closed = blink || emote === 'laugh';
    for (const sx of [-9, 9]) {
      if (closed || a.eyes === 'happy') {
        ctx.beginPath(); ctx.arc(sx, y + 2, 4.5, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke();
      } else if (a.eyes === 'sleepy') {
        ctx.beginPath(); ctx.moveTo(sx - 5, y + 1); ctx.lineTo(sx + 5, y + 1); ctx.stroke();
        ctx.beginPath(); ctx.arc(sx, y + 1, 4, 0, Math.PI); ctx.fill();
      } else if (a.eyes === 'wink' && sx > 0) {
        ctx.beginPath(); ctx.moveTo(sx - 5, y); ctx.lineTo(sx + 4, y - 3); ctx.moveTo(sx - 5, y); ctx.lineTo(sx + 4, y + 3); ctx.stroke();
      } else if (a.eyes === 'star') {
        ctx.save(); ctx.translate(sx, y); ctx.fillStyle = '#ffcf3d'; ctx.beginPath();
        for (let i = 0; i < 10; i++) { const r = i % 2 ? 2.6 : 6.5, an = -Math.PI / 2 + i * Math.PI / 5; ctx.lineTo(Math.cos(an) * r, Math.sin(an) * r); }
        ctx.closePath(); ctx.fill(); ctx.strokeStyle = '#a07400'; ctx.lineWidth = 1; ctx.stroke(); ctx.restore();
      } else {
        ellipse(ctx, sx, y, 4.2, 5.4); ctx.fill();
        ctx.fillStyle = '#fff'; ellipse(ctx, sx + 1.5, y - 2, 1.6, 1.6); ctx.fill(); ctx.fillStyle = '#2a2230';
      }
    }
    // mouth
    ctx.beginPath();
    if (emote === 'laugh') { ctx.arc(0, HEAD_Y + 11, 6, 0, Math.PI); ctx.closePath(); ctx.fillStyle = '#c9364a'; ctx.fill(); }
    else { ctx.arc(0, HEAD_Y + 10, 4.5, Math.PI * 0.15, Math.PI * 0.85); ctx.lineWidth = 2; ctx.stroke(); }
  }

  function drawHat(ctx, a) {
    const top = HEAD_Y - HEAD_R;
    switch (a.hat) {
      case 'cap':
        ctx.beginPath(); ctx.arc(0, HEAD_Y - 4, HEAD_R + 1, Math.PI, 0); ctx.closePath(); fillStroke(ctx, a.topColor);
        rr(ctx, 4, HEAD_Y - 8, 32, 6, 3); fillStroke(ctx, shade(a.topColor, -30)); break;
      case 'beanie':
        ctx.beginPath(); ctx.arc(0, HEAD_Y - 6, HEAD_R + 2, Math.PI, 0); ctx.closePath(); fillStroke(ctx, a.bottomColor);
        rr(ctx, -26, HEAD_Y - 10, 52, 8, 3); fillStroke(ctx, shade(a.bottomColor, -25));
        ellipse(ctx, 0, top - 8, 6, 6); fillStroke(ctx, '#ffffff'); break;
      case 'headphones':
        ctx.beginPath(); ctx.arc(0, HEAD_Y, HEAD_R + 4, Math.PI * 1.05, Math.PI * 1.95); ctx.lineWidth = 5; ctx.strokeStyle = '#333'; ctx.stroke();
        rr(ctx, -31, HEAD_Y - 6, 10, 18, 4); fillStroke(ctx, '#ff5d73'); rr(ctx, 21, HEAD_Y - 6, 10, 18, 4); fillStroke(ctx, '#ff5d73'); break;
      case 'tophat':
        rr(ctx, -26, top + 2, 52, 6, 3); fillStroke(ctx, '#1d1d24');
        rr(ctx, -16, top - 28, 32, 32, 3); fillStroke(ctx, '#1d1d24'); rr(ctx, -16, top - 6, 32, 5, 0); fillStroke(ctx, '#c9364a'); break;
      case 'crown':
        ctx.beginPath(); ctx.moveTo(-18, top + 6); ctx.lineTo(-20, top - 14); ctx.lineTo(-10, top - 4); ctx.lineTo(0, top - 20);
        ctx.lineTo(10, top - 4); ctx.lineTo(20, top - 14); ctx.lineTo(18, top + 6); ctx.closePath(); fillStroke(ctx, '#ffd93d', '#b08a00');
        ellipse(ctx, 0, top, 3, 3); ctx.fillStyle = '#ff5d73'; ctx.fill(); break;
      case 'cat':
        for (const s of [-1, 1]) {
          ctx.beginPath(); ctx.moveTo(s * 8, top + 4); ctx.lineTo(s * 20, top - 14); ctx.lineTo(s * 22, top + 8); ctx.closePath(); fillStroke(ctx, a.hairColor);
          ctx.beginPath(); ctx.moveTo(s * 12, top + 4); ctx.lineTo(s * 19, top - 7); ctx.lineTo(s * 20, top + 6); ctx.closePath(); ctx.fillStyle = '#ffb3c8'; ctx.fill();
        }
        break;
    }
  }

  function drawAcc(ctx, a, front) {
    if (!front && a.acc === 'wings') {
      for (const s of [-1, 1]) {
        ctx.beginPath(); ctx.moveTo(s * 8, -60); ctx.quadraticCurveTo(s * 50, -95, s * 48, -50); ctx.quadraticCurveTo(s * 34, -46, s * 8, -48);
        ctx.closePath(); fillStroke(ctx, 'rgba(200,230,255,0.85)', '#7fb2e5');
      }
    }
    if (!front) return;
    const y = HEAD_Y + 2;
    switch (a.acc) {
      case 'glasses':
        ctx.strokeStyle = '#333'; ctx.lineWidth = 1.8;
        ellipse(ctx, -9, y, 7, 6); ctx.stroke(); ellipse(ctx, 9, y, 7, 6); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(-2, y); ctx.lineTo(2, y); ctx.stroke(); break;
      case 'shades':
        rr(ctx, -18, y - 5, 15, 10, 4); fillStroke(ctx, '#15151c'); rr(ctx, 3, y - 5, 15, 10, 4); fillStroke(ctx, '#15151c');
        ctx.beginPath(); ctx.moveTo(-3, y - 2); ctx.lineTo(3, y - 2); ctx.strokeStyle = '#15151c'; ctx.stroke(); break;
      case 'scarf':
        rr(ctx, -17, -64, 34, 9, 4); fillStroke(ctx, '#ff6fb5'); rr(ctx, 6, -60, 8, 20, 3); fillStroke(ctx, '#ff6fb5'); break;
      case 'blush':
        ctx.fillStyle = 'rgba(255,110,140,0.45)'; ellipse(ctx, -15, HEAD_Y + 9, 5, 3); ctx.fill(); ellipse(ctx, 15, HEAD_Y + 9, 5, 3); ctx.fill(); break;
    }
  }

  function drawTop(ctx, a) {
    const c = a.topColor;
    if (a.top === 'tux') {
      rr(ctx, -15, -63, 30, 30, 7); fillStroke(ctx, '#1f1f28');
      ctx.beginPath(); ctx.moveTo(-6, -63); ctx.lineTo(0, -40); ctx.lineTo(6, -63); ctx.closePath(); ctx.fillStyle = '#fff'; ctx.fill();
      ctx.beginPath(); ctx.moveTo(-5, -60); ctx.lineTo(0, -57); ctx.lineTo(5, -60); ctx.lineTo(5, -55); ctx.lineTo(0, -57); ctx.lineTo(-5, -55); ctx.closePath();
      ctx.fillStyle = c; ctx.fill(); return;
    }
    rr(ctx, -15, -63, 30, 30, 7); fillStroke(ctx, c);
    if (a.top === 'stripe') {
      ctx.save(); rr(ctx, -15, -63, 30, 30, 7); ctx.clip(); ctx.fillStyle = 'rgba(255,255,255,0.55)';
      for (let y = -58; y < -33; y += 7) ctx.fillRect(-15, y, 30, 3); ctx.restore();
    }
    if (a.top === 'hoodie') {
      rr(ctx, -12, -50, 24, 9, 3); fillStroke(ctx, shade(c, -20));
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(-4, -62); ctx.lineTo(-4, -54); ctx.moveTo(4, -62); ctx.lineTo(4, -54); ctx.stroke();
    }
    if (a.top === 'jacket') {
      ctx.strokeStyle = shade(c, -70); ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(0, -63); ctx.lineTo(0, -33); ctx.stroke();
      rr(ctx, -15, -37, 30, 5, 2); fillStroke(ctx, shade(c, -40));
    }
    if (a.top === 'tank') {
      ctx.fillStyle = a.skin; ctx.beginPath(); ctx.arc(0, -63, 8, 0, Math.PI); ctx.fill();
    }
  }

  function drawArm(ctx, a, side, angle) {
    ctx.save(); ctx.translate(side * 14, -59); ctx.rotate(angle);
    const sleeve = a.top === 'tank' ? a.skin : (a.top === 'tux' ? '#1f1f28' : a.topColor);
    rr(ctx, -4.5, 0, 9, 22, 4.5); fillStroke(ctx, sleeve);
    ellipse(ctx, 0, 23, 5, 5); fillStroke(ctx, a.skin);
    ctx.restore();
  }

  function drawLegs(ctx, a, walk) {
    const sw = Math.sin(walk) * 5;
    for (const [sx, off] of [[-7, sw], [7, -sw]]) {
      ctx.save(); ctx.translate(sx, -36);
      ctx.rotate(off * 0.04);
      const len = 32;
      // skin underneath
      rr(ctx, -5, 0, 10, len, 4); fillStroke(ctx, a.skin);
      // pants
      const c = a.bottomColor;
      if (a.bottom === 'jeans' || a.bottom === 'cargo') { rr(ctx, -5.5, 0, 11, len - 2, 4); fillStroke(ctx, c); }
      if (a.bottom === 'cargo') { rr(ctx, sx < 0 ? -6 : 1, 10, 5, 7, 1); fillStroke(ctx, shade(c, -25)); }
      if (a.bottom === 'shorts') { rr(ctx, -5.5, 0, 11, 13, 3); fillStroke(ctx, c); }
      // shoe
      const sc = a.shoesColor;
      if (a.shoes === 'boots') { rr(ctx, -6, len - 12, 12, 14, 3); fillStroke(ctx, shade(sc, -40)); }
      else if (a.shoes === 'hightops') { rr(ctx, -6, len - 9, 13, 11, 4); fillStroke(ctx, sc); ctx.fillStyle = '#fff'; ctx.fillRect(-6, len - 1, 13, 2); }
      else { rr(ctx, -6, len - 4, 14, 7, 3.5); fillStroke(ctx, sc); }
      ctx.restore();
    }
    if (a.bottom === 'skirt') {
      ctx.beginPath(); ctx.moveTo(-14, -38); ctx.lineTo(14, -38); ctx.lineTo(19, -20); ctx.lineTo(-19, -20); ctx.closePath(); fillStroke(ctx, a.bottomColor);
    } else {
      rr(ctx, -14, -40, 28, 9, 3); fillStroke(ctx, a.bottom === 'shorts' || a.bottom === 'jeans' || a.bottom === 'cargo' ? a.bottomColor : a.topColor);
    }
  }

  // opts: { scale, facing (1|-1), walk (phase), emote, emoteT (seconds), t (time) }
  function draw(ctx, a, x, y, opts) {
    opts = opts || {};
    const s = opts.scale || 1, t = opts.t || 0, e = opts.emote, et = opts.emoteT || 0;
    let bob = 0, armL = 0.25, armR = -0.25, lean = 0, sit = 0;
    if (opts.walking) { bob = Math.abs(Math.sin(opts.walk)) * -2.5; armL = 0.25 + Math.sin(opts.walk) * 0.5; armR = -0.25 - Math.sin(opts.walk) * 0.5; }
    else bob = Math.sin(t * 2) * 0.8;
    if (e === 'wave') armR = -2.6 + Math.sin(et * 14) * 0.4;
    if (e === 'jump') bob = -Math.abs(Math.sin(et * 6)) * 26;
    if (e === 'dance') { bob = -Math.abs(Math.sin(et * 8)) * 6; lean = Math.sin(et * 8) * 0.15; armL = 2.4 + Math.sin(et * 8) * 0.6; armR = -2.4 + Math.cos(et * 8) * 0.6; }
    if (e === 'laugh') { bob = Math.sin(et * 20) * 1.5; armL = 0.6; armR = -0.6; }
    if (e === 'sit') sit = 14;

    ctx.save();
    ctx.translate(x, y);
    // shadow
    ctx.fillStyle = 'rgba(0,0,0,0.18)'; ellipse(ctx, 0, 0, 22 * s * (1 + bob / 80), 6 * s); ctx.fill();
    ctx.scale(s * (opts.facing || 1), s);
    ctx.translate(0, bob + sit);
    ctx.rotate(lean);

    drawAcc(ctx, a, false);
    drawHairBack(ctx, a);
    if (sit) { ctx.save(); ctx.translate(0, -36); ctx.scale(1.15, 0.6); ctx.translate(0, 36); drawLegs(ctx, a, 0); ctx.restore(); }
    else drawLegs(ctx, a, opts.walking ? opts.walk : 0);
    drawArm(ctx, a, -1, armL);
    drawTop(ctx, a);
    drawArm(ctx, a, 1, armR);
    // neck + head
    rr(ctx, -5, -66, 10, 6, 2); ctx.fillStyle = shade(a.skin, -20); ctx.fill();
    ellipse(ctx, 0, HEAD_Y, HEAD_R, HEAD_R - 1); fillStroke(ctx, a.skin);
    ellipse(ctx, -HEAD_R + 1, HEAD_Y + 3, 4, 6); fillStroke(ctx, a.skin); ellipse(ctx, HEAD_R - 1, HEAD_Y + 3, 4, 6); fillStroke(ctx, a.skin);
    ellipse(ctx, 0, HEAD_Y, HEAD_R - 1.5, HEAD_R - 2.5); ctx.fillStyle = a.skin; ctx.fill();
    const blink = (Math.floor(t * 10) % 37) === 0;
    drawEyes(ctx, a, blink, e);
    drawHairFront(ctx, a);
    drawAcc(ctx, a, true);
    drawHat(ctx, a);
    if (e === 'heart') {
      const hy = HEAD_Y - 40 - et * 25;
      ctx.globalAlpha = Math.max(0, 1 - et / 2);
      ctx.font = '22px sans-serif'; ctx.textAlign = 'center'; ctx.fillText('💖', 0, hy);
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  }

  root.AvatarRenderer = { draw, shade, rr, HEIGHT: 112 };
})(this);
