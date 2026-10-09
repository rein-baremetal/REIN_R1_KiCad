import sys, math, random, json, collections
sys.path.insert(0,'/home/claude/w/tools')
import numpy as np
from geom import *
random.seed(7); np.random.seed(7)
raw,t,P=load()
PAD=0.15  # extra margin on each side of every courtyard

def is_passive(r): return (r[0] in 'RC' and r not in('RSH1',)) or r=='FB1'
MED=[r for r in P if not is_passive(r)]

# ---------- fixed placements (board-local coords) ----------
FIX={}   # ref -> (x,y,rot,side)
def edge_left(ref,cy):
    x0,y0,x1,y1=P[ref]['bbox']          # rot 90: x'=y, y'=-x
    ox=-y0; oy=cy+(x0+x1)/2
    FIX[ref]=(ox,oy,90,'T')
FIX['U5']=(78.25,14.6,270,'T')
FIX['J1']=(12.3,51.85,0,'T')
FIX['J2']=(20.6,52.0,0,'T')
FIX['J4']=(36.55,47.12,0,'T')
FIX['J8']=(47.2,52.7,0,'T')
edge_left('J3',17.0); edge_left('J6',27.0); edge_left('J7',35.2)
FIX['BT1']=(22.5,17.45,0,'T')
FIX['J15']=(83.0,35.2,0,'T'); FIX['J14']=(78.9,35.2,0,'T')

# static blockers (both sides): holes, Pi-socket
HOLES=[(3.5,3.5),(61.5,3.5),(3.5,52.5),(61.5,52.5)]
BLOCK=[(x-3.2,y-3.2,x+3.2,y+3.2) for x,y in HOLES]
J9_X0=8.37; J9_Y_EVEN=2.23; J9_Y_ODD=4.77
BLOCK.append((J9_X0-1.77,0.46,J9_X0+19*2.54+1.77,6.54))

TOP_ONLY=lambda r: r.startswith('SW') or r.startswith('J') or r=='BT1' or r in('D8','D9','D10','U1','U2','U3','U4','Y1','Y2','U16','U17','U18','U8','U22','U23','U21')
free=[r for r in MED if r not in FIX and r!='J9']
print('movable',len(free),'fixed',len(FIX))

# ---------- state arrays ----------
refs=list(FIX)+free
idx={r:i for i,r in enumerate(refs)}
N=len(refs)
st=np.zeros((N,3)); side=[ 'T']*N
for r,(x,y,th,s) in FIX.items():
    st[idx[r]]=(x,y,th); side[idx[r]]=s
nfix=len(FIX)
for r in free:
    i=idx[r]; st[i]=(random.uniform(10,60),random.uniform(8,50),random.choice([0,90,180,270]))
    side[i]='T'
sidearr=np.array([0]*N)  # 0 top,1 bottom
thtarr=np.array([1 if P[r]['tht'] else 0 for r in refs])

def bb(i):
    r=refs[i]; x,y,th=st[i]
    b=world_bbox(P[r],x,y,int(th),'B' if sidearr[i] else 'T')
    return (b[0]-PAD,b[1]-PAD,b[2]+PAD,b[3]+PAD)
B=np.array([bb(i) for i in range(N)])
BLK=np.array(BLOCK)

# nets
netpads=collections.defaultdict(list)   # net -> [(i,padindex)]
for r in refs:
    for k,(n,net,px,py,w,h) in enumerate(P[r]['pads']):
        if net and net not in('/GND',) and not net.startswith('unconnected'):
            netpads[net].append((idx[r],k))
nets=[(n,l) for n,l in netpads.items() if len({i for i,_ in l})>=2]
def wt(n,l):
    c=len(l)
    if n in('/3V3','/5V'): return 0.03
    return 1.0 if c<=8 else 0.3
netw=[wt(n,l) for n,l in nets]
part_nets=collections.defaultdict(list)
for ni,(n,l) in enumerate(nets):
    for i in {i for i,_ in l}: part_nets[i].append(ni)
PADW=[None]*N
def upd_pads(i):
    r=refs[i]; x,y,th=st[i]
    pw=pad_world(P[r],x,y,int(th),'B' if sidearr[i] else 'T')
    PADW[i]=np.array([(a[2],a[3]) for a in pw])
for i in range(N): upd_pads(i)
def net_cost(ni):
    l=nets[ni][1]
    xs=[PADW[i][k,0] for i,k in l]; ys=[PADW[i][k,1] for i,k in l]
    return netw[ni]*((max(xs)-min(xs))+(max(ys)-min(ys)))
