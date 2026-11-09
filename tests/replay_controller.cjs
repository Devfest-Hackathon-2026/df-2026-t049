const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({});vm.runInContext(fs.readFileSync('web/replay-controller.js','utf8').replace('export function','function'),context);
let pending,elapsed=[],cancelled=0;const clock=context.createReplayController({advance:ms=>elapsed.push(ms),request:cb=>(pending=cb,1),cancel:()=>cancelled++});
clock.play();pending(0);pending(50);assert.deepEqual(elapsed,[0,50]);clock.pause();pending(100);assert.equal(elapsed.length,2);assert.equal(cancelled,1);
clock.play();pending(10000);assert.equal(elapsed.at(-1),0);pending(11000);assert.equal(elapsed.at(-1),100);clock.resetTime();pending(12000);assert.equal(elapsed.at(-1),0);clock.pause();assert.equal(clock.playing,false);
console.log('PASS: replay clock pause, resume, time reset and background clamp');
