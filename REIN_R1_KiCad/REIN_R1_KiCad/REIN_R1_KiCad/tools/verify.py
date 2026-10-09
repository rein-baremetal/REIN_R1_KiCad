import sys, json, math, collections
sys.path.insert(0,'/home/claude/w/tools')
from sx import *
from geom import rot_pt, OX, OY, BW, BH
path=sys.argv[1]
t=parse(open(path,newline='').read())
fps=find(t,'footprint'); print('footprints',len(fps))
pads=[]   # (ref,padno,net,layerset,x0,y0,x1,y1)
bad=0
for fp in fps:
    ref=[q(p[2]) for p in find(fp,'property') if q(p[1])=='Reference'][0]
    at=find(fp,'at')[0]; fx,fy=float(at[1]),float(at[2]); fth=float(at[3]) if len(at)>3 else 0.0
    side='B' if q(find(fp,'layer')[0][1])=='B.Cu' else 'T'
    for p in find(fp,'pad'):
        a=find(p,'at')[0]; lx,ly=float(a[1]),float(a[2]); pa=float(a[3]) if len(a)>3 else 0.0
        sz=find(p,'size')[0]; w,h=float(sz[1]),float(sz[2])
        # pad angle absolute => relative to footprint = pa - fth ; world position uses fp rotation
        rx,ry=rot_pt(lx,ly,int(round(fth))%360)
        X,Y=fx+rx,fy+ry
        if int(round(pa))%180==90: w,h=h,w
        lay=[q(l) for l in find(p,'layers')[0][1:]]
        typ=q(p[2])
        sides=set()
        if '*.Cu' in lay or typ in('thru_hole',): sides={'T','B'}
        elif 'F.Cu' in lay: sides={'T'}
        elif 'B.Cu' in lay: sides={'B'}
        if typ=='np_thru_hole': sides=set()
        n=find(p,'net'); net=q(n[0][1]) if n else None
        if (sides=={'T'} and side=='B') or (sides=={'B'} and side=='T'): pass
        pads.append((ref,q(p[1]),net,sides,X-w/2-OX,Y-h/2-OY,X+w/2-OX,Y+h/2-OY,side))
print('pads',len(pads))
# pad vs outline
out=[p for p in pads if p[3] and (p[4]<0.2 or p[5]<0.2 or p[6]>BW-0.2 or p[7]>BH-0.2)]
print('pads closer than 0.2mm to/outside edge:',len(out),[(p[0],p[1]) for p in out][:15])
# pad-pad overlap/clearance different nets same side
import itertools
clear=0.10
viol=[]
for s in 'TB':
    L=[p for p in pads if s in p[3]]
    L.sort(key=lambda p:p[4])
    for i,a in enumerate(L):
        for b in L[i+1:]:
            if b[4]>a[6]+clear: break
            if a[0]==b[0]: continue
            if a[2]==b[2] and a[2] is not None: continue
            dx=max(a[4]-b[6],b[4]-a[6]); dy=max(a[5]-b[7],b[5]-a[7])
            if dx<clear and dy<clear: viol.append((s,a[0],a[1],b[0],b[1],round(max(dx,dy),2)))
print('pad clearance violations (<0.1mm, different parts/nets):',len(viol)); print(viol[:20])
# footprint side counts
print(collections.Counter('B' if q(find(fp,'layer')[0][1])=='B.Cu' else 'T' for fp in fps))
