// One animation clock; snapshots remain authoritative at integer boundaries.
export function createReplayController({advance, request = cb => requestAnimationFrame(cb), cancel = id => cancelAnimationFrame(id)}) {
  let handle = null, previous = null, running = false;
  function pause() { running=false; if(handle!==null)cancel(handle);handle=null;previous=null; }
  function tick(now) {
    if(!running)return;
    const elapsed=previous===null?0:Math.min(Math.max(0,now-previous),100);
    previous=now;
    if(advance(elapsed)===false){pause();return;}
    if(running)handle=request(tick);
  }
  return {play(){if(running)return;running=true;previous=null;handle=request(tick);},pause,resetTime(){previous=null;},get playing(){return running;}};
}