EDGEPREF={'J5','J10','J11','J12','J13','J16','J17','J18'}
def part_cost(i):
    c=sum(net_cost(ni) for ni in part_nets[i])
    if refs[i] in EDGEPREF:
        bq=B[i]; c+=0.5*max(0,min(bq[0],bq[1],BW-bq[2],BH-bq[3]))
    # overlap
    b=B[i]
    ox=np.minimum(B[:,2],b[2])-np.maximum(B[:,0],b[0])
    oy=np.minimum(B[:,3],b[3])-np.maximum(B[:,1],b[1])
    m=(ox>0)&(oy>0)&((sidearr==sidearr[i])|(thtarr==1)|(thtarr[i]==1))
    m[i]=False
    ov=float(np.sum(np.minimum(ox[m],oy[m])*np.minimum(ox[m],oy[m]))) if m.any() else 0.0
    ov=float(np.sum(ox[m]*oy[m]))
    ox=np.minimum(BLK[:,2],b[2])-np.maximum(BLK[:,0],b[0]); oy=np.minimum(BLK[:,3],b[3])-np.maximum(BLK[:,1],b[1])
    m2=(ox>0)&(oy>0); ov+=float(np.sum(ox[m2]*oy[m2]))
    if sidearr[i]==1: c+=6.0
    oob=max(0,-b[0]+0.1)+max(0,-b[1]+0.1)+max(0,b[2]-(BW-0.1))+max(0,b[3]-(BH-0.1))
    return c, ov*30+oob*60, ov
def total():
    c=sum(net_cost(ni) for ni in range(len(nets)))
    ov=0;pen=0
    for i in range(N):
        _,p,o=part_cost(i); ov+=o; pen+=p
    return c,ov
free_idx=list(range(nfix,N))
def run(iters,T0,T1):
    global B
    T=T0; alpha=(T1/T0)**(1/iters)
    cur={i:part_cost(i) for i in range(N)}
    for it in range(iters):
        T*=alpha
        i=random.choice(free_idx)
        old=(st[i].copy(),sidearr[i],B[i].copy(),PADW[i].copy())
        mv=random.random()
        j=None
        if mv<0.55:
            st[i,0]+=random.gauss(0,max(0.25,T*1.2)); st[i,1]+=random.gauss(0,max(0.25,T*1.2))
        elif mv<0.68:
            st[i,0]=random.uniform(2,BW-2); st[i,1]=random.uniform(2,BH-2)
        elif mv<0.88:
            st[i,2]=(st[i,2]+random.choice([90,180,270]))%360
        elif mv<0.94:
            if TOP_ONLY(refs[i]): continue
            sidearr[i]^=1
        else:
            j=random.choice(free_idx)
            if j==i: continue
            oldj=(st[j].copy(),sidearr[j],B[j].copy(),PADW[j].copy())
            st[i,:2],st[j,:2]=st[j,:2].copy(),st[i,:2].copy()
        # old cost (affected)
        aff=[i]+([j] if j is not None else [])
        # evaluate affected costs before/after incl neighbors' overlap -> approximate with total over affected + nets
        before=sum(sum(cur[a][1:2]) +0 for a in aff)
        nb=set()
        for a in aff: nb.update(part_nets[a])
        cb=sum(net_cost(ni) for ni in nb)
        # overlap before: sum of overlap penalties involving aff parts (pairwise counted) -> use cur
        ob=sum(cur[a][1] for a in aff)
        for a in aff:
            B[a]=bb(a); upd_pads(a)
        ca=sum(net_cost(ni) for ni in nb)
        new={a:part_cost(a) for a in aff}
        oa=sum(new[a][1] for a in aff)
        d=(ca-cb)+(oa-ob)
        if d<=0 or random.random()<math.exp(-d/max(T,1e-6)):
            for a in aff: cur[a]=new[a]
            # neighbors' overlap costs go stale -> refresh occasionally
            if it%50==0:
                for a in range(N): cur[a]=part_cost(a)
        else:
            st[i],sidearr[i],B[i],PADW[i]=old
            if j is not None: st[j],sidearr[j],B[j],PADW[j]=oldj
        if it%20000==0:
            for a in range(N): cur[a]=part_cost(a)
            c,ov=total(); print(it,'T%.2f'%T,'wl %.0f ov %.2f'%(c,ov),flush=True)
run(int(sys.argv[1]) if len(sys.argv)>1 else 150000, 6.0, 0.05)
c,ov=total(); print('final wl %.0f overlap %.3f'%(c,ov))
res={r:(float(st[idx[r],0]),float(st[idx[r],1]),int(st[idx[r],2]),'B' if sidearr[idx[r]] else 'T') for r in refs}
json.dump(res,open('sa_result.json','w'))
