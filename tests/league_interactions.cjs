const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/league.js','utf8');
(async()=>{const elements={'copy-token':{},'management-token':{value:'test-only-token'},'management-status':{textContent:''}};let writes=0;
const c=vm.createContext({$:id=>elements[id],text:key=>key,navigator:{clipboard:{writeText:async value=>{assert.equal(value,'test-only-token');writes++;}}}});
const copyHandler=source.split(/\r?\n/).find(line=>line.startsWith("$('copy-token').onclick="));
assert.ok(copyHandler,'Production copy handler missing');vm.runInContext(copyHandler,c);
await elements['copy-token'].onclick();assert.equal(writes,1);assert.equal(elements['management-status'].textContent,'copied');
c.navigator.clipboard.writeText=async()=>{throw Error('permission denied');};await elements['copy-token'].onclick();assert.equal(elements['management-status'].textContent,'copyFailed');
elements['management-token'].value='';await elements['copy-token'].onclick();assert.equal(writes,1);
console.log('PASS: production token copy handler success, denied permission and empty value');
})().catch(e=>{console.error(e);process.exitCode=1;});

// Exercise the actual request path: localized validation must not alter payloads.
(async()=>{
 let lang='ja', reply={ok:false,status:400,json:async()=>({error:'Pilot registration limit reached'})};
 const c=vm.createContext({getLocale:()=>lang,text:key=>key,fetch:async(path,options)=>{assert.equal(path,'/api/league/bots');assert.deepEqual(JSON.parse(options.body),{name:'test',config:{}});return reply;}});
 vm.runInContext(source.slice(source.indexOf('const validationMessages ='),source.indexOf('const $ =')),c);
 vm.runInContext(source.slice(source.indexOf('async function request('),source.indexOf('function cell(')),c);
 await assert.rejects(c.request('/api/league/bots',{name:'test',config:{}}),/登録上限/);
 lang='zh';await assert.rejects(c.request('/api/league/bots',{name:'test',config:{}}),/注册上限/);
 lang='en';await assert.rejects(c.request('/api/league/bots',{name:'test',config:{}}),/Pilot registration limit/);
 lang='ja';reply={ok:false,status:400,json:async()=>({error:'Unsupported syntax: Import'})};
 await assert.rejects(c.request('/api/league/bots',{name:'test',config:{}}),/Unsupported syntax: Import/);
 reply={ok:true,status:201,json:async()=>({id:'test-id'})};
 assert.equal((await c.request('/api/league/bots',{name:'test',config:{}})).id,'test-id');
 console.log('PASS: localized API validation, diagnostic fallback and unchanged request/success data');
})().catch(e=>{console.error(e);process.exitCode=1;});
