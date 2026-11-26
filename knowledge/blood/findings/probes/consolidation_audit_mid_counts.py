"""Cheap campaign recounts for the mid-third audit."""
import sys, os; sys.path.insert(0, os.getcwd()); sys.path.insert(0, 'work/consolidation/audit_mid')
from m import *
import statistics, math
from collections import Counter
writ=Counter(); writmaps={}; amb=[]; ambper=[]; chans={}; masks=Counter(); links=[0,0]; t2183=Counter(); xsec={}
LINK={6,7,9,10,11,12,13,14}  # up/low link, water, stack, goo
for p in campaign_maps():
    S,W,P=load(p); n=p.stem
    for i,q in enumerate(P):
        if q['picnum'] in (826,1105,2345): writ[q['picnum']]+=1; writmaps.setdefault(q['picnum'],set()).add(n)
        if q['status']<1024 and 'skill' in str(q.keys()): pass
    a=sum(1 for q in P if q['type']==710); amb.append(a); ambper.append(100*a/len(S))
    ch=set()
    for r in S+W+P:
        for k in ('tx_id','rx_id'):
            v=r.get(k) or 0
            if v>=100: ch.add(v)
    chans[n]=len(ch)
    xsec[n]=sum(1 for s in S if 'rx_id' in s or 'tx_id' in s or 'busy_time_a' in s or any(k for k in s if k not in record_fields.__code__.co_varnames))
    for q in P:
        for k in q:
            if 'skill' in k.lower() or 'lockout' in k.lower(): pass
    for w in W:
        if w['picnum']==2183: t2183[w.get('type',0)]+=1
    for q in P:
        if q['picnum']==2183: t2183[('spr',q['type'])]+=1
print('writings', writ, {k:len(v) for k,v in writmaps.items()})
print('ambient 710 median', statistics.median(amb), 'per100', round(statistics.median(ambper),1), 'total', sum(amb))
print('channels>=100 max', max(chans.items(), key=lambda kv: kv[1]))
print('2183', t2183)
S,W,P=load('E1M1'); print('sprite keys sample', sorted(set(k for q in P for k in q))[:80])
