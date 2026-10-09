import sys; sys.path.insert(0,'.')
from sx import *
from geom import rot_pt,OX,OY,BW,BH
t=parse(open(sys.argv[1],newline='').read())
items=[]
for fp in find(t,'footprint'):
    ref=[q(p[2]) for p in find(fp,'property') if q(p[1])=='Reference'][0]
    at=find(fp,'at')[0]; fx,fy=float(at[1])-OX,float(at[2])-OY; th=int(round(float(at[3])))%360 if len(at)>3 else 0
    side='B' if q(find(fp,'layer')[0][1])=='B.Cu' else 'T'
    cy='B.CrtYd' if side=='B' else 'F.CrtYd'
    pts=[]
    for k in ('fp_line','fp_rect','fp_arc','fp_circle','fp_poly'):
        for r in find(fp,k):
            if q(find(r,'layer')[0][1])!=cy: continue
            for tag in ('start','end','mid','center'):
                for p in find(r,tag): pts.append((float(p[1]),float(p[2])))
            for pp in find(r,'pts'):
                for xy in find(pp,'xy'): pts.append((float(xy[1]),float(xy[2])))
            if k=='fp_circle':
                c=find(r,'center')[0];e=find(r,'end')[0];rad=((float(c[1])-float(e[1]))**2+(float(c[2])-float(e[2]))**2)**.5
                pts+= [(float(c[1])-rad,float(c[2])-rad),(float(c[1])+rad,float(c[2])+rad)]
    if ref=='U5': pts=[(-9.75,-6.75),(9.75,13.45)]
    if not pts: continue
    w=[rot_pt(x,y,th) for x,y in pts]
    b=(fx+min(a[0] for a in w),fy+min(a[1] for a in w),fx+max(a[0] for a in w),fy+max(a[1] for a in w))
    tht=any(q(p[2]) in('thru_hole','np_thru_hole') for p in find(fp,'pad'))
    padpts=[]
    for p in find(fp,'pad'):
        if q(p[2]) in('thru_hole',):
            a=find(p,'at')[0]; rx,ry=rot_pt(float(a[1]),float(a[2]),th); padpts.append((fx+rx,fy+ry,q(p[1])))
    items.append((ref,b,side,tht,padpts))
bad=0
for i,(r,b,s,th,pp) in enumerate(items):
    if b[0]<0 or b[1]<0 or b[2]>BW or b[3]>BH:
        if r!='U5': print('OUT',r,[round(v,2) for v in b]); bad+=1
    for (r2,b2,s2,th2,pp2) in items[i+1:]:
        if not (s==s2): 
            pass
        else:
            ox=min(b[2],b2[2])-max(b[0],b2[0]); oy=min(b[3],b2[3])-max(b[1],b2[1])
            if ox>0.001 and oy>0.001: print('COURTYARD',r,r2,round(ox,2),round(oy,2)); bad+=1
        for (A,PA,BB) in ((r,pp,b2),(r2,pp2,b)):
            pass
        for x,y,n in pp:
            if b2[0]<x<b2[2] and b2[1]<y<b2[3]: print('PTH',r,n,'in',r2); bad+=1
        for x,y,n in pp2:
            if b[0]<x<b[2] and b[1]<y<b[3]: print('PTH',r2,n,'in',r); bad+=1
print('problems',bad)
