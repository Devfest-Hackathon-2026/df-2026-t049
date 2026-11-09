const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('web/i18n.js', 'utf8').replaceAll('export function ', 'function ');
function locale(languages, saved, blocked = false) {
  const context = vm.createContext({
    navigator: {languages, language: languages[0]},
    localStorage: {getItem() {if (blocked) throw Error('blocked'); return saved;}}
  });
  return vm.runInContext(source + '\ngetLocale()', context);
}
assert.equal(locale(['ja-JP', 'en-US']), 'ja');
assert.equal(locale(['zh-TW']), 'ja');
assert.equal(locale(['fr-FR', 'en-GB']), 'ja');
assert.equal(locale(['de-DE']), 'ja');
assert.equal(locale(['en-US'], 'zh'), 'zh');
assert.equal(locale(['ja-JP'], 'invalid'), 'ja');
assert.equal(locale(['ja-JP'], null, true), 'ja');
assert.equal(locale([]), 'ja');
console.log('PASS: Japanese project default regardless of browser language, saved preference and blocked storage');

for(const language of ['zh','ja','en']){
 const saved={};const c=vm.createContext({Intl,Date,localStorage:{getItem:()=>null,setItem:(key,value)=>saved[key]=value}});
 vm.runInContext(source,c);c.setLocale(language);assert.equal(saved['reliefroute.language'],language);assert.equal(c.getLocale(),language);
 for(let i=1;i<=6;i++)assert.equal(c.t('S'+i),'S'+i);
 assert.equal(locale(['en-US'],language),language);
 const result=c.formatLeagueTime(Date.UTC(2026,10,9,18,0));assert.ok(result.includes('JST')&&result.includes('UTC'));assert.ok(result.includes('03:00')&&result.includes('18:00'));if(language==='ja')assert.ok(result.includes('2026/11/10')&&result.includes('2026/11/09'));
}
const blocked=vm.createContext({localStorage:{getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}}});vm.runInContext(source,blocked);assert.equal(blocked.getLocale(),'ja');blocked.setLocale('en');assert.equal(blocked.getLocale(),'en');
console.log('PASS: Japanese default, explicit preferences, storage failures, facility IDs and JST/UTC rollover');
