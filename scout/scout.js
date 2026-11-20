#!/usr/bin/env node
// Theme Scout: a PAPER-TRADING memecoin scanner. It never touches a wallet or real money.
//
//   node scout.js            watch real launches on DexScreener and paper-trade them
//   node scout.js --demo     run against a simulated market (fast, no internet needed)
//   node scout.js report     print results so far
//   node scout.js reset      wipe paper portfolio and start fresh
//
// Options: --keywords gta,rockstar   --cash 300   --stop-at 23:30   --config my.json

const fs = require('fs');
const path = require('path');
const dex = require('./lib/dexscreener');
const { grokReview } = require('./lib/grok');
const { screen, exitSignal, stopTimestamp, fmtX } = require('./lib/strategy');
const pf = require('./lib/portfolio');
const { createMockMarket } = require('./lib/mockmarket');

const args = process.argv.slice(2);
const flag = (name) => {
  const i = args.indexOf('--' + name);
  return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : undefined;
};
const command = args[0] && !args[0].startsWith('--') ? args[0] : 'run';
const demo = !!flag('demo');

const cfgPath = flag('config') || path.join(__dirname, 'config.json');
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
if (flag('keywords')) cfg.keywords = String(flag('keywords')).split(',').map((s) => s.trim()).filter(Boolean);
if (flag('cash')) cfg.startingCash = Number(flag('cash'));
if (flag('stop-at') !== undefined) cfg.stopAt = flag('stop-at') === 'none' ? null : String(flag('stop-at'));

const dataDir = path.join(__dirname, 'data', demo ? 'demo' : 'live');
const statePath = path.join(dataDir, 'state.json');
const csvPath = path.join(dataDir, 'trades.csv');

