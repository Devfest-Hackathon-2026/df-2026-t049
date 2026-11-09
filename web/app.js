import {createReplayController} from '/replay-controller.js';
import {createMapRenderer} from '/map-renderer.js';
import { createGeometry, createMapLayout, mapStatus } from '/map-geometry.js';
import { t, getLocale, setLocale, applyTranslations } from '/i18n.js';
const $ = (selector) => document.querySelector(selector);
const NS = 'http://www.w3.org/2000/svg';
let positions={}, mapLayout, variant=0;
let match = null, frame = 0, timer = null, selected = 'S3', loading = false, comparison = null;
let requestId = 0;
const pct = (n) => `${(n * 100).toFixed(1)}%`;
const time = (turn) => `${String(Math.floor(turn * 10 / 60)).padStart(2, '0')}:${String(turn * 10 % 60).padStart(2, '0')}`;

let noticeState = null, comparing = false;
function notice(key = '', params = {}, error = false) {
  noticeState = key ? {key, params, error} : null;
  renderNotice();
}
function renderNotice() {
  const current = noticeState;
  const params = current ? {...current.params} : {};
  if (params.bot) params.bot = t(params.bot);
  if (params.reason) params.reason = t(params.reason);
  $('#notice').textContent = current ? t(current.key, params) : '';
  $('#notice').hidden = !current;
  $('#notice').classList.toggle('error', Boolean(current?.error));
}
function element(tag, attrs = {}, text) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}
async function fetchJSON(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      const error = new Error('Request failed');
      error.code = response.status === 400 ? 'badRequest' : 'serverError';
      throw error;
    }
    return await response.json();
  } catch (error) {
    if (!error.code) error.code = 'networkError';
    throw error;
  }
}
// One clock drives both the replay boundary and continuous vehicle placement.
let fraction = 0, environment = 'city';
function stop() {
  clock.pause();
  timer = null;
  document.body.classList.remove('is-playing');
  $('#play').textContent = t('play');
  if (match) $('#replay-status').textContent = frame === match.log.length - 1 ? t('replayEnd') : t('paused');
}
function play() {
  if (!match || loading) return;
  if (timer) { stop(); return; }
  if (frame >= match.log.length - 1) { frame = 0; fraction = 0; render(); }
  document.body.classList.add('is-playing');
  $('#play').textContent = t('pause'); $('#replay-status').textContent = t('playing');
  timer = true; clock.play();
}
const clock=createReplayController({advance(elapsed){
  fraction += elapsed * Number($('#speed').value) / 1000;
  while(fraction>=1 && frame<match.log.length-1){fraction--;frame++;render();}
  if(frame>=match.log.length-1){fraction=0;renderVehicles();stop();return false;}
  renderVehicles();
}});
function lockPlayback(disabled) {
  for (const id of ['play', 'restart', 'next', 'timeline', 'download']) $(`#${id}`).disabled = disabled;
}
const configKeys = ['priority_rule', 'load_rule', 'dispatch_rule'];
function readConfig() { return Object.fromEntries(configKeys.map(key => [key, $(`#${key}`).value])); }
function setConfig(config) { for (const key of configKeys) $(`#${key}`).value = config[key]; }
function configSummary(config) { return config ? t('configSummary', {priority:t(`option_${config.priority_rule}`),load:t(`option_${config.load_rule}`),dispatch:t(`option_${config.dispatch_rule}`)}) : ''; }
function syncBot() { $('#custom-fields').hidden = $('input[name=bot]:checked').value !== 'custom'; }
async function run(autoplay = true) {
  if (loading) return;
  stop(); loading = true; const id = ++requestId;
  const scenario = $('#scenario').value;
  const seed = scenario === 'fixture' ? '0' : $('#seed').value;
  const bot = $('input[name=bot]:checked').value;
  $('#run').disabled = true; $('#run').firstElementChild.textContent = t('calculating');
  lockPlayback(true); notice();
  try {
    const data = await fetchJSON(`/api/match?${new URLSearchParams({ scenario, seed, bot, ...(bot === 'custom' ? readConfig() : {}) })}`);
    if (id !== requestId) return;
    validateRecord(data); match = data; mapLayout=createMapLayout(match,{environment,variant});positions=mapLayout.positions; frame = 0; fraction = 0; selected = 'S3'; $('#city')?.remove();
    renderScore(); render();
    $('#match-label').textContent = `SEED ${match.seed} · ${t(match.bot)}`;
    $('#replay-status').textContent = t('paused');
    notice('matchDone', {bot: match.bot, seed: match.seed});
  } catch (error) {
    notice('runError', {reason: error.code || 'networkError'}, true);
  } finally {
    loading = false; $('#run').disabled = false; $('#run').firstElementChild.textContent = t('run');
    lockPlayback(!match);
    if (id === requestId && autoplay && match && !$('#arena-view').hidden && !$('#notice').classList.contains('error')) {
      if (window.innerWidth <= 720) $('.map-panel').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
      play();
    }
  }
}
function renderScore() {
  const score = match.score;
  $('#match-config').textContent = configSummary(match.bot_config);
  $('#total-score').textContent = score.total.toFixed(2);
  $('#score-caption').textContent = `${t(match.bot)} · ${match.scenario_version}`;
  $('#score-metrics').replaceChildren();
  for (const key of ['C', 'T', 'F', 'E']) {
    const label = t(key);
    const wrapper = document.createElement('div'); wrapper.className = 'metric';
    wrapper.innerHTML = `<div class="metric-label"><span>${label}<small>${key} / ${score.weights[key]}%</small></span><strong>${pct(score.metrics[key])}</strong></div><div class="metric-track"><span style="width:${score.metrics[key] * 100}%"></span></div>`;
    $('#score-metrics').append(wrapper);
  }
  $('#cost').textContent = t('vehicleTurns', {count: score.movement_cost});
  $('#final-delivered').textContent = t('units', {count: match.summary.delivered});
}
const mapRenderer=createMapRenderer($('#map'),t,id=>{selected=id;render();},$('#map-selection'));
function renderMap(snapshot){$('#map-incidents').textContent=t('mapIncidents',mapStatus(match,frame));mapRenderer.render({match,positions,environment,layout:mapLayout,frame,fraction,selected});}
function renderVehicles(){mapRenderer.vehicles({frame,fraction});}
function renderShelters(snapshot) {
  $('#shelter-cards').replaceChildren();
  for (const shelter of snapshot.shelters) {
    const demand = shelter.batches.reduce((s, b) => s + b.amount, 0);
    const received = shelter.batches.reduce((s, b) => s + b.received, 0);
    const pending = shelter.batches.filter(b => b.amount > b.received);
    const due = pending.length ? Math.min(...pending.map(b => b.due_turn)) : null;
    const button = document.createElement('button');
    button.className = `shelter-card ${selected === shelter.id ? 'selected' : ''}`;
    button.setAttribute('aria-pressed', String(selected === shelter.id));
    button.innerHTML = `<div class="card-top"><strong>${t('shelterLabel',{id:shelter.id})}</strong><span class="priority">P${shelter.priority}</span></div><div class="quantity">${received}<span> / ${t('units', {count: demand})}</span></div><div class="bar"><span style="width:${demand ? received / demand * 100 : 0}%"></span></div><div class="card-bottom"><span>${t('remaining', {count: demand - received})}</span><span>${due === null ? t('satisfied') : due < frame ? t('overdue', {count: frame - due}) : t('due', {turn: String(due).padStart(2, '0')})}</span></div>`;
    button.onclick = () => { selected = shelter.id; render(); };
    $('#shelter-cards').append(button);
  }
}
function renderFleet(snapshot) {
  $('#stock-label').textContent = t('stock', {count: snapshot.depot.stock});
  $('#fleet').replaceChildren();
  for (const vehicle of snapshot.vehicles) {
    const row = document.createElement('button');row.type='button';row.onclick=()=>{selected=vehicle.id;render();$('#map-selection').scrollIntoView({block:'nearest'});}; row.className = 'fleet-row';
    const target = vehicle.leg === 'returning' ? snapshot.depot.id : vehicle.target ? t(vehicle.target) : t('waitDispatch');
    row.innerHTML = `<div class="fleet-row-top"><span class="vehicle-id">${vehicle.id}</span><small>${t(vehicle.status)}</small></div><div class="route"><span>${vehicle.status === 'idle' ? target : `→ ${target}`}</span><span>${vehicle.cargo} / ${t('units', {count: vehicle.capacity})}</span></div>`;
    $('#fleet').append(row);
  }
}
function renderEvents() {
  const messages = [];
  for (const row of match.log.slice(0, frame + 1)) {
    for (const e of row.events) {
      let label, tone = 'alert';
      if (e.type === 'demand_spike') label = t('demandEvent', {name: t(e.payload.shelter_id), amount: e.payload.amount, turn: e.payload.due_turn});
      else if (e.type === 'road_closed') { label = t(e.phase === 'started' ? 'closureEvent' : 'reopenEvent', {road: e.payload.road_id}); tone = e.phase === 'started' ? 'danger' : ''; }
      else label = t(e.phase === 'started' ? 'congestionEvent' : 'clearEvent', {road: e.payload.road_id, multiplier: e.payload.multiplier});
      messages.push({ turn: row.turn, label, tone, target:e.payload.road_id||e.payload.shelter_id });
    }
    for (const d of row.deliveries) messages.push({ turn: row.turn, label: t('deliveryEvent', {vehicle: d.vehicle_id, name: t(d.shelter_id), amount: d.quantity}), tone: '' });
    for (const a of row.actions.filter(a => !a.accepted)) messages.push({ turn: row.turn, label: t('rejectedEvent', {reason: t(a.reason || 'unknown_error')}), tone: 'danger' });
  }
  $('#event-count').textContent = t('entries', {count: messages.length});
  const list = $('#event-list'); list.replaceChildren();
  if (!messages.length) { const p = document.createElement('p'); p.className = 'event-empty'; p.textContent = t('emptyEvents'); list.append(p); }
  for (const event of messages.reverse()) {
    const row = document.createElement(event.target?'button':'div');if(event.target){row.type='button';row.title=t('eventFocus',{turn:event.turn});row.onclick=()=>{selected=event.target;render();$('#map-selection').scrollIntoView({block:'nearest'});};} row.className = `event-row ${event.tone}`;
    const timestamp = document.createElement('time'); timestamp.textContent = time(event.turn);
    const dot = document.createElement('i'); dot.setAttribute('aria-hidden', 'true');
    const text = document.createElement('span'); text.textContent = event.label;
    row.append(timestamp, dot, text); list.append(row);
  }
}
function render() {
  if (!match) return;
  const snapshot = match.log[frame].state;
  $('#timeline').value = frame;
  $('#turn-label').innerHTML = `${String(frame).padStart(2, '0')} <span>${t('turnSuffix')}</span>`;
  renderMap(snapshot); renderShelters(snapshot); renderFleet(snapshot); renderEvents();
  $('#next').disabled = loading || frame >= match.log.length - 1;
  if (!timer) $('#replay-status').textContent = frame === match.log.length - 1 ? t('replayEnd') : t('paused');
}
function comparisonSummary(data) {
  const ranked = [...(data?.ranking || [])].filter(row => Number.isFinite(row.mean_score)).sort((a,b)=>b.mean_score-a.mean_score);
  if (ranked.length < 2) return null;
  const [first, second] = ranked;
  const means = bot => {
    const rows = data.matches.filter(row=>row.bot===bot);
    if (!rows.length || rows.some(row=>!['C','T','F','E'].every(key=>Number.isFinite(row.score?.metrics?.[key])))) return null;
    return Object.fromEntries(['C','T','F','E'].map(key=>[key,rows.reduce((sum,row)=>sum+row.score.metrics[key],0)/rows.length]));
  };
  const a=means(first.bot), b=means(second.bot);
  return {bot:first.bot, gap:first.mean_score-second.mean_score, metrics:a&&b?['C','T','F','E'].map(key=>`${key} ${((a[key]-b[key])*100).toFixed(1)} pp`).join(' · '):null};
}
function renderComparison() {
  if (!comparison) return;
  const summary=comparisonSummary(comparison), box=$('#comparison-summary');box.replaceChildren();
  if(summary){
    for(const label of [summary.gap===0?t('sampleTie'):t('sampleLead',{bot:t(summary.bot),gap:summary.gap.toFixed(2)}),summary.metrics?t('metricComparison',{metrics:summary.metrics}):null,t('sampleLimit')].filter(Boolean)){
      const p=document.createElement('p');p.textContent=label;box.append(p);
    }
  }

    $('#comparison-config').textContent = configSummary(comparison.matches.find(row => row.bot === 'custom')?.bot_config);
    $('#ranking').replaceChildren();
    comparison.ranking.forEach((r, index) => {
      const card = document.createElement('div'); card.className = 'rank-card';
      card.innerHTML = `<div><span>0${index + 1} / ${t(r.bot)}</span><small>${t('averageSeeds')}</small></div><strong>${r.mean_score.toFixed(2)}</strong>`;
      $('#ranking').append(card);
    });
    $('#comparison-body').replaceChildren();
    for (const row of comparison.matches) {
      const tr = document.createElement('tr');
      for (const value of [row.seed, t(row.bot), ...['C', 'T', 'F', 'E'].map(k => pct(row.score.metrics[k])), row.score.total.toFixed(2)]) {
        const cell = document.createElement('td'); cell.textContent = value; tr.append(cell);
      }
      const cell = document.createElement('td'), button = document.createElement('button'); button.textContent = t('view');
      button.onclick = () => {
        if (loading) return;
        $('#scenario').value = 'events'; syncScenario(); $('#seed').value = row.seed;
        $(`input[name=bot][value=${row.bot}]`).checked = true;
        if (row.bot_config) setConfig(row.bot_config);
        syncBot(); syncSeeds(); view('arena'); run(false);
      };
      cell.append(button); tr.append(cell); $('#comparison-body').append(tr);
    }
}
async function compare() {
  comparing = true;
  const button = $('#compare-run'); button.disabled = true; button.textContent = t('compareCalculating'); notice();
  try {
    comparison = await fetchJSON(`/api/compare?${new URLSearchParams(readConfig())}`);
    renderComparison();
  } catch (error) { notice('compareError', {reason: error.code || 'networkError'}, true); }
  finally { comparing = false; button.disabled = false; button.textContent = t(comparison ? 'compareAgain' : 'compareRun'); }
}
function view(name) {
  stop(); $('#arena-view').hidden = name !== 'arena'; $('#compare-view').hidden = name !== 'compare';
  for (const button of document.querySelectorAll('[data-view]')) {
    button.classList.toggle('active', button.dataset.view === name);
    button.setAttribute('aria-current', button.dataset.view === name ? 'page' : 'false');
  }
  if (name === 'compare' && !comparison && !$('#compare-run').disabled) compare();
}
function syncSeeds() { document.querySelectorAll('[data-seed]').forEach(b => b.classList.toggle('selected', b.dataset.seed === $('#seed').value)); }
function syncScenario() {
  const fixed = $('#scenario').value === 'fixture';
  $('#seed').disabled = fixed; $('#seed').value = fixed ? '0' : '11';
  document.querySelectorAll('[data-seed]').forEach(b => { b.disabled = fixed; }); syncSeeds();
}
$('#match-form').onsubmit = e => { e.preventDefault(); run(); };
$('#scenario').onchange = syncScenario;
document.querySelectorAll('input[name=bot]').forEach(input => input.onchange = syncBot);
$('#seed').oninput = syncSeeds;
document.querySelectorAll('[data-seed]').forEach(b => b.onclick = () => { $('#seed').value = b.dataset.seed; syncSeeds(); });
document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => view(b.dataset.view));
$('#play').onclick = play;
$('#restart').onclick = () => { stop(); fraction = 0; frame = 0; render(); };
$('#previous').onclick=()=>{stop();fraction=0;if(match)frame=Math.max(0,frame-1);render();};
$('#next').onclick = () => { stop(); fraction = 0; if (match) frame = Math.min(frame + 1, match.log.length - 1); render(); };
$('#timeline').oninput = e => { stop(); fraction = 0; frame = Number(e.target.value); render(); };
$('#speed').onchange = () => { clock.resetTime(); };
$('#compare-run').onclick = compare;
$('#download').onclick = () => {
  if (!match) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(match, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = `reliefroute-${match.seed}-${match.bot}.json`;
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
};
function changeLanguage(value) {
  setLocale(value); $('#previous').setAttribute('aria-label',t('previousTurn'));
  applyTranslations();
  $('#run').firstElementChild.textContent = t(loading ? 'calculating' : 'run');
  $('#compare-run').textContent = t(comparing ? 'compareCalculating' : comparison ? 'compareAgain' : 'compareRun');
  if (match) {
    renderScore(); render();
    $('#match-label').textContent = `SEED ${match.seed} · ${t(match.bot)}`;
    $('#replay-status').textContent = t(timer ? 'playing' : frame === match.log.length - 1 ? 'replayEnd' : 'paused');
  }
  $('#play').textContent = t(timer ? 'pause' : 'play');
  renderComparison(); renderNotice();
}
$('#language').onchange = e => changeLanguage(e.target.value);
function changeLayout(){environment=$('#map-environment').value;variant=Number($('#map-layout').value);if(match){mapLayout=createMapLayout(match,{environment,variant});positions=mapLayout.positions;render();}}
$('#map-environment').onchange=changeLayout;$('#map-layout').onchange=changeLayout;
changeLanguage(getLocale());
run(false);


// Geometry is a presentation of existing edges; no routable edges are invented.
function roadPoints(road) { return createGeometry(match, positions, environment).roadPoints(road); }
function pathPoint(points, progress) { return createGeometry(match, positions, environment).pathPoint(points, progress); }
function vehiclePose(index, id, part) { return createGeometry(match, positions, environment).vehiclePose(index, id, part); }
function validateRecord(data) {
  if(!data?.log?.length || !Number.isFinite(data?.score?.total)) throw new Error('Invalid match');
  for(const row of data.log) {
    if(!row.state?.roads?.length || !Array.isArray(row.state.vehicles) || !Array.isArray(row.state.shelters) || !Array.isArray(row.events) || !Array.isArray(row.deliveries)) throw new Error('Invalid replay');
    for(const r of row.state.roads) if(!r.from||!r.to) throw new Error('Unsupported map');
  }
}

document.querySelectorAll('[data-map-view]').forEach(button=>{button.onclick=()=>{$('#map').closest('.map-wrap').classList.toggle('fit-map',button.dataset.mapView==='fit');document.querySelectorAll('[data-map-view]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));};});
