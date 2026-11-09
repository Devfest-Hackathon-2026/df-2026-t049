const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process');
const c=vm.createContext({});vm.runInContext(fs.readFileSync('web/map-geometry.js','utf8').replaceAll('export function','function'),c);
const records=JSON.parse(execFileSync('python',['-c',`import json
from reliefroute.scenario import hourly_scenario
from reliefroute.engine import Engine
from reliefroute.bots import BOTS
print(json.dumps([Engine(hourly_scenario(h)).run(BOTS[b]) for h in [498380,498381,498382] for b in ['nearest','urgency']]))`],{encoding:'utf8',maxBuffer:32*1024*1024}));
let count=0;for(const record of records){const g=c.createGeometry(record,c.layoutNodes(record.log[0].state));for(let i=0;i<record.log.length;i++)for(const v of record.log[i].state.vehicles){const p=g.vehiclePose(i,v.id,0);assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y));if(i+1<record.log.length){const a=g.vehiclePose(i,v.id,1),b=g.vehiclePose(i+1,v.id,0);assert.ok(Math.hypot(a.x-b.x,a.y-b.y)<1e-6);}count++;}}
console.log('PASS: '+count+' league vehicle frames across three hours and two Bots');
