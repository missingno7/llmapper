import sys
"""The ModDB logo: run from the repository root, `python projects/blood-city/renders/moddb/render/final.py 3 d2` writes fin_d2.png beside this."""
from scene import *
import cv2
def finish(rgb,out,ts=True):
    H,W=rgb.shape[:2]; yy,xx=np.mgrid[0:H,0:W]
    # a red breath over the far floor
    g=np.random.default_rng(2); n=sum(cv2.resize(g.random((H//s+3,W//s+3)).astype('f4'),(W,H),interpolation=cv2.INTER_CUBIC)*w for s,w in ((300,.6),(140,.4)))
    far=np.clip(1-yy/(H*.36),0,1)**1.1*np.clip((n-.28)*2.6,0,1)
    rgb=rgb+far[...,None]*np.array([.075,.006,.003])
    if ts:
        k=np.clip(np.maximum((H*.13-yy)/(H*.13),(yy-H*.93)/(H*.07)),0,1)[...,None]
        b=cv2.GaussianBlur(rgb.astype('f4'),(0,0),W/1600*4.5); rgb=rgb*(1-k)+b*k
    x=tonemap(rgb,bloom=.5,th=1.0)
    l=x.mean(2,keepdims=True); x=np.clip(l+(x-l)*1.08,0,1)
    x=np.clip(x+.35*(x-cv2.GaussianBlur(x.astype('f4'),(0,0),1.0)),0,1)
    v=1-.5*np.clip(((xx-W/2)/(W*.6))**2+((yy-H*.52)/(H*.62))**2-.55,0,1); x=x*v[...,None]
    save(x,out)
if __name__=='__main__':
    ss=int(sys.argv[1]); which=sys.argv[2:]
    C=City(1600,1200,ss); com=scene(C)
    V={'d2':dict(eye=(45,67,136),at=(28.7,-9.2,22.0),fov=34.5),'c2':dict(eye=(29,78,134),at=(29,-7.5,20.5),fov=35.5),'e2':dict(eye=(58,64,130),at=(29.5,-7.5,20.5),fov=35.5)}
    for k in which or V:
        rgb,a,M=C.shot(**V[k],**com); finish(rgb,S/f'fin_{k}.png')
