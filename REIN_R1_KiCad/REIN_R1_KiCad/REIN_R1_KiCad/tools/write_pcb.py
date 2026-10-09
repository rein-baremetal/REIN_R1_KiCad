import sys, json, uuid, re, copy
sys.path.insert(0,'/home/claude/w/tools')
from geom import *
raw,tree,P=load()
place={k:tuple(v) for k,v in json.load(open('final_place.json')).items()}
NL='\r\n'
def fmt(v):
    s=('%.4f'%v).rstrip('0').rstrip('.')
    return '0' if s in('-0','') else s
def ser(n,ind):
    if isinstance(n,str): return n
    head=[];i=0
    while i<len(n) and isinstance(n[i],str): head.append(n[i]); i+=1
    rest=n[i:]
    if not rest: return '('+' '.join(head)+')'
    out='('+' '.join(head)+NL
    for c in rest: out+='\t'*(ind+1)+ser(c,ind+1)+NL
    return out+'\t'*ind+')'
SWAP={'F.Cu':'B.Cu','B.Cu':'F.Cu','F.SilkS':'B.SilkS','B.SilkS':'F.SilkS','F.Mask':'B.Mask','B.Mask':'F.Mask',
      'F.Paste':'B.Paste','B.Paste':'F.Paste','F.CrtYd':'B.CrtYd','B.CrtYd':'F.CrtYd','F.Fab':'B.Fab','B.Fab':'F.Fab',
      'F.Adhes':'B.Adhes','B.Adhes':'F.Adhes'}
def swap_layer_tok(tok):
    s=q(tok); return '"%s"'%SWAP.get(s,s)
def flipy(n,mode):
    """transform a point list (xy-like) in place: mode 'flip' -> y=-y ; 'transpose' -> swap x,y"""
    x,y=float(n[1]),float(n[2])
    if mode=='flip': y=-y
    elif mode=='transpose': x,y=y,x
    n[1]=fmt(x); n[2]=fmt(y)
def walk_pts(n,mode):
    for c in n:
        if isinstance(c,list):
            if c[0] in('start','end','center','mid'): flipy(c,mode)
            elif c[0]=='pts':
                for xy in c:
                    if isinstance(xy,list) and xy[0]=='xy': flipy(xy,mode)
def swap_layers_in(n):
    for c in n:
        if isinstance(c,list):
            if c[0]=='layer' and len(c)==2: c[1]=swap_layer_tok(c[1])
            elif c[0]=='layers': 
                for k in range(1,len(c)): c[k]=swap_layer_tok(c[k])
def add_mirror(eff):
    for e in eff:
        if isinstance(e,list) and e[0]=='justify':
            if 'mirror' not in e: e.append('mirror')
            return
    eff.append(['justify','mirror'])
def setat(n,x,y,a=None):
    del n[1:]
    n.extend([fmt(x),fmt(y)])
    if a is not None and abs(a%360)>1e-9: n.append(fmt(a%360))

def transform(ref,fp,pos,th,side):
    """pos: file coords. Returns new node (deep-copied & modified)"""
    fp=copy.deepcopy(fp)
    oldpos=[float(v) for v in find(fp,'at')[0][1:3]]
    bottom=(side=='B')
    mode='flip' if bottom else None
    if ref=='J9': mode='transpose'; bottom=True
    for c in fp:
        if not isinstance(c,list): continue
        k=c[0]
        if k=='layer':
            if bottom: c[1]='"B.Cu"'
        elif k=='at':
            setat(c,pos[0],pos[1],th)
        elif k in('property','fp_text'):
            at=[d for d in c if isinstance(d,list) and d[0]=='at'][0]
            lx,ly=float(at[1]),float(at[2]); la=float(at[3]) if len(at)>3 else 0.0
            if mode=='flip': ly=-ly
            elif mode=='transpose': lx,ly=ly,lx
            if k=='property': a=0.0
            else: a=((-la if bottom else la)+th)%360
            setat(at,lx,ly,a if a else 0.0)
            if len(at)==3: at.append('0')
            if k=='property' and q(c[1])=='Reference' and (ref[0] in 'RC' or ref=='FB1'):
                for d in c:
                    if isinstance(d,list) and d[0]=='layer': d[1]='"F.Fab"'
            if bottom: swap_layers_in(c)
            for d in c:
                if isinstance(d,list) and d[0]=='effects':
                    if bottom: add_mirror(d)
                    if k=='property' and q(c[1])=='Reference':
                        for f in d:
                            if isinstance(f,list) and f[0]=='font':
                                small = False
                                for g in f:
                                    if isinstance(g,list) and g[0]=='size': g[1]=g[2]='0.8'
                                    if isinstance(g,list) and g[0]=='thickness': g[1]='0.12'
        elif k in('fp_line','fp_rect','fp_circle','fp_arc','fp_poly','fp_curve'):
            if mode: walk_pts(c,mode)
            if bottom: swap_layers_in(c)
        elif k=='pad':
            at=[d for d in c if isinstance(d,list) and d[0]=='at'][0]
            lx,ly=float(at[1]),float(at[2]); la=float(at[3]) if len(at)>3 else 0.0
            if mode=='flip': ly=-ly
            elif mode=='transpose': lx,ly=ly,lx
            a=((-la if bottom else la)+th)%360
            if ref=='J9': a=0.0
            setat(at,lx,ly,a)
            if bottom: swap_layers_in(c)
        elif k=='zone':
            for pl in c:
                if isinstance(pl,list) and pl[0]=='polygon':
                    for pts in pl:
                        if isinstance(pts,list) and pts[0]=='pts':
                            for xy in pts:
                                if isinstance(xy,list) and xy[0]=='xy':
                                    rx,ry=float(xy[1])-oldpos[0],float(xy[2])-oldpos[1]
                                    if bottom: ry=-ry
                                    rx,ry=rot_pt(rx,ry,int(th))
                                    xy[1]=fmt(pos[0]+rx); xy[2]=fmt(pos[1]+ry)
            if bottom: swap_layers_in(c)
    return fp

