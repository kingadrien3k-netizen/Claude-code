// Optional AI check using xAI's Grok API (OpenAI-compatible chat endpoint).
// Only runs if XAI_API_KEY is set. Without it the scout uses its built-in rules only.
async function grokReview(pair, keywords, model) {
  const key = process.env.XAI_API_KEY;
  if (!key) return null;
  const prompt = `You screen brand-new Solana memecoins for a PAPER-TRADING experiment (no real money).
Theme keywords: ${keywords.join(', ')}.
Token: name="${pair.name}", symbol="${pair.symbol}", market cap $${Math.round(pair.marketCap)},
liquidity $${Math.round(pair.liquidityUsd)}, age ${pair.ageHours.toFixed(1)}h, 24h volume $${Math.round(pair.volume24h)}.
Is this a genuine on-theme coin rather than an obvious copycat, spam or likely rug?
Reply ONLY with JSON: {"score": 0-10, "reason": "<12 words"}`;

  const res = await fetch('https://api.x.ai/v1/chat/completions', {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
    body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], temperature: 0 }),
  });
  if (!res.ok) throw new Error(`Grok API ${res.status}: ${(await res.text()).slice(0, 200)}`);
  const text = (await res.json()).choices?.[0]?.message?.content || '';
  const m = text.match(/\{[\s\S]*\}/);
  if (!m) throw new Error('Grok reply had no JSON: ' + text.slice(0, 120));
  const j = JSON.parse(m[0]);
  return { score: Number(j.score) || 0, reason: String(j.reason || '') };
}

module.exports = { grokReview };
