# Theme Scout (paper trading)

A **paper-trading** memecoin scanner. It watches new Solana launches on DexScreener for
coins matching a theme (default: `gta`), "buys" the original coin of each ticker with
**fake money**, and sells by fixed rules. Use it to find out whether this strategy would
have made money **before** you risk anything real.

> It never connects to a wallet, never asks for keys, and cannot spend real money.

## What it does
- **Scans** DexScreener every 30 s for coins whose name matches your keywords.
- **Skips** copycats of a ticker that already launched, ticker-only look-alikes
  (e.g. symbol `GTA` but name "Grand Token Alpha"), thin liquidity, and caps outside your range.
- **Optional Grok check:** if you set `XAI_API_KEY`, Grok rates each candidate 0–10 and
  anything below `grokMinScore` is skipped.
- **Buys** 20% of free cash per coin (max $120), up to 4 at once, with 3% simulated slippage.
- **Sells** half at 3x and trails the rest by 25%. It also exits at −50% (stop loss), when
  liquidity is pulled (a rug, with a 50% slippage penalty), after 12 hours, and everything at `stopAt` (23:30).
- **Logs** every trade to `data/live/trades.csv` and saves state, so you can stop and resume.

## Run it
You need **Node.js 18+**. On a computer, install it from nodejs.org. On Android, install
**Termux** and run `pkg install nodejs git`.

```bash
git clone <this repo> && cd <repo>/scout
node scout.js --demo        # 10-second simulated day, no internet needed
node scout.js               # real launches, fake money (leave it running)
node scout.js report        # results so far
node scout.js reset         # wipe the paper portfolio
npm test
```

Options: `--keywords gta,rockstar`, `--cash 300`, `--stop-at 23:30` (or `none`), `--config other.json`.

### Turn on Grok (optional, costs a little API credit)
Get an API key at console.x.ai, then:
```bash
export XAI_API_KEY=your_key_here     # Windows PowerShell: $env:XAI_API_KEY="your_key_here"
node scout.js
```
If xAI renames its models, change `grokModel` in `config.json`.

## Tuning
Every rule lives in `config.json`: keywords, sizing, take-profit multiple, trailing stop,
stop loss, liquidity and market-cap filters, and stop time.

## Reading the results honestly
- Run it for **at least 1–2 weeks** across different themes before trusting a number.
- Paper fills are kinder than real ones. Real memecoin trades also pay priority fees and
  suffer front-running (MEV), and a rug often leaves you unable to sell at all.
- If it can't beat zero on paper, it won't with real money.
