const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Node {
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.dataset={};this.textContent='';}
 setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k];}
 append(...nodes){for(const n of nodes){n.parent=this;this.children.push(n);}}
 replaceChildren(...nodes){this.children=[];this.append(...nodes);}
 insertBefore(n,b){n.parent=this;this.children.splice(this.children.indexOf(b),0,n);}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this);}
 querySelector(selector){if(selector[0]!=='#')return null;return find(this,n=>n.attrs.id===selector.slice(1));}
 querySelectorAll(){const result=[];const visit=n=>{if(n.attrs['data-map-target'])result.push(n);n.children.forEach(visit);};visit(this);return result;}
 focus(){this.focused=true;}
 get firstChild(){return this.children[0];}get lastChild(){return this.children.at(-1);}
}
function find(node,predicate){if(predicate(node))return node;for(const child of node.children){const result=find(child,predicate);if(result)return result;}return null;}
const root=new Node('svg');for(const id of ['roads','nodes','vehicles']){const n=new Node('g');n.setAttribute('id',id);root.append(n);}const panel=new Node('div');
const context=vm.createContext({document:{createElement:tag=>new Node(tag),createElementNS:(_,tag)=>new Node(tag)},window:{matchMedia:()=>({matches:false})},localStorage:{getItem:()=>null,setItem(){}},Intl,Date});
for(const name of ['i18n','map-geometry','map-renderer'])vm.runInContext(fs.readFileSync(`web/${name}.js`,'utf8').replace(/^import .*;\r?\n/gm,'').replaceAll('export function','function'),context);
const state={depot:{id:'D1',node_id:'N0',stock:30},shelters:[{id:'S1',node_id:'N1',batches:[{amount:20,received:5,due_turn:8}]}],roads:[{id:'R1',from:'N0',to:'N1',travel_turns:2,is_open:true}],vehicles:[{id:'V1',node_id:'N0',status:'delivering',cargo:10,capacity:12,target:'S1',edge:{road_id:'R1',to:'N1',remaining:1}}]};
const later=JSON.parse(JSON.stringify(state));later.roads[0].is_open=false;later.vehicles[0].edge=null;later.vehicles[0].node_id='N1';later.vehicles[0].cargo=0;later.vehicles[0].leg='returning';
const record={log:[{state,events:[],deliveries:[]},{state:later,events:[],deliveries:[]}]},before=JSON.stringify(record);
const layout=context.createMapLayout(record,{environment:'city',variant:0});let selected=null,frame=0;
const renderer=context.createMapRenderer(root,context.t,id=>{selected=id;draw();},panel);
function draw(){renderer.render({match:record,...layout,layout,frame,fraction:0,selected});}draw();
find(root,n=>n.attrs['data-road']==='R1').onclick();assert.equal(selected,'R1');assert.ok(panel.children.some(n=>n.textContent.includes('N0 ↔ N1')));
find(root,n=>n.attrs['data-vehicle']==='V1').onkeydown({key:'Enter',preventDefault(){}});assert.equal(selected,'V1');assert.ok(find(root,n=>n.attrs['data-vehicle']==='V1').focused);assert.ok(panel.children.some(n=>n.textContent.includes('10/12')));
const vehicle=()=>find(root,n=>n.attrs['data-vehicle']==='V1');renderer.vehicles({frame:0,fraction:.4});const pose=vehicle().attrs.transform;renderer.vehicles({frame:0,fraction:.4});assert.equal(vehicle().attrs.transform,pose);
root.querySelector('#nodes').children[1].onclick();assert.equal(selected,'S1');assert.ok(panel.children.some(n=>n.textContent.includes('S1')));
frame=1;selected='R1';draw();assert.ok(panel.children.some(n=>n.textContent===context.t('closed')));frame=0;draw();assert.ok(panel.children.some(n=>n.textContent===context.t('open')));
for(const language of ['ja','zh','en']){context.setLocale(language);selected='D1';draw();assert.ok(panel.children.some(n=>n.textContent.includes('D1')));}
assert.equal(JSON.stringify(record),before);console.log('PASS: production SVG road/vehicle/facility clicks, keyboard, inspector, pause, event rollback and IDs');
