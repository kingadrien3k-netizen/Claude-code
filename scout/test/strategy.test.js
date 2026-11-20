const test = require('node:test');
const assert = require('node:assert');
const { screen, exitSignal } = require('../lib/strategy');
const pf = require('../lib/portfolio');

const cfg = JSON.parse(require('fs').readFileSync(__dirname + '/../config.json', 'utf8'));
const H = 3600e3;
const now = Date.UTC(2026, 10, 18, 12);
const pair = (o) => ({ chain: 'solana', name: 'GTA 6', symbol: 'GTA6', address: 'A', priceUsd: 0.0001,
  liquidityUsd: 20000, marketCap: 50000, createdAt: now - H, volume24h: 0, ...o });

test('buys an on-theme OG, skips clone, look-alike, off-theme and illiquid coins', () => {
  const { buy, skipped } = screen([
    pair({ address: 'OG', createdAt: now - 2 * H }),
    pair({ address: 'CLONE', createdAt: now - H }),
    pair({ address: 'LOOK', name: 'Grand Token Alpha', symbol: 'GTA' }),
    pair({ address: 'OFF', name: 'Moon Frog', symbol: 'MFROG' }),
    pair({ address: 'THIN', name: 'GTA Rocco', symbol: 'ROCCO', liquidityUsd: 100 }),
  ], cfg, now, {});
  assert.deepStrictEqual(buy.map((p) => p.address), ['OG']);
  const why = Object.fromEntries(skipped.map((s) => [s.address, s.reason]));
  assert.strictEqual(why.CLONE, 'clone of earlier ticker');
  assert.strictEqual(why.LOOK, 'ticker-only look-alike');
  assert.strictEqual(why.OFF, 'off theme');
  assert.strictEqual(why.THIN, 'low liquidity');
});

test('exit rules: take profit, trailing stop, stop loss, rug, stop time', () => {
  const pos = { entryPrice: 1, peak: 1, tookProfit: false, openedAt: now };
  const q = (priceUsd, liquidityUsd = 20000) => ({ priceUsd, liquidityUsd });
  assert.strictEqual(exitSignal(pos, q(1.5), cfg, now), null);
  assert.strictEqual(exitSignal(pos, q(3.2), cfg, now).fraction, 0.5);
  assert.match(exitSignal(pos, q(0.4), cfg, now).reason, /stop loss/);
  assert.ok(exitSignal(pos, q(2, 100), cfg, now).rug);
  assert.match(exitSignal(pos, q(1.2), cfg, now, now - 1).reason, /stop time/);
  const after = { ...pos, tookProfit: true, peak: 6 };
  assert.match(exitSignal(after, q(4.4), cfg, now).reason, /trailing stop/);
  assert.strictEqual(exitSignal(after, q(5), cfg, now), null);
});

test('paper portfolio math includes slippage', () => {
  const p = pf.newPortfolio(300);
  pf.buy(p, pair({ priceUsd: 1 }), 100, 0, now);
  pf.sell(p, 'A', 0.5, 3, 0, 'tp', now);
  pf.sell(p, 'A', 1, 2, 0, 'trail', now);
  assert.strictEqual(p.cash, 200 + 150 + 100);
  assert.strictEqual(p.closed[0].pnl, 150);
  const q = pf.newPortfolio(100);
  pf.buy(q, pair({ priceUsd: 1 }), 100, 0.03, now);
  pf.sell(q, 'A', 1, 1, 0.03, 'flat', now);
  assert.ok(q.cash < 95, 'round trip at same price loses ~6% to slippage');
});
