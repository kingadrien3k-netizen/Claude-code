# Avaterra

An original, browser-based multiplayer avatar hangout in the spirit of the mid-2000s
avatar communities: build a character, walk around themed rooms, chat, emote, play
mini-games, earn coins and spend them on new looks.

All art is drawn procedurally in code (no image assets). The name, characters and rooms
are original.

## Features
- **Accounts**: sign up / log in (scrypt-hashed passwords, stored in `data/users.json`)
- **Avatar creator**: skin, hair, eyes, tops, bottoms, shoes, hats, extras, plus color palettes
- **5 rooms**: Sunny Plaza, Bean There Café, Glitter Beach, Byte Arcade, Neon Rooftop (animated)
- **Real-time multiplayer** over WebSockets: click to walk, speech bubbles, chat log
- **Emotes**: wave, dance, jump, laugh, heart, sit (buttons or `/dance` etc. in chat)
- **Economy**: start with 250 coins, +100 daily bonus, earn up to 60 per Star Catch round
- **Shop**: buy items; ownership is enforced server-side
- **Friends**: click a player to add them; see which room they're in and jump there
- **Local residents**: friendly NPCs wander, chat and emote so the world never feels empty
- Basic chat filter and rate limiting

## Run it
```bash
npm install
npm start          # http://localhost:3000  (PORT env var to change)
npm test           # end-to-end protocol smoke test
```

## Layout
| File | Purpose |
|---|---|
| `server.js` | HTTP static server + WebSocket world, accounts, shop, coins, NPCs |
| `public/catalog.js` | Items, prices, palettes, rooms (shared by server and client) |
| `public/avatar.js` | Procedural avatar renderer with walk/emote animation |
| `public/rooms.js` | Animated room backdrops |
| `public/game.js` | Star Catch mini-game |
| `public/client.js` | UI, networking, rendering loop, dress-up / shop / map / friends |

---

# Thumb Hoops (`hoops/`)

A one-thumb portrait basketball game for phones. Open `hoops/index.html` in any mobile
browser — no install, no build step.

| Gesture | Action |
|---|---|
| Drag anywhere | Dribble (floating joystick appears under your thumb) |
| Press & hold still | Shot meter — release in the green for a perfect shot |
| Quick tap | Crossover burst — can break the defender's ankles |
| Flick upward while dribbling | Quick-release jump shot |
| Drive into the restricted area | Automatic layup (dunk if you're bursting or on fire) |

90-second games, 14-second shot clock, 2s and 3s, rebounds off misses, steals, blocks,
an "on fire" streak bonus, a second defender once you hit 10 points, and a saved best score.

---

# Bar Lab (`bars/`)

A writing gym for lyrical rap. Open `bars/index.html` in any browser, no install.

- **Rhyme Engine**: rhymes by sound from a 26,000-word phonetic dictionary: perfect rhymes,
  multisyllable vowel matches, two-word phrase rhymes ("pocket" → "lock it", "rock it") and slant rhymes
- **The Pad + Breakdown**: write one bar per line; rhyme families are highlighted in color,
  multisyllable rhymes are underlined, with rhyme-scheme letters and syllables per bar
- **Bar Coach**: a 0–100 score from rhyme density, multis, end rhymes, vocabulary and rhythm,
  plus specific fixes (unanswered end words, clichés, repeated rhymes, bars that will rush)
- **Flow**: built-in synthesized beats (boom bap, trap, lo-fi) with a teleprompter that moves one line per bar
- **Drills**: Word Drop freestyle, a 45-second Rhyme Race, Flip It double-entendre cards and a devices reference

Edit `bars/src/app.html`, then rebuild with `pip install cmudict wordfreq && python3 bars/build.py`.
