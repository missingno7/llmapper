"""A bounded native-fragment mashup: E1M3 gallery and E1M4 push-wall gate.

Original-map-derived outputs belong under ignored work/, not in version control.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from bloodmap.format import read_map, encode_map, parse_map
from bloodmap.patterns import corpus_map_path
from bloodmap.construction import LevelBuilder, new_level, portal_profiles
from bloodmap.analysis import validate_map
from bloodmap.composition import find_layout_conflicts
from bloodmap.conditional import build_graph, Held, frontier, what_becomes_reachable
from bloodmap.switches import exit_switch

SOURCE_HASHES = {
    'E1M3': 'bc3633ef9f402e21eafb2050737c54812ed45f45eef296f895ad3e6c79c42595',
    'E1M4': 'ae239537a4d6973cc0c75ae90e30fc68a8a8c241dbc2bb1293e318cb792b7408',
}


def initial_pose(level):
    """The source is drawn open but initializes with state=0 in Blood."""
    disk = level.to_disk_map()
    sector = disk.sectors[1]
    assert sector.extra.fields['state'] == 0
    sector.fields['ceiling_z'] = sector.extra.fields['off_ceiling_z']
    sector.fields['floor_z'] = sector.extra.fields['off_floor_z']
    return disk


def build():
    for name, expected in SOURCE_HASHES.items():
        if hashlib.sha256(corpus_map_path(name + '.MAP').read_bytes()).hexdigest() != expected:
            raise ValueError(f'{name}: source differs from the selected specimen')
    sources = {name: read_map(corpus_map_path(name + '.MAP')).to_level_ir() for name in ('E1M3', 'E1M4')}
    gallery = sources['E1M3'].extract_closed([287], max_sectors=6)
    gate = sources['E1M4'].extract_closed([359], max_sectors=6)
    assert gallery.selected_sector_ids == [287]
    assert gate.selected_sector_ids == [359, 361]
    assert not gallery.unresolved_relationships and not gate.unresolved_relationships
    base = new_level()
    base.player_start = {'x': 6144, 'y': -33792, 'z': -8192, 'sector': 0, 'angle': 0}
    base.sky = copy.deepcopy(sources['E1M3'].sky)
    placed = base.insert(gallery.fragment, channel_policy='remap')
    level = placed.level
    attached = level.attach(gate.fragment, destination_wall=0, fragment_wall=4,
                            dz=-32768, channel_policy='remap')
    level = attached.level
    before_sectors, before_walls = len(level.sectors), len(level.walls)
    builder = LevelBuilder(level)
    goal = builder.add_sector([(8576,-35072),(11648,-35072),(11648,-32512),
                               (8576,-32512),(8576,-33280),(8576,-34304)],
                              ceiling_z=-20480, floor_z=8192,
                              ceiling_picnum=255, floor_picnum=255, wall_picnum=315,
                              wall_shade=12, floor_shade=12)
    door_wall = attached.composition.allocations['wall'].resolve(0)
    builder.connect(door_wall, goal.wall_ids[4])
    spec = exit_switch()
    behavior = spec.pop('behavior'); spec.pop('height_player_heights')
    exit_id = builder.add_sprite(sector=goal.sector_id, x=11640, y=-33792, z=-4096,
                                 angle=1024, **spec)
    builder.set_behavior('sprite', exit_id, **behavior)
    builder.set_player_start(sector=0, x=6144, y=-33792, z=-8192, angle=0)
    level = builder.build()
    # Only the selected boundary portal may change in the transplanted gallery.
    assert level.sectors[:1] == placed.level.sectors
    assert level.sprites[:len(placed.level.sprites)] == placed.level.sprites
    for index, original in enumerate(placed.level.walls):
        expected = copy.deepcopy(original)
        if index == 0:
            for field in ('next_wall', 'next_sector'):
                expected['fields'][field] = level.walls[index]['fields'][field]
        assert level.walls[index] == expected
    # The goal connection must not change the transplanted mechanism fields.
    assert level.sectors[1:3] == attached.level.sectors[1:3]
    assert level.walls[18] == attached.level.walls[18]
    conflicts = find_layout_conflicts(level, existing_sector_count=before_sectors,
        existing_wall_count=before_walls, portal_wall_pairs=[(door_wall,goal.wall_ids[4])])
    assert not conflicts, conflicts
    disk = level.to_disk_map()
    diagnostics = validate_map(disk)
    assert not [d for d in diagnostics if d.severity == 'error']
    analysis_disk = initial_pose(level)
    graph = build_graph(analysis_disk)
    rest = graph.reachable(graph.at_rest())
    channel = attached.composition.channel_map[129]
    fired = graph.reachable(Held(channels=frozenset([channel])))
    actions = [a.to_dict() for a in graph.available_actions(graph.at_rest(), rest)]
    from bloodmap.switches import check as check_switches
    from bloodmap.street_model import switch_faults
    assert not check_switches(disk)
    assert not switch_faults(disk)
    report = {'sources': {name: {'path': str(corpus_map_path(name+'.MAP')),
               'sha256': hashlib.sha256(corpus_map_path(name+'.MAP').read_bytes()).hexdigest()} for name in sources},
              'gallery_closure':gallery.report(), 'gate_closure':gate.report(),
              'gallery_insertion':placed.report(), 'gate_attachment':attached.report(),
              'goal_sector':goal.sector_id,'exit_sprite':exit_id,'gate_sector':1,
              'channel':channel,'reachable_at_rest':sorted(rest),'reachable_after_channel':sorted(fired),
              'available_actions':actions,'layout_conflicts':conflicts,
              'progression':frontier(analysis_disk, graph=graph),
              'analysis_pose_sha256':hashlib.sha256(encode_map(analysis_disk)).hexdigest(),
              'analysis_pose_note':'Explicit off endpoint for state=0. The preserved source MAP is drawn open; editor drawing is not runtime initialization.',
              'preservation':{'gallery_except_selected_portal':True, 'gate_behavior':True},
              'wall_use_probe':{'standing_sector':0,'x':8064,'y':-33792,
                  'wall':18,'wall_x':8320,'distance_xy':256,
                  'note':'Straight approach through the 128-unit antechamber; physical use remains runtime-unverified.'},
              'validation':[{'severity':d.severity,'code':d.code,'location':d.location,'message':d.message} for d in diagnostics],
              'counts':{'sectors':len(level.sectors),'walls':len(level.walls),'sprites':len(level.sprites)},
              'limitations':['Static channel-state analysis is not a runtime activation or passage test.',
                 'Gallery actors and props are retained; combat has not been balanced.',
                 'Unused external portal boundaries are sealed. No room-over-room transfer is claimed.']}
    assert goal.sector_id not in rest, report['reachable_at_rest']
    assert goal.sector_id in fired, report['reachable_after_channel']
    assert any(a.get('channel') == channel for a in actions), actions
    action = next(a for a in graph.available_actions(graph.at_rest(), rest) if a.channel == channel)
    report['activation_chain'] = what_becomes_reachable(analysis_disk, action, graph=graph)
    report['endpoint_portals'] = {}
    for pose, endpoint in [('closed', 'off_ceiling_z'), ('open', 'on_ceiling_z')]:
        posed = copy.deepcopy(level)
        posed.sectors[1]['fields']['ceiling_z'] = posed.sectors[1]['blood']['fields'][endpoint]
        report['endpoint_portals'][pose] = portal_profiles(posed, min_width=384, min_opening=16960)
    raw=encode_map(disk)
    assert encode_map(parse_map(raw)) == raw
    report['map_sha256']=hashlib.sha256(raw).hexdigest()
    return level, report


def observe(output: Path) -> dict:
    """Render explicit endpoint geometry; these are not runtime frames."""
    from bloodmap.visual import ObservationRequest, Viewpoint, run_observation, default_binary
    records = {}
    for pose in ('closed', 'open'):
        disk = read_map(output / 'mashup.MAP')
        sector = disk.sectors[1]
        sector.fields['ceiling_z'] = sector.extra.fields[
            'off_ceiling_z' if pose == 'closed' else 'on_ceiling_z']
        path = output / f'{pose}-editor-pose.MAP'
        path.write_bytes(encode_map(disk))
        request = ObservationRequest(
            map_path=str(path), output_dir=str(output / pose),
            resource_dir=str(Path('reference/blood').resolve()), screenshots=True,
            viewpoints=(Viewpoint('approach',7300,-33792,-6000,0,sector=0,screenshot=True),
                        Viewpoint('goal',10624,-33792,-6000,1024,sector=3,screenshot=True),
                        Viewpoint('gallery',4800,-33792,-6000,0,sector=0,screenshot=True)))
        manifest = run_observation(request, timeout=45)
        if manifest.invalid():
            raise ValueError(f'{pose}: invalid observation: {manifest.invalid()}')
        records[pose] = {'map_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                         'views':[v['id'] for v in manifest.views]}
    records['observer_sha256'] = hashlib.sha256(default_binary().read_bytes()).hexdigest()
    records['interpretation'] = 'Editor endpoint geometry only; no game was launched.'
    return records


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--render',action='store_true')
    args=p.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=False)
    level, report=build()
    assert encode_map(build()[0].to_disk_map())==encode_map(level.to_disk_map())
    (args.output/'mashup.MAP').write_bytes(encode_map(level.to_disk_map()))
    (args.output/'initial-state-analysis.MAP').write_bytes(encode_map(initial_pose(level)))
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (args.output/'build.py').write_bytes(Path(__file__).read_bytes())
    sources = sorted(Path('bloodmap').rglob('*.py')) + [Path(__file__).resolve()]
    for source in sources:
        relative = source.resolve().relative_to(Path.cwd().resolve())
        target = args.output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if args.render:
        observation = observe(args.output)
        (args.output/'observation-binding.json').write_text(json.dumps(observation,indent=2)+'\n')
    revision = subprocess.run(['git','-c',f'safe.directory={Path.cwd().as_posix()}',
                               'rev-parse','HEAD'],capture_output=True,text=True)
    manifest = {'python':sys.version,'git_revision':revision.stdout.strip(),
                'map_sha256':report['map_sha256'], 'status':'static_checks_passed',
                'runtime':'not_run',
                'files':{path.relative_to(args.output).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted(args.output.rglob('*')) if path.is_file()}}
    if args.render:
        manifest['external_render_inputs'] = {
            str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path('reference/blood').glob('*'))
            if path.is_file() and path.suffix.lower() in {'.art', '.rff'}}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['counts','reachable_at_rest','reachable_after_channel','available_actions','map_sha256']},indent=2))

if __name__=='__main__': main()

