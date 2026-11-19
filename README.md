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

# Sec+ Drill (`secplus/`)

**Phone app:** Sec+ Drill installs as a home-screen app (full screen, offline, bottom tab bar). It is served by GitHub Pages from this branch: once Pages is on, open https://kingadrien3k-netizen.github.io/Claude-code/secplus/ on your phone and choose *Add to Home Screen* (iPhone: Share menu in Safari) or *Install app* (Android Chrome). `secplus/manifest.webmanifest` and `secplus/sw.js` handle install and offline; bump `VERSION` in `sw.js` when app files change so installed copies update.

A study app for the 304 CompTIA Security+ cards in the Quizlet folder
"Sec+ Flashcards (in progress)". Open `secplus/index.html` in any browser; no install or build step.

- **Today's one thing**: the top of the lobby shows one concept per day (a 37-day path through the lessons, `secplus/daily.js`, Day 1 = 2026-11-19): one animated picture, a plain explanation, 3 questions, a learning streak, and a catch-up button for yesterday. A noon (US Eastern) phone reminder teaches the same day's concept.
- **Learn** (start here): 9 picture-first lessons, 37 animated diagrams (packets moving, attacks blocked or getting through) with a plain-English caption and a "think of it as" comparison per scene, then a quick check on the matching cards. Content in `secplus/lessons.js`.
- **Labs** (hands-on, like the exam's performance-based questions): flag attacks in logs, fix firewall rule order and actions against test traffic, order processes, sort controls into buckets, work the risk math. 20 labs in `secplus/labs.js`.
- **Lobby**: the home page is a hunter status screen (dark mode by default, with a light toggle): rank badge, level and XP, five stats that are your mastery of the five exam domains (tap one to aim every mode at it), a daily quest, and a Rank-up Trial that unlocks at each rank's level cap. Every mode earns XP; the leveling rules are shared with the terminal game (`secplus/hunter-core.js`).
- **Breach** (arcade): definitions come in as threats with a burning fuse; pick the term to block them, build combos up to x5, and beat a scenario boss each wave. Misses cost a shield and show the right answer; at game over you can drill everything that got through.
- **Scenarios**: 48 original exam-style questions (in `secplus/scenarios.js`) with an explanation after each answer
- **Exam readiness**: every card is tagged with its SY0-701 domain; readiness is weighted by each domain's share of the exam and flags where to focus. Tap a domain to aim every mode at it.
- **Flashcards**: flip, then mark "Still learning" or "Knew it" (Space, 1, 2)
- **Multiple choice**: four options picked from similar cards, so distractors are plausible (keys 1-4, Enter)
- **Type the term**: accepts the full term or its acronym, ignores case and punctuation, allows a small typo on long terms
- **Browse**: search every card and see its mastery level
- Weakest cards come first; three correct answers in a row marks a card mastered, a miss resets it. Progress is kept in the browser's local storage.
- Exam-clue and memory-trick cards (e.g. "ICS memory trick") appear in Flashcards and Browse only.

| File | Purpose |
|---|---|
| `secplus/cards.js` | The card data, one block per Quizlet set. Add new sets here. |
| `secplus/lessons.js` | Animated picture lessons (scene data) |
| `secplus/labs.js` | Hands-on labs and their checkers |
| `secplus/scenarios.js` | Exam-style scenario questions, tagged by domain |
| `secplus/engine.js` | Answer checking, distractor choice, ordering, mastery levels, domain readiness |
| `secplus/index.html` | The app |
| `test/secplus.js` | `npm run test:secplus` |
