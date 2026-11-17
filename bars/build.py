#!/usr/bin/env python3
"""Build bars/index.html: bakes a phonetic dictionary and the songs in beats/lyrics into bars/src/app.html.

Needs `pip install cmudict wordfreq`. Usage:
    python3 bars/build.py [--fragment OUT]   # --fragment also writes the page without the <html> wrapper
"""
import json, os, re, sys

import cmudict
from wordfreq import top_n_list

HERE = os.path.dirname(os.path.abspath(__file__))
VOWELS = ["AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"]
CONS = ["B", "CH", "D", "DH", "F", "G", "HH", "JH", "K", "L", "M", "N", "NG", "P", "R", "S", "SH", "T", "TH", "V", "W", "Y", "Z", "ZH"]
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+-./;<=>?@[]^_{}~"
# slurs are left out of the rhyme results
BLOCK = set("""nigger niggers nigga niggas faggot faggots fag fags retard retards retarded spic spics chink chinks
kike kikes tranny trannies dyke dykes wetback wetbacks coon coons gook gooks""".split())


def build_dict(limit=26000):
    syms = [v + s for v in VOWELS for s in "012"] + CONS
    code = {s: ALPHABET[i] for i, s in enumerate(syms)}
    pron = cmudict.dict()
    out, seen = [], set()
    for w in top_n_list("en", 40000):
        if not re.fullmatch(r"[a-z]+(?:'[a-z]+)?", w) or w in seen or w in BLOCK:
            continue
        if len(w) == 1 and w not in ("a", "i"):
            continue
        p = pron.get(w)
        if not p:
            continue
        seen.add(w)
        out.append(w + ":" + "".join(code[x] for x in p[0]))
        if len(out) >= limit:
            break
    return {"alphabet": ALPHABET[:len(syms)], "syms": syms, "words": "|".join(out)}


SKIP = re.compile(r"^(recorded|where it came from|hook \(old)", re.I)


def build_catalog():
    """Read the artist's own songs from beats/lyrics/*.md into [{title, text, note, voice}]."""
    out = []
    folder = os.path.join(HERE, "..", "beats", "lyrics")
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        raw = open(os.path.join(folder, name)).read().splitlines()
        title, note, sections, cur, skip = name[:-3].replace("_", " ").title(), [], [], None, False
        for line in raw:
            if line.startswith("# "):
                m = re.search(r'["“](.+?)["”]', line)
                title = m.group(1) if m else line[2:].replace("nocap —", "").strip().replace("IG caption bars", "IG Caption Bars")
            elif line.startswith("## "):
                head = line[3:].strip()
                skip = bool(SKIP.match(head))
                if not skip:
                    label = re.sub(r"\s*\(.*?\)", "", head).strip() or head
                    cur = [label, []]
                    sections.append(cur)
            elif cur is None and re.match(r"^\s*(\d+\.\s|\s{2,}\S)", line):
                # numbered bars with no section heading (the IG captions file)
                cur = ["Captions", [line]]
                sections.append(cur)
            elif cur is None:
                if line.strip():
                    note.append(line.strip())
            elif not skip and line.strip():
                cur[1].append(line.rstrip())
        voice, lines = [], []
        first_hook = next((sec[1] for sec in sections if sec[0].lower().startswith("hook") and sec[1]), [])
        for label, body in sections:
            body = body or (first_hook if label.lower().startswith("hook") else [])
            lines.append(f"[{label}]")
            for l in body:
                l = re.sub(r"^\s*\d+\.\s*", "", l).strip()
                mine = "*" in l
                l = re.sub(r"\s*\*+\s*", " ", l).strip()
                if mine:
                    voice.append(l)
                lines.append(l)
        out.append({"title": title, "text": "\n".join(lines), "note": " ".join(note)[:400], "voice": voice})
    return out


def main():
    page = open(os.path.join(HERE, "src", "app.html")).read()
    page = page.replace("__CATALOG__", json.dumps(build_catalog(), separators=(",", ":")).replace("</", "<\\/"))
    data = json.dumps(build_dict(), separators=(",", ":")).replace("</", "<\\/")
    page = page.replace("__DICT__", data)
    if "--fragment" in sys.argv:
        open(sys.argv[sys.argv.index("--fragment") + 1], "w").write(page)
    full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + page + "\n</html>\n")
    open(os.path.join(HERE, "index.html"), "w").write(full)
    print("wrote bars/index.html", len(full) // 1024, "KB")


if __name__ == "__main__":
    main()
