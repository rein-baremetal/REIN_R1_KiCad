import sys, json, math, collections
sys.path.insert(0,'/home/claude/w/tools')
import numpy as np
from geom import *
raw,t,P=load()
secs=json.load(open('secs.json'))
sa={k:tuple(v) for k,v in json.load(open('sa_result.json')).items()}
RES=1/0.1
GW,GH=int(BW*RES)+1,int(BH*RES)+1
grid={'T':np.zeros((GW,GH),dtype=np.int32),'B':np.zeros((GW,GH),dtype=np.int32)}
def mark(b,sides,m=0.1):
    x0=max(0,int(math.floor((b[0]-m)*RES))); x1=min(GW,int(math.ceil((b[2]+m)*RES)))
    y0=max(0,int(math.floor((b[1]-m)*RES))); y1=min(GH,int(math.ceil((b[3]+m)*RES)))
    for s in sides: grid[s][x0:x1,y0:y1]=1
# board edge margin 0.35
for s in 'TB':
    e=int(0.35*RES)
    grid[s][:e,:]=1; grid[s][-e:,:]=1; grid[s][:,:e]=1; grid[s][:,-e:]=1
# fixed blockers
for hx,hy in [(3.5,3.5),(61.5,3.5),(3.5,52.5),(61.5,52.5)]: mark((hx-3.2,hy-3.2,hx+3.2,hy+3.2),'TB',0)
mark((8.37-1.77,0.46,8.37+19*2.54+1.77,6.54),'TB',0.1)
res=dict(sa)
for r,(x,y,th,s) in sa.items():
    b=world_bbox(P[r],x,y,th,s)
    mark(b,'TB' if P[r]['tht'] else s,0.1)
# U5 antenna side is off-board; nothing to do.

meds={r:v for r,v in sa.items()}
def sec(r): return secs.get(r,'')
passives=[r for r in P if r not in sa and r!='J9']
print('passives',len(passives))
# anchor pads
anchor=collections.defaultdict(list)   # net -> [(ref,x,y)]
for r,(x,y,th,s) in meds.items():
    for n,net,px,py in pad_world(P[r],x,y,th,s):
        if net and net!='/GND' and not net.startswith('unconnected'): anchor[net].append((r,px,py))
assigned=collections.Counter()
def target(p):
    pts=[]
    nets=sorted({n for (_,n,*_) in P[p]['pads'] if n and n!='/GND' and not n.startswith('unconnected')})
    for net in nets:
        cand=[a for a in anchor[net] if sec(a[0])==sec(p)]
        if not cand: cand=anchor[net]
        if not cand: continue
        # prefer ICs; balance by assigned count
        cand.sort(key=lambda a:(0 if a[0].startswith('U') else 1, assigned[a[0]]))
        best=cand[0][0]
        same=[a for a in cand if a[0]==best]
        # pick the pad of that part with this net, round robin
        a=same[assigned[(best,net)]%len(same)]
        assigned[(best,net)]+=1; assigned[best]+=1
        pts.append((a[1],a[2]))
    if not pts: return None
    return (sum(q[0] for q in pts)/len(pts), sum(q[1] for q in pts)/len(pts))
def sat(g):
    s=np.zeros((g.shape[0]+1,g.shape[1]+1),dtype=np.int32)
    s[1:,1:]=g.cumsum(0).cumsum(1); return s
sats={k:sat(grid[k]) for k in 'TB'}
dirty={'T':False,'B':False}
def find_site(p,tx,ty):
    bx0,by0,bx1,by1=P[p]['bbox']
    best=None
    for s in 'TB':
        if dirty[s]: sats[s]=sat(grid[s]); dirty[s]=False
        S=sats[s]
        for th in (0,90,180,270) if False else (0,90):
            ys0,ys1=(by0,by1) if s=='T' else (-by1,-by0)
            cs=[rot_pt(a,b,th) for a in (bx0,bx1) for b in (ys0,ys1)]
            lx0=min(c[0] for c in cs);lx1=max(c[0] for c in cs);ly0=min(c[1] for c in cs);ly1=max(c[1] for c in cs)
            W=15.0
            xs=np.arange(max(lx1+0.4,tx-W),min(BW-0.4+lx0,tx+W),0.1)
            ys=np.arange(max(ly1+0.4,ty-W),min(BH-0.4+ly0,ty+W),0.1)
            if len(xs)==0 or len(ys)==0: continue
            X,Y=np.meshgrid(xs,ys,indexing='ij')
            ix0=np.floor((X+lx0-0.05)*RES).astype(int); ix1=np.ceil((X+lx1+0.05)*RES).astype(int)
            iy0=np.floor((Y+ly0-0.05)*RES).astype(int); iy1=np.ceil((Y+ly1+0.05)*RES).astype(int)
            ok=(ix0>=0)&(iy0>=0)&(ix1<=GW)&(iy1<=GH)
            ix0c=np.clip(ix0,0,GW);ix1c=np.clip(ix1,0,GW);iy0c=np.clip(iy0,0,GH);iy1c=np.clip(iy1,0,GH)
            cnt=S[ix1c,iy1c]-S[ix0c,iy1c]-S[ix1c,iy0c]+S[ix0c,iy0c]
            free=ok&(cnt==0)
            if not free.any(): continue
            d=np.hypot(X-tx,Y-ty)+(2.5 if s=='B' else 0)+(0.0 if th==0 else 0.15)
            d=np.where(free,d,1e9)
            k=np.unravel_index(np.argmin(d),d.shape)
            if best is None or d[k]<best[0]: best=(d[k],round(float(X[k]),2),round(float(Y[k]),2),th,s)
    return best
order=sorted(passives,key=lambda r:(sec(r),r[0],int(''.join(c for c in r if c.isdigit()))))
fail=[]
for p in order:
    tg=target(p)
    if tg is None: tg=(BW/2,BH/2)
    b=find_site(p,*tg)
    if b is None: fail.append(p); continue
    _,x,y,th,s=b
    res[p]=(x,y,th,s)
    mark(world_bbox(P[p],x,y,th,s),s,0.1); dirty[s]=True
print('failed',fail)
json.dump(res,open('final_place.json','w'))
nb=sum(1 for r,v in res.items() if v[3]=='B')
print('placed',len(res),'on bottom',nb)
