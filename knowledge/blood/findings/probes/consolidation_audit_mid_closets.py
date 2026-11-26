"""Recount logic closets and signature letters over the campaign with bloodmap.reachability."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys, os
import statistics
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.reachability import classify_offmap
closets=[]; sig={}; maps_with=set(); per=[]
for p in campaign_maps():
    d=read_map(p); c=classify_offmap(d)
    n=0
    for comp in c["components"]:
        if comp["kind"]=="logic_closet":
            closets.append((p.stem,len(comp["sectors"]),comp["switches"],comp["generators"])); n+=1
        if comp["kind"]=="signature":
            sig[p.stem]=sig.get(p.stem,0)+len(comp["sectors"])
    per.append(n)
print(len(closets),"closets in",sum(1 for n in per if n),"maps; sizes",sorted({c[1] for c in closets}))
print("multi-sector:",[c for c in closets if c[1]>1])
sw=sorted(c[2] for c in closets); print("switches median",statistics.median(sw),"min",sw[0],"max",sw[-1])
print(sorted(closets,key=lambda c:-c[2])[:5])
from collections import Counter; print(Counter(per))
print("signature sectors",sum(sig.values()),"maps",len(sig),sorted(sig.items()))
