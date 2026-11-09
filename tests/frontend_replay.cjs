// Exercise production geometry against actual Python replay records.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const source=fs.readFileSync('web/map-geometry.js','utf8');
const context=vm.createContext({Math});
vm.runInContext(source.replaceAll('export function','function'),context);
const records=JSON.parse(execFileSync(process.env.PYTHON || 'python',['-c',`import json
import itertools
from reliefroute.bots import CONFIG_OPTIONS
from reliefroute.server import run_match
records = [run_match({'scenario':[kind],'seed':[str(seed)],'bot':[bot]}) for kind,seeds in [('fixture',[0]),('events',[11,22,33])] for seed in seeds for bot in ['nearest','urgency']]
for values in itertools.product(*CONFIG_OPTIONS.values()):
 for seed in [11,22,33]:
  params = {'scenario':['events'],'seed':[str(seed)],'bot':['custom']}
  params.update({key:[value] for key,value in zip(CONFIG_OPTIONS, values)})
  records.append(run_match(params))
print(json.dumps(records))`],{encoding:'utf8',maxBuffer:32*1024*1024}));
let checks=0;
for(const record of records) for(const setting of ['city','river','mountain']) {
 context.input=record;context.setting=setting;
 vm.runInContext('var g=createGeometry(input,createMapLayout(input,{environment:setting,variant:0}).positions,setting);var vehiclePose=g.vehiclePose;',context);
 for(let frame=0;frame<record.log.length;frame++) for(const vehicle of record.log[frame].state.vehicles) {
  context.index=frame;context.id=vehicle.id;
  const start=vm.runInContext('vehiclePose(index,id,0)',context);
  assert.ok(Number.isFinite(start.x)&&Number.isFinite(start.y));
  if(frame<record.log.length-1) {
   const end=vm.runInContext('vehiclePose(index,id,1)',context);
   const next=vm.runInContext('vehiclePose(index+1,id,0)',context);
   assert.ok(Math.hypot(end.x-next.x,end.y-next.y)<1e-6,`Discontinuous ${setting}/${frame}/${vehicle.id}`);
   for(const fraction of [.1,.5,.9]) {
    context.part=fraction;
    const pos=vm.runInContext('vehiclePose(index,id,part)',context);
    assert.ok(pos.x>=0&&pos.x<=880&&pos.y>=0&&pos.y<=500);
   }
  }
  checks++;
 }
}
console.log(`PASS: ${checks} vehicle/frame/environment cases across ${records.length} real match records`);
