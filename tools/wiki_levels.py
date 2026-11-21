"""What players wrote about each campaign level on the Blood Wiki, mined into facts the catalog can show and search.

The owner, 2026-11-21: "You should be able to mine info about levels into our
catalog from https://www.blood-wiki.org/index.php/E3M3:_Raw_Sewage". Each level
page is MediaWiki text: a `{{level_stats}}` block (designer, song, enemies per
difficulty, secrets), then `== Walkthrough ==`, `== Enemies Present ==`,
`== Weapons Available ==`, `== Secrets ==` (each ending ``''Reward: X''``) and
`== Trivia ==`.

What is kept, in `knowledge/blood/wiki/levels.json`, is facts: numbers,
names, the keys in the order the walkthrough takes them, each secret's
reward, and the words of `WORDS` each section uses. The page's own prose is
not redistributed (the wiki states no license): it is cached under
`work/wiki/` for whoever is working here to read with `show`.

    python -m tools.wiki_levels fetch [E3M3 ...]   # raw wikitext into work/wiki/ (all levels by default)
    python -m tools.wiki_levels mine               # work/wiki/*.wiki -> knowledge/blood/wiki/levels.json
    python -m tools.wiki_levels show E3M3          # the facts, then the cached walkthrough and secrets
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "work" / "wiki"
FACTS = ROOT / "knowledge" / "blood" / "wiki" / "levels.json"
SITE = "https://www.blood-wiki.org/index.php"

#: map -> its page title (Category:Levels, read 2026-11-21)
TITLES: dict[str, str] = {
    "E1M1": "Cradle to Grave", "E1M2": "Wrong Side of the Tracks", "E1M3": "Phantom Express",
    "E1M4": "Dark Carnival", "E1M5": "Hallowed Grounds", "E1M6": "The Great Temple",
    "E1M7": "Altar of Stone", "E1M8": "House of Horrors",
    "E2M1": "Shipwrecked", "E2M2": "The Lumber Mill", "E2M3": "Rest for the Wicked",
    "E2M4": "The Overlooked Hotel", "E2M5": "The Haunting", "E2M6": "The Cold Rush",
    "E2M7": "Bowels of the Earth", "E2M8": "The Lair of Shial", "E2M9": "Thin Ice",
    "E3M1": "Ghost Town", "E3M2": "The Siege", "E3M3": "Raw Sewage", "E3M4": "The Sick Ward",
    "E3M5": "Spare Parts", "E3M6": "Monster Bait", "E3M7": "The Pit of Cerberus", "E3M8": "Catacombs",
    "E4M1": "Butchery Loves Company", "E4M2": "Breeding Grounds", "E4M3": "Charnel House",
    "E4M4": "Crystal Lake", "E4M5": "Fire and Brimstone", "E4M6": "The Ganglion Depths",
    "E4M7": "In The Flesh", "E4M8": "The Hall of the Epiphany", "E4M9": "Mall of the Dead",
    "E6M1": "Welcome To Your Life", "E6M2": "They Are Here", "E6M3": "Public Storage",
    "E6M4": "Aqueducts", "E6M5": "The Ruined Temple", "E6M6": "Forbidden Rituals",
    "E6M7": "The Dungeon", "E6M8": "Beauty and the Beast", "E6M9": "Forgotten Catacombs",
}

#: Blood's keys, as players name them
KEYS = ("skull", "eye", "fire", "dagger", "spider", "moon")
#: words worth finding a level by: what is in it and what is done there. A
#: word is counted once per section; a plural or -ing form counts as the word.
WORDS = (
    "water", "underwater", "swim", "sewage", "sewer", "slime", "waterfall", "pool", "river", "lake",
    "ice", "lava", "valve", "wheel", "pipe", "pump", "fan", "crusher", "conveyor", "machine",
    "generator", "bridge", "catwalk", "ladder", "stairs", "lift", "elevator", "door", "gate",
    "switch", "button", "lever", "symbol", "seal", "key", "bars", "grate", "vent", "duct", "crate",
    "box", "barrel", "train", "boat", "ship", "car", "truck", "cart", "rail", "mine", "tunnel",
    "cave", "crypt", "tomb", "coffin", "grave", "cemetery", "church", "altar", "temple", "chapel",
    "hotel", "hospital", "morgue", "mall", "shop", "store", "bar", "library", "office", "kitchen",
    "factory", "mill", "warehouse", "dock", "pier", "street", "alley", "roof", "window", "glass",
    "spinning", "rotating", "explode", "dynamite", "trap", "spike", "blade", "fire", "darkness",
    "bed", "straw", "plant", "statue", "painting", "bookcase", "fireplace", "summoning", "ritual",
)
SECTIONS = {"walkthrough": "walkthrough", "enemies present": "enemies", "weapons available": "weapons",
            "secrets": "secrets", "trivia": "trivia"}


def url(map_name: str, raw: bool = True) -> str:
    title = f"{map_name}: {TITLES[map_name]}".replace(" ", "_")
    if raw:
        return f"{SITE}?title={urllib.parse.quote(title)}&action=raw"
    return f"{SITE}/{urllib.parse.quote(title)}"


def fetch(names: list[str], pause: float = 1.0) -> dict[str, str]:
    """Each level's raw wikitext into the cache; returns map -> what happened."""
    CACHE.mkdir(parents=True, exist_ok=True)
    done = {}
    for name in names:
        request = urllib.request.Request(url(name), headers={"User-Agent": "llmapper-wiki-miner/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8")
        except Exception as error:                     # one page failing is reported, not fatal
            done[name] = f"failed: {type(error).__name__}: {error}"
            continue
        (CACHE / f"{name}.wiki").write_text(text, "utf-8")
        done[name] = f"{len(text)} characters"
        time.sleep(pause)
    return done


def _plain(text: str) -> str:
    """Wikitext to plain words: links to their labels, a quotation kept, other templates and markup dropped."""
    # links first: a piped link's `|` inside a quotation would end it
    text = re.sub(r"\[\[(?:[^|\]]*\|)*([^|\]]*)\]\]", r"\1", text)
    text = re.sub(r"\{\{\s*quote\s*\|\s*quotation\s*=\s*\"?(.*?)\"?\s*(?:\|[^{}]*)?\}\}", r"\1" + chr(10), text,
                  flags=re.S | re.I)
    text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text)


