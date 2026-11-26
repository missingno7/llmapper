import sys; sys.path.insert(0, "work/consolidation/audit3")
from lib import *
import math
def chain(mp, start, n=4):
    seen=[start]; cur=start
    for i in seen:
        pass
def flight(mp, secs):
    m = M(mp)
    for i in secs:
        f,_ = sec(mp,i)
        ws = walls(mp,i)
        row=[]
        for j,w,_x in ws:
            if w["next_sector"]>=0: continue
            p2 = F(m.walls[w["point2"]])
            L = math.hypot(p2["x"]-w["x"], p2["y"]-w["y"])
            row.append((j,w["picnum"],w["x_panning"],w["y_panning"],w["x_repeat"],w["y_repeat"],int(L),w["cstat"]))
        print(mp,i,"fz",f["floor_z"],"cz",f["ceiling_z"],"cst",f["ceiling_stat"],"hei",f.get("ceiling_heinum"),row)
flight("E3M1",[78,79,39]); flight("E3M7",[89,88,80]); flight("E6M5",[304,305,314]); flight("E3M8",[113,114,115]); flight("E4M5",[5,114,113])
