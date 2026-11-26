import sys
from city3d import *
C0=np.array([29.,18.])
FL=BASE-.03
ANG=(141,180,219,-39,0,39)
MID=(160.5,199.5,270,-19.5,19.5,90)
rng=np.random.default_rng(3)
def P(R,a,c=C0): return c+R*np.array([math.cos(a),math.sin(a)])
def band(R,w,y,n=360,amp=.25,seed=1,a0=0,a1=2*math.pi):
    """a ring painted by hand: its edges wander"""
    g=np.random.default_rng(seed); from scipy.ndimage import gaussian_filter1d as gf
    ni=gf(g.normal(size=n+1),2.5,mode='wrap'); no=gf(g.normal(size=n+1),2.5,mode='wrap'); ni[-1]=ni[0]; no[-1]=no[0]
    v=[]
    for i in range(n):
        a,b=a0+(a1-a0)*i/n,a0+(a1-a0)*(i+1)/n
        q=[P(R-w/2+amp*ni[i],a),P(R+w/2+amp*no[i],a),P(R+w/2+amp*no[i+1],b),P(R-w/2+amp*ni[i+1],b)]
        for j in (0,1,2,0,2,3): v.append((q[j][0],y,q[j][1],q[j][0]/6,q[j][1]/6,0,1,0,1))
    return v
def spoke(R0,R1,a,w,y,seed):
    g=np.random.default_rng(seed); n=24; v=[]; d=np.array([math.cos(a),math.sin(a)]); o=np.array([-d[1],d[0]])
    ws=w/2*(1+.35*g.normal(size=(n+1,2)))
    for i in range(n):
        p,q=C0+d*(R0+(R1-R0)*i/n),C0+d*(R0+(R1-R0)*(i+1)/n)
        Q=[p-o*ws[i,0],p+o*ws[i,1],q+o*ws[i+1,1],q-o*ws[i+1,0]]
        for j in (0,1,2,0,2,3): v.append((Q[j][0],y,Q[j][1],Q[j][0]/6,Q[j][1]/6,0,1,0,1))
    return v
def floor(R):
    q=[(C0[0]-R,C0[1]-R),(C0[0]+R,C0[1]-R),(C0[0]+R,C0[1]+R),(C0[0]-R,C0[1]+R)]
    return [(q[j][0],FL,q[j][1],q[j][0]/18,q[j][1]/18,0,1,0,1) for j in (0,1,2,0,2,3)]
def rite(R=57,rot=30,disc=5.0,blood=.55):
    rot=math.radians(rot)
    ang=[math.radians(x) for x in ANG]
    six=[P(R,x) for x in ang]
    W_=4.2; b=band(R+W_,1.5,FL+.02,seed=1)+band(R-W_,1.0,FL+.02,seed=2)
    for k in range(6):
        for s in (-1,1): b+=spoke(R-W_,R+W_,ang[k]+s*.15,.8,FL+.02,10+k*2+s)
    # between the keys: nothing but strokes, as a clock has
    for k,mid in enumerate(MID):
        for j in range(-2,3) if abs(mid-90)<2 or abs(mid-270)<2 else (-1,0,1): b+=spoke(R-2.8,R+2.8 if j%2 else R+1.0,math.radians(mid)+j*.075,.7,FL+.02,50+k*9+j)
    dec=[(floor(420),253,(.55,.5,.5),0.,.8),(b,1130,(1.5,.9,.9),blood,1.0)]
    discs=[(2540+k,(p[0],FL+disc*.9,p[1]),disc,1.5) for k,p in enumerate(six)]
    cand=[]
    g=np.random.default_rng(8)
    for a,n in ((122,3),(160,2),(199,2),(238,3),(258,2),(-58,3),(-20,2),(20,2),(58,3),(283,2),(106,2),(74,2)):
        for q in range(n):
            p=P(R+8.6,math.radians(a))+g.normal(size=2)*1.5; cand.append((p[0],FL,p[1],float(g.uniform(2.8,5.6))))
    return dec,discs,cand,six