def _words(text: str) -> list[str]:
    low = text.lower()
    found = []
    for word in WORDS:
        if re.search(rf"\b{re.escape(word)}(s|es|ing|ed)?\b", low):
            found.append(word)
    return found


def _bullets(body: str) -> list[str]:
    return [line.lstrip("*# ").strip() for line in body.splitlines() if line.strip().startswith(("*", "#"))]


def parse(map_name: str, text: str) -> dict:
    """The facts of one level page."""
    row: dict = {"map": map_name, "title": TITLES.get(map_name, ""), "url": url(map_name, raw=False)}
    stats = re.search(r"\{\{\s*level_stats\s*\|(.*?)\}\}", text, re.S | re.I)
    if stats:
        fields = {}
        inner = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", lambda m: m.group(1), stats.group(1))
        for part in inner.split("|"):
            if "=" in part:
                key, value = part.split("=", 1)
                fields[key.strip().lower()] = _plain(value).strip()
        row["designer"] = fields.get("designer", "")
        row["song"] = fields.get("song", "")
        row["enemies_by_difficulty"] = [fields.get(str(n), "") for n in range(1, 6)]
        said = fields.get("secrets", "")
        count = re.match(r"\s*(\d+)", said)
        if count:
            row["secrets_declared"] = int(count.group(1))
        extra = re.search(r"\+\s*(\d+)\s*super", said, re.I)
        if extra:
            row["super_secrets"] = int(extra.group(1))
    sections: dict[str, str] = {}
    parts = re.split(r"^==\s*([^=].*?)\s*==\s*$", text, flags=re.M)
    for heading, body in zip(parts[1::2], parts[2::2]):
        key = SECTIONS.get(heading.strip().lower())
        if key:
            sections[key] = body
    walk = _plain(sections.get("walkthrough", ""))
    row["keys_in_route_order"] = []
    for match in re.finditer(r"\b(" + "|".join(KEYS) + r")\s+key\b", walk, re.I):
        key = match.group(1).lower()
        if key not in row["keys_in_route_order"]:
            row["keys_in_route_order"].append(key)
    row["enemies"] = [_plain(b).strip() for b in _bullets(sections.get("enemies", ""))]
    row["weapons"] = [_plain(b).strip() for b in _bullets(sections.get("weapons", ""))]
    row["secrets"] = []
    for bullet in _bullets(sections.get("secrets", "")):
        reward = re.search(r"Reward:\s*(.*?)(?:''|$)", bullet)
        plain = _plain(bullet)
        row["secrets"].append({"reward": _plain(reward.group(1)).strip().rstrip(".") if reward else "",
                               "words": _words(plain)})
    row["words"] = {key: _words(_plain(sections.get(key, ""))) for key in ("walkthrough", "secrets", "trivia")}
    row["has_text"] = {key: bool(sections.get(key, "").strip()) for key in SECTIONS.values()}
    return row


