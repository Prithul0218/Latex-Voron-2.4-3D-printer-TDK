set -e
BASE='"power":60,"dutyCap":1,"prefDir":0,"perpTol":10,"minRun":1,"defWidth":0.6,"pwmCmd":"LASER_PWM","armCmd":"LASER_ARM","disarmCmd":"LASER_DISARM","zhop":1,"travelF":9000,"primeE":40,"purgeLen":50,"purgeX":50,"purgeY":320,"xMin":50'
run() { # label settings-extra
  node runjs.js ../latex-laser-postprocessor.html "{$BASE,$2}" in_dogbone.gcode in_dogbone_seed2.gcode in_zigzag_split.gcode in_dogbone_noarm.gcode in_dogbone_plain.gcode
  for f in in_dogbone in_dogbone_seed2 in_zigzag_split in_dogbone_noarm in_dogbone_plain; do
    python3 verify.py $f.gcode out_$f.gcode | python3 -c "
import json,sys; d=json.load(sys.stdin)
ok = d['missing']==0 and d['extra']==0 and d['against']==0 and d['laser_off_beads']==0 and d['beads_unpowered']==0 and abs(d['E_in']-d['E_out'])<1e-3 and d['arm_count']==1 and d['disarm_count']==1 and d['legacy_LASER_ON']==0 and d['pwm_on_outside_arm_window']==0 and not d['zmove_with_laser'] and d['end_laser']==0 and d['end_power']==False and d['min_x']>=50
print(('PASS' if ok else 'FAIL'), '$1', '$f'.ljust(18), 'beads %d/%d missing %d extra %d against %d | E %.3f/%.3f prime %.2f | arm %d disarm %d | minX %.1f' % (d['beads_out'],d['beads_in'],d['missing'],d['extra'],d['against'],d['E_in'],d['E_out'],d['prime_E'],d['arm_count'],d['disarm_count'],d['min_x']))
if not ok: print('   ', {k:v for k,v in d.items() if k not in ('missing_ex','extra_ex')}, d['missing_ex'], d['extra_ex'])"
  done
}
run "overrun1 prime" '"overrun":1,"retract":false,"prime":true,"addPower":true'
run "overrun10 prime" '"overrun":10,"retract":false,"prime":true,"addPower":true'
run "no-prime retract" '"overrun":1,"retract":true,"prime":false,"addPower":true'
