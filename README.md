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
