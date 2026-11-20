// Paper-money accounting. Nothing here touches a real wallet.

function newPortfolio(startingCash) {
  return { startingCash, cash: startingCash, positions: {}, closed: [], log: [] };
}

function buy(pf, pair, usd, slippage, now) {
  const fill = pair.priceUsd * (1 + slippage);
  const qty = usd / fill;
  pf.cash -= usd;
  pf.positions[pair.address] = {
    address: pair.address, name: pair.name, symbol: pair.symbol, url: pair.url,
    qty, entryPrice: fill, costUsd: usd, proceedsUsd: 0,
    peak: pair.priceUsd, tookProfit: false, openedAt: now,
  };
  pf.log.push({ t: now, side: 'BUY', symbol: pair.symbol, address: pair.address, price: fill, usd, mc: pair.marketCap });
  return pf.positions[pair.address];
}

function sell(pf, address, fraction, price, slippage, reason, now) {
  const pos = pf.positions[address];
  if (!pos) return null;
  const qty = fraction >= 1 ? pos.qty : pos.qty * fraction;
  const fill = price * (1 - slippage);
  const usd = qty * fill;
  pos.qty -= qty;
  pos.proceedsUsd += usd;
  pf.cash += usd;
  pf.log.push({ t: now, side: 'SELL', symbol: pos.symbol, address, price: fill, usd, reason });
  if (fraction >= 1 || pos.qty <= 1e-12) {
    delete pf.positions[address];
    const pnl = pos.proceedsUsd - pos.costUsd;
    pf.closed.push({
      symbol: pos.symbol, name: pos.name, address, url: pos.url,
      costUsd: pos.costUsd, proceedsUsd: pos.proceedsUsd, pnl,
      multiple: pos.proceedsUsd / pos.costUsd, openedAt: pos.openedAt, closedAt: now, reason,
    });
  }
  return usd;
}

function equity(pf, quotes) {
  let held = 0;
  for (const p of Object.values(pf.positions)) {
    const q = quotes[p.address];
    held += p.qty * (q?.priceUsd ?? p.entryPrice);
  }
  return pf.cash + held;
}

function summary(pf, quotes = {}) {
  const eq = equity(pf, quotes);
  const wins = pf.closed.filter((c) => c.pnl > 0);
  const best = pf.closed.reduce((b, c) => (!b || c.multiple > b.multiple ? c : b), null);
  const worst = pf.closed.reduce((w, c) => (!w || c.multiple < w.multiple ? c : w), null);
  return {
    startingCash: pf.startingCash,
    equity: eq,
    pnl: eq - pf.startingCash,
    pnlPct: ((eq - pf.startingCash) / pf.startingCash) * 100,
    trades: pf.closed.length,
    open: Object.keys(pf.positions).length,
    winRate: pf.closed.length ? (wins.length / pf.closed.length) * 100 : 0,
    best, worst,
  };
}

module.exports = { newPortfolio, buy, sell, equity, summary };
