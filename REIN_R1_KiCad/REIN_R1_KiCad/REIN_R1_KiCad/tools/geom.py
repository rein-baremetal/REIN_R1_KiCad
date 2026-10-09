import sys, math, json, collections
sys.path.insert(0,'/home/claude/w/tools')
from sx import *
SRC='/home/claude/w/REIN_R1_KiCad_v0.3/REIN_R1_KiCad/REIN_R1.kicad_pcb'
OX,OY=60.0,60.0     # board origin in file coords
BW,BH=85.0,56.0

def load():
    raw=open(SRC,newline='').read()
    t=parse(raw)
    parts={}
    for fp in find(t,'footprint'):
        ref=[q(p[2]) for p in find(fp,'property') if q(p[1])=='Reference'][0]
        at=[float(v) for v in find(fp,'at')[0][1:]]
        xs=[];ys=[]
        for k in ('fp_line','fp_rect'):
            for r in find(fp,k):
                if q(find(r,'layer')[0][1])=='F.CrtYd':
                    for pt in find(r,'start')+find(r,'end'):
                        xs.append(float(pt[1]));ys.append(float(pt[2]))
        for k in ('fp_arc','fp_circle','fp_poly'):
            pass
        pads=[];tht=False
        for p in find(fp,'pad'):
            a=find(p,'at')[0]; sz=find(p,'size')[0]
            n=find(p,'net'); net=q(n[0][1]) if n else None
            pads.append((q(p[1]),net,float(a[1]),float(a[2]),float(sz[1]),float(sz[2])))
            if q(p[2]) in('thru_hole','np_thru_hole'): tht=True
        if ref=='U5': xs=[-9.75,9.75];ys=[-6.75,13.45]   # body only; antenna keepout handled separately
        if ref=='BT1': xs=[-11.87,11.87];ys=[-10.5,10.5]
        if not xs:
            for p in pads:
                xs+= [p[2]-p[4]/2,p[2]+p[4]/2]; ys+=[p[3]-p[5]/2,p[3]+p[5]/2]
        parts[ref]=dict(ref=ref,fp=q(fp[1]),node=fp,at=at,bbox=(min(xs),min(ys),max(xs),max(ys)),pads=pads,tht=tht)
    return raw,t,parts

def rot_pt(x,y,th):
    th%=360
    if th==0: return x,y
    if th==90: return y,-x
    if th==180: return -x,-y
    if th==270: return -y,x
    raise ValueError(th)

def world_bbox(part,x,y,th,side):
    x0,y0,x1,y1=part['bbox']
    if side=='B': y0,y1=-y1,-y0
    cs=[rot_pt(a,b,th) for a in (x0,x1) for b in (y0,y1)]
    return (x+min(c[0] for c in cs),y+min(c[1] for c in cs),x+max(c[0] for c in cs),y+max(c[1] for c in cs))

def pad_world(part,x,y,th,side):
    out=[]
    for n,net,px,py,w,h in part['pads']:
        if side=='B': py=-py
        rx,ry=rot_pt(px,py,th)
        out.append((n,net,x+rx,y+ry))
    return out
