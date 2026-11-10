#!/usr/bin/env python3
"""Build bars/index.html: bakes a phonetic dictionary into bars/src/app.html.

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


def main():
    page = open(os.path.join(HERE, "src", "app.html")).read()
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
