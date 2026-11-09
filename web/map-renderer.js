import {createGeometry, inRiver, riverX} from './map-geometry.js';
export function createMapRenderer(root, translate, onSelect=()=>{}, detailPanel=null) {
const t=translate, NS='http://www.w3.org/2000/svg';
const $=selector=>selector==='#map'?root:root.querySelector(selector);
let match,positions,environment,frame,fraction,selected,layout,geometry,geometryKey;
function element(tag,attrs={},text){const node=document.createElementNS(NS,tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);if(text!==undefined)node.textContent=text;return node;}
function roadPoints(r){return geometry.roadPoints(r);}
function pathPoint(p,u){return geometry.pathPoint(p,u);}
function vehiclePose(i,id,u){return geometry.vehiclePose(i,id,u);}
function choose(id,keyboard=false){selected=id;onSelect(id);if(keyboard){const target=[...root.querySelectorAll('[data-map-target]')].find(n=>n.getAttribute('data-map-target')===id);target?.focus({preventScroll:true});}}
function renderMap(snapshot) {
  drawCity(snapshot);
  const roads=$('#roads'); roads.replaceChildren();const badges=[];
  const occupied=Object.values(positions).map(([x,y])=>({x:x-78,y:y-62,w:156,h:155}));
  for(const road of snapshot.roads) {
    const base=match.log[0].state.roads.find(r=>r.id===road.id).travel_turns;
    const kind=!road.is_open?'closed':road.travel_turns>base?'congested':'open';
    const points=roadPoints(road), d=points.map((p,i)=>`${i?'L':'M'}${p[0]} ${p[1]}`).join(' ');
    for(const cls of ['street-sidewalk','street-asphalt','street-centre']) roads.append(element('path',{d,class:cls,style:cls==='street-asphalt'?`stroke:${snapshot.roads.indexOf(road)%2?'#6b7c82':'#596d76'}`:''}));
    if(environment==='river'){
      // Each bridge is a clipped portion of an existing road, never a new edge.
      let segment=[];const segments=[];
      for(const p of points){if(inRiver(p[0],p[1],layout?.variant,5))segment.push(p);else if(segment.length){segments.push(segment);segment=[];}}
      if(segment.length)segments.push(segment);
      for(const crossing of segments)if(crossing.length>1){const d=crossing.map((p,i)=>`${i?'L':'M'}${p[0]} ${p[1]}`).join(' ');
        roads.append(element('path',{d,fill:'none',stroke:'#ece5d5','stroke-width':47}),element('path',{d,fill:'none',stroke:'#677983','stroke-width':39}),element('path',{d,fill:'none',stroke:'#eee2a8','stroke-width':1.5,'stroke-dasharray':'8 8'}));
        for(const side of [-1,1]){const rail=crossing.map((p,i)=>{const a=crossing[Math.max(0,i-1)],b=crossing[Math.min(crossing.length-1,i+1)],length=Math.hypot(b[0]-a[0],b[1]-a[1])||1;return [p[0]-(b[1]-a[1])/length*side*21,p[1]+(b[0]-a[0])/length*side*21];});roads.append(element('path',{d:rail.map((p,i)=>`${i?'L':'M'}${p[0]} ${p[1]}`).join(' '),fill:'none',stroke:'#846f51','stroke-width':2}));for(const p of [rail[0],rail.at(-1)])roads.append(element('circle',{cx:p[0],cy:p[1],r:3,fill:'#e9dfc7',stroke:'#846f51'}));}}
    }
    // Crosswalk markings are visual details on existing roads only.
    for(const u of [.20,.80]) {
      const at=pathPoint(points,u),crossing=element('g',{transform:`translate(${at.x} ${at.y}) rotate(${at.angle})`,'aria-hidden':'true'});
      for(let stripe=-15;stripe<=15;stripe+=6) crossing.append(element('rect',{x:-3,y:stripe,width:6,height:3,fill:'#e7e7da',opacity:.7}));
      roads.append(crossing);
    }
    if(selected===road.id)roads.append(element('path',{d,class:'road-selection'}));
    const hit=element('path',{d,class:'road-inspect','data-road':road.id,'data-map-target':road.id,tabindex:0,role:'button','aria-pressed':String(selected===road.id),'aria-label':`${road.id}: ${road.from} ↔ ${road.to} · ${t(kind)}`});hit.append(element('title',{},`${road.id}: ${road.from} ↔ ${road.to}`));hit.onclick=()=>choose(road.id);hit.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(road.id,true);}};roads.append(hit);
    if(kind!=='open') roads.append(element('path',{d,class:`street-impact ${kind}`}));
    const mid=pathPoint(points,road.id==='R4'?.72:.5);
    let label=mid, visible=true;
    {
      visible=false;
      for(const u of [.5,.35,.65,.25,.75]){const q=pathPoint(points,u),box={x:q.x-41,y:q.y-39,w:82,h:26};
        if(!occupied.some(b=>box.x<b.x+b.w&&box.x+box.w>b.x&&box.y<b.y+b.h&&box.y+box.h>b.y)){label=q;occupied.push(box);visible=true;break;}}
    }
    const badge=element('g',{transform:`translate(${Math.max(42,Math.min(838,label.x))} ${Math.max(15,label.y-27)})`});
    badge.append(element('rect',{x:-39,y:-11,width:78,height:22,rx:5,class:'street-badge'}),element('text',{'text-anchor':'middle',y:4,class:'street-text'},kind==='open'?`${road.id} · ${t('roadTurns',{count:road.travel_turns})}`:t(kind)));
    badge.append(element('title',{},`${road.id}: ${t('roadTurns',{count:road.travel_turns})}`)); if(visible&&(kind!=='open'||selected===road.id))badges.push(badge);
    if(kind==='closed') {
      const barrier=element('g',{transform:`translate(${mid.x} ${mid.y}) rotate(${mid.angle+90})`,class:'closure-barrier'});
      barrier.append(element('rect',{x:-20,y:-5,width:40,height:10,rx:2,fill:'#fff1df',stroke:'#a64935','stroke-width':2}));
      for(let x=-16;x<18;x+=10) barrier.append(element('path',{d:`M${x} -4 l6 8`,stroke:'#ce6247','stroke-width':4}));
      roads.append(barrier);
    }
    if(kind==='congested') for(let k=0;k<4;k++) {
      const at=pathPoint(points,.37+k*.055);
      const car=element('g',{transform:`translate(${at.x} ${at.y}) rotate(${at.angle})`,'aria-label':t('queueSymbol')});
      car.append(element('title',{},t('queueSymbol')),element('rect',{x:-6,y:-19,width:12,height:7,rx:2,fill:'#c28c51',stroke:'#fff0cc'})); roads.append(car);
    }
  }
  roads.append(...badges);
  const nodes=$('#nodes'); nodes.replaceChildren();
  for(const point of [snapshot.depot,...snapshot.shelters]) {
    const [x,y]=positions[point.node_id], depot=point.id===snapshot.depot.id;
    const remaining=depot?0:point.batches.reduce((n,b)=>n+b.amount-b.received,0);
    const overdue=!depot && point.batches.some(b=>b.amount>b.received && b.due_turn<frame);
    const g=element('g',{transform:`translate(${x} ${y})`,class:`facility ${selected===point.id?'selected':''}`,tabindex:0,role:'button','data-map-target':point.id,'aria-label':depot?`${point.id}: ${t('depotAria',{count:point.stock})}`:t('viewShelter',{name:t(point.id)})});
    g.append(element('rect',{x:-49,y:-49,width:98,height:98,rx:12,class:'facility-yard'}));
    // The node is a loading apron, with the building above it.
    g.append(element('rect',{x:-37,y:-44,width:74,height:29,rx:3,fill:depot?'#9caeb7':'#d5bca0',stroke:'#607681','stroke-width':2}));
    for(let k=-28;k<32;k+=14) g.append(element('path',{d:`M${k} -41 V-18`,stroke:depot?'#dde5e8':'#eedfce','stroke-width':3}));
    g.append(element('rect',{x:-12,y:-40,width:24,height:20,rx:2,fill:depot?'#274d67':'#1b7f89'}),element('text',{x:0,y:-26,'text-anchor':'middle',fill:'#fff','font-size':11,'font-weight':700},point.id));
    for(let k=-30;k<=30;k+=30) g.append(element('path',{d:`M${k-10} -6 v22 h20 v-22`,fill:'none',stroke:'#aab7b8','stroke-width':1}));
    g.append(element('rect',{x:-74,y:51,width:148,height:38,rx:5,class:'facility-label'}),element('text',{y:66,'text-anchor':'middle',class:'facility-name'},point.id),element('text',{y:81,'text-anchor':'middle',class:'facility-detail',fill:overdue?'#ffb6a4':remaining?'#f2ce8c':'#90e3cb'},depot?t('stockMeta',{count:point.stock}):remaining?t('remaining',{count:remaining}):t('satisfied')));
    if(!depot) {
      g.append(element('title',{},t('demandSymbols')));
      for(let k=0;k<Math.min(8,Math.ceil(remaining/5));k++) {
        g.append(element('circle',{cx:53+(k%2)*8,cy:-30+Math.floor(k/2)*12,r:2.5,fill:overdue?'#c15d48':'#5b6874'}),element('path',{d:`M${53+(k%2)*8} ${-26+Math.floor(k/2)*12} v5`,stroke:overdue?'#c15d48':'#5b6874','stroke-width':3}));
      }
      const delivery=match.log[frame].deliveries.filter(d=>d.shelter_id===point.id).reduce((n,d)=>n+d.quantity,0);
      const spike=match.log[frame].events.find(e=>e.type==='demand_spike'&&e.payload.shelter_id===point.id);
      if(spike)g.append(element('rect',{x:-50,y:-50,width:100,height:100,rx:13,class:'demand-alert'}));
      if(delivery || spike) g.append(element('text',{y:-58,'text-anchor':'middle',class:'facility-feedback'},delivery?t('deliveredBadge',{count:delivery}):t('demandBadge',{count:spike.payload.amount})));
    }
    g.setAttribute('aria-pressed',String(selected===point.id));g.onclick=()=>choose(point.id);
    g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(point.id,true);}};nodes.append(g);
  }
  renderVehicles();
  if(detailPanel){detailPanel.replaceChildren();for(const line of selectionDetails(match,frame,selected,t)){const p=document.createElement('p');p.textContent=line;detailPanel.append(p);}}
}
function renderVehicles() {
  if(!match) return;
  const layer=$('#vehicles');
  const currentIds=match.log[frame].state.vehicles.map(v=>v.id).join(',');
  if(layer.dataset.ids!==currentIds){layer.replaceChildren();layer.dataset.ids=currentIds;}
  const part=window.matchMedia('(prefers-reduced-motion: reduce)').matches?0:fraction;
  match.log[frame].state.vehicles.forEach((v,i)=>{
    const pose=vehiclePose(frame,v.id,part);
    // Parallel display lanes remain within the road width and preserve progress.
    const lane=(i-(match.log[frame].state.vehicles.length-1)/2)*Math.min(12,24/Math.max(1,match.log[frame].state.vehicles.length-1)),rad=pose.angle*Math.PI/180;
    const blend=pose.parked?0:Math.sin(Math.PI*pose.progress);
    const count=match.log[frame].state.vehicles.length,parkX=count>3?[-30,0,30,-15,15][i%5]:(i-(count-1)/2)*30,parkY=count>3&&i%5>2?29:5;
    const x=pose.x-Math.sin(rad)*lane*blend+parkX*(1-blend),y=pose.y+Math.cos(rad)*lane*blend+parkY*(1-blend);
    let g=layer.children[i];
    const labelY=blend>.2&&count>3?-17-(i%3)*18:count>3&&i%5>2?13:-12;
    if(g){g.lastChild.setAttribute('y',labelY);g.children[2].setAttribute('y',labelY-11);}
    if(g){g.setAttribute('transform',`translate(${x} ${y})`);g.setAttribute('class',`rescue-truck ${v.status} ${selected===v.id?'selected':''}`);g.setAttribute('aria-pressed',String(selected===v.id));g.setAttribute('aria-label',t('vehicleAria',{id:v.id,status:t(v.status),cargo:v.cargo}));g.children[1].setAttribute('transform',`rotate(${pose.angle})`);g.firstChild.textContent=t('vehicleAria',{id:v.id,status:t(v.status),cargo:v.cargo});return;}
    g=element('g',{class:`rescue-truck ${v.status} ${selected===v.id?'selected':''}`,tabindex:0,role:'button','aria-pressed':String(selected===v.id),'aria-label':t('vehicleAria',{id:v.id,status:t(v.status),cargo:v.cargo}),transform:`translate(${x} ${y})`,'data-vehicle':v.id,'data-map-target':v.id});
    g.append(element('title',{},t('vehicleAria',{id:v.id,status:t(v.status),cargo:v.cargo})));
    const body=element('g',{transform:`rotate(${pose.angle})`});
    body.append(element('rect',{x:-13,y:-7,width:28,height:14,rx:3,fill:'#f4f3e9',stroke:'#183543','stroke-width':1.5}),element('rect',{x:7,y:-5,width:6,height:10,rx:1,fill:'#456d84'}),element('rect',{x:-12,y:-6,width:17,height:12,rx:1,fill:['#c3e9e5','#c9ddf4','#f5dfb8'][i%3]}),element('path',{d:'M-5 -4 V4 M-9 0 H-1',stroke:'#167c83','stroke-width':2}),element('path',{d:'M-8 -8 h6 M-8 8 h6 M9 -8 h4 M9 8 h4',stroke:'#122631','stroke-width':3}));
    g.onclick=()=>choose(v.id);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(v.id,true);}};
    g.append(body,element('rect',{x:-12,y:labelY-11,width:24,height:15,rx:3,class:'vehicle-tag','data-vehicle-label':v.id}),element('text',{x:0,y:labelY,'text-anchor':'middle',class:'vehicle-label'},v.id));layer.append(g);
  });
}
function drawCity(snapshot) {
  if($('#city')) return;
  const map=$('#map'); map.querySelector('.terrain')?.remove();
  const city=element('g',{id:'city','aria-hidden':'true'});map.insertBefore(city,$('#roads'));
  city.append(element('rect',{width:880,height:500,fill:environment==='mountain'?'#b5c5ae':environment==='river'?'#c4d4cf':'#d7dad2'}));
  if(environment==='river'){const pts=Array.from({length:111},(_,i)=>layout?.variant===1?[i*8,225+18*Math.sin(i*8/130)]:[riverX(i*5,layout?.variant),i*5]);const d=pts.map((p,i)=>`${i?'L':'M'}${p[0]} ${p[1]}`).join(' ');for(const [stroke,width] of [['#9aafa0',74],['#719fab',54],['#a2c9cf',42]])city.append(element('path',{d,fill:'none',stroke,'stroke-width':width}));}
  if(environment==='mountain') for(let i=0;i<9;i++) city.append(element('path',{d:`M-30 ${15+i*13} Q${220+(layout?.variant||0)*110} ${80+i*14} 460 ${20+i*15} T920 ${70+i*17}`,fill:'none',stroke:'#8da582','stroke-width':2}));
  const samples=snapshot.roads.flatMap(roadPoints);
  for(let row=0;row<9;row++) for(let col=0;col<16;col++) {
    const n=row*17+col,x=25+col*54+(row%2)*9,y=40+row*49;
    if(Object.values(positions).some(p=>Math.hypot(x-p[0],y-p[1])<100)||samples.some(p=>Math.hypot(x-p[0],y-p[1])<45))continue;
    if(environment==='river'&&inRiver(x,y,layout?.variant,35))continue;
    const tree=environment==='mountain'?n%4!==0:n%5===0;
    if(tree) {for(let j=0;j<3;j++) city.append(element('circle',{cx:x+j*7-7,cy:y+(j%2)*8,r:8,fill:['#769374','#648966','#87a082'][j],stroke:'#577b60','stroke-width':1}));continue;}
    const w=22+n%4*5,h=18+n%3*5,c=['#b5b1a7','#a8bac2','#c7b29b','#a4adb0'][n%4];
    const g=element('g',{transform:`translate(${x} ${y})`});
    g.append(element('rect',{x:-w/2+3,y:-h/2+4,width:w,height:h,rx:2,fill:'#6c7e7633'}),element('rect',{x:-w/2,y:-h/2,width:w,height:h,rx:2,fill:c,stroke:'#81908c','stroke-width':1.5}),element('path',{d:`M${-w/2+3} 0 H${w/2-3}`,stroke:'#e5e5dc','stroke-width':2}));
    if(n%3===0)g.append(element('rect',{x:-6,y:-h/2+3,width:10,height:7,fill:'#6d8998'}));
    if(n%3===1)g.append(element('rect',{x:3,y:-3,width:7,height:8,fill:'#d9d8c9',stroke:'#89948f'}));city.append(g);
  }
}

