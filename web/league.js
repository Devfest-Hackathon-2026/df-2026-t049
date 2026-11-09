import {createMapRenderer} from './map-renderer.js';
import {createMapLayout,mapStatus} from './map-geometry.js';
import {createReplayController} from './replay-controller.js';
import {getLocale, setLocale, t, formatLeagueTime} from './i18n.js';
const copy = {
en: {language:'Language',title:'Hourly Bot League',intro:'Deploy a strategy. It automatically competes on a shared new scenario every UTC hour.',refresh:'Refresh',deploy:'Deploy strategy Bot',name:'Bot name',priority:'Destination priority',urgency:'Urgency first',nearest:'Nearest first',fair:'Lowest coverage first',load:'Load limit',full:'Full capacity',half:'Half capacity',dispatch:'Dispatch condition',any:'Any available load',full_load:'Wait for full load',starts:'New and resumed Bots enter the next hourly round. Keep your management token to pause or resume.',manage:'Manage your Bot',secret:'The token controls your Bot. It is shown once after deployment; save it privately. No account recovery in this pilot.',token:'Management token',pauseBot:'Pause Bot',resumeBot:'Resume Bot',ranking:'Leaderboard',ratingHelp:'Start: 1000 points. Each round: at most ±16 points based on pairwise results; ties score zero. This is not Elo.',rating:'Rank points',played:'Rounds',state:'Status',round:'Latest completed round',score:'Score',delta:'Points change',watch:'Watch',recorded:'Recorded simulation: scrub every turn or play it back. This is not live vehicle telemetry.',play:'Play / pause',turn:'Turn',download:'Download record',simulation:'Entirely fictional educational simulation. Not real disaster guidance.',active:'Active',paused:'Paused',waiting:'Waiting for the scheduler to finish the first round.',stale:'Latest result is from an earlier hour; waiting for this hour’s settlement.',next:'Next hourly boundary',deployed:'Deployed. Starts at',saved:'Updated',error:'Request failed',stock:'Depot stock',events:'Events and deliveries through this turn',empty:'No participants in this round.'},
zh: {language:'界面语言',title:'每小时 Bot 联赛',intro:'部署策略后，每个 UTC 整点自动参加同一新场景的比赛。',refresh:'刷新',deploy:'部署策略 Bot',name:'Bot 名称',priority:'目标优先规则',urgency:'紧急度优先',nearest:'最近优先',fair:'最低覆盖率优先',load:'装载上限',full:'全部容量',half:'一半容量',dispatch:'派车条件',any:'有物资即出发',full_load:'等待满载',starts:'新部署与恢复的 Bot 从下一小时参赛。保存管理令牌，以便暂停或恢复。',manage:'管理自己的 Bot',secret:'管理令牌可控制你的 Bot，仅在部署时显示一次，请私下保存。试用版暂不支持账号找回。',token:'管理令牌',pauseBot:'暂停 Bot',resumeBot:'恢复 Bot',ranking:'排行榜',ratingHelp:'初始 1000 分；每轮按同场成对胜负增减，最多 ±16 分，平局不变。这不是 Elo。',rating:'排名积分',played:'场数',state:'状态',round:'最近完成的一轮',score:'得分',delta:'积分变化',watch:'观战',recorded:'这是已计算比赛的逐回合回放，可拖动或播放，并非实时车辆遥测。',play:'播放 / 暂停',turn:'回合',download:'下载比赛记录',simulation:'完全虚构的教育模拟，不提供真实救灾建议。',active:'参赛中',paused:'已暂停',waiting:'等待调度器完成第一轮。',stale:'最新结果来自上一小时，正在等待本小时结算。',next:'下一个整点',deployed:'已部署，开始参赛时间',saved:'已更新',error:'请求失败',stock:'仓库库存',events:'截至本回合的事件和配送',empty:'本轮没有参赛 Bot。'},
ja: {language:'表示言語',title:'時間別 Bot リーグ',intro:'戦略を登録すると、UTC の毎正時に共通の新しいシナリオで自動対戦します。',refresh:'更新',deploy:'戦略 Bot を登録',name:'Bot 名',priority:'配送先の優先順位',urgency:'緊急度優先',nearest:'近距離優先',fair:'最低充足率優先',load:'積載上限',full:'最大容量',half:'半分',dispatch:'出発条件',any:'荷物があれば出発',full_load:'満載まで待つ',starts:'新規・再開 Bot は次の時間帯から参加します。管理トークンを保存してください。',manage:'自分の Bot を管理',secret:'トークンは登録時に一度だけ表示されます。非公開で保存してください。試用版にはアカウント復旧がありません。',token:'管理トークン',pauseBot:'Bot を停止',resumeBot:'Bot を再開',ranking:'ランキング',ratingHelp:'初期 1000 点。各ラウンドの相対成績で最大 ±16 点、同点は変化なし。Elo ではありません。',rating:'順位ポイント',played:'試合数',state:'状態',round:'直近の完了ラウンド',score:'スコア',delta:'ポイント変動',watch:'観戦',recorded:'計算済みの試合リプレイです。各ターンへ移動できます。実際の車両のライブ情報ではありません。',play:'再生 / 一時停止',turn:'ターン',download:'試合記録を保存',simulation:'完全に架空の教育シミュレーションです。実際の救援判断には使えません。',active:'参加中',paused:'停止中',waiting:'最初のラウンドの完了を待っています。',stale:'前の時間帯の結果です。現在のラウンドの完了を待っています。',next:'次の正時',deployed:'登録しました。開始時刻',saved:'更新しました',error:'リクエスト失敗',stock:'倉庫在庫',events:'このターンまでのイベントと配送',empty:'このラウンドに参加者はいません。'}
};
Object.assign(copy.en, {botType:'Bot type',strategyType:'Parameter strategy',programType:'Write decision code',programHelp:'Restricted Python: define decide(request). Lists, dictionaries, for/if, arithmetic, len/min/max/abs and append(list, item) are supported. No imports, file/network access, while loops or Python libraries. 12,000 steps per turn. append returns a new list. Errors cause no dispatch that turn. Deploy a new Bot to change code.',example:'Load example',source:'Decision code'});
Object.assign(copy.zh, {botType:'Bot 类型',strategyType:'参数策略',programType:'编写决策代码',programHelp:'受限 Python：定义 decide(request)。支持列表、字典、for/if、算术及 len/min/max/abs、append(list, item)。不支持导入、文件、网络、while 或 Python 库。每回合限 12000 步，append 返回新列表。运行错误会跳过该回合派车。修改代码需部署新 Bot。',example:'载入示例',source:'决策代码'});
Object.assign(copy.ja, {botType:'Bot 種類',strategyType:'パラメーター戦略',programType:'決定コードを書く',programHelp:'制限付き Python：decide(request) を定義します。リスト、辞書、for/if、算術、len/min/max/abs、append(list, item) に対応。import、ファイル、ネットワーク、while、Python ライブラリーは使用不可。各ターン12000ステップ。append は新しいリストを返します。エラー時はそのターンの派車なし。コード変更は新規 Bot として登録します。',example:'サンプル読込',source:'決定コード'});
const extra = {
zh:{copyToken:'复制管理令牌',copied:'已复制，请保存在私密位置',copyFailed:'无法复制，请从管理令牌输入框手动复制',network:'网络连接失败，请检查连接后重试',expired:'回放已过期或不存在',denied:'管理令牌无效，请检查 Bot ID 和令牌',unavailable:'联赛暂时不可用，请稍后刷新',pending:'等待下一小时参赛',history:'仅最近完成轮次保留完整回放；更早历史暂不提供浏览入口。',rules:'紧急度优先考虑期限；最近优先考虑距离；最低覆盖率优先照顾尚未满足的需求。半载限制每次装载量，等待满载可能延迟小额配送。',review:'部署将注册一个新 Bot，从下一小时参赛；修改代码需重新注册。',line:'定位错误行',emptySource:'请输入决策代码',loading:'正在请求…'},
ja:{copyToken:'管理トークンをコピー',copied:'コピーしました。安全に保管してください',copyFailed:'コピーできません。入力欄から手動でコピーしてください',network:'接続に失敗しました。再試行してください',expired:'リプレイの期限切れ、または見つかりません',denied:'Bot ID と管理トークンを確認してください',unavailable:'リーグは一時的に利用できません',pending:'次の時間帯への参加待ち',history:'完全なリプレイは最新ラウンドのみ保存されます。過去一覧は未対応です。',rules:'緊急度は期限、近距離は距離、最低充足率は未充足需要を優先します。半積載は積載量を制限し、満載待ちは少量配送を遅らせる場合があります。',review:'新しい Bot を登録し、次の時間帯から参加します。コード変更は再登録が必要です。',line:'エラー行へ移動',emptySource:'決定コードを入力してください',loading:'処理中…'},
en:{copyToken:'Copy management token',copied:'Copied. Store it privately.',copyFailed:'Copy unavailable. Copy manually from the token field.',network:'Connection failed. Check your network and retry.',expired:'Replay expired or not found.',denied:'Check the Bot ID and management token.',unavailable:'League temporarily unavailable. Try again later.',pending:'Waiting for next hourly round',history:'Only the latest completed round retains full replays. Older history browsing is not available.',rules:'Urgency prioritizes deadlines; nearest prioritizes distance; lowest coverage prioritizes unmet needs. Half load caps cargo; waiting for a full load can delay small deliveries.',review:'Deployment registers a new Bot for the next hour. Code changes require a new registration.',line:'Go to error line',emptySource:'Enter decision code.',loading:'Loading…'}
};
for(const lang of Object.keys(extra))Object.assign(copy[lang],extra[lang]);
for(const [lang,value] of Object.entries({zh:'此服务器未启用联赛。请按本地开发说明配置数据库并重新启动。',ja:'このサーバーではリーグが未設定です。ローカル起動手順を確認してください。',en:'League is not enabled on this server. Configure the local database and restart using the development guide.'}))copy[lang].disabled=value;
const validationMessages = {
  ja: {'Bot name must contain 1–40 characters':'Bot 名は前後の空白を除いて 1～40 文字で入力してください。','Invalid strategy configuration':'戦略の設定を確認してください。','Pilot registration limit reached':'登録上限（100 Bot）に達しました。','Source must contain 1–6000 UTF-8 bytes':'コードは UTF-8 で 1～6000 バイトにしてください。','Invalid decision function syntax':'決定関数の構文を確認してください。','Provide exactly one def decide(request) function':'def decide(request) 関数を一つだけ定義してください。'},
  zh: {'Bot name must contain 1–40 characters':'Bot 名称去除首尾空白后须为 1～40 个字符。','Invalid strategy configuration':'请检查策略配置。','Pilot registration limit reached':'已达到注册上限（100 个 Bot）。','Source must contain 1–6000 UTF-8 bytes':'代码须为 1～6000 个 UTF-8 字节。','Invalid decision function syntax':'请检查决策函数语法。','Provide exactly one def decide(request) function':'请只定义一个 def decide(request) 函数。'},
  en: {}
};
function validationMessage(message) {
  return validationMessages[getLocale()][message] || message || '';
}
const $ = id => document.getElementById(id);
const text = key => copy[getLocale()][key];
let latest, record, loading = false, fraction=0;
let autoWatchAttempted=false, userWatchSelected=false;
let watchRequest=0, mapLayout, selected=null, deploymentInfo=null;
const renderer=createMapRenderer($('league-map'),t,id=>{selected=id;renderReplay();},$('league-map-selection'));
const clock=createReplayController({advance(ms){
 fraction+=ms*Number($('replay-speed').value)/1000;
 while(fraction>=1){fraction--;const next=Number($('replay-turn').value)+1;if(next>=record.log.length){fraction=0;clock.pause();$('replay-play').textContent=t('play');return false;}$('replay-turn').value=next;renderReplay();}
 renderer.vehicles({frame:Number($('replay-turn').value),fraction});
}});
function translate() {
  document.documentElement.lang = getLocale();
  document.title = text('title') + ' · ReliefRoute';
  document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=t(el.dataset.i18n));
  document.querySelectorAll('[data-copy]').forEach(el => el.textContent = text(el.dataset.copy));
  $('language').value = getLocale();
  document.querySelectorAll('[data-i18n-aria-label]').forEach(el=>el.setAttribute('aria-label',t(el.dataset.i18nAriaLabel)));
  for(const [id,key] of [['replay-reset','restart'],['replay-back','previous'],['replay-next','next'],['replay-speed','speed']]) $(id).setAttribute('aria-label',({zh:{restart:'回到开始',previous:'上一回合',next:'下一回合',speed:'播放速度'},ja:{restart:'最初に戻る',previous:'前のターン',next:'次のターン',speed:'再生速度'},en:{restart:'Restart',previous:'Previous turn',next:'Next turn',speed:'Playback speed'}})[getLocale()][key]);
  if(deploymentInfo)$('deployment').textContent=`${text('deployed')}: ${formatLeagueTime(deploymentInfo.starts_hour*3600000)}\nBot ID: ${deploymentInfo.id}`;
  if (latest) renderLeague();
  if (record) renderReplay();
}
async function request(path, payload) {
  let response;try{response = await fetch(path, payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});}catch{throw Error(text('network'));}
  const data = await response.json();
  if (!response.ok) throw Error(response.status===404?text('expired'):response.status===403?text('denied'):data.error==='Hourly league has not been enabled on this server'?text('disabled'):response.status>=500?text('unavailable'):text('error')+' · '+validationMessage(data.error));
  return data;
}
function cell(row, value) {const el=document.createElement('td');el.textContent=String(value);row.append(el);return el;}
function renderLeague() {
  const current = latest.current;
  if(!record && !current.results.length) $('replay-empty-message').textContent=t('noReplayYet');
  $('league-count').textContent=t('registeredBots',{count:latest.ranking.length});
  $('league-status').textContent = `${text('next')}: ${formatLeagueTime(latest.next_round_at*1000)}`;
  $('league-ranking').replaceChildren();
  if(!latest.ranking.length){const row=document.createElement('tr');const item=cell(row,text('empty'));item.colSpan=5;$('league-ranking').append(row);}
  latest.ranking.forEach((bot,index) => {const row=document.createElement('tr'); [index+1,bot.name,(bot.rating/latest.rating_scale).toFixed(2),bot.played,text(!bot.active?'paused':bot.played?'active':'pending')].forEach(value=>cell(row,value));$('league-ranking').append(row);});
  $('round-info').textContent = current.hour === null ? text('waiting') : formatLeagueTime(current.hour*3600000) + (current.hour < latest.server_hour ? ' · '+text('stale') : '') + (!current.results.length?' · '+text('empty'):'');
  $('league-results').replaceChildren();
  [...current.results].sort((a,b)=>b.score.total-a.score.total || a.bot_id.localeCompare(b.bot_id)).forEach(result=>{
    const row=document.createElement('tr');cell(row,result.name);cell(row,result.score.total.toFixed(2));cell(row,(result.delta/latest.rating_scale).toFixed(2));
    const button=document.createElement('button');button.textContent=text('watch');button.onclick=()=>watch(current.hour,result.bot_id);cell(row,'').append(button);$('league-results').append(row);
  });
}
async function refresh() {if(loading)return;loading=true;$('refresh').disabled=true;$('league-status').textContent=text('loading');try{latest=await request('/api/league');renderLeague();autoWatchLatest();}catch(error){$('league-status').textContent=error.message;}finally{loading=false;$('refresh').disabled=false;}}
function autoWatchLatest() {
  if(autoWatchAttempted || userWatchSelected || record) return;
  const current=latest?.current;
  if(current?.hour==null || !current.results?.length) return;
  const candidate=[...current.results].sort((a,b)=>b.score.total-a.score.total || a.bot_id.localeCompare(b.bot_id))[0];
  autoWatchAttempted=true;
  return watch(current.hour,candidate.bot_id,true);
}
async function watch(hour,id,automatic=false) {
  if(automatic && userWatchSelected)return;
  if(!automatic)userWatchSelected=true;
  const requestId=++watchRequest;if(!automatic)$('league-status').textContent=text('loading');
  try {const next=await request(`/api/league/replay?hour=${hour}&bot=${encodeURIComponent(id)}`);if(requestId!==watchRequest)return;if(!next?.log?.length||!next.log.every(row=>row.state?.depot&&Array.isArray(row.state.vehicles)&&Array.isArray(row.state.shelters)&&row.state.roads?.length))throw Error(text('error'));clock.pause();fraction=0;record=next;selected=null;mapLayout=createMapLayout(record);$('league-map').querySelector('#city')?.remove();$('league-replay').hidden=false;$('replay-empty').hidden=true;$('replay-turn').max=record.log.length-1;$('replay-turn').value=0;renderReplay();if(latest)renderLeague();if(!automatic)$('league-replay').scrollIntoView({behavior:'smooth'});}catch(error){if(requestId===watchRequest){if(automatic)$('replay-empty-message').textContent=t('autoReplayUnavailable');else $('league-status').textContent=error.message;}}
}
function svg(tag, attributes, label) {const el=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attributes).forEach(([key,value])=>el.setAttribute(key,String(value)));if(label!==undefined)el.textContent=label;return el;}
function renderReplay() {
  const turn=Number($('replay-turn').value), state=record.log[turn].state;
  $('replay-name').textContent=`${record.bot_name} · ${record.score.total.toFixed(2)}`;
  $('replay-position').textContent=`${turn} / ${record.log.length-1}`;
  $('replay-state').textContent=`${text('stock')}: ${state.depot.stock}`;
  $('league-map-incidents').textContent=t('mapIncidents',mapStatus(record,turn));
  $('replay-map-info').textContent=`${t(mapLayout.environment+'Environment')} · ${t('layoutNumber',{number:mapLayout.variant+1})} · ${record.league_hour!=null?formatLeagueTime(record.league_hour*3600000):'—'} · ${state.roads.length} ${t('mapRoads')}`;
  renderer.render({match:record,positions:mapLayout.positions,environment:mapLayout.environment,layout:mapLayout,frame:turn,fraction,selected});
  $('replay-play').textContent=t(clock.playing?'pause':'play');
  const details=$('replay-details');details.replaceChildren();
  for(const vehicle of state.vehicles){const item=document.createElement('button');item.type='button';item.onclick=()=>{selected=vehicle.id;renderReplay();$('league-map-selection').scrollIntoView({block:'nearest'});};item.className='replay-detail';item.textContent=`${vehicle.id} · ${t(vehicle.status)} · ${vehicle.cargo}/${vehicle.capacity} → ${vehicle.leg==='returning'?state.depot.id:vehicle.target||'—'}`;details.append(item);}
  for(const shelter of state.shelters){const item=document.createElement('button');item.type='button';item.onclick=()=>{selected=shelter.id;renderReplay();$('league-map-selection').scrollIntoView({block:'nearest'});};item.className='replay-detail';const total=shelter.batches.reduce((n,b)=>n+b.amount,0),received=shelter.batches.reduce((n,b)=>n+b.received,0);item.textContent=`${shelter.id} · ${received}/${total} · ${t('remaining',{count:total-received})}`;details.append(item);}
  for(const road of state.roads){const item=document.createElement('button');item.type='button';item.onclick=()=>{selected=road.id;renderReplay();$('league-map-selection').scrollIntoView({block:'nearest'});};item.className='replay-detail';item.textContent=`${road.id} · ${road.from} ↔ ${road.to} · ${road.is_open?t('roadTurns',{count:road.travel_turns}):t('closed')}`;details.append(item);}
  const events=$('replay-events');events.replaceChildren();
  for(const row of record.log.slice(0,turn+1)){
    for(const e of row.events){const target=e.payload.road_id||e.payload.shelter_id;
      const label=e.type==='demand_spike'?t('demandEvent',{name:e.payload.shelter_id,amount:e.payload.amount,turn:e.payload.due_turn}):e.type==='road_closed'?t(e.phase==='started'?'closureEvent':'reopenEvent',{road:e.payload.road_id}):t(e.phase==='started'?'congestionEvent':'clearEvent',{road:e.payload.road_id,multiplier:e.payload.multiplier});
      const button=document.createElement('button');button.type='button';button.className='event-focus';button.textContent=`T${row.turn} · ${label}`;button.title=t('eventFocus',{turn:row.turn});button.onclick=()=>{selected=target;renderReplay();$('league-map-selection').scrollIntoView({block:'nearest'});};events.append(button);
    }
    for(const d of row.deliveries){const p=document.createElement('p');p.textContent=`T${row.turn} · ${d.vehicle_id} → ${d.shelter_id}: +${d.quantity}`;events.append(p);}
    for(const a of row.actions.filter(a=>!a.accepted)){const p=document.createElement('p');p.textContent=`T${row.turn} · ${t(a.reason||'unknown_error')}${a.detail?' · '+a.detail:''}`;events.append(p);}
  }

}
$('deploy-form').onsubmit=async event=>{event.preventDefault();const button=event.currentTarget.querySelector('button[type=submit]');if(button.disabled)return;button.disabled=true;try{const fields=new FormData(event.currentTarget);if($('bot-type').value==='program'&&!$('bot-source').value.trim())throw Error(text('emptySource'));const data=await request('/api/league/bots',$('bot-type').value==='program' ? {name:fields.get('name'),source:$('bot-source').value} : {name:fields.get('name'),config:Object.fromEntries(['priority_rule','load_rule','dispatch_rule'].map(key=>[key,fields.get(key)]))});deploymentInfo={id:data.id,starts_hour:data.starts_hour};$('deployment').textContent=`${text('deployed')}: ${formatLeagueTime(data.starts_hour*3600000)}\nBot ID: ${data.id}`;$('bot-management').open=true;$('management-id').value=data.id;$('management-token').value=data.token;await refresh();}catch(error){$('deployment').textContent=error.message;}finally{button.disabled=false;}};
async function active(value) {if($('pause-bot').disabled)return;$('pause-bot').disabled=true;$('resume-bot').disabled=true;try{await request('/api/league/bots/active',{id:$('management-id').value.trim(),token:$('management-token').value.trim(),active:value});$('management-status').textContent=text('saved');await refresh();}catch(error){$('management-status').textContent=error.message;}finally{$('pause-bot').disabled=false;$('resume-bot').disabled=false;}}
$('pause-bot').onclick=()=>active(false);$('resume-bot').onclick=()=>active(true);
$('refresh').onclick=refresh;$('language').onchange=event=>{setLocale(event.target.value);translate();};
$('replay-turn').oninput=()=>{clock.pause();fraction=0;renderReplay();};
$('replay-play').onclick=()=>{if(!record)return;if(clock.playing){clock.pause();$('replay-play').textContent=t('play');return;}if(Number($('replay-turn').value)>=record.log.length-1){$('replay-turn').value=0;fraction=0;renderReplay();}clock.play();$('replay-play').textContent=t('pause');};
function seek(turn){if(!record)return;clock.pause();fraction=0;$('replay-turn').value=Math.max(0,Math.min(record.log.length-1,turn));renderReplay();}
$('replay-back').onclick=()=>seek(Number($('replay-turn').value)-1);
$('replay-next').onclick=()=>seek(Number($('replay-turn').value)+1);
$('replay-reset').onclick=()=>seek(0);
$('replay-speed').onchange=()=>clock.resetTime();
$('replay-download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(record)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`league-${record.league_hour}-${record.bot_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
translate();refresh();setInterval(()=>{if(!document.hidden)refresh();},30000);

$('bot-type').onchange=()=>{document.body.classList.toggle('code-mode',$('bot-type').value==='program');$('program-editor').hidden=$('bot-type').value!=='program';['priority_rule','load_rule','dispatch_rule'].forEach(name=>{document.querySelector(`[name="${name}"]`).closest('label').hidden=$('bot-type').value==='program';});};
$('load-example').onclick=async()=>{try{const response=await fetch('/bot-example.py');if(!response.ok)throw Error(text('error'));$('bot-source').value=await response.text();}catch(error){$('deployment').textContent=error.message;}};

$('copy-token').onclick=async()=>{try{if(!$('management-token').value)return;await navigator.clipboard.writeText($('management-token').value);$('management-status').textContent=text('copied');}catch{$('management-status').textContent=text('copyFailed');}};

document.querySelectorAll('[data-map-view]').forEach(button=>{button.onclick=()=>{$('league-map').parentElement.classList.toggle('fit-map',button.dataset.mapView==='fit');document.querySelectorAll('[data-map-view]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));};});
