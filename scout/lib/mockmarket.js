// A fake memecoin market for `--demo` mode and tests. Prices are random, not real.
// It deliberately includes copycats, ticker-only look-alikes, rugs and the odd runner.

function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
}

const NAMES = [
  ['GTA 6', 'GTA6'], ['Rocco GTA', 'ROCCO'], ['Leonida GTA', 'LEONIDA'], ['GTA Wasted', 'WASTED'],
  ['Lucia GTA VI', 'LUCIA'], ['Jason GTA', 'JASON'], ['GTA Vice Dog', 'VICEDOG'], ['GTA Trailer Cat', 'TCAT'],
];
const OFF_THEME = [['Moon Frog', 'MFROG'], ['Christmas Cat', 'XCAT'], ['Doge Lite', 'DOGEL']];

function createMockMarket(clock, seed = 42) {
  const rand = rng(seed);
  const tokens = [];
  let n = 0;

  function spawn(name, symbol, fate) {
    n++;
    const price = 0.00001 + rand() * 0.00004;
    tokens.push({
      chain: 'solana', address: `Mock${n}${symbol}pump`, pairAddress: `Pair${n}`,
      name, symbol, priceUsd: price, supply: 1e9,
      liquidityUsd: 8000 + rand() * 20000, createdAt: clock.now(), volume24h: 0,
      fate, rugAt: clock.now() + (0.5 + rand() * 6) * 3600e3,
      drift: fate === 'runner' ? 0.03 + rand() * 0.04 : fate === 'pop' ? 0.015 : -0.004,
      peakAt: clock.now() + (1 + rand() * 4) * 3600e3, dead: false,
      url: `https://dexscreener.com/solana/Pair${n}`,
    });
  }

  function step() {
    // New launches.
    if (rand() < 0.35) {
      const r = rand();
      if (r < 0.45) {
        const [name, sym] = NAMES[Math.floor(rand() * NAMES.length)];
        const fates = ['runner', 'pop', 'pop', 'bleed', 'rug', 'rug'];
        spawn(name, sym, fates[Math.floor(rand() * fates.length)]); // OG or a clone, if the ticker exists
      } else if (r < 0.65) {
        spawn('Grand Token Alpha', 'GTA', 'rug'); // ticker-only look-alike
      } else {
        const [name, sym] = OFF_THEME[Math.floor(rand() * OFF_THEME.length)];
        spawn(name, sym, 'bleed');
      }
    }
    // Move prices.
    for (const t of tokens) {
      if (t.dead) continue;
      const now = clock.now();
      if (t.fate === 'rug' && now >= t.rugAt) { t.liquidityUsd = 200; t.priceUsd *= 0.05; t.dead = true; continue; }
      let drift = t.drift;
      if (now > t.peakAt) drift = -Math.abs(t.drift) * 0.8 - 0.004; // everything fades eventually
      const shock = (rand() - 0.5) * 0.12;
      t.priceUsd *= Math.exp(drift + shock);
      t.liquidityUsd = Math.max(300, t.liquidityUsd * Math.exp(drift * 0.5 + shock * 0.3));
      t.volume24h += t.liquidityUsd * rand() * 0.2;
    }
  }

  const view = (t) => ({
    chain: t.chain, pairAddress: t.pairAddress, address: t.address, name: t.name, symbol: t.symbol,
    priceUsd: t.priceUsd, liquidityUsd: t.liquidityUsd, marketCap: t.priceUsd * t.supply,
    createdAt: t.createdAt, volume24h: t.volume24h, url: t.url,
  });

  return {
    step,
    async searchPairs(keyword, chain) {
      const k = keyword.toLowerCase();
      return tokens
        .filter((t) => (t.name + ' ' + t.symbol).toLowerCase().includes(k) && (!chain || t.chain === chain))
        .map(view);
    },
    async getTokens(chain, addresses) {
      return tokens.filter((t) => addresses.includes(t.address)).map(view);
    },
  };
}

module.exports = { createMockMarket };
