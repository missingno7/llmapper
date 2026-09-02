"""Owner review pack: a decompiled hierarchy browsed on the map, with marks.

    PYTHONPATH=. python tools/review_pack.py MAP HIERARCHY.json -o pack.html

One HTML file, no dependencies: the tree on the left, the map on the right
(XMapEdit's orientation, +Y down), click a node to light its sectors, click
a sector to select the deepest node that owns it, "mark wrong" to attach a
note, and "copy review" to put every mark on the clipboard as JSON the
agent reads back as the owner's answers. Colours are explicit throughout;
the owner runs a dark theme.

The hierarchy is the `hierarchy.json` shape of projects/e2m3-decompiled:
`nodes` is a list of {id, kind, name, parent, children, sectors}. A reader
that produces a different tree adapts `load_nodes` and nothing else.

With `--claims claims.json` -- the shared `(record, field) -> [claims]` ledger
of `bloodmap.read_ledger` -- the pack shows ONE ASPECT AT A TIME (a select of
the tree's top-level branches dims the rest) and a record's fact panel lists
every claim on its fields and every field nothing claims. The owner then marks
a CLAIM rather than a node, and the review JSON carries the record, the field
and the claim's owner. Without the flag the pack is exactly what it was.
Orientation (+Y down) and the explicit colours are untouched either way.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from bloodmap.format import parse_map
from bloodmap.sector_map import _loops_for_sector

PALETTE = ["#d9cfae", "#a8c7e0", "#c6e0a8", "#e0b8a8", "#cdb8e0", "#e0d8a8",
           "#a8e0d4", "#e0a8c9", "#b8c9a0", "#c9b8a0", "#a0b8c9", "#c9a0b8", "#b0b0b0"]


def load_nodes(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data["nodes"] if isinstance(data, dict) else data
    return [{"id": n["id"], "kind": n.get("kind", "?"), "name": n.get("name", n["id"]),
             "parent": n.get("parent"), "children": list(n.get("children", [])),
             "sectors": list(n.get("sectors", []))} for n in nodes]


def build(map_path: Path, hierarchy: Path, title: str,
          claims: dict | None = None, candidates: dict | None = None) -> str:
    disk = parse_map(map_path.read_bytes())
    nodes = load_nodes(hierarchy)
    xs = [w.fields["x"] for w in disk.walls]
    ys = [w.fields["y"] for w in disk.walls]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    width = 1100
    scale = width / max(1, max_x - min_x)
    height = int((max_y - min_y) * scale) + 2

    def xy(p):
        # XMapEdit's orientation: +Y down. Never flip.
        return f"{(p[0] - min_x) * scale:.1f},{(p[1] - min_y) * scale:.1f}"

    # colour by top-level child of the root (assembly), so the coarse
    # partition is visible before any node is clicked
    by_id = {n["id"]: n for n in nodes}
    root = next((n for n in nodes if n["parent"] is None), nodes[0])
    top_colour: dict[str, str] = {}
    for index, child in enumerate(root["children"]):
        top_colour[child] = PALETTE[index % len(PALETTE)]

    def top_of(node_id: str) -> str | None:
        node = by_id.get(node_id)
        while node and node["parent"] not in (None, root["id"]):
            node = by_id.get(node["parent"])
        return node["id"] if node and node["parent"] == root["id"] else None

    sector_owner: dict[int, str] = {}
    for n in nodes:  # deepest owner wins: leaves are listed after parents
        for s in n["sectors"]:
            if n["id"] == root["id"]:
                continue
            prev = sector_owner.get(s)
            if prev is None or len(by_id[prev]["sectors"]) >= len(n["sectors"]):
                sector_owner[s] = n["id"]

    polys = []
    for i, sec in enumerate(disk.sectors):
        loops = _loops_for_sector(disk, i)
        if not loops:
            continue
        f = sec.fields
        owner = sector_owner.get(i)
        colour = top_colour.get(top_of(owner) or "", "#eeeeee") if owner else "#eeeeee"
        shade = f["floor_shade"]
        tip = (f"sector {i} | node {owner or 'RESIDUE'} | floor {f['floor_picnum']} | shade {shade} | "
               f"floor_z {f['floor_z']} | ceil_z {f['ceiling_z']} | type {f['type']}")
        d = " ".join("M" + " L".join(xy(p) for p in lp) + " Z" for lp in loops)
        polys.append(
            f'<path class="sec" d="{d}" fill="{colour}" stroke="#333" stroke-width="0.6" '
            f'data-id="{i}" data-node="{html.escape(owner or "")}"><title>{html.escape(tip)}</title></path>'
            f'<path d="{d}" fill="#000" fill-opacity="{min(0.5, max(0, shade) / 60):.2f}" pointer-events="none"/>')

    # The shared ledger, indexed by sector: the sector's own fields and the
    # fields of every wall it owns. Unclaimed fields are listed too -- a fact
    # panel has to show what nothing explains, not only what something does.
    facts = {}
    if claims is not None:
        from bloodmap.read_ledger import fields_of

        owner_of_wall = {}
        for index, sec in enumerate(disk.sectors):
            start = sec.fields["wall_ptr"]
            for wall in range(start, start + sec.fields["wall_count"]):
                owner_of_wall[wall] = index
        held = {i: [] for i in range(len(disk.sectors))}
        for key, rows in claims.items():
            kind, index, name = key.split(":", 2)
            index = int(index)
            if kind in ("sector", "xsector"):
                sector = index
            elif kind in ("wall", "xwall"):
                sector = owner_of_wall.get(index)
            else:
                sector = disk.sprites[index].fields["sector"]
            if sector is None or sector not in held:
                continue
            held[sector].append({"record": kind + ":" + str(index),
                                 "field": name, "claims": rows})
        # candidates hang off a record id, so they reach a sector the same
        # way a claim does: a reading that is still ambiguous about a record
        # belongs in that record's panel, next to what IS settled about it.
        maybe = {}
        for key, rows in (candidates or {}).items():
            if ":" not in key:
                continue
            kind, rest = key.split(":", 1)
            if not rest.isdigit():
                continue
            index = int(rest)
            if kind in ("sector", "xsector"):
                sector = index
            elif kind in ("wall", "xwall"):
                sector = owner_of_wall.get(index)
            elif kind in ("sprite", "xsprite"):
                sector = disk.sprites[index].fields["sector"]
            else:
                continue
            if sector is None:
                continue
            maybe.setdefault(sector, []).extend(
                {"about": key, **row} for row in rows)
        names = fields_of("sector")
        for index in range(len(disk.sectors)):
            mine = {row["field"] for row in held[index]
                    if row["record"] == "sector:" + str(index)}
            facts[index] = {
                "claims": sorted(held[index],
                                 key=lambda r: (r["record"], r["field"])),
                "candidates": maybe.get(index, []),
                "unclaimed_sector_fields": [n for n in names if n not in mine],
            }
    facts_json = json.dumps(facts)
    aspects_json = json.dumps([{"id": c, "name": by_id[c]["name"]}
                               for c in root["children"] if c in by_id])
    tree_json = json.dumps([{k: n[k] for k in ("id", "kind", "name", "parent", "children", "sectors")} for n in nodes])
    residue = sorted(i for i in range(len(disk.sectors)) if i not in sector_owner)
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>
<style>
:root{{color-scheme:light}}html,body{{background:#fff;color:#111;margin:0;height:100%}}
body{{font:13px system-ui;display:grid;grid-template-columns:320px 1fr 300px;height:100vh}}
#tree,#side{{overflow:auto;padding:10px;background:#fff;color:#111}}#tree{{border-right:1px solid #ccc}}#side{{border-left:1px solid #ccc}}
#mapwrap{{overflow:auto;background:#fafafa}}svg{{width:100%;height:100%}}
.n{{cursor:pointer;padding:1px 2px;white-space:nowrap}}.n:hover{{background:#eef}}.n.sel{{background:#ffe8a0}}.n.marked{{color:#b00000;font-weight:600}}
.kids{{margin-left:14px}}.tg{{display:inline-block;width:12px;color:#666}}
path.sec.lit{{stroke:#e00000;stroke-width:2.2}}path.sec:hover{{stroke:#06c;stroke-width:2}}
button{{margin:4px 2px;padding:4px 8px;background:#f0f0f0;color:#111;border:1px solid #888;cursor:pointer}}
#facts,#marks{{white-space:pre-wrap;background:#f3f3f3;color:#111;padding:6px;margin-top:8px;min-height:60px}}
#claims{{white-space:pre-wrap;background:#f3f3f3;color:#111;padding:6px;margin-top:8px;font:11px ui-monospace,monospace}}
textarea{{width:100%;height:120px;background:#fff;color:#111;border:1px solid #888}}
</style>
<div id=tree><b>{html.escape(title)}</b><div style="color:#666">click a node: its sectors light up. click a sector: its node is selected. residue: {len(residue)} sectors</div><div id=treebody></div></div>
<div id=mapwrap><svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">{''.join(polys)}</svg></div>
<div id=side><b>aspect</b> <select id=aspect><option value="">all</option></select>
<b>selected</b><div id=facts>nothing selected</div>
<div id=claims></div>
<button id=wrong>mark wrong</button><button id=markclaim>mark a claim</button><button id=copy>copy review</button><button id=clear>clear marks</button>
<div id=marks>no marks</div><textarea id=out readonly placeholder="review JSON appears here"></textarea>
<div style="color:#666;margin-top:6px">Orientation as in XMapEdit (+Y down). Darker = higher floor shade. Sector ids are the editor's.</div></div>
<script>
const NODES={tree_json};const byId={{}};NODES.forEach(n=>byId[n.id]=n);
const FACTS={facts_json};const ASPECTS={aspects_json};
const root=NODES.find(n=>n.parent===null)||NODES[0];
let selected=null;const marks=[];
function render(){{const body=document.getElementById('treebody');body.innerHTML='';body.appendChild(item(root));}}
function item(n){{const d=document.createElement('div');const row=document.createElement('div');row.className='n';row.dataset.id=n.id;
const tg=document.createElement('span');tg.className='tg';tg.textContent=n.children.length?'▸':' ';row.appendChild(tg);
row.appendChild(document.createTextNode(n.kind+' '+n.name+' ('+n.sectors.length+')'));d.appendChild(row);
const kids=document.createElement('div');kids.className='kids';kids.hidden=n.id!==root.id;n.children.forEach(c=>{{if(byId[c])kids.appendChild(item(byId[c]))}});d.appendChild(kids);
tg.onclick=e=>{{e.stopPropagation();kids.hidden=!kids.hidden;tg.textContent=kids.hidden?'▸':'▾'}};
row.onclick=()=>select(n.id);return d;}}
function select(id){{selected=id;const n=byId[id];document.querySelectorAll('.n').forEach(e=>e.classList.toggle('sel',e.dataset.id===id));
const set=new Set(n.sectors);document.querySelectorAll('path.sec').forEach(p=>p.classList.toggle('lit',set.has(+p.dataset.id)));
document.getElementById('facts').textContent=n.kind+'\\n'+n.id+'\\nname: '+n.name+'\\nparent: '+n.parent+'\\nsectors: '+n.sectors.join(', ');
let e=document.querySelector('.n[data-id="'+CSS.escape(id)+'"]');let k=e&&e.parentElement.parentElement;while(k&&k.classList&&k.classList.contains('kids')){{k.hidden=false;k=k.parentElement.parentElement}}
if(e)e.scrollIntoView({{block:'nearest'}});}}
document.querySelectorAll('path.sec').forEach(p=>p.onclick=()=>{{const t=p.querySelector('title').textContent.replaceAll(' | ','\\n');if(p.dataset.node)select(p.dataset.node);document.getElementById('facts').textContent+='\\n\\n'+t;showFacts(+p.dataset.id);}});
const aspectSel=document.getElementById('aspect');
ASPECTS.forEach(a=>{{const o=document.createElement('option');o.value=a.id;o.textContent=a.name;aspectSel.appendChild(o)}});
aspectSel.onchange=()=>{{const id=aspectSel.value;const keep=id?new Set(byId[id].sectors):null;
document.querySelectorAll('path.sec').forEach(p=>{{p.style.opacity=(!keep||keep.has(+p.dataset.id))?1:0.12}});}};
function showFacts(sectorId){{const box=document.getElementById('claims');const f=FACTS[sectorId];
if(!f){{box.textContent='';return;}}
let t='claims on sector '+sectorId+' and its walls:\\n';
if(!f.claims.length)t+='  (nothing claims any field of this sector)\\n';
f.claims.forEach(r=>{{r.claims.forEach(c=>{{t+='  '+r.record+'.'+r.field+' = '+JSON.stringify(c.value)+'  [layer '+c.layer+' '+c.owner+']\\n    '+c.why+'\\n'}})}});
if(f.candidates&&f.candidates.length){{t+='\\ncandidates still open on this record:\\n';
f.candidates.forEach(c=>{{t+='  '+c.about+': '+(c.readings||[]).join(' | ')+'\\n    '+(c.why||'')+'\\n'}});}}
t+='\\nunclaimed fields of the sector record:\\n  '+f.unclaimed_sector_fields.join(', ');
box.textContent=t;box.dataset.sector=sectorId;}}
document.getElementById('markclaim').onclick=()=>{{const box=document.getElementById('claims');
const s=box.dataset.sector;if(s===undefined)return;const f=FACTS[s];if(!f)return;
const which=prompt('Which claim is wrong? record.field, e.g. sector:'+s+'.floor_z');if(which===null)return;
const note=prompt('What is wrong with it?');if(note===null)return;
marks.push({{sector:+s,claim:which,note:note}});showMarks();}};
document.getElementById('wrong').onclick=()=>{{if(!selected)return;const note=prompt('What is wrong with '+selected+'?');if(note===null)return;marks.push({{node:selected,sectors:byId[selected].sectors,note}});showMarks();}};
document.getElementById('clear').onclick=()=>{{marks.length=0;showMarks();}};
function showMarks(){{const ids=new Set(marks.map(m=>m.node));document.querySelectorAll('.n').forEach(e=>e.classList.toggle('marked',ids.has(e.dataset.id)));
document.getElementById('marks').textContent=marks.length?marks.map(m=>m.node+': '+m.note).join('\\n'):'no marks';
document.getElementById('out').value=JSON.stringify({{map:{json.dumps(map_path.name)},hierarchy:{json.dumps(hierarchy.name)},marks}},null,1);}}
document.getElementById('copy').onclick=()=>{{showMarks();const o=document.getElementById('out');o.select();try{{navigator.clipboard.writeText(o.value)}}catch(e){{document.execCommand('copy')}}}};
render();
</script>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("map")
    ap.add_argument("hierarchy")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--title")
    ap.add_argument("--candidates", help="readings still open on a record, "
                                          "so the panel can show what is "
                                          "ambiguous beside what is settled")
    ap.add_argument("--claims", help="the shared (record, field) -> [claims] "
                                     "ledger, so a record's fact panel can "
                                     "list what explains each of its fields "
                                     "and what explains none of them")
    args = ap.parse_args()
    map_path, hierarchy = Path(args.map), Path(args.hierarchy)
    claims = (json.loads(Path(args.claims).read_text(encoding="utf-8"))
              if args.claims else None)
    candidates = (json.loads(Path(args.candidates).read_text(encoding="utf-8"))
                  if args.candidates else None)
    out = build(map_path, hierarchy,
                args.title or f"{map_path.stem} review pack", claims,
                candidates)
    Path(args.output).write_text(out, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
