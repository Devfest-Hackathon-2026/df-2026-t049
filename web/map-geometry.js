const geometryCache = new Map();
// Geometry shared by arena and league. Positions describe presentation only.
export function createGeometry(record, positions, environment = 'city') {
  const match = record;
const cacheKey=JSON.stringify([positions,environment,record.log[0].state.roads.map(r=>[r.id,r.from,r.to]).sort()]);
const paths=geometryCache.get(cacheKey)||new Map();
geometryCache.set(cacheKey,paths);
if(geometryCache.size>64)geometryCache.delete(geometryCache.keys().next().value);
function roadPoints(road) {
  if (!paths.size) for(const edge of [...match.log[0].state.roads].sort((a,b)=>a.id.localeCompare(b.id))) paths.set(edge.id,routeRoad(edge,positions,environment,[...paths.values()]));
  return paths.get(road.id);
}
function pathPoint(points,progress) {
  const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
  let distance=Math.max(0,Math.min(1,progress))*lengths.reduce((a,b)=>a+b,0);
  for(let i=0;i<lengths.length;i++) {
    if(distance<=lengths[i] || i===lengths.length-1) {
      const u=distance/lengths[i],a=points[i],b=points[i+1];
      return {x:a[0]+(b[0]-a[0])*u,y:a[1]+(b[1]-a[1])*u,angle:Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI};
    } distance-=lengths[i];
  }
}
function vehicleLocation(index,id) {
  const v=match.log[index].state.vehicles.find(v=>v.id===id);
  if(!v.edge) return {node:v.node_id,progress:0};
  let first=index;
  while(first>0) {
    const prior=match.log[first-1].state.vehicles.find(v=>v.id===id);
    if(!prior.edge || prior.edge.road_id!==v.edge.road_id || prior.edge.to!==v.edge.to || prior.node_id!==v.node_id) break;
    first--;
  }
  const initial=match.log[first].state.vehicles.find(v=>v.id===id).edge.remaining+1;
  return {node:v.node_id,edge:v.edge.road_id,to:v.edge.to,progress:1-v.edge.remaining/initial};
}
function vehiclePose(index,id,part) {
  const a=vehicleLocation(index,id),b=index+1<match.log.length?vehicleLocation(index+1,id):a;
  let edge=a.edge||b.edge,from=a.node,p=a.progress,q=a.edge?(b.edge===a.edge?b.progress:1):b.progress;
  if(!edge && a.node!==b.node) {edge=match.log[index].state.roads.find(r=>(r.from===a.node&&r.to===b.node)||(r.to===a.node&&r.from===b.node))?.id;q=1;}
  if(!edge) return {x:positions[a.node][0],y:positions[a.node][1],angle:0,parked:true};
  const road=match.log[index].state.roads.find(r=>r.id===edge);
  const direction=road.from===from;
  const progress=p+(q-p)*part,point=pathPoint(roadPoints(road),direction?progress:1-progress);
  point.angle+=direction?0:180;point.progress=progress;return point;
}

return {roadPoints, pathPoint, vehicleLocation, vehiclePose};
}
// Versioned presentation layouts. Never alter edges, travel_turns or simulation state.
const ENVIRONMENTS = ['city', 'river', 'mountain'];
const SITES = {
 city: [
  [[130,90],[440,90],[750,90],[130,250],[750,250],[300,395],[600,395]],
  [[750,395],[440,395],[130,395],[750,230],[130,230],[290,75],[610,75]],
  [[130,240],[310,75],[580,75],[750,240],[580,395],[310,395],[440,235]]
 ],
 river: [
  [[135,85],[290,245],[135,395],[720,85],[590,245],[735,395],[285,85]],
  [[140,80],[440,80],[740,80],[140,370],[440,370],[740,370],[290,370]],
  [[125,90],[440,85],[125,260],[740,230],[470,395],[740,395],[320,395]]
 ],
 mountain: [
  [[125,380],[175,80],[350,225],[440,390],[555,75],[740,220],[740,390]],
  [[750,85],[520,85],[310,230],[130,80],[130,385],[520,385],[750,260]],
  [[130,85],[365,100],[690,80],[750,260],[535,250],[330,390],[130,300]]
 ]
};
function stableHash(value) {
 let hash=2166136261;
 for(const c of String(value)) hash=Math.imul(hash^c.charCodeAt(0),16777619);
 return hash>>>0;
}
export function mapIdentity(record) {
 const state=record.log[0].state;
 const topology=state.roads.map(r=>[r.id,...[r.from,r.to].sort()].join(':')).sort().join('|');
 // Scores, Bot IDs, mutable road states and browser locale are deliberately excluded.
 return String(record.league_hour ?? record.scenario_id ?? record.seed ?? '')+'|'+topology;
}
export function createMapLayout(record, options={}) {
 const state=record.log[0].state, key=mapIdentity(record), hash=stableHash(key);
 const environment=ENVIRONMENTS.includes(options.environment)?options.environment:ENVIRONMENTS[hash%3];
 const variant=Number.isInteger(options.variant)?((options.variant%3)+3)%3:Math.floor(hash/3)%3;
 const ids=[state.depot.node_id,...new Set([...state.shelters.map(s=>s.node_id),...state.roads.flatMap(r=>[r.from,r.to])].filter(id=>id!==state.depot.node_id).sort())];
 const sites=SITES[environment][variant], positions={};
 // Four-node arena uses widely separated sites; league uses all seven, with no central depot.
 const subset=ids.length<=4?([0,2,3,5].map(i=>sites[i])):sites;
 ids.forEach((id,i)=>{positions[id]=ids.length>7?[90+(i%5)*170,80+Math.floor(i/5)*170]:[...subset[i]];});
 return {id:`visual-v1-${environment}-${variant+1}`,environment,variant,positions,key,
   width:Math.max(880,...Object.values(positions).map(p=>p[0]+90)),height:Math.max(500,...Object.values(positions).map(p=>p[1]+100))};
}
export function layoutNodes(state) {return createMapLayout({log:[{state}]},{environment:'city',variant:0}).positions;}
// River center line is shared by terrain, bridge clipping and decoration exclusion.
export function riverX(y, variant=0) {return variant===2?210+y*.92:440+28*Math.sin(y/95);}
export function inRiver(x,y,variant=0,margin=0) {
 return variant===1?Math.abs(y-(225+18*Math.sin(x/130)))<27+margin:Math.abs(x-riverX(y,variant))<27+margin;
}
function routeRoad(road, positions, environment, used=[]) {
 const a=positions[road.from],b=positions[road.to];
 const obstacles=Object.entries(positions).filter(([id])=>id!==road.from&&id!==road.to).map(([,p])=>({x:p[0]-70,y:p[1]-65,w:140,h:130}));
 obstacles.push(...[a,b].map(p=>({x:p[0]-46,y:p[1]-50,w:92,h:36})));
 const inside=(x,y,o)=>x>o.x&&x<o.x+o.w&&y>o.y&&y<o.y+o.h;
 const xs=[...new Set([a[0],b[0],45,835,220,440,660,...obstacles.flatMap(o=>[o.x-12,o.x+o.w+12])])].sort((x,y)=>x-y);
 const ys=[...new Set([a[1],b[1],35,450,180,310,...obstacles.flatMap(o=>[o.y-12,o.y+o.h+12])].filter(y=>y>=25&&y<=460))].sort((x,y)=>x-y);
 const points=[];
 for(const x of xs)for(const y of ys)if(!obstacles.some(o=>inside(x,y,o)))points.push([x,y]);
 const start=points.findIndex(p=>p[0]===a[0]&&p[1]===a[1]),end=points.findIndex(p=>p[0]===b[0]&&p[1]===b[1]);
 const distance=points.map(()=>Infinity),previous=points.map(()=>-1),done=new Set();distance[start]=0;
 const clear=(p,q)=>!obstacles.some(o=>p[0]===q[0]?p[0]>o.x&&p[0]<o.x+o.w&&Math.max(p[1],q[1])>o.y&&Math.min(p[1],q[1])<o.y+o.h:p[1]>o.y&&p[1]<o.y+o.h&&Math.max(p[0],q[0])>o.x&&Math.min(p[0],q[0])<o.x+o.w);
 while(done.size<points.length){let u=-1;for(let i=0;i<points.length;i++)if(!done.has(i)&&(u<0||distance[i]<distance[u]))u=i;
  if(u<0||!Number.isFinite(distance[u])||u===end)break;done.add(u);
  for(let v=0;v<points.length;v++)if(!done.has(v)&&(points[u][0]===points[v][0]||points[u][1]===points[v][1])&&clear(points[u],points[v])){
   const p=points[u],q=points[v],length=Math.hypot(p[0]-q[0],p[1]-q[1]);
   const reuse=used.reduce((n,path)=>n+path.filter(r=>p[0]===q[0]?Math.abs(r[0]-p[0])<23&&r[1]>Math.min(p[1],q[1])&&r[1]<Math.max(p[1],q[1]):Math.abs(r[1]-p[1])<23&&r[0]>Math.min(p[0],q[0])&&r[0]<Math.max(p[0],q[0])).length,0);
   const cost=distance[u]+length+reuse*18+4;
   if(cost<distance[v]){distance[v]=cost;previous[v]=u;}
  }
 }
 let route=[];for(let at=end;at>=0;at=previous[at])route.unshift(points[at]);
 if(route.length<2)route=[a,b];
 route=route.filter((p,i,all)=>!i||i===all.length-1||(p[0]-all[i-1][0])*(all[i+1][1]-p[1])!==(p[1]-all[i-1][1])*(all[i+1][0]-p[0]));
 // Round bends on the same route. Sampling is shared by roads, vehicles and bridges.
 const result=[route[0]],radius=environment==='city'?10:environment==='river'?22:36;
 for(let i=1;i<route.length-1;i++){
  const p=route[i-1],q=route[i],r=route[i+1],l1=Math.hypot(q[0]-p[0],q[1]-p[1]),l2=Math.hypot(r[0]-q[0],r[1]-q[1]),d=Math.min(radius,l1/3,l2/3);
  const before=[q[0]+(p[0]-q[0])*d/l1,q[1]+(p[1]-q[1])*d/l1],after=[q[0]+(r[0]-q[0])*d/l2,q[1]+(r[1]-q[1])*d/l2];
  result.push(before);for(let j=1;j<=12;j++){const t=j/12;result.push([(1-t)**2*before[0]+2*(1-t)*t*q[0]+t*t*after[0],(1-t)**2*before[1]+2*(1-t)*t*q[1]+t*t*after[1]]);}
 }
 result.push(route.at(-1));
 // Densify straight segments too: terrain exclusion must inspect the full road.
 return result.flatMap((p,i)=>{if(!i)return [p];const q=result[i-1],n=Math.max(1,Math.ceil(Math.hypot(p[0]-q[0],p[1]-q[1])/8));const candidates=Array.from({length:n},(_,j)=>{const t=(j+1)/n,dx=p[0]-q[0],dy=p[1]-q[1],len=Math.hypot(dx,dy),wave=environment==='mountain'&&len>180?Math.sin(Math.PI*t)**2*Math.sin(2*Math.PI*t)*Math.min(12,len/15):0;return [q[0]+dx*t-dy/len*wave,q[1]+dy*t+dx/len*wave];});
   return candidates.some(c=>obstacles.some(o=>inside(c[0],c[1],o)))?Array.from({length:n},(_,j)=>[q[0]+(p[0]-q[0])*(j+1)/n,q[1]+(p[1]-q[1])*(j+1)/n]):candidates;});
}

export function mapStatus(record,frame) {
 const row=record.log[frame],base=record.log[0].state.roads;
 return {closed:row.state.roads.filter(r=>!r.is_open).length,congested:row.state.roads.filter(r=>r.is_open&&r.travel_turns>base.find(b=>b.id===r.id).travel_turns).length,
  spikes:row.events.filter(e=>e.type==='demand_spike').map(e=>e.payload.shelter_id).join(', ')||'—'};
}
