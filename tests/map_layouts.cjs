const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process');
const c=vm.createContext({});vm.runInContext(fs.readFileSync('web/map-geometry.js','utf8').replaceAll('export function','function'),c);
const records=JSON.parse(execFileSync('python',['-c',`import json
from reliefroute.scenario import hourly_scenario
from reliefroute.engine import Engine
from reliefroute.bots import BOTS
from reliefroute.server import run_match
records=[run_match({'scenario':['events'],'seed':['11'],'bot':['nearest']})]
for h in range(498380,498383):
 for bot in ['nearest','urgency']:
  r=Engine(hourly_scenario(h)).run(BOTS[bot]);r['league_hour']=h;records.append(r)
print(json.dumps(records))`],{encoding:'utf8',maxBuffer:32*1024*1024}));
let cases=0;
for(const record of records){
 const original=JSON.stringify(record), layouts=new Set();
 for(const environment of ['city','river','mountain'])for(let variant=0;variant<3;variant++){
  const layout=c.createMapLayout(record,{environment,variant}),g=c.createGeometry(record,layout.positions,environment),state=record.log[0].state;
  layouts.add(JSON.stringify(layout.positions));
  const sites=Object.values(layout.positions);
  if(environment==='river')for(const [x,y] of sites)assert.ok(!c.inRiver(x,y,variant,55),'Facility overlaps river');
  for(let i=0;i<sites.length;i++)for(let j=i+1;j<sites.length;j++)assert.ok(Math.abs(sites[i][0]-sites[j][0])>=148||Math.abs(sites[i][1]-sites[j][1])>=140,`Facility labels overlap: ${environment}/${variant}`);
  for(const road of state.roads){const points=g.roadPoints(road);assert.equal(JSON.stringify(points[0]),JSON.stringify(layout.positions[road.from]));assert.equal(JSON.stringify(points.at(-1)),JSON.stringify(layout.positions[road.to]));
   for(const p of points){assert.ok(p.every(Number.isFinite));assert.ok(p[0]>=0&&p[0]<=layout.width&&p[1]>=0&&p[1]<=layout.height);
    for(const [id,q] of Object.entries(layout.positions))if(id!==road.from&&id!==road.to)assert.ok(Math.abs(p[0]-q[0])>50||Math.abs(p[1]-q[1])>50,`Road through facility ${environment}/${variant}/${road.id}/${id}`);
   }
  }
  for(let i=0;i<record.log.length;i++)for(const v of record.log[i].state.vehicles){for(const f of [0,.25,.5,.75,1]){const p=g.vehiclePose(i,v.id,f);assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y)&&Number.isFinite(p.angle));}
   if(i+1<record.log.length){const a=g.vehiclePose(i,v.id,1),b=g.vehiclePose(i+1,v.id,0);assert.ok(Math.hypot(a.x-b.x,a.y-b.y)<1e-6);}cases++;
  }
 }
 assert.equal(layouts.size,9);assert.equal(JSON.stringify(record),original,'Rendering changed simulation');
 const shuffled=JSON.parse(original);shuffled.log[0].state.roads.reverse();shuffled.log[0].state.shelters.reverse();shuffled.bot_id='different-bot';shuffled.score={total:0};
 assert.equal(JSON.stringify(c.createMapLayout(shuffled)),JSON.stringify(c.createMapLayout(record)));
}
for(let i=1;i<records.length;i+=2)assert.equal(JSON.stringify(c.createMapLayout(records[i])),JSON.stringify(c.createMapLayout(records[i+1])),'Different Bots get different maps');
const choices=new Set();for(let hour=498000;hour<498100;hour++){const r={...records[1],league_hour:hour};choices.add(c.createMapLayout(r).id);}assert.equal(choices.size,9);
console.log(`PASS: ${cases} vehicle frames in nine layouts; stable hours/Bots, label separation, road endpoints and facility avoidance`);

for(const record of records){for(let frame=0;frame<record.log.length;frame++){
 const status=c.mapStatus(record,frame),row=record.log[frame];assert.equal(status.closed,row.state.roads.filter(r=>!r.is_open).length);
 assert.equal(status.spikes,row.events.filter(e=>e.type==='demand_spike').map(e=>e.payload.shelter_id).join(', ')||'—');
 assert.equal(JSON.stringify(status),JSON.stringify(c.mapStatus(record,frame)),'Seeking changed event status');
}}
console.log('PASS: snapshot-driven incident reconstruction');
