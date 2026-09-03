"""The owner's tile-naming sheet: one word per tile the machine cannot name.

    PYTHONPATH=. python tools/tile_naming_sheet.py -o work/tile-sheet.html [--limit 200]

Every reader and writer picks tiles, and a tile whose ROLE nobody has stated
gets picked by a statistic (tile 510, a metal plate, became a "sconce" by
brightness). `knowledge/blood/design/owner-anchors-v1.json` holds the tiles
the owner has named; this sheet lists the ones still unnamed that the
campaign actually uses on architecture (wall, floor, ceiling, mask) or as
untyped decoration sprites, ordered by where they matter most: tiles in our
own city first, then E3M1's, then by how many campaign maps use them.

Each card shows the tile rendered through BLOOD.PAL, its engine surface
type from SURFACE.DAT (stone, metal, wood, cloth ...), the slots it is used
in, and one text field. "copy answers" puts the filled cards on the
clipboard as JSON in the anchors' own shape (picnum, kind, label_cs), ready
to merge. Colours are explicit; the owner runs a dark theme.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

from bloodmap.art import read_art_directory, read_palette, tile_preview_png
from bloodmap.format import parse_map
from bloodmap.owner_anchors import load_owner_anchors
from bloodmap.patterns import corpus_root, corpus_map_path, list_corpus_maps

ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "reference" / "blood"
PALETTE = ROOT / "reference" / "blood" / "xmapedit" / "palettes" / "import" / "BLOOD.PAL"
SURFACE = ROOT / "reference" / "blood" / "SURFACE.DAT"
#: NBlood/source/blood/src/tile.h:29-45, in order.
SURF_NAMES = ["none", "stone", "metal", "wood", "flesh", "water", "dirt", "clay",
              "snow", "ice", "leaves", "cloth", "plant", "goo", "lava"]


def census(extra_maps: dict[str, Path]) -> list[dict]:
    """Unanchored tiles on architecture and untyped decoration, by map count."""
    anchored = {a.picnum for a in load_owner_anchors().anchors}
    maps_by: dict[int, set[str]] = defaultdict(set)
    slot: dict[int, Counter] = defaultdict(Counter)

    def scan(disk, name):
        for sec in disk.sectors:
            f = sec.fields
            maps_by[f["floor_picnum"]].add(name); slot[f["floor_picnum"]]["floor"] += 1
            if not f["ceiling_stat"] & 1:
                maps_by[f["ceiling_picnum"]].add(name); slot[f["ceiling_picnum"]]["ceiling"] += 1
        for wall in disk.walls:
            f = wall.fields
            maps_by[f["picnum"]].add(name); slot[f["picnum"]]["wall"] += 1
            if f["cstat"] & 16 and f["over_picnum"] > 0:
                maps_by[f["over_picnum"]].add(name); slot[f["over_picnum"]]["mask"] += 1
        for sprite in disk.sprites:
            f = sprite.fields
            # typed sprites (dudes, pickups, switches, markers) are known by
            # their type; only untyped decoration needs a name from the owner
            if f["cstat"] & 0x8000 or f["type"] != 0:
                continue
            maps_by[f["picnum"]].add(name); slot[f["picnum"]]["deco"] += 1

    for item in list_corpus_maps(corpus_root(), population="blood-campaign", attach_tiers=False):
        try:
            scan(parse_map(Path(item.path).read_bytes()), item.name)
        except Exception:
            continue
    present: dict[str, set[int]] = {}
    for label, path in extra_maps.items():
        if not path.exists():
            continue
        disk = parse_map(path.read_bytes())
        tiles = set()
        for sec in disk.sectors:
            tiles.add(sec.fields["floor_picnum"]); tiles.add(sec.fields["ceiling_picnum"])
        for wall in disk.walls:
            tiles.add(wall.fields["picnum"]); tiles.add(wall.fields["over_picnum"])
        for sprite in disk.sprites:
            tiles.add(sprite.fields["picnum"])
        present[label] = tiles
    rows = []
    for tile, maps in maps_by.items():
        if tile <= 0 or tile in anchored:
            continue
        rows.append({"picnum": tile, "maps": len(maps), "uses": sum(slot[tile].values()),
                     "slots": dict(slot[tile]),
                     "where": [label for label, tiles in present.items() if tile in tiles]})
    order = list(extra_maps)
    rows.sort(key=lambda r: (-sum(len(order) - order.index(w) for w in r["where"]), -r["maps"], -r["uses"]))
    return rows


def build(rows: list[dict], *, limit: int, title: str) -> str:
    tiles = read_art_directory(ART_DIR)
    palette = read_palette(PALETTE)
    surf = SURFACE.read_bytes() if SURFACE.exists() else b""
    cards = []
    for row in rows[:limit]:
        tile = tiles.get(row["picnum"])
        if tile is None or tile.width == 0 or tile.height == 0:
            continue
        png = base64.b64encode(tile_preview_png(tile, palette, max_size=96)).decode("ascii")
        kind = surf[row["picnum"]] if row["picnum"] < len(surf) else 0
        surf_name = SURF_NAMES[kind] if kind < len(SURF_NAMES) else str(kind)
        slots = ", ".join(f"{k} {v}" for k, v in sorted(row["slots"].items(), key=lambda kv: -kv[1]))
        where = " · ".join(row["where"]) or ""
        cards.append(
            f'<div class="card" data-pic="{row["picnum"]}" data-slots="{html.escape(json.dumps(row["slots"]))}">'
            f'<img src="data:image/png;base64,{png}" alt="tile {row["picnum"]}" title="{tile.width}x{tile.height}">'
            f'<div class="meta"><b>#{row["picnum"]}</b> <span class="surf">{surf_name}</span> {tile.width}×{tile.height}'
            f'<br><span class="slots">{html.escape(slots)}</span><br><span class="maps">{row["maps"]} maps'
            f'{(" · " + html.escape(where)) if where else ""}</span></div>'
            f'<input type="text" placeholder="co to je (jedno slovo)" autocomplete="off">'
            f'<label><input type="checkbox" class="skip"> nevím / není důležité</label></div>')
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>
<style>
:root{{color-scheme:light}}html,body{{background:#fff;color:#111;margin:0}}
body{{font:13px system-ui;padding:12px}}
header{{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ccc;z-index:2}}
button{{padding:5px 10px;background:#f0f0f0;color:#111;border:1px solid #888;cursor:pointer;margin-right:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:10px}}
.card{{border:1px solid #bbb;padding:8px;background:#fafafa;display:grid;grid-template-columns:100px 1fr;gap:6px;align-items:start}}
.card.done{{background:#eaf7ea;border-color:#5a5}}
.card img{{width:96px;height:96px;object-fit:contain;image-rendering:pixelated;background:#222;border:1px solid #444;grid-row:1/3}}
.meta{{font-size:12px;line-height:1.3}}.surf{{background:#eee;padding:0 4px;border:1px solid #bbb}}.slots{{color:#333}}.maps{{color:#666}}
.card input[type=text]{{grid-column:2;width:100%;box-sizing:border-box;padding:4px;border:1px solid #888;background:#fff;color:#111}}
.card label{{grid-column:1/3;font-size:11px;color:#666}}
textarea{{width:100%;height:90px;margin-top:8px;background:#fff;color:#111;border:1px solid #888}}
</style>
<header><b>{html.escape(title)}</b> — {len(cards)} dlaždic bez role. Napiš, co to je (česky stačí, jedno slovo nebo krátká fráze:
„cihlová zeď", „dlažba", „okno se závěsem", „plech", „socha"). Tmavé pozadí obrázku je jen rámeček, ne dlaždice.
<div style="margin-top:6px"><button id=copy>copy answers</button><button id=clear>clear</button>
<span id=count></span></div><textarea id=out readonly placeholder="JSON answers appear here after copy"></textarea></header>
<div class="grid">{''.join(cards)}</div>
<script>
const cards=[...document.querySelectorAll('.card')];
function collect(){{const out=[];cards.forEach(c=>{{const t=c.querySelector('input[type=text]').value.trim();const skip=c.querySelector('.skip').checked;
c.classList.toggle('done',!!t||skip);if(t||skip){{const slots=JSON.parse(c.dataset.slots);const kind=Object.entries(slots).sort((a,b)=>b[1]-a[1])[0][0];
out.push({{picnum:+c.dataset.pic,kind:kind==='deco'?'sprite':kind,label_cs:t||null,skip:skip||undefined}});}}}});
document.getElementById('count').textContent=out.length+' answered';return out;}}
document.addEventListener('input',()=>{{try{{localStorage.setItem('tile-sheet',JSON.stringify(collect()));}}catch(e){{}}}});
document.getElementById('copy').onclick=()=>{{const o=document.getElementById('out');o.value=JSON.stringify({{sheet:{json.dumps(title)},answers:collect()}},null,1);o.select();try{{navigator.clipboard.writeText(o.value)}}catch(e){{document.execCommand('copy')}}}};
document.getElementById('clear').onclick=()=>{{cards.forEach(c=>{{c.querySelector('input[type=text]').value='';c.querySelector('.skip').checked=false;c.classList.remove('done')}});collect();}};
try{{const saved=JSON.parse(localStorage.getItem('tile-sheet')||'[]');const by={{}};saved.forEach(a=>by[a.picnum]=a);
cards.forEach(c=>{{const a=by[+c.dataset.pic];if(a){{if(a.label_cs)c.querySelector('input[type=text]').value=a.label_cs;if(a.skip)c.querySelector('.skip').checked=true;}}}});}}catch(e){{}}
collect();
</script>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--title", default="Blood tiles without a role")
    args = ap.parse_args()
    extra = {
        "Blood City": ROOT / "projects" / "blood-city" / "level" / "slice2-streets.MAP",
        "E3M1": corpus_map_path("E3M1.MAP", root=corpus_root(), missing_ok=True),
    }
    rows = census(extra)
    Path(args.output).write_text(build(rows, limit=args.limit, title=args.title), encoding="utf-8")
    print(args.output, "cards:", min(args.limit, len(rows)), "of", len(rows), "unanchored")


if __name__ == "__main__":
    main()
