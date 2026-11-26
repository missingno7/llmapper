"""Who sends on the exit channel (4) in each campaign map, and by what."""
import sys; sys.path.insert(0,'work/consolidation/audit_mid')
from m import *
from collections import Counter
tot=Counter(); permap={}
for p in campaign_maps():
    S,W,P=load(p)
    kinds=[]
    for i,s in enumerate(S):
        if s.get('tx_id')==4: kinds.append(('sector', s['type'], 'enter' if s.get('trigger_enter') else ('push' if s.get('trigger_push') else 'other')))
    for i,w in enumerate(W):
        if w.get('tx_id')==4: kinds.append(('wall', w['type'], w['picnum']))
    for i,q in enumerate(P):
        if q.get('tx_id')==4: kinds.append(('sprite', q['type'], q['picnum'], 'closet?'))
    permap[p.stem]=kinds
    for k in kinds: tot[k[:2]]+=1
for k,v in permap.items(): print(k, v)
print(tot)
