import math, sys, json
from verify import parse, simulate, key
def feeds(lines):
    """effective feedrate of every XY extrusion move, keyed like verify.key"""
    x=y=z=0; F=None; res={}; inprime=False
    for raw in lines:
        s=raw.strip()
        if s.startswith("; unidir_laser: prime done"): inprime=False; continue
        if s.startswith("; unidir_laser: prime"): inprime=True; continue
        c,p=parse(raw)
        if c=="G28": x=y=0
        if c in("G0","G1"):
            if "F" in p: F=p["F"]
            nx,ny,nz=p.get("X",x),p.get("Y",y),p.get("Z",z); e=p.get("E",0)
            if e>0 and math.hypot(nx-x,ny-y)>1e-9 and not inprime:
                res.setdefault(key(dict(x0=x,y0=y,x1=nx,y1=ny,z=nz,e=e)),[]).append(F)
            x,y,z=nx,ny,nz
    return res
def main(inp,out,out2,overrun):
    A=open(inp).read().splitlines(); B=open(out).read().splitlines(); C=open(out2).read().splitlines()
    fa,fb=feeds(A),feeds(B)
    bad_feed=[(k,fa[k],fb.get(k)) for k in fa if sorted(fa[k])!=sorted(fb.get(k,[]))]
    sb=simulate(B); dry=[b for b in sb["beads"] if b.get("dry")]
    dry_bad=[b for b in dry if abs(math.hypot(b["x1"]-b["x0"],b["y1"]-b["y0"])-overrun)>1e-3 or abs(b["y1"]-b["y0"])>1e-6 or b["x1"]<=b["x0"]]
    # idempotence: second pass must lay identical beads, no second prime, one arm/disarm
    s2=simulate(C)
    from collections import Counter
    k1=Counter(key(b) for b in sb["beads"] if not b.get("dry")); k2=Counter(key(b) for b in s2["beads"] if not b.get("dry"))
    tokens=Counter(l.split(";")[0].split()[0].upper() for l in B if l.split(";")[0].strip())
    laser_words=[t for t in tokens if "LASER" in t or t in("SET_PIN","M3","M4","M5")]
    print(json.dumps(dict(
        feed_mismatches=len(bad_feed), feed_ex=bad_feed[:2],
        overrun_moves=len(dry), overrun_wrong_length=len(dry_bad),
        second_pass_same_beads=(k1==k2), second_pass_primes=sum(1 for l in C if l.startswith("; unidir_laser: prime (")),
        second_pass_arm=sum(1 for l in C if l.split(";")[0].strip().upper()=="LASER_ARM"),
        second_pass_disarm=sum(1 for l in C if l.split(";")[0].strip().upper()=="LASER_DISARM"),
        laser_commands_in_output={t:tokens[t] for t in laser_words},
        G10_G11_left=tokens.get("G10",0)+tokens.get("G11",0))))
main(*sys.argv[1:4], float(sys.argv[4]))
