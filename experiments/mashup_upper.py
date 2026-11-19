"""Second mashup: native E1M2 stairs, elevated gallery deck and stacked goal."""
from __future__ import annotations
import copy, hashlib, json, argparse, dataclasses, shutil, sys
from pathlib import Path
from experiments.mashup_gate import build as build_v1, initial_pose
from bloodmap.format import read_map, encode_map, parse_map
from bloodmap.patterns import corpus_map_path
from bloodmap.construction import LevelBuilder, portal_profiles
from bloodmap.planar_layout import PlanarLayout
from bloodmap.prefab import sprite_bridge
from bloodmap import layers
from bloodmap.analysis import validate_map
from collections import deque

STAIRS=[101,100,99,98,94,95,97,96,117,116]
UPPER=-28672

def outline(level,sector):
 f=level.sectors[sector]['fields']
 return [(w['fields']['x'],w['fields']['y']) for w in level.walls[f['wall_ptr']:f['wall_ptr']+f['wall_count']]]

def layer_view(level, groups):
 layout=PlanarLayout()
 for i,s in enumerate(level.sectors):
  f=s['fields']
  layout.add_region(str(i),outline(level,i),floor_z=f['floor_z'],ceiling_z=f['ceiling_z'],layer=groups[i],role='stair' if groups[i] in ('stairs','descent') else 'gameplay')
 for i,s in enumerate(level.sectors):
  f=s['fields']
  for w in range(f['wall_ptr'],f['wall_ptr']+f['wall_count']):
   a=level.walls[w]['fields'];other=a['next_sector']
   if other>i:
    b=level.walls[a['point2']]['fields']
    layout.add_connection(str(w),str(i),str(other),a1=(a['x'],a['y']),a2=(b['x'],b['y']))
 return layout