const money = (n) => (n < 0 ? '-' : '') + '$' + Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const usdShort = (n) => (n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n.toFixed(0)}`);

function loadState() {
  try { return JSON.parse(fs.readFileSync(statePath, 'utf8')); } catch { return null; }
}
function saveState(state) {
  fs.mkdirSync(dataDir, { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(state, null, 1));
}
function appendCsv(entry, clock) {
  fs.mkdirSync(dataDir, { recursive: true });
  if (!fs.existsSync(csvPath)) fs.writeFileSync(csvPath, 'time,side,symbol,address,price_usd,usd,note\n');
  const note = (entry.reason || (entry.mc ? `mc ${Math.round(entry.mc)}` : '')).replace(/,/g, ';');
  fs.appendFileSync(csvPath, [new Date(entry.t).toISOString(), entry.side, entry.symbol, entry.address,
    entry.price.toPrecision(6), entry.usd.toFixed(2), note].join(',') + '\n');
  void clock;
}

function printReport(state, quotes = {}) {
  const s = pf.summary(state.portfolio, quotes);
  const line = '─'.repeat(52);
  console.log(`\n${line}\n PAPER RESULTS ${demo ? '(DEMO — simulated market)' : '(live data, fake money)'}\n${line}`);
  console.log(` Started with   ${money(s.startingCash)}`);
  console.log(` Now worth      ${money(s.equity)}   (${s.pnl >= 0 ? '+' : ''}${money(s.pnl)}, ${s.pnlPct.toFixed(1)}%)`);
  console.log(` Closed trades  ${s.trades}   win rate ${s.winRate.toFixed(0)}%   still open ${s.open}`);
  if (s.best) console.log(` Best           ${s.best.symbol} ${fmtX(s.best.multiple)} (${money(s.best.pnl)})`);
  if (s.worst) console.log(` Worst          ${s.worst.symbol} ${fmtX(s.worst.multiple)} (${money(s.worst.pnl)}) — ${s.worst.reason}`);
  const reasons = {};
  for (const c of state.portfolio.closed) {
    const key = c.reason.replace(/\s*\(.*\)$/, '').replace(/ at x.*$/, '');
    reasons[key] = (reasons[key] || 0) + 1;
  }
  if (Object.keys(reasons).length) console.log(' Exits          ' + Object.entries(reasons).map(([k, v]) => `${k}: ${v}`).join(', '));
  const sk = state.skipCounts || {};
  if (Object.keys(sk).length) console.log(' Skipped        ' + Object.entries(sk).map(([k, v]) => `${k}: ${v}`).join(', '));
  console.log(` Trade log      ${path.relative(process.cwd(), csvPath)}\n${line}\n`);
}

async function main() {
  if (command === 'reset') {
    fs.rmSync(dataDir, { recursive: true, force: true });
    console.log('Paper portfolio wiped:', dataDir);
    return;
  }
  if (command === 'report') {
    const st = loadState();
    if (!st) return console.log('No results yet. Run `node scout.js` (or `--demo`) first.');
    return printReport(st);
  }

  // Clock: real time live, accelerated virtual time in demo (5 simulated minutes per tick).
  let virtual = new Date().setHours(9, 0, 0, 0);
  const clock = demo
    ? { now: () => virtual, sleep: async () => { virtual += 5 * 60e3; await new Promise((r) => setTimeout(r, Number(flag('speed') ?? 40))); } }
    : { now: () => Date.now(), sleep: (ms) => new Promise((r) => setTimeout(r, ms)) };
  const market = demo ? createMockMarket(clock, Number(flag('seed') ?? 7)) : dex;

  let state = demo ? null : loadState();
  if (!state) {
    state = { startedAt: clock.now(), portfolio: pf.newPortfolio(cfg.startingCash), seenSymbols: {}, traded: {}, reviews: {}, skipCounts: {} };
  } else {
    console.log('Resuming saved paper portfolio. (`node scout.js reset` to start over.)');
  }
  if (demo) fs.rmSync(dataDir, { recursive: true, force: true });

  const stopTime = stopTimestamp(cfg.stopAt, clock.now());
  const useGrok = cfg.useGrok && !!process.env.XAI_API_KEY && !demo;

  console.log(`\nTheme Scout — PAPER TRADING ONLY, no real money is used.`);
  console.log(`Keywords: ${cfg.keywords.join(', ')} | chain: ${cfg.chain} | start ${money(cfg.startingCash)}`);
  console.log(`Rules: sell ${cfg.takeProfitFraction * 100}% at x${cfg.takeProfitMultiple}, trail ${cfg.trailingStopPct * 100}%, stop loss -${cfg.stopLossPct * 100}%` +
    (stopTime ? `, sell everything at ${new Date(stopTime).toLocaleString()}` : ''));
  console.log(`AI check: ${useGrok ? 'Grok (' + cfg.grokModel + ')' : demo ? 'off in demo' : 'off (set XAI_API_KEY to turn on)'}\n`);

  const ts = () => new Date(clock.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const say = (msg) => console.log(`${ts()}  ${msg}`);
  const record = () => {
    const e = state.portfolio.log[state.portfolio.log.length - 1];
    appendCsv(e, clock);
  };

  let stopping = false;
  process.on('SIGINT', () => { if (stopping) process.exit(1); stopping = true; console.log('\nStopping after this round… (Ctrl+C again to quit now)'); });

  let lastQuotes = {};
  while (true) {
    if (demo) market.step();
    const now = clock.now();
    const pastStop = stopTime && now >= stopTime;
    try {
      // 1) Manage what we hold.
      const held = Object.keys(state.portfolio.positions);
      if (held.length) {
        const quotes = await market.getTokens(cfg.chain, held);
        lastQuotes = Object.fromEntries(quotes.map((q) => [q.address, q]));
        for (const addr of held) {
          const pos = state.portfolio.positions[addr];
          const q = lastQuotes[addr];
          if (q?.priceUsd) pos.peak = Math.max(pos.peak, q.priceUsd);
          const sig = exitSignal(pos, q, cfg, now, stopTime);
          if (!sig) continue;
          const slip = sig.rug ? cfg.rugSlippagePct : cfg.slippagePct;
          const got = pf.sell(state.portfolio, addr, sig.fraction, q.priceUsd, slip, sig.reason, now);
          if (sig.tookProfit && state.portfolio.positions[addr]) state.portfolio.positions[addr].tookProfit = true;
          record();
          say(`SELL ${sig.fraction >= 1 ? 'all' : Math.round(sig.fraction * 100) + '%'} ${pos.symbol} → ${money(got)}  (${sig.reason})`);
        }
      }

      // 2) Look for new coins (not after the stop time).
      if (!pastStop && !stopping) {
        let pairs = [];
        for (const k of cfg.keywords) pairs.push(...(await market.searchPairs(k, cfg.chain)));
        pairs = dex.bestPerToken(pairs);
        const { buy, skipped } = screen(pairs, cfg, now, state.seenSymbols);
        for (const s of skipped) {
          if (state.traded[s.address] || state.traded['skip:' + s.address]) continue;
          state.traded['skip:' + s.address] = true;
          state.skipCounts[s.reason] = (state.skipCounts[s.reason] || 0) + 1;
          if (s.reason !== 'off theme' && s.reason !== 'too old') say(`skip ${s.symbol} "${s.name}" — ${s.reason}`);
        }
        for (const p of buy) {
          if (state.traded[p.address]) continue;
          if (Object.keys(state.portfolio.positions).length >= cfg.maxOpenPositions) break;
          if (useGrok) {
            let r = state.reviews[p.address];
            if (!r) {
              try { r = await grokReview(p, cfg.keywords, cfg.grokModel); } catch (e) { say(`Grok error: ${e.message}`); continue; }
              state.reviews[p.address] = r;
            }
            if (r.score < cfg.grokMinScore) {
              state.traded[p.address] = 'grok-skip';
              state.skipCounts['Grok said no'] = (state.skipCounts['Grok said no'] || 0) + 1;
              say(`skip ${p.symbol} — Grok ${r.score}/10: ${r.reason}`);
              continue;
            }
          }
          const usd = Math.min(state.portfolio.cash * cfg.positionPct, cfg.maxPositionUsd);
          if (usd < 5) break;
          pf.buy(state.portfolio, p, usd, cfg.slippagePct, now);
          state.traded[p.address] = 'bought';
          record();
          say(`BUY  ${p.symbol} "${p.name}" ${money(usd)} at ${usdShort(p.marketCap)} MC, liq ${usdShort(p.liquidityUsd)}, ${p.ageHours.toFixed(1)}h old`);
        }
      }
    } catch (e) {
      say(`⚠ ${e.message} — will retry`);
    }

    saveState(state);
    const s = pf.summary(state.portfolio, lastQuotes);
    if (!demo || Math.round(clock.now() / 60e3) % 60 === 0) {
      say(`worth ${money(s.equity)} (${s.pnl >= 0 ? '+' : ''}${s.pnlPct.toFixed(1)}%) · cash ${money(state.portfolio.cash)} · open ${s.open}`);
    }

    const done = (pastStop || stopping) && Object.keys(state.portfolio.positions).length === 0;
    if (done || (stopping && !pastStop)) break;
    await clock.sleep(cfg.pollSeconds * 1000);
  }

  printReport(state, lastQuotes);
}

main().catch((e) => { console.error(e); process.exit(1); });