return {render(options){({match,positions,environment,frame,fraction,selected,layout}=options);const key=JSON.stringify([positions,environment,layout?.id,match.log[0].state.roads]);if(geometryKey!==key){geometryKey=key;$('#city')?.remove();}geometry=createGeometry(match,positions,environment);root.setAttribute('viewBox',`0 0 ${layout?.width||880} ${layout?.height||500}`);renderMap(match.log[frame].state);},vehicles(options){({frame,fraction}=options);renderVehicles();}};
}

// Pure inspection model: display only recorded values, never infer a new dispatch.
export function selectionDetails(record,frame,id,t) {
 const state=record.log[frame].state,header=t('mapSelection',{turn:frame});
 const vehicle=state.vehicles.find(v=>v.id===id);
 if(vehicle)return [header,`${vehicle.id} · ${t(vehicle.status)}`,`${t('cargo')}: ${vehicle.cargo}/${vehicle.capacity}`,`${t('destination')}: ${vehicle.leg==='returning'?state.depot.id:vehicle.target||'—'}`,vehicle.edge?`${t('currentRoad')}: ${vehicle.edge.road_id} · ${t('remainingTravel',{count:vehicle.edge.remaining})}`:t('noRoute')];
 const road=state.roads.find(r=>r.id===id);
 if(road){const base=record.log[0].state.roads.find(r=>r.id===id);return [header,`${road.id} · ${road.from} ↔ ${road.to}`,t(!road.is_open?'closed':road.travel_turns>base.travel_turns?'congested':'open'),t('roadTurns',{count:road.travel_turns})];}
 const shelter=state.shelters.find(s=>s.id===id);
 if(shelter){const total=shelter.batches.reduce((n,b)=>n+b.amount,0),received=shelter.batches.reduce((n,b)=>n+b.received,0);return [header,t('shelterLabel',{id:shelter.id}),t('demandTotal',{total,received}),t('remaining',{count:total-received})];}
 if(id===state.depot.id)return [header,t('depotLabel',{id:state.depot.id}),t('stockMeta',{count:state.depot.stock})];
 return [t('inspectMap')];
}
