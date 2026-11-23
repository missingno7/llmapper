"""Frames from named sectors of a map: stand at each sector's inside point and look four ways (or at a given sector)."""
import pathlib
import sys

sys.path.insert(0, '.')
from shapely.geometry import Polygon  # noqa: E402

from bloodmap.format import read_map  # noqa: E402
from bloodmap.model import record_fields  # noqa: E402
from bloodmap.sector_geom import outline_and_holes  # noqa: E402
from bloodmap.viewplan import angle_toward, eye_z  # noqa: E402
from bloodmap.visual import HORIZ_LEVEL, ObservationRequest, Viewpoint, as_played, run_observation  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

tag, cols = sys.argv[1], 4
BR = 1.8
jobs = {}
for a in sys.argv[2:]:
    path, spec = a.rsplit(':', 1)
    for s in spec.split(','):
        jobs.setdefault(path, []).append(s)
tiles = []
for path, specs in jobs.items():
    disk = read_map(path)
    level = disk.to_level_ir()
    out = (pathlib.Path('work/aldermack/pose') / pathlib.Path(path).stem).resolve()
    out.mkdir(parents=True, exist_ok=True)
    views = []
    for spec in specs:
        eye, _, target = spec.partition('>')
        eye = int(eye)
        o, h = outline_and_holes(disk, eye)
        poly = Polygon(o, h).buffer(0)
        p = poly.representative_point() if not poly.contains(poly.centroid) else poly.centroid
        x, y = int(p.x), int(p.y)
        f = record_fields(disk.sectors[eye])
        z = min(int(f['floor_z']) - 15264, int(f['floor_z']))
        z = max(z, int(f['ceiling_z']) + 2048)
        if target:
            o2, _ = outline_and_holes(disk, int(target))
            q = Polygon(o2).centroid
            looks = [(int(q.x), int(q.y))]
        else:
            looks = [(x + 9000, y), (x, y + 9000), (x - 9000, y), (x, y - 9000)]
        for k, (tx, ty) in enumerate(looks):
            views.append(Viewpoint(view_id=f's{eye}_{target or k}', x=x, y=y, z=z, sector=eye,
                                   angle=angle_toward((x, y), (tx, ty)), horiz=HORIZ_LEVEL, screenshot=True))
    try:
        run_observation(ObservationRequest(
            map_path=as_played(path, out), output_dir=out, resource_dir=pathlib.Path('reference/blood'),
            viewpoints=views, width=640, height=480, screenshots=[v.view_id for v in views], brightness=0, rff=None))
    except Exception as exc:
        print('failed', path, str(exc)[:200])
        continue
    for v in views:
        fr = out / 'frames' / f'{v.view_id}.png'
        if fr.exists():
            tiles.append((f'{pathlib.Path(path).stem} {v.view_id}', fr))
w, h = 400, 300
sheet = Image.new('RGB', (cols * w, h * ((len(tiles) + cols - 1) // cols)))
for k, (n, fr) in enumerate(tiles):
    im = Image.open(fr).convert('RGB').resize((w, h)); im = im.point(lambda v: min(255, int(v * BR)))
    ImageDraw.Draw(im).text((4, 4), n, fill=(255, 255, 0))
    sheet.paste(im, ((k % cols) * w, (k // cols) * h))
sheet.save(f'work/aldermack/pose-{tag}.png')
print(len(tiles))