def append_rectangles(level, records, links):
 layout=PlanarLayout()
 for floor in sorted({r[2] for r in records}):layout.declare_layer(f'height_{floor}',ceiling_z=floor-32768,floor_z=floor)
 for name,(x1,y1,x2,y2),floor in records:
  layout.add_region(name,[(x1,y1),(x2,y1),(x2,y2),(x1,y2)],floor_z=floor,ceiling_z=floor-32768,wall_picnum=255,floor_picnum=438,ceiling_picnum=255,role='stair',layer=f'height_{floor}')
 for i,(a,ra,fa) in enumerate(records):
  for b,rb,fb in records[i+1:]:
   if abs(fa-fb)>4096:continue
   x1,y1,x2,y2=ra;u1,v1,u2,v2=rb
   if (x2==u1 or u2==x1) and max(y1,v1)<min(y2,v2):
    x=x2 if x2==u1 else x1
    layout.add_connection(a+'-'+b,a,b,a1=(x,max(y1,v1)),a2=(x,min(y2,v2)))
   elif (y2==v1 or v2==y1) and max(x1,u1)<min(x2,u2):
    y=y2 if y2==v1 else y1
    layout.add_connection(a+'-'+b,a,b,a1=(max(x1,u1),y),a2=(min(x2,u2),y))
 name,box,floor=records[0]
 layout.set_player_start(name,x=(box[0]+box[2])//2,y=(box[1]+box[3])//2,z=floor-14000)
 compiled=layout.compile().level
 fragment=compiled.extract(range(len(compiled.sectors)))
 insertion=level.insert(fragment,channel_policy='remap');result=insertion.level
 for oldwall,a,b in links:
  matches=[]
  for j in range(len(level.walls),len(result.walls)):
   f=result.walls[j]['fields'];g=result.walls[f['point2']]['fields']
   if (f['x'],f['y'])==a and (g['x'],g['y'])==b:matches.append(j)
  assert len(matches)==1,(oldwall,a,b,matches)
  result=result.connect_portals(oldwall,matches[0])
 return result,{'regions':[r[0] for r in records],'insertion':insertion.report()}

def build():
 level,baseline=build_v1()
 # Owner-confirmed material correction applies only to the generated room.
 for w in range(20,26):level.walls[w]['fields']['picnum']=255
 level.sectors[0]['fields']['ceiling_z']=-61440
 source_path=corpus_map_path('E1M2.MAP')
 if hashlib.sha256(source_path.read_bytes()).hexdigest()!='d82e5a135ee0f911a7cea11388b4a96d4841c672dfa207529058464cf7947466':raise ValueError('E1M2 source changed')
 source=read_map(source_path).to_level_ir()
 closure=source.extract_closed(STAIRS,max_sectors=10)
 assert set(closure.selected_sector_ids)==set(STAIRS) and not closure.unresolved_relationships
 low=closure.fragment.index_maps['wall'].localize(951)
 attach=level.attach(closure.fragment,destination_wall=10,fragment_wall=low,dz=32768,channel_policy='remap')
 level=attach.level
 upper_start=len(level.sectors)
 upper_records=[('deck_vestibule',(7936,-33280,8576,-31232),UPPER),('south_gallery',(8576,-32000,12416,-31232),UPPER),('upper_goal',(8832,-34816,11520,-32768),UPPER),('east_cap',(11648,-35072,12416,-34304),UPPER),('east_middle',(11520,-34304,12416,-32256),UPPER),('east_foot',(11648,-32256,12416,-32000),UPPER)]
 level,upper_report=append_rectangles(level,upper_records,[(2,(7936,-31232),(7936,-33280))])
 def wall_at(a,b):
  matches=[j for j,w in enumerate(level.walls) if (w['fields']['x'],w['fields']['y'])==a and (level.walls[w['fields']['point2']]['fields']['x'],level.walls[w['fields']['point2']]['fields']['y'])==b and w['fields']['next_sector']==-1]
  assert len(matches)==1,(a,b,matches)
  return matches[0]
 top_entry=wall_at((12416,-34304),(12416,-32256))
 descent_entry=wall_at((12416,-32000),(12416,-31232))
 high=attach.composition.allocations['wall'].resolve(closure.fragment.index_maps['wall'].localize(836))
 top_records=[('north',(8448,-41984,10496,-38912),UPPER),('top',(8448,-44032,15360,-41984),UPPER),('east',(15360,-44032,17408,-32256),UPPER),('return',(12416,-34304,15360,-32256),UPPER)]
 level,top_report=append_rectangles(level,top_records,[(high,(10496,-38912),(8448,-38912)),(top_entry,(12416,-32256),(12416,-34304))])
 descending_start=len(level.sectors)
 desc=[]
 for n in range(6):desc.append((f'out_{n}',(12416+n*768,-32000,13184+n*768,-31232),UPPER+n*2048))
 desc.append(('turn_east',(17024,-32000,17792,-31232),-16384))
 for n in range(6):desc.append((f'down_{n}',(17024,-31232+n*768,17792,-30464+n*768),-14336+n*2048))
 desc.append(('turn_south',(17024,-26624,17792,-25856),-2048))
 for n in range(6):desc.append((f'back_{n}',(16000-n*1024,-26624,17024-n*1024,-25856),min(8192,n*2048)))
 desc.append(('ground_return',(8576,-32512,11648,-26624),8192))
 level,down_report=append_rectangles(level,desc,[(descent_entry,(12416,-31232),(12416,-32000)),(22,(8576,-32512),(11648,-32512))])
 host=PlanarLayout();host.add_region('gallery',outline(level,0),floor_z=8192,ceiling_z=-61440)
 sprite_bridge(host,'overlook','gallery',start=(4832,-32896),end=(7904,-32896),z=UPPER,repeat=24,tile=256)
 host.placements[-1].x += 16
 host.placements[-1].x_repeat += 1  # seat the final 32-unit threshold strip at the open portal
 b=LevelBuilder(level);decks=[]
 for spec in host.placements:
  decks.append(b.add_sprite(sector=0,x=spec.x,y=spec.y,z=spec.z,picnum=spec.picnum,cstat=spec.cstat,x_repeat=spec.x_repeat,y_repeat=spec.y_repeat,shade=spec.shade,angle=spec.angle))
 level=b.build()
 groups=['ground']*4+['stairs']*10+['upper']*(descending_start-14)+['descent']*(len(level.sectors)-descending_start)
 view=layer_view(level,groups);lr=layers.report(view)
 errors=[x for x in lr['findings'] if x['severity']=='error']
 report={'baseline_sha256':baseline['map_sha256'],'source_sha256':hashlib.sha256(corpus_map_path('E1M2.MAP').read_bytes()).hexdigest(),'stair_closure':closure.report(),'stair_attachment':attach.report(),'top_path':top_report,'down_path':down_report,'upper_sectors':list(range(upper_start,upper_start+6)),'upper_rooms':upper_report,'deck_sprites':decks,'layers':lr,'validation':[{'severity':d.severity,'code':d.code,'message':d.message} for d in validate_map(level.to_disk_map())],'counts':[len(level.sectors),len(level.walls),len(level.sprites)],'errors':errors}
 return level,report

def standing_routes(level):
 """Bounded flat-sector route check: standing height, step height, and wall flags.

 Sprite-supported traversal is checked separately; never treat gallery's floor
 as the elevated deck. Falling is allowed, climbing is capped at 4096 Z units.
 """
 posed=initial_pose(level).to_level_ir()
 profiles=portal_profiles(posed,min_width=384,min_opening=16960)
 graph={i:[] for i in range(len(posed.sectors))}
 for p in profiles:
  if not p['wide_enough'] or not p['walkable_at_rest']:continue
  if any(posed.walls[w]['fields']['cstat']&1 for w in p['walls']):continue
  a,b=p['sectors']
  for src,dst in [(a,b),(b,a)]:
   rise=posed.sectors[src]['fields']['floor_z']-posed.sectors[dst]['fields']['floor_z']
   if rise<=4096:graph[src].append(dst)
 # A separate queue stores the complete witness, keeping this small check explicit.
 paths={0:[0]};queue=deque([0])
 while queue:
  src=queue.popleft()
  for dst in graph[src]:
   if dst not in paths:paths[dst]=paths[src]+[dst];queue.append(dst)
 return {'paths':paths,'profiles':profiles,'reachable':sorted(paths),
         'limits':'Flat sector geometry, 16960 standing height, 4096 maximum climb. No enemies, timing, runtime collision or sprite-deck traversal simulation.'}


def verify(level, report):
 native=validate_map(level.to_disk_map())
 if native:raise ValueError(native)
 findings=report['layers']['findings']
 if any(f['severity'] in ('error','warning') for f in findings):raise ValueError(findings)
 assert all(o['z']=='vertically_disjoint' for o in report['layers']['overlaps']), 'vertical bands must be disjoint in this specimen'
 baseline,_=build_v1()
 assert level.sectors[1:3]==baseline.sectors[1:3]
 assert level.walls[18]==baseline.walls[18]
 assert level.sprites[:17]==baseline.sprites
 assert all(level.walls[w]['fields']['picnum']==255 for w in range(20,26))
 route=standing_routes(level)
 assert 16 in route['paths'] and 3 in route['paths']
 assert 1 not in route['paths'], 'original gate must remain closed in the initial model'
 assert any(4<=sector<14 for sector in route['paths'][16]), 'upper route must use donor stairs'
 assert all(p['wide_enough'] and p['walkable_when_open'] for p in route['profiles'])
 report['standing_routes']=route
 report['gate_preserved']=True
 panels=[level.sprites[i]['fields'] for i in report['deck_sprites']]
 rectangles=[]
 for f in panels:
  assert f['cstat']&1 and f['cstat']&32 and f['z']==UPPER and f['sector']==0
  hx=f['x_repeat']*128//8;hy=f['y_repeat']*128//8
  rectangles.append([f['x']-hx,f['y']-hy,f['x']+hx,f['y']+hy])
 assert rectangles[-1][2]==7936
 assert all(a[2]==b[0] for a,b in zip(rectangles,rectangles[1:]))
 report['deck_footprints']=rectangles
 report['deck_tile_dimensions']=[128,128]
 report['deck_headroom']=UPPER-level.sectors[0]['fields']['ceiling_z']
 assert report['deck_headroom']>=16960
 raw=encode_map(level.to_disk_map());assert encode_map(parse_map(raw))==raw
 report['map_sha256']=hashlib.sha256(raw).hexdigest()
 report['limitations']=['Owner verified v1 only; this v2 has not been played.',
   'Two stacked-sector pairs pass band/separation checks; collinear-wall notes remain in the layer report.',
   'The deck is a supported dead-end overlook with a return to the upper hall; the separate stairs descend to the exit.',
   'Render observations are editor poses, not runtime playback. Combat is inherited and untuned.']
 return report


def observe(output):
 from bloodmap.visual import ObservationRequest,Viewpoint,run_observation,default_binary
 from bloodmap.art import read_art_directory
 art=read_art_directory('reference/blood')[256]
 assert (art.width,art.height)==(128,128)
 posed=initial_pose(read_map(output/'mashup.MAP').to_level_ir())
 (output/'initial-state-analysis.MAP').write_bytes(encode_map(posed))
 poses=(Viewpoint('upper_to_deck',8300,-32896,-42752,1024,sector=14,screenshot=True),
   Viewpoint('deck_to_upper',5200,-32896,-42752,0,sector=0,screenshot=True),
   Viewpoint('upper_room',10000,-33792,-42752,0,sector=16,screenshot=True),
   Viewpoint('stair_entry',6144,-33792,-6000,1536,sector=0,screenshot=True),
   Viewpoint('stair_top',9472,-38300,-42752,1536,sector=11,screenshot=True),
   Viewpoint('ground_gate_closed',7300,-33792,-6000,0,sector=0,screenshot=True),
   Viewpoint('goal_material',10500,-33792,-6000,0,sector=3,screenshot=True))
 request=ObservationRequest(map_path=str(output/'initial-state-analysis.MAP'),output_dir=str(output/'views'),resource_dir=str(Path('reference/blood').resolve()),viewpoints=poses,screenshots=True)
 m=run_observation(request,timeout=45)
 if m.invalid():raise ValueError(m.invalid())
 # The specific defect that forced a redesign must stay absent in its witness view.
 assert not m.view('deck_to_upper')['unorderable']
 return {'binary_sha256':hashlib.sha256(default_binary().read_bytes()).hexdigest(),
         'views':[{k:v[k] for k in ['id','status','frame','unorderable']} for v in m.views]}


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--render',action='store_true')
 args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
 level,report=build();verify(level,report)
 assert encode_map(level.to_disk_map())==encode_map(build()[0].to_disk_map())
 (output/'mashup.MAP').write_bytes(encode_map(level.to_disk_map()))
 (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 if args.render:
  observation=observe(output)
  (output/'observation-binding.json').write_text(json.dumps(observation,indent=2)+'\n',encoding='utf-8')
 sources=list(Path('bloodmap').rglob('*.py'))+[Path('experiments/mashup_gate.py'),Path(__file__).resolve(),Path('knowledge/blood/design/owner-anchors-v1.json'),Path('projects/mashup-gate/owner-review.json')]
 for source in sources:
  target=output/'source'/source.resolve().relative_to(Path.cwd().resolve())
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 manifest={'python':sys.version,'status':'static_and_render_checks_passed' if args.render else 'static_checks_passed','runtime':'v2_not_run','map_sha256':report['map_sha256'],
 'files':{p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}}
 if args.render:manifest['render_inputs']={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('reference/blood').glob('*')) if p.is_file() and p.suffix.lower() in ('.art','.rff')}
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'counts':report['counts'],'map_sha256':report['map_sha256'],'upper_route':report['standing_routes']['paths'][16],'exit_route':report['standing_routes']['paths'][3]},indent=2))

if __name__=='__main__':main()
