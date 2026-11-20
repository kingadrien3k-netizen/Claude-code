// Pure decision logic: which coins to buy, and when to sell. No network, no I/O.

const HOUR = 3600e3;

function norm(s) {
  return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function matchesKeyword(text, keywords) {
  const t = norm(text);
  return keywords.some((k) => t.includes(norm(k)));
}

// Decide which pairs are buy candidates. `seenSymbols` maps normalised symbol ->
// earliest createdAt we've ever seen, so later copies of the same ticker are skipped.
function screen(pairs, cfg, now, seenSymbols = {}) {
  const buy = [];
  const skipped = [];
  const skip = (p, reason) => skipped.push({ ...p, reason });

  // Record the earliest launch per symbol first, so the "OG" wins regardless of order.
  for (const p of pairs) {
    const s = norm(p.symbol);
    if (!s || !p.createdAt) continue;
    if (!(s in seenSymbols) || p.createdAt < seenSymbols[s].createdAt) {
      seenSymbols[s] = { createdAt: p.createdAt, address: p.address };
    }
  }

  for (const p of pairs) {
    const nameHit = matchesKeyword(p.name, cfg.keywords);
    const symHit = matchesKeyword(p.symbol, cfg.keywords);
    p.ageHours = p.createdAt ? (now - p.createdAt) / HOUR : Infinity;

    if (cfg.chain && p.chain !== cfg.chain) { skip(p, 'wrong chain'); continue; }
    if (!nameHit && !symHit) { skip(p, 'off theme'); continue; }
    if (cfg.requireNameMatch && symHit && !nameHit) { skip(p, 'ticker-only look-alike'); continue; }
    if (!p.priceUsd) { skip(p, 'no price'); continue; }
    if (p.ageHours > cfg.maxAgeHours) { skip(p, 'too old'); continue; }
    if (p.liquidityUsd < cfg.minLiquidityUsd) { skip(p, 'low liquidity'); continue; }
    if (p.marketCap < cfg.minMarketCap) { skip(p, 'market cap too small'); continue; }
    if (p.marketCap > cfg.maxMarketCap) { skip(p, 'market cap too big'); continue; }
    const og = seenSymbols[norm(p.symbol)];
    if (og && og.address !== p.address) { skip(p, 'clone of earlier ticker'); continue; }
    buy.push(p);
  }
  // Freshest first.
  buy.sort((a, b) => b.createdAt - a.createdAt);
  return { buy, skipped };
}

// Returns null, or { fraction, reason, rug } describing what to sell.
function exitSignal(pos, quote, cfg, now, stopTime) {
  if (!quote || !quote.priceUsd) return null;
  const price = quote.priceUsd;
  const multiple = price / pos.entryPrice;

  if (quote.liquidityUsd < cfg.rugLiquidityUsd) return { fraction: 1, reason: 'liquidity pulled (rug)', rug: true };
  if (stopTime && now >= stopTime) return { fraction: 1, reason: `stop time ${cfg.stopAt}` };
  if (multiple <= 1 - cfg.stopLossPct) return { fraction: 1, reason: `stop loss (${fmtX(multiple)})` };
  if (!pos.tookProfit && multiple >= cfg.takeProfitMultiple) {
    return { fraction: cfg.takeProfitFraction, reason: `take profit at ${fmtX(multiple)}`, tookProfit: true };
  }
  if (pos.tookProfit && price <= pos.peak * (1 - cfg.trailingStopPct)) {
    return { fraction: 1, reason: `trailing stop (${fmtX(multiple)})` };
  }
  if (now - pos.openedAt >= cfg.maxHoldHours * HOUR) return { fraction: 1, reason: 'max hold time' };
  return null;
}

// "23:30" -> timestamp of that local time today (or tomorrow if already past at start).
function stopTimestamp(hhmm, startedAt) {
  if (!hhmm) return null;
  const [h, m] = hhmm.split(':').map(Number);
  const d = new Date(startedAt);
  d.setHours(h, m, 0, 0);
  if (d.getTime() <= startedAt) d.setDate(d.getDate() + 1);
  return d.getTime();
}

function fmtX(x) {
  return 'x' + x.toFixed(x < 10 ? 2 : 1);
}

module.exports = { screen, exitSignal, stopTimestamp, matchesKeyword, norm, fmtX, HOUR };