def mine() -> dict:
    """Every cached page parsed into the facts file."""
    levels = {}
    for path in sorted(CACHE.glob("*.wiki")):
        name = path.stem.upper()
        if name in TITLES:
            levels[name] = parse(name, path.read_text("utf-8"))
    data = {"source": "Blood Wiki (https://www.blood-wiki.org), level pages; facts only, the prose is "
                      "cached locally under work/wiki/ by `python -m tools.wiki_levels fetch`",
            "mined": datetime.date.today().isoformat(), "levels": levels}
    FACTS.parent.mkdir(parents=True, exist_ok=True)
    FACTS.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", "utf-8")
    return data


def facts() -> dict:
    return json.loads(FACTS.read_text("utf-8")).get("levels", {}) if FACTS.exists() else {}


def summary(map_name: str) -> list[str]:
    """The facts of one level as lines for `catalog map`."""
    row = facts().get(map_name.upper())
    if not row:
        return []
    lines = [f"  {row['map']}: {row['title']}" + (f", by {row['designer']}" if row.get("designer") else "")
             + (f"; song {row['song']}" if row.get("song") else "")]
    if row.get("enemies_by_difficulty"):
        lines.append("  enemies by difficulty: " + " / ".join(v or "?" for v in row["enemies_by_difficulty"]))
    if row.get("keys_in_route_order"):
        lines.append("  keys in the walkthrough's order: " + ", ".join(row["keys_in_route_order"]))
    if row.get("secrets"):
        lines.append(f"  secrets: {row.get('secrets_declared', len(row['secrets']))}; rewards "
                     + "; ".join(s["reward"] or "?" for s in row["secrets"]))
    if row.get("words", {}).get("walkthrough"):
        lines.append("  the walkthrough speaks of: " + ", ".join(row["words"]["walkthrough"]))
    if row.get("enemies"):
        lines.append("  enemies: " + ", ".join(row["enemies"]))
    lines.append(f"  read it: python -m tools.wiki_levels show {row['map']}   ({row['url']})")
    return lines


def find(words: list[str]) -> list[str]:
    """Levels whose page facts (or cached text) use every one of the words."""
    out = []
    for name, row in sorted(facts().items()):
        said = " ".join([row.get("title", ""), " ".join(row.get("enemies", [])), " ".join(row.get("weapons", [])),
                         " ".join(s["reward"] + " " + " ".join(s["words"]) for s in row.get("secrets", [])),
                         " ".join(w for v in row.get("words", {}).values() for w in v)]).lower()
        cached = CACHE / f"{name}.wiki"
        if cached.exists():
            said += " " + _plain(cached.read_text("utf-8")).lower()
        if all(re.search(rf"\b{re.escape(w.lower())}", said) for w in words):
            out.append(f"  {name}: {row.get('title', '')}  (python -m tools.wiki_levels show {name})")
    return out


def show(map_name: str) -> str:
    name = map_name.upper()
    lines = ["THE BLOOD WIKI SAYS", *summary(name)]
    cached = CACHE / f"{name}.wiki"
    if not cached.exists():
        lines.append(f"  (no cached page: python -m tools.wiki_levels fetch {name})")
        return "\n".join(lines)
    text = cached.read_text("utf-8")
    parts = re.split(r"^==\s*([^=].*?)\s*==\s*$", text, flags=re.M)
    for heading, body in zip(parts[1::2], parts[2::2]):
        if SECTIONS.get(heading.strip().lower()) in ("walkthrough", "secrets", "trivia"):
            lines.append(f"-- {heading.strip()} (the wiki's words, cached locally) --")
            lines.append(_plain(body).strip())
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("maps", nargs="*")
    sub.add_parser("mine")
    s = sub.add_parser("show")
    s.add_argument("map")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        names = [m.upper() for m in args.maps] or list(TITLES)
        unknown = [n for n in names if n not in TITLES]
        if unknown:
            print("no page known for", unknown)
            return 2
        for name, said in fetch(names).items():
            print(f"{name}: {said}")
    elif args.command == "mine":
        data = mine()
        print(f"{len(data['levels'])} levels -> {FACTS}")
    else:
        print(show(args.map))
    return 0


if __name__ == "__main__":
    sys.exit(main())
