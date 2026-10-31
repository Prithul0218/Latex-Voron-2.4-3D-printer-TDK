"""Independent machine simulator: replays G-code and compares beads in Orca input vs processed output."""
import math, sys, re, json
TOL=1e-3
def parse(line):
    code=line.split(";")[0].strip()
    if not code: return None,{}
    parts=code.split(); p={}
    for t in parts[1:]:
        if len(t)<2: continue
        k,val=(t.split("=",1) if "=" in t[1:] else (t[0],t[1:]))
        try: p[k.upper()]=float(val)
        except ValueError: pass
    return parts[0].upper(), p
def simulate(lines, pwm_cmd="LASER_PWM"):
    x=y=z=0.0; laser=0.0; inprime=False; power=False
    beads=[]; stationary=0.0; prime_e=0.0; minx=1e9; events=[]
    for raw in lines:
        s=raw.strip()
        if s.startswith("; unidir_laser: prime done"): inprime=False; continue
        if s.startswith("; unidir_laser: prime"): inprime=True; continue
        c,p=parse(raw)
        if c is None: continue
        if c==pwm_cmd: laser=p.get("S",0.0); events.append(("pwm",laser)); continue
        if c in("LASER_ON",): laser=p.get("S",1.0); events.append(("legacy_on",laser)); continue
        if c in("LASER_OFF",): laser=0.0; continue
        if c=="LASER_ARM": power=True; events.append(("arm",)); continue
        if c=="LASER_DISARM": power=False; laser=0.0; events.append(("disarm",)); continue
        if c=="G28": x=y=0.0; continue
        if c in("G0","G1"):
            nx=p.get("X",x); ny=p.get("Y",y); nz=p.get("Z",z); e=p.get("E",0.0)
            moved=math.hypot(nx-x,ny-y)>1e-9
            if moved: minx=min(minx,nx)
            if e>0:
                if inprime: prime_e+=e
                elif moved: beads.append(dict(x0=x,y0=y,x1=nx,y1=ny,z=nz,e=e,laser=laser,power=power))
                else: stationary+=e
            elif moved and laser>0 and nz==z: beads.append(dict(x0=x,y0=y,x1=nx,y1=ny,z=nz,e=0,laser=laser,power=power,dry=True))
            if laser>0 and abs(nz-z)>1e-9: events.append(("zmove_laser_on",raw.strip()))
            x,y,z=nx,ny,nz
        elif c in("G2","G3"): events.append(("arc",raw.strip()))
    return dict(beads=beads,stationary=stationary,prime_e=prime_e,minx=minx,events=events,end_laser=laser,end_power=power)
def key(b):
    a=(round(b["x0"],2),round(b["y0"],2)); c=(round(b["x1"],2),round(b["y1"],2))
    return (min(a,c),max(a,c),round(b["z"],3),round(b["e"],4))
def compare(inp, out, prefdir=0.0, perp_tol=10.0, cmd="LASER_PWM"):
    A=simulate(open(inp).read().splitlines(),cmd); B=simulate(open(out).read().splitlines(),cmd)
    ux,uy=math.cos(math.radians(prefdir)),math.sin(math.radians(prefdir)); st=math.sin(math.radians(perp_tol))
    from collections import Counter
    ka=Counter(key(b) for b in A["beads"]); 
    outbeads=[b for b in B["beads"] if not b.get("dry")]
    kb=Counter(key(b) for b in outbeads)
    missing=ka-kb; extra=kb-ka
    against=[]; laser_off=[]; power_off=[]
    for b in outbeads:
        L=math.hypot(b["x1"]-b["x0"],b["y1"]-b["y0"]); c=((b["x1"]-b["x0"])*ux+(b["y1"]-b["y0"])*uy)/L
        if c< -st: against.append((round(L,2),key(b)))
        if b["laser"]<=0: laser_off.append(key(b))
        if not b["power"]: power_off.append(key(b))
    ea=sum(b["e"] for b in A["beads"])+A["stationary"]; eb=sum(b["e"] for b in outbeads)+B["stationary"]
    # power pin: count arm/disarm events and where pwm commands appear relative to them
    ev=B["events"]; arms=[i for i,e in enumerate(ev) if e[0]=="arm"]; disarms=[i for i,e in enumerate(ev) if e[0]=="disarm"]
    legacy=[e for e in ev if e[0]=="legacy_on"]
    pwm_outside=[e for i,e in enumerate(ev) if e[0]=="pwm" and e[1]>0 and not (arms and disarms and arms[0]<i<disarms[-1])]
    return dict(beads_in=sum(ka.values()),beads_out=sum(kb.values()),missing=sum(missing.values()),extra=sum(extra.values()),
                missing_ex=list(missing)[:3],extra_ex=list(extra)[:3],against=len(against),against_ex=against[:3],
                laser_off_beads=len(laser_off),beads_unpowered=len(power_off),E_in=round(ea,4),E_out=round(eb,4),prime_E=round(B["prime_e"],3),
                arm_count=len(arms),disarm_count=len(disarms),legacy_LASER_ON=len(legacy),pwm_on_outside_arm_window=len(pwm_outside),
                zmove_with_laser=[e for e in ev if e[0]=="zmove_laser_on"][:2],arcs=len([e for e in ev if e[0]=="arc"]),
                end_laser=B["end_laser"],end_power=B["end_power"],min_x=round(B["minx"],3))
if __name__=="__main__":
    print(json.dumps(compare(sys.argv[1],sys.argv[2],cmd=sys.argv[3] if len(sys.argv)>3 else "LASER_PWM"),indent=1))
