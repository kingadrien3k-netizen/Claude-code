// Shared item catalog + room definitions (used by both server and browser).
(function (root) {
  const PALETTES = {
    skin: ['#ffe0c7', '#f5c9a3', '#e0a878', '#c48552', '#8d5a36', '#5e3b22', '#b8e0c8', '#c9c2f0'],
    hair: ['#2b1d14', '#5a3a22', '#a8692f', '#e8c46a', '#f2efe9', '#d6453d', '#ff7ac8', '#5c7cfa', '#38c39a', '#8a4fff'],
    cloth: ['#ff5d73', '#ff9f43', '#ffd93d', '#6bcb77', '#4d96ff', '#9b5de5', '#222831', '#f4f4f4', '#00c2c7', '#ff6fb5', '#8d6e63', '#3d5a80'],
  };

  // price 0 = free starter item
  const ITEMS = {
    hair: [
      { id: 'short', name: 'Short Crop', price: 0 },
      { id: 'spiky', name: 'Spiky', price: 0 },
      { id: 'long', name: 'Long Flow', price: 0 },
      { id: 'bob', name: 'Bob', price: 60 },
      { id: 'bun', name: 'Space Buns', price: 120 },
      { id: 'mohawk', name: 'Mohawk', price: 150 },
      { id: 'afro', name: 'Cloud Puff', price: 150 },
      { id: 'bald', name: 'Clean Dome', price: 0 },
    ],
    eyes: [
      { id: 'round', name: 'Round', price: 0 },
      { id: 'happy', name: 'Happy', price: 0 },
      { id: 'sleepy', name: 'Sleepy', price: 40 },
      { id: 'star', name: 'Starry', price: 200 },
      { id: 'wink', name: 'Wink', price: 80 },
    ],
    top: [
      { id: 'tee', name: 'Basic Tee', price: 0 },
      { id: 'hoodie', name: 'Hoodie', price: 100 },
      { id: 'tank', name: 'Tank Top', price: 0 },
      { id: 'jacket', name: 'Bomber Jacket', price: 250 },
      { id: 'stripe', name: 'Striped Tee', price: 80 },
      { id: 'tux', name: 'Tux', price: 500 },
    ],
    bottom: [
      { id: 'jeans', name: 'Jeans', price: 0 },
      { id: 'shorts', name: 'Shorts', price: 0 },
      { id: 'skirt', name: 'Skirt', price: 60 },
      { id: 'cargo', name: 'Cargo Pants', price: 120 },
    ],
    shoes: [
      { id: 'sneakers', name: 'Sneakers', price: 0 },
      { id: 'boots', name: 'Boots', price: 90 },
      { id: 'hightops', name: 'High-Tops', price: 140 },
    ],
    hat: [
      { id: 'none', name: 'No Hat', price: 0 },
      { id: 'cap', name: 'Ball Cap', price: 50 },
      { id: 'beanie', name: 'Beanie', price: 70 },
      { id: 'headphones', name: 'Headphones', price: 180 },
      { id: 'tophat', name: 'Top Hat', price: 300 },
      { id: 'crown', name: 'Crown', price: 1000 },
      { id: 'cat', name: 'Cat Ears', price: 220 },
    ],
    acc: [
      { id: 'none', name: 'Nothing', price: 0 },
      { id: 'glasses', name: 'Glasses', price: 60 },
      { id: 'shades', name: 'Shades', price: 150 },
      { id: 'scarf', name: 'Scarf', price: 110 },
      { id: 'blush', name: 'Blush', price: 30 },
      { id: 'wings', name: 'Pixel Wings', price: 800 },
    ],
  };

  const SLOTS = Object.keys(ITEMS);
  const COLOR_FIELDS = { skin: 'skin', hairColor: 'hair', topColor: 'cloth', bottomColor: 'cloth', shoesColor: 'cloth' };

  const DEFAULT_AVATAR = {
    skin: PALETTES.skin[1], hair: 'short', hairColor: PALETTES.hair[1], eyes: 'round',
    top: 'tee', topColor: PALETTES.cloth[4], bottom: 'jeans', bottomColor: PALETTES.cloth[11],
    shoes: 'sneakers', shoesColor: PALETTES.cloth[7], hat: 'none', acc: 'none',
  };

  const EMOTES = ['wave', 'dance', 'jump', 'laugh', 'heart', 'sit'];

  // Rooms: walk band is the y-range avatars can stand in. Doors link rooms.
  const ROOMS = {
    plaza:   { name: 'Sunny Plaza', walk: [330, 520], spawn: [480, 430],
               doors: [{ to: 'cafe', x: 90, y: 360, label: 'Café' }, { to: 'beach', x: 870, y: 360, label: 'Beach' },
                       { to: 'arcade', x: 300, y: 330, label: 'Arcade' }, { to: 'rooftop', x: 660, y: 330, label: 'Rooftop' }] },
    cafe:    { name: 'Bean There Café', walk: [340, 520], spawn: [700, 440],
               doors: [{ to: 'plaza', x: 880, y: 380, label: 'Plaza' }] },
    beach:   { name: 'Glitter Beach', walk: [350, 520], spawn: [200, 440],
               doors: [{ to: 'plaza', x: 70, y: 380, label: 'Plaza' }] },
    arcade:  { name: 'Byte Arcade', walk: [340, 520], spawn: [480, 390],
               doors: [{ to: 'plaza', x: 480, y: 510, label: 'Plaza' }],
               games: [{ id: 'starcatch', x: 200, y: 345, label: 'Star Catch' }, { id: 'starcatch', x: 760, y: 345, label: 'Star Catch' }] },
    rooftop: { name: 'Neon Rooftop', walk: [330, 520], spawn: [480, 450],
               doors: [{ to: 'plaza', x: 90, y: 400, label: 'Plaza' }] },
  };

  function findItem(slot, id) { return (ITEMS[slot] || []).find((i) => i.id === id); }
  function itemKey(slot, id) { return slot + ':' + id; }
  function starterItems() {
    const out = [];
    for (const s of SLOTS) for (const it of ITEMS[s]) if (it.price === 0) out.push(itemKey(s, it.id));
    return out;
  }

  // Returns a clean avatar object or null if invalid / not owned.
  function sanitizeAvatar(a, owned) {
    if (!a || typeof a !== 'object') return null;
    const out = {};
    for (const s of SLOTS) {
      const it = findItem(s, a[s]);
      if (!it) return null;
      if (owned && !owned.includes(itemKey(s, it.id))) return null;
      out[s] = it.id;
    }
    for (const [f, pal] of Object.entries(COLOR_FIELDS)) {
      if (!PALETTES[pal].includes(a[f])) return null;
      out[f] = a[f];
    }
    return out;
  }

  const api = { PALETTES, ITEMS, SLOTS, COLOR_FIELDS, DEFAULT_AVATAR, EMOTES, ROOMS, findItem, itemKey, starterItems, sanitizeAvatar };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Catalog = api;
})(this);
