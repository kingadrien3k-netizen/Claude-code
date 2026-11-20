// Thin client for the public DexScreener API (no key needed).
// Docs: https://docs.dexscreener.com/api/reference
const BASE = 'https://api.dexscreener.com';

async function getJson(path) {
  const res = await fetch(BASE + path, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`DexScreener ${res.status} on ${path}`);
  return res.json();
}

// Normalise a DexScreener pair into the shape the rest of the code uses.
function toPair(p) {
  return {
    chain: p.chainId,
    pairAddress: p.pairAddress,
    address: p.baseToken?.address,
    name: p.baseToken?.name || '',
    symbol: p.baseToken?.symbol || '',
    priceUsd: p.priceUsd ? Number(p.priceUsd) : null,
    liquidityUsd: p.liquidity?.usd ?? 0,
    marketCap: p.marketCap ?? p.fdv ?? 0,
    createdAt: p.pairCreatedAt ?? null,
    volume24h: p.volume?.h24 ?? 0,
    url: p.url || `https://dexscreener.com/${p.chainId}/${p.pairAddress}`,
  };
}

// Keep the most liquid pair for each token.
function bestPerToken(pairs) {
  const byToken = new Map();
  for (const p of pairs) {
    if (!p.address) continue;
    const cur = byToken.get(p.address);
    if (!cur || p.liquidityUsd > cur.liquidityUsd) byToken.set(p.address, p);
  }
  return [...byToken.values()];
}

async function searchPairs(keyword, chain) {
  const data = await getJson(`/latest/dex/search?q=${encodeURIComponent(keyword)}`);
  const pairs = (data.pairs || []).map(toPair).filter((p) => !chain || p.chain === chain);
  return bestPerToken(pairs);
}

// Current price/liquidity for up to 30 tokens per request.
async function getTokens(chain, addresses) {
  const out = [];
  for (let i = 0; i < addresses.length; i += 30) {
    const chunk = addresses.slice(i, i + 30).join(',');
    const data = await getJson(`/tokens/v1/${chain}/${chunk}`);
    out.push(...(Array.isArray(data) ? data : data.pairs || []).map(toPair));
  }
  return bestPerToken(out);
}

module.exports = { searchPairs, getTokens, toPair, bestPerToken };