# ---- final placement table (file coords) ----
J9=(8.37,4.77,0,'B')
place['J9']=J9
assert len(place)==173,len(place)

# ---- locate footprint spans in raw text ----
spans=[];depth=0;i=0;n=len(raw);instr=False
start=None
while i<n:
    ch=raw[i]
    if instr:
        if ch=='\\': i+=2; continue
        if ch=='"': instr=False
    else:
        if ch=='"': instr=True
        elif ch=='(':
            depth+=1
            if depth==2 and raw.startswith('(footprint',i): start=i
        elif ch==')':
            if depth==2 and start is not None: spans.append((start,i+1)); start=None
            depth-=1
    i+=1
print('spans',len(spans))
out=[];last=0
fpnodes=find(tree,'footprint'); assert len(fpnodes)==len(spans)
for (s,e),node in zip(spans,fpnodes):
    ref=[q(p[2]) for p in find(node,'property') if q(p[1])=='Reference'][0]
    x,y,th,side=place[ref]
    new=transform(ref,node,(OX+x,OY+y),th,side)
    out.append(raw[last:s]); out.append(ser(new,1)); last=e
out.append(raw[last:])
body=''.join(out)

# ---- mounting holes (NPTH 2.75, board-only footprints) ----
def U(): return '"%s"'%uuid.uuid4()
def hole(i,x,y):
    t_=lambda s:s.replace('\n',NL)
    return t_('''\t(footprint "MountingHole_2.75mm_M2.5_HAT"
\t\t(layer "F.Cu")
\t\t(uuid %s)
\t\t(at %s %s)
\t\t(descr "Raspberry Pi HAT mounting hole, 2.75 mm drill, 6.2 mm keep-out")
\t\t(tags "mounting hole HAT")
\t\t(property "Reference" "H%d"
\t\t\t(at 0 -4.2 0)
\t\t\t(layer "F.SilkS")
\t\t\t(hide yes)
\t\t\t(uuid %s)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 0.8 0.8)
\t\t\t\t\t(thickness 0.12)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Value" "MountingHole"
\t\t\t(at 0 4.2 0)
\t\t\t(layer "F.Fab")
\t\t\t(hide yes)
\t\t\t(uuid %s)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 0.8 0.8)
\t\t\t\t\t(thickness 0.12)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(attr exclude_from_pos_files exclude_from_bom board_only)
\t\t(fp_circle
\t\t\t(center 0 0)
\t\t\t(end 3.1 0)
\t\t\t(stroke
\t\t\t\t(width 0.05)
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(fill no)
\t\t\t(layer "F.CrtYd")
\t\t\t(uuid %s)
\t\t)
\t\t(pad "" np_thru_hole circle
\t\t\t(at 0 0)
\t\t\t(size 2.75 2.75)
\t\t\t(drill 2.75)
\t\t\t(layers "*.Cu" "*.Mask")
\t\t\t(uuid %s)
\t\t)
\t\t(embedded_fonts no)
\t)
'''%(U(),fmt(x),fmt(y),i,U(),U(),U(),U()))
holes=''.join(hole(i+1,OX+x,OY+y) for i,(x,y) in enumerate([(3.5,3.5),(61.5,3.5),(3.5,52.5),(61.5,52.5)]))
# insert before the final (embedded_fonts no) of the board
k=body.rfind('\t(embedded_fonts no)')
body=body[:k]+holes+body[k:]
# also tidy the board-text note
body=body.replace('HAT 65x56 | snap-off wing from x=65','HAT 65x56 | snap-off wing from x=65 | REIN R1 v0.4 placement')
open('/home/claude/w/REIN_R1.kicad_pcb','w',newline='').write(body)
print('written',len(body))
