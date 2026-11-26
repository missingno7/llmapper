"""Prepare a guarded washhouse pass from the static-room repair snapshot."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bloodmap.art import read_art_directory
from bloodmap.format import read_map
from bloodmap.model import record_fields as f

PROJECT = Path(__file__).resolve().parent
INPUT_SHA = "692ad84dc626f9a1ed934f6df63d0d7fa114cf8f3d6845b272b5819e10e7aab3"
ROOMS = [58, 59, 60, 119, 125, 152]
PARTITIONS = [52, 53, 54, 55, 61]


def prepare():
    source = PROJECT / "E4L1-current.MAP"
    if hashlib.sha256(source.read_bytes()).hexdigest() != INPUT_SHA:
        source = PROJECT / "snapshots" / (INPUT_SHA + ".MAP")
    if hashlib.sha256(source.read_bytes()).hexdigest() != INPUT_SHA:
        raise ValueError("The reviewed washhouse input snapshot is missing")
    disk = read_map(source)
    art = read_art_directory(ROOT / "reference/blood")
    edits, sprites = [], []

    def edit(kind, index, **new):
        old = f(getattr(disk, kind + "s")[index])
        identity = {k: old[k] for k in ({"sector": ["wall_ptr", "wall_count"],
                                       "wall": ["x", "y", "point2"]}[kind])}
        changed = {k: [old[k], v] for k, v in new.items() if old[k] != v}
        if changed:
            edits.append(dict(kind=kind, index=index, identity=identity, fields=changed))

    for sid in ROOMS + PARTITIONS:
        s = f(disk.sectors[sid])
        partition = sid in PARTITIONS
        edit("sector", sid, floor_picnum=2453 if partition else 296,
             ceiling_picnum=215, floor_shade=24 if partition else 30,
             ceiling_shade=38)
        for wid in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
            w = f(disk.walls[wid])
            # Both sides of a stall partition must describe the same material.
            partition_face = partition or w["next_sector"] in PARTITIONS
            tile = 2453 if partition_face or sid == 125 else 297
            edit("wall", wid, picnum=tile, shade=28 if partition_face else 30,
                 y_repeat=8, x_panning=0, y_panning=0)
    # Retain the existing vent recesses; a grille on their back wall closes
    # their depth without adding another room or modifying portal topology.
    for sid in [64, 67]:
        s = f(disk.sectors[sid])
        edit("sector", sid, floor_picnum=2453, ceiling_picnum=2453,
             floor_shade=36, ceiling_shade=36)
        for wid in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
            w = f(disk.walls[wid])
            edit("wall", wid, picnum=2178 if w["next_sector"] < 0 else 2453,
                 shade=34, y_repeat=8, x_panning=0, y_panning=0)

    def sprite(name, sid, x, y, z, tile, xr, yr, cstat, angle=0, shade=22, extra=None, type=0):
        row = {"name": name, "fields": dict(sector=sid, x=x, y=y, z=z,
                   type=type, picnum=tile, status=0, cstat=cstat, angle=angle,
                   x_repeat=xr, y_repeat=yr, shade=shade)}
        if extra:
            row["extra"] = extra
        sprites.append(row)

    def flat(name, sid, x, y, z, width, depth, tile=43, shade=-12):
        # Engine floor sprites at angle zero: tile X runs along world Y;
        # tile Y runs along world X. Dimensions are rounded to ART increments.
        sprite(name, sid, x, y, z, tile, round(depth * 4 / art[tile].width),
               round(width * 4 / art[tile].height), 33, shade=shade)

    def wall(name, sid, x, y, top, bottom, span, angle, tile=43, shade=-12):
        sprite(name, sid, x, y, (top + bottom)//2, tile,
               round(span * 4 / art[tile].width),
               round((bottom-top) / (art[tile].height*4)),
               16 | 128 | 1 | 256, angle=angle, shade=shade)

    def box(name, sid, x, y, top, bottom, width, depth, cap=True):
        wall(name+"-front",sid,x+width//2,y,top,bottom,depth,0)
        wall(name+"-back",sid,x-width//2,y,top,bottom,depth,1024)
        wall(name+"-left",sid,x,y-depth//2,top,bottom,width,1536,shade=-8)
        wall(name+"-right",sid,x,y+depth//2,top,bottom,width,512,shade=-8)
        if cap:
            flat(name+"-top",sid,x,y,top,width,depth)

    def bowl(name, sid, x, y, top, bottom, width, depth, rim=128):
        box(name,sid,x,y,top,bottom,width,depth,cap=False)
        flat(name+"-rim-front",sid,x+(width-rim)//2,y,top,rim,depth)
        flat(name+"-rim-back",sid,x-(width-rim)//2,y,top,rim,depth)
        flat(name+"-rim-left",sid,x,y-(depth-rim)//2,top,width-2*rim,rim)
        flat(name+"-rim-right",sid,x,y+(depth-rim)//2,top,width-2*rim,rim)
        flat(name+"-water",sid,x,y,top+512,width-2*rim,depth-2*rim,2915,shade=-10)

    # E2M4:467-469/487 is the evidence for stone 43, a liquid bowl below its
    # rim and a separate rear cistern. Water 2915 replaces its sewage 997.
    # Keep fixtures inside
    # their stalls, clear of SE11 door61 and its sweep.
    for sid, y in [(58, 48192), (59, 49920)]:
        name = "toilet-" + str(sid)
        bowl(name,sid,22976,y,-2560,1536,640,512,rim=96)
        box(name+"-cistern",sid,22576,y,-9984,1536,160,576)
        # The native campaign uses an invisible Push toggle with both sounds
        # set to 369. No TX/RX or invented channel is needed for local sound.
        sprite(name+"-flush",sid,22912,y,-8192,0,64,64,33152,
               extra={"trigger_push":1,"data_1":369,"data_2":369},type=20)
    for number, y in enumerate([51456, 52608], 1):
        name = "urinal-" + str(number)
        bowl(name,119,22736,y,-8192,-2048,384,576,rim=64)
        # Rear vertical stone splashback, then a narrow exposed supply pipe.
        wall(name+"-backplate",119,22528,y,-14336,-2048,576,0)
        wall(name+"-pipe",119,22544,y,-22528,-14336,64,0,tile=2453,shade=-8)
        sprite(name+"-flush",119,22736,y,-14336,0,64,64,33152,
               extra={"trigger_push":1,"data_1":369,"data_2":369},type=20)
    # Practical illumination is authored in the static shades above. These
    # are visible fittings, not a claim of dynamic light or working ballast.
    for name, x, y, sid in [("stall-light",25200,48000,152),
                             ("wash-light",25200,52700,152)]:
        sprite(name,sid,x,y,-46048,2290,48,48,32,angle=512,shade=-24)

    patch = {"id":"10-washhouse", "purpose":"Restore the workers' washhouse with native Blood materials and stone plumbing fixtures; retain source geometry, entry signal and the repaired stall door.",
             "input_sha256":INPUT_SHA,"scope":{"rooms":ROOMS,"partitions":PARTITIONS,"vents":[64,67],"excluded_support":[57]},
             "edits":edits,"sprites":sprites}
    target = PROJECT / "passes/10-washhouse.json"
    target.write_text(json.dumps(patch,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"patch":str(target),"edits":len(edits),"sprites":len(sprites)}))


if __name__ == "__main__":
    prepare()
