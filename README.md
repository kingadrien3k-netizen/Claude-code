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

# Clipbot (`clipbot/`)

A Python bot that watches Twitch chats, clips hype moments, renders them as vertical
videos with hook text and posts them to TikTok with captions. See `clipbot/README.md`.
