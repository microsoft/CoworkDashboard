#!/usr/bin/env python3
"""
build_dashboard.py — render team_data.json (from parse_posts.py) into a single
self-contained, team-safe HTML dashboard.

v1 scope: small, homogeneous teams at the team level. Anonymized — members are
numbers, the only attribute is Role, and NOTHING is shown at an individual level.
A per-Role breakdown appears only when >= kThreshold members share that Role
(privacy k-anonymity); otherwise contributors collapse into one combined bar.

Tabs (each small, one clear purpose):
  Overview          — auto-insights + the single KPI band.
  Impact & Value    — value pillars, task categories ($), roles, deliverables by type.
  How Cowork is used— business process (grouped, lead), skills, category mix (k-anon), analyzed->produced.
  Trends            — minimal fortnight-over-fortnight time-saved line.
  Glossary & method — definitions, the value model, privacy rule, sources.

Every $ figure = hours x rate, computed live in the browser (live rate control).
Usage: python build_dashboard.py --in working/team_data.json --out output/cowork-team-roi-dashboard.html
"""
import json, argparse

CSS = r"""
:root{--bg:#f3f4f8;--panel:#fff;--ink:#1f2329;--muted:#5d6470;--faint:#8a909c;--line:#e4e7ee;
--brand:#0f6cbd;--brand-d:#0b5394;--soft:#eaf3fb;--good:#107c10;--shadow:0 1px 2px rgba(16,24,40,.06),0 4px 16px rgba(16,24,40,.06);
--t:#0f6cbd;--rg:#107c10;--cr:#ca5010;--rm:#8764b8;
--c0:#0f6cbd;--c1:#2e8b57;--c2:#ca5010;--c3:#8764b8;--c4:#0099bc;--c5:#c4314b;--c6:#7a7574;--c7:#498205;}
@media (prefers-color-scheme:dark){:root{--bg:#16181d;--panel:#1f2228;--ink:#e9ebef;--muted:#a7adb8;--faint:#7c828d;--line:#2c3038;--brand:#4aa3e8;--brand-d:#74b9ee;--soft:#1b2a39;--shadow:0 1px 2px rgba(0,0,0,.4);}}
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.45;-webkit-font-smoothing:antialiased}
.wrap{max-width:1140px;margin:0 auto;padding:0 20px 60px}
header.top{background:linear-gradient(120deg,var(--brand-d),var(--brand));color:#fff;padding:24px 0 18px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:9px}.brand .nm{font-size:13px;letter-spacing:.3px;opacity:.92;font-weight:600}
header.top h1{font-size:26px;margin:2px 0 4px;font-weight:700;letter-spacing:-.2px}
header.top .sub{font-size:14px;opacity:.93;margin:0}header.top .gen{font-size:12px;opacity:.82;margin-top:7px}
.banner{background:#fff7e6;border:1px solid #f3d98b;color:#7a5b00;border-radius:10px;padding:10px 14px;font-size:12.5px;margin:16px 0 0;display:flex;gap:9px;align-items:flex-start}
@media (prefers-color-scheme:dark){.banner{background:#332a12;border-color:#5c4a17;color:#e8cf8f}}
.controls{position:sticky;top:0;z-index:30;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);padding:13px 16px;margin:16px 0 0;display:flex;flex-wrap:wrap;gap:14px 24px;align-items:flex-end}
.ctl{display:flex;flex-direction:column;gap:6px}.ctl label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--faint);font-weight:700}
.ctl select,.ctl input{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-width:150px}
.rate-in{display:flex;align-items:center;gap:6px}.rate-in span{color:var(--faint);font-weight:600}.rate-in input{width:82px;min-width:70px}
.btn{font:inherit;font-size:13px;font-weight:600;padding:8px 14px;border-radius:8px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.btn.primary{background:var(--brand);border-color:var(--brand);color:#fff}.btn:hover{border-color:var(--brand)}.spacer{flex:1 1 auto}
.tabs{position:sticky;top:0;z-index:25;display:flex;gap:4px;flex-wrap:wrap;margin:16px 0 8px;border-bottom:2px solid var(--line);background:var(--bg)}
.tab-btn{font:inherit;font-size:13.5px;font-weight:600;padding:11px 15px;border:none;background:none;color:var(--muted);cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px}
.tab-btn.on{color:var(--brand);border-bottom-color:var(--brand)}.tab-btn:hover{color:var(--ink)}
.tab-panel{display:none}.tab-panel.on{display:block}
section.block{margin:24px 0 0}
h2.sec{font-size:16px;font-weight:700;margin:0 0 3px;display:flex;align-items:center;gap:9px}
h2.sec .dot{width:9px;height:9px;border-radius:3px;background:var(--brand)}
.sec-note{font-size:12.5px;color:var(--muted);margin:0 0 13px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi .k-l{font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700}
.kpi .k-v{font-size:25px;font-weight:750;margin:5px 0 2px;letter-spacing:-.3px}.kpi .k-s{font-size:12px;color:var(--muted)}
.kpi.hero{background:linear-gradient(135deg,var(--soft),var(--panel));border-color:#cfe3f5}
@media (prefers-color-scheme:dark){.kpi.hero{border-color:#274a68}}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px 18px 15px;box-shadow:var(--shadow)}
.card h3{font-size:14px;margin:0 0 4px;font-weight:700}.card .hint{font-size:11.5px;color:var(--faint);margin:0 0 12px}
.row{display:grid;grid-template-columns:180px 1fr auto;align-items:center;gap:11px;padding:5px 0}
.row .rl{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row .rbar{background:var(--bg);border-radius:6px;height:16px;overflow:hidden}.row .rfill{height:100%;border-radius:6px;min-width:2px}
.row .rv{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}.row .rv b{color:var(--ink);font-weight:650}
table.dt{width:100%;border-collapse:collapse;font-size:13px}
table.dt th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700;padding:8px 10px;border-bottom:2px solid var(--line)}
table.dt th.r,table.dt td.r{text-align:right;font-variant-numeric:tabular-nums}
table.dt td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}table.dt tr:last-child td{border-bottom:none}
table.dt tr.tot td{font-weight:700;border-top:2px solid var(--line);background:var(--bg)}
.pill{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;background:var(--soft);color:var(--brand-d);font-weight:600;margin:1px 3px 1px 0}
.insights{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.ins{display:flex;gap:11px;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--brand);border-radius:10px;padding:12px 14px;box-shadow:var(--shadow)}
.ins .ic{font-size:18px;line-height:1.2}.ins .tx{font-size:13px}.ins .tx b{font-weight:700}
.donut-wrap{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.legend{display:flex;flex-direction:column;gap:7px;font-size:12.5px}.legend .li{display:flex;align-items:center;gap:9px}
.legend .sw{width:12px;height:12px;border-radius:3px;flex:none}.legend .lt{flex:1}.legend .lv{color:var(--muted);font-variant-numeric:tabular-nums}
.stackrow{display:grid;grid-template-columns:200px 1fr;align-items:center;gap:11px;padding:6px 0}
.stackbar{display:flex;height:22px;border-radius:6px;overflow:hidden;background:var(--bg)}.stackseg{height:100%}
.io2{display:grid;grid-template-columns:1fr 1fr;gap:26px}.io2 h4{font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);margin:0 0 10px}
.svgtrend{width:100%;height:150px}.trend-empty{font-size:12.5px;color:var(--muted);margin-top:8px}
details.meth{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);margin-bottom:12px}
details.meth summary{cursor:pointer;padding:14px 18px;font-weight:700;font-size:14px;list-style:none}
details.meth summary::-webkit-details-marker{display:none}
details.meth summary::before{content:'\25B8';margin-inline-end:9px;color:var(--brand);display:inline-block;transition:.15s}
details.meth[open] summary::before{transform:rotate(90deg)}
details.meth .mbody{padding:0 18px 16px;font-size:13px;color:var(--muted)}details.meth .mbody h4{color:var(--ink);font-size:13px;margin:13px 0 5px}details.meth a{color:var(--brand)}
footer.foot{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-size:11.5px;color:var(--faint)}
@media (max-width:860px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2,.io2,.insights{grid-template-columns:1fr}.row{grid-template-columns:130px 1fr auto}.stackrow{grid-template-columns:120px 1fr}}
@media print{body{background:#fff}.controls,.banner,.tabs{display:none}.tab-panel{display:block!important}
.card,.kpi,details.meth{box-shadow:none;border-color:#ccc}details.meth summary{display:none}details.meth .mbody{display:block!important}
header.top{background:var(--brand)!important}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}section.block{break-inside:avoid}}
"""

JS = r"""
const RAW=JSON.parse(document.getElementById('cw-data').textContent);
const RATE0=RAW.meta.defaultRate, KMIN=RAW.meta.kThreshold||3;
const PILL_COLOR={'Transformation':'var(--t)','Revenue Growth':'var(--rg)','Cost Reduction':'var(--cr)','Risk Mitigation':'var(--rm)'};
const CAT_COLOR={'Analysis & Research':'var(--c0)','Write or debug code':'var(--c1)','Document & content creation':'var(--c2)','Meeting workflows':'var(--c3)','Specialized workflows':'var(--c4)','General assistance / Other':'var(--c6)','Email workflows':'var(--c5)','Communication workflows':'var(--c7)'};
const PAL=['var(--c0)','var(--c1)','var(--c2)','var(--c3)','var(--c4)','var(--c5)','var(--c6)','var(--c7)'];
const posted=RAW.members.filter(m=>m.posted);
const state={snapshot:RAW.snapshots[RAW.snapshots.length-1].id,rate:RATE0,tab:'overview'};
const el=id=>document.getElementById(id);
const money=v=>'$'+Math.round(v).toLocaleString('en-US');
const hrs=h=>h.toFixed(1)+' h';
const pct=(n,d)=>d>0?Math.round(n/d*100):0;
const wk=h=>(h/40).toFixed(1);
function snapIds(){return state.snapshot==='ALL'?RAW.snapshots.map(s=>s.id):[state.snapshot];}
function snapLabel(){if(state.snapshot==='ALL')return 'All snapshots';const s=RAW.snapshots.find(x=>x.id===state.snapshot);return s.label+(s.periodStart?' ('+s.periodStart+' → '+s.periodEnd+')':'');}
function activeMembers(){const ids=snapIds();return posted.filter(m=>ids.some(id=>m.reports[id]));}
function memberReports(m){return snapIds().map(id=>m.reports[id]).filter(Boolean);}

function aggregate(members){
  const a={n:members.length,head:{timeTyp:0,timeLow:0,timeHigh:0,expertH:0,assistedH:0,sessions:0,runTasks:0,deliverables:0,activeDays:0},
    cat:{},pil:{},proc:{},role:{},skill:{},deliv:{},inputs:{},outputs:{},inA:0,outP:0};
  let lowN=0,highN=0;
  members.forEach(m=>memberReports(m).forEach(r=>{
    const h=r.headline;for(const k in a.head){if(k!=='timeLow'&&k!=='timeHigh')a.head[k]+=(h[k]||0);}
    if(h.timeLow!=null){a.head.timeLow+=h.timeLow;lowN++;} if(h.timeHigh!=null){a.head.timeHigh+=h.timeHigh;highN++;}
    r.categories.forEach(c=>{const o=a.cat[c.name]||(a.cat[c.name]={tasks:0,hours:0});o.tasks+=c.tasks;o.hours+=c.hours;});
    r.pillars.forEach(p=>{const o=a.pil[p.name]||(a.pil[p.name]={hours:0,sessions:0});o.hours+=p.hours;o.sessions+=(p.sessions||0);});
    r.processes.forEach(p=>{const o=a.proc[p.name]||(a.proc[p.name]={sessions:0,hours:0});o.sessions+=p.sessions;o.hours+=p.hours;});
    r.roles.forEach(x=>{const o=a.role[x.name]||(a.role[x.name]={hours:0});o.hours+=x.hours;});
    r.skills.forEach(x=>{const o=a.skill[x.name]||(a.skill[x.name]={deliverables:0,sessions:0,hours:0});o.deliverables+=x.deliverables;o.sessions+=x.sessions;o.hours+=x.hours;});
    r.deliverables.forEach(d=>{const o=a.deliv[d.type]||(a.deliv[d.type]={count:0,hours:0,skills:new Set()});o.count+=d.count;o.hours+=d.hours;(d.skills||[]).forEach(s=>o.skills.add(s));});
    (r.io.inputs||[]).forEach(i=>a.inputs[i.type]=(a.inputs[i.type]||0)+i.count);
    (r.io.outputs||[]).forEach(i=>a.outputs[i.type]=(a.outputs[i.type]||0)+i.count);
    a.inA+=r.io.inputsAnalyzed||0;a.outP+=r.io.outputsProduced||0;
  }));
  if(!lowN)a.head.timeLow=a.head.timeTyp; if(!highN)a.head.timeHigh=a.head.timeTyp;
  return a;
}
const toArr=o=>Object.keys(o).map(k=>Object.assign({name:k},o[k]));
const sortH=a=>a.sort((x,y)=>y.hours-x.hours);
function barRow(label,p,color,v){return `<div class="row"><div class="rl" title="${label}">${label}</div><div class="rbar"><div class="rfill" style="width:${p}%;background:${color}"></div></div><div class="rv">${v}</div></div>`;}

function render(){
  const R=state.rate,mem=activeMembers(),A=aggregate(mem),H=A.head;
  const teamSpeed=H.assistedH>0?H.expertH/H.assistedH:0;
  const catArr=sortH(toArr(A.cat)),totCatH=catArr.reduce((s,x)=>s+x.hours,0);
  const pilArr=sortH(toArr(A.pil)),totPilH=pilArr.reduce((s,x)=>s+x.hours,0);
  const procArr=sortH(toArr(A.proc)),totProcH=procArr.reduce((s,x)=>s+x.hours,0);
  el('ctxline').textContent=`${snapLabel()} · ${mem.length} contributor${mem.length===1?'':'s'} · $${R}/hr`;

  // Overview KPIs
  el('ov-kpis').innerHTML=[
    {l:'Time saved',v:hrs(H.timeTyp),s:`≈ ${wk(H.timeTyp)} expert work-weeks · ${hrs(H.timeLow)}–${hrs(H.timeHigh)}`,h:1},
    {l:'Value / cost reduction',v:money(H.expertH*R),s:`at $${R}/hr · ${money(H.timeLow*R)}–${money(H.timeHigh*R)}`,h:1},
    {l:'Team speed multiplier',v:teamSpeed.toFixed(1)+'×',s:`${hrs(H.expertH)} expert ÷ ${hrs(H.assistedH)} hands-on`,h:1},
    {l:'Contributors',v:mem.length,s:`posted this period`,h:1},
    {l:'Sessions',v:H.sessions,s:`${H.runTasks} run tasks`},{l:'Deliverables',v:H.deliverables,s:'produced'},
    {l:'Active days',v:H.activeDays,s:`person-days · ${(H.activeDays?H.expertH/H.activeDays:0).toFixed(1)} h/day`},
    {l:'Hands-on time',v:hrs(H.assistedH),s:`vs ${hrs(H.expertH)} expert-equivalent`},
  ].map(k=>`<div class="kpi${k.h?' hero':''}"><div class="k-l">${k.l}</div><div class="k-v">${k.v}</div><div class="k-s">${k.s}</div></div>`).join('');

  const ins=[];
  ins.push({i:'⏱️',t:`The team reclaimed <b>${hrs(H.timeTyp)}</b> (~${money(H.expertH*R)}) — about <b>${wk(H.timeTyp)} expert work-weeks</b> at <b>${teamSpeed.toFixed(1)}×</b> leverage over hands-on time.`});
  if(catArr[0])ins.push({i:'🎯',t:`Most leverage is in <b>${catArr[0].name}</b> — <b>${pct(catArr[0].hours,totCatH)}%</b> of saved time.`});
  if(procArr[0])ins.push({i:'🏭',t:`The biggest business process is <b>${procArr[0].name}</b> — <b>${pct(procArr[0].hours,totProcH)}%</b> of the work.`});
  if(pilArr[0])ins.push({i:'💼',t:`<b>${pilArr[0].name}</b> is the dominant value pillar at <b>${pct(pilArr[0].hours,totPilH)}%</b> of saved hours.`});
  ins.push({i:'🧭',t:`Read as <b>modeled tool-impact, not performance scores</b> — alongside team context (project phase, seasonality). Anonymized: nothing is shown at an individual level.`});
  el('ov-insights').innerHTML=ins.map(x=>`<div class="ins"><div class="ic">${x.i}</div><div class="tx">${x.t}</div></div>`).join('');

  // Impact & Value
  renderDonut('im-pillars',pilArr,totPilH,R);
  (function(){const mx=Math.max(1,...catArr.map(a=>a.hours));el('im-categories').innerHTML=catArr.map(c=>{const band=RAW.meta.categoryBands[c.name]?`<span style="font-size:11px;color:var(--faint)"> &nbsp;band ${RAW.meta.categoryBands[c.name]} min/run</span>`:'';
    return barRow(c.name,c.hours/mx*100,CAT_COLOR[c.name]||'var(--c0)',`<b>${hrs(c.hours)}</b> · ${money(c.hours*R)} · ${c.tasks} tasks · ${pct(c.hours,totCatH)}%`)+`<div style="margin:-4px 0 6px 191px">${band}</div>`;}).join('');})();
  (function(){const arr=sortH(toArr(A.role)),mx=Math.max(1,...arr.map(a=>a.hours));el('im-roles').innerHTML=arr.length?arr.map((x,i)=>barRow(x.name,x.hours/mx*100,PAL[i%PAL.length],`<b>${hrs(x.hours)}</b> · ${money(x.hours*R)}`)).join(''):'<div class="sec-note">No role data in these posts.</div>';})();
  (function(){const arr=sortH(toArr(A.deliv)),tc=arr.reduce((s,x)=>s+x.count,0),th=arr.reduce((s,x)=>s+x.hours,0);
    el('im-deliv').innerHTML=`<table class="dt"><thead><tr><th>Deliverable type</th><th class="r">Count</th><th class="r">Hours</th><th class="r">Value</th><th>Skills behind them</th></tr></thead><tbody>`+
      arr.map(d=>`<tr><td><b>${d.name}</b></td><td class="r">${d.count}</td><td class="r">${hrs(d.hours)}</td><td class="r">${money(d.hours*R)}</td><td>${[...d.skills].sort().map(s=>`<span class="pill">${s}</span>`).join('')}</td></tr>`).join('')+
      `<tr class="tot"><td>Total</td><td class="r">${tc}</td><td class="r">${hrs(th)}</td><td class="r">${money(th*R)}</td><td></td></tr></tbody></table>`;})();

  // How Cowork is used — process leads
  (function(){el('wk-proc').innerHTML=`<table class="dt"><thead><tr><th>Business process</th><th class="r">Sessions</th><th class="r">Hours</th><th class="r">Value</th><th class="r">% time</th></tr></thead><tbody>`+
      procArr.map(p=>`<tr><td>${p.name}</td><td class="r">${p.sessions}</td><td class="r">${hrs(p.hours)}</td><td class="r">${money(p.hours*R)}</td><td class="r">${pct(p.hours,totProcH)}%</td></tr>`).join('')+
      `<tr class="tot"><td>Total</td><td class="r">${procArr.reduce((s,x)=>s+x.sessions,0)}</td><td class="r">${hrs(totProcH)}</td><td class="r">${money(totProcH*R)}</td><td class="r">100%</td></tr></tbody></table>`;})();
  (function(){const arr=sortH(toArr(A.skill));el('wk-skills').innerHTML=`<table class="dt"><thead><tr><th>Skill</th><th class="r">Deliverables</th><th class="r">Sessions</th><th class="r">Hours</th><th class="r">Value</th></tr></thead><tbody>`+
      arr.map(s=>`<tr><td>${s.name}</td><td class="r">${s.deliverables}</td><td class="r">${s.sessions}</td><td class="r">${hrs(s.hours)}</td><td class="r">${money(s.hours*R)}</td></tr>`).join('')+`</tbody></table>`;})();
  renderCatMix('wk-stack',mem,catArr.map(c=>c.name));
  (function(){const inA=Object.keys(A.inputs).map(k=>({t:k,c:A.inputs[k]})).sort((a,b)=>b.c-a.c),outP=Object.keys(A.outputs).map(k=>({t:k,c:A.outputs[k]})).sort((a,b)=>b.c-a.c);
    const mxi=Math.max(1,...inA.map(x=>x.c)),mxo=Math.max(1,...outP.map(x=>x.c));
    const col=(arr,mx,c)=>arr.map(x=>`<div class="row"><div class="rl">${x.t}</div><div class="rbar"><div class="rfill" style="width:${x.c/mx*100}%;background:${c}"></div></div><div class="rv"><b>${x.c}</b></div></div>`).join('')||'<div class="sec-note">—</div>';
    el('wk-io').innerHTML=`<div class="io2"><div><h4>Analyzed · ${A.inA} inputs</h4>${col(inA,mxi,'var(--c4)')}</div><div><h4>Produced · ${A.outP} outputs</h4>${col(outP,mxo,'var(--c1)')}</div></div><div class="sec-note" style="margin-top:12px">${A.inA} sources analyzed → ${A.outP} deliverables produced · ~${(A.outP?A.inA/A.outP:0).toFixed(1)} sources per deliverable.</div>`;})();

  renderTrend('tr-trend',R);
}

// k-anonymity: a Role breaks out only when >= KMIN members share it; else combine.
function renderCatMix(id,mem,cats){
  const groups={};mem.forEach(m=>{const r=m.role||'Unspecified';(groups[r]=groups[r]||[]).push(m);});
  let bars=[],pooled=[];
  Object.keys(groups).forEach(r=>{groups[r].length>=KMIN?bars.push({label:r,members:groups[r]}):pooled=pooled.concat(groups[r]);});
  if(pooled.length)bars.push({label:bars.length?'Other contributors (combined)':'Team (combined)',members:pooled});
  const rows=bars.map(b=>{const cm={};b.members.forEach(m=>memberReports(m).forEach(r=>r.categories.forEach(k=>cm[k.name]=(cm[k.name]||0)+k.hours)));
    const tot=Object.values(cm).reduce((s,v)=>s+v,0)||1;
    const segs=cats.filter(c=>cm[c]).map(c=>`<div class="stackseg" style="width:${cm[c]/tot*100}%;background:${CAT_COLOR[c]||'var(--c6)'}" title="${c}: ${hrs(cm[c])}"></div>`).join('');
    return `<div class="stackrow"><div class="rl" style="font-size:12.5px">${b.label} · ${b.members.length}</div><div class="stackbar">${segs}</div></div>`;}).join('');
  const leg=cats.map(c=>`<div class="li"><span class="sw" style="background:${CAT_COLOR[c]||'var(--c6)'}"></span><span class="lt" style="font-size:12px">${c}</span></div>`).join('');
  el(id).innerHTML=rows+`<div class="legend" style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:6px 14px">${leg}</div>`+
    `<div class="sec-note" style="margin-top:10px">Privacy rule: a role breaks out only when <b>${KMIN}+</b> contributors share it; otherwise contributors are combined into one bar. Never shown individually.</div>`;
}
function renderDonut(id,arr,tot,R){const r=58,c=2*Math.PI*r;let off=0;
  const segs=arr.map((p,i)=>{const f=tot>0?p.hours/tot:0,col=PILL_COLOR[p.name]||PAL[i%PAL.length];const s=`<circle r="${r}" cx="80" cy="80" fill="none" stroke="${col}" stroke-width="22" stroke-dasharray="${(f*c).toFixed(2)} ${(c-f*c).toFixed(2)}" stroke-dashoffset="${(-off*c).toFixed(2)}" transform="rotate(-90 80 80)"></circle>`;off+=f;return s;}).join('');
  const leg=arr.map((p,i)=>{const col=PILL_COLOR[p.name]||PAL[i%PAL.length];return `<div class="li"><span class="sw" style="background:${col}"></span><span class="lt">${p.name}</span><span class="lv">${hrs(p.hours)} · ${money(p.hours*R)} · ${pct(p.hours,tot)}%</span></div>`;}).join('');
  el(id).innerHTML=`<div class="donut-wrap"><svg width="160" height="160" viewBox="0 0 160 160"><circle r="${r}" cx="80" cy="80" fill="none" stroke="var(--line)" stroke-width="22"></circle>${segs}<text x="80" y="74" text-anchor="middle" font-size="22" font-weight="700" fill="var(--ink)">${hrs(tot)}</text><text x="80" y="92" text-anchor="middle" font-size="10" fill="var(--muted)">total</text></svg><div class="legend">${leg}</div></div>`;}
function renderTrend(id,R){
  const series=RAW.snapshots.map(s=>{const ms=posted.filter(m=>m.reports[s.id]);const h=ms.reduce((t,m)=>t+(m.reports[s.id].headline.timeTyp||0),0);return {label:s.periodEnd||s.id,hours:h,value:h*R,n:ms.length};});
  if(series.length<=1){const s=series[0]||{hours:0,value:0,n:0,label:''};
    el(id).innerHTML=`<div style="display:flex;gap:30px;align-items:baseline;flex-wrap:wrap"><div><div class="k-v" style="font-size:30px">${hrs(s.hours)}</div><div class="k-s">time saved · ${money(s.value)} · ${s.n} contributors · ${s.label}</div></div></div><div class="trend-empty">📈 First snapshot. Each ${RAW.meta.cadenceDays}-day cycle adds one point here so you can see whether team impact is growing. Cowork is used for specific tasks, so this tracks fortnight-over-fortnight totals — not daily usage.</div>`;return;}
  const W=1080,Hh=140,pad=32,mx=Math.max(1,...series.map(s=>s.hours)),x=i=>pad+i*(W-2*pad)/(series.length-1),y=v=>Hh-pad-(v/mx)*(Hh-2*pad);
  const pts=series.map((s,i)=>`${x(i).toFixed(1)},${y(s.hours).toFixed(1)}`).join(' ');
  const dots=series.map((s,i)=>`<circle cx="${x(i).toFixed(1)}" cy="${y(s.hours).toFixed(1)}" r="4" fill="var(--brand)"></circle><text x="${x(i).toFixed(1)}" y="${Hh-8}" text-anchor="middle" font-size="10" fill="var(--muted)">${s.label}</text>`).join('');
  el(id).innerHTML=`<svg class="svgtrend" viewBox="0 0 ${W} ${Hh}" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="var(--brand)" stroke-width="2.5"></polyline>${dots}</svg><div class="sec-note">Total time saved per fortnight. Cowork is used for specific tasks — this is a cycle-over-cycle trend, not daily activity.</div>`;}

function build(){
  const ss=el('snapSel');RAW.snapshots.forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.label+(s.periodEnd?' · '+s.periodEnd:'');ss.appendChild(o);});
  if(RAW.snapshots.length>1){const o=document.createElement('option');o.value='ALL';o.textContent='All snapshots';ss.appendChild(o);}
  ss.value=state.snapshot;ss.addEventListener('change',()=>{state.snapshot=ss.value;render();});
  const ri=el('rateInput');ri.value=state.rate;ri.addEventListener('input',()=>{const v=parseFloat(ri.value);state.rate=(isFinite(v)&&v>0)?v:0;render();});
  el('resetBtn').addEventListener('click',()=>{state.rate=RATE0;state.snapshot=RAW.snapshots[RAW.snapshots.length-1].id;ss.value=state.snapshot;ri.value=RATE0;render();});
  el('printBtn').addEventListener('click',()=>window.print());
  document.querySelectorAll('.tab-btn').forEach(b=>b.addEventListener('click',()=>{state.tab=b.getAttribute('data-tab');document.querySelectorAll('.tab-btn').forEach(x=>x.classList.toggle('on',x===b));document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('on',p.id==='tab-'+state.tab));}));
}
build();render();
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark">
<title>Cowork ROI — Team Dashboard</title>
<style>__CSS__</style>
</head>
<body>
<header class="top"><div class="wrap">
  <div class="brand"><svg width="22" height="22" viewBox="0 0 23 23" aria-hidden="true"><rect x="1" y="1" width="10" height="10" fill="#F25022"></rect><rect x="12" y="1" width="10" height="10" fill="#7FBA00"></rect><rect x="1" y="12" width="10" height="10" fill="#00A4EF"></rect><rect x="12" y="12" width="10" height="10" fill="#FFB900"></rect></svg><span class="nm">Microsoft Copilot Cowork</span></div>
  <h1>Cowork ROI — Team Dashboard</h1>
  <p class="sub">__TEAM__ — team impact &amp; how Cowork is used</p>
  <p class="gen">Generated __GENERATED__ · <span id="ctxline"></span></p>
</div></header>
<div class="wrap">
  <div class="banner"><span>🔒</span><span><b>Anonymized — numbers only.</b> Built from teammates' de-identified Cowork posts (no names, files, or prompts). Modeled tool-impact estimates for status reporting, <b>not</b> individual performance. Nothing is shown at an individual level; a Role breaks out only when <b>__KTHRESH__+</b> contributors share it. Small-team (v1) view — read with team context.</span></div>
  <div class="controls">
    <div class="ctl"><label for="snapSel">Period</label><select id="snapSel"></select></div>
    <div class="ctl"><label for="rateInput">Hourly rate</label><div class="rate-in"><span>$</span><input id="rateInput" type="number" min="1" step="1" inputmode="numeric"><span>/hr</span></div></div>
    <div class="spacer"></div>
    <button class="btn" id="resetBtn" type="button">Reset</button>
    <button class="btn primary" id="printBtn" type="button">Save / Print PDF</button>
  </div>
  <div class="tabs">
    <button class="tab-btn on" type="button" data-tab="overview">Overview</button>
    <button class="tab-btn" type="button" data-tab="impact">Impact &amp; Value</button>
    <button class="tab-btn" type="button" data-tab="work">How Cowork is used</button>
    <button class="tab-btn" type="button" data-tab="trends">Trends</button>
    <button class="tab-btn" type="button" data-tab="method">Glossary &amp; method</button>
  </div>

  <div class="tab-panel on" id="tab-overview">
    <section class="block"><h2 class="sec"><span class="dot"></span>What the data says</h2><p class="sec-note">Auto-generated reading of the team's posts — updates with the rate control.</p><div class="insights" id="ov-insights"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Team impact at a glance</h2><div class="kpis" id="ov-kpis"></div></section>
  </div>

  <div class="tab-panel" id="tab-impact">
    <section class="block"><h2 class="sec"><span class="dot"></span>Business value pillars</h2><p class="sec-note">Where the saved hours land. Value = hours × the rate above.</p><div class="card" id="im-pillars"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Where the time went — by task category</h2><p class="sec-note">With the research-anchored time bands (minutes saved per run).</p><div class="card" id="im-categories"></div></section>
    <section class="block"><div class="grid2">
      <div class="card"><h3>Roles Cowork stood in for</h3><p class="hint">Roles a services firm would have billed.</p><div id="im-roles"></div></div>
      <div class="card"><h3>Deliverables produced — by type</h3><p class="hint">The output the team shipped, with the skills behind each type.</p><div id="im-deliv"></div></div>
    </div></section>
  </div>

  <div class="tab-panel" id="tab-work">
    <section class="block"><h2 class="sec"><span class="dot"></span>Work by business process</h2><p class="sec-note">Grouped into the shared canonical set (mirrors the Member skill). This is the spine of the tab — what the team actually does with Cowork.</p><div class="card" id="wk-proc"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Skills applied</h2><p class="sec-note">Curated to the shared ~30-skill canonical vocabulary.</p><div class="card" id="wk-skills"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Category mix</h2><p class="sec-note">How saved time splits across task categories — grouped by Role where privacy allows.</p><div class="card" id="wk-stack"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Analyzed → Produced</h2><p class="sec-note">Inputs the team analyzed vs. deliverables produced, by type.</p><div class="card" id="wk-io"></div></section>
  </div>

  <div class="tab-panel" id="tab-trends">
    <section class="block"><h2 class="sec"><span class="dot"></span>Time saved over time</h2><p class="sec-note">Minimal by design — one point per posting cycle. Is team impact growing?</p><div class="card" id="tr-trend"></div></section>
  </div>

  <div class="tab-panel" id="tab-method">
    <details class="meth" open><summary>How to read this dashboard</summary><div class="mbody">
      <p>Built by aggregating the de-identified Cowork ROI posts teammates publish to the team channel. Metric &amp; section titles match the <b>Copilot ROI Report</b> and <b>Copilot ROI Member</b> skills. Treat numbers as <b>directional</b>: Cowork isn't the only factor behind any change — consider project phase and seasonality. This is a small, homogeneous-team (v1) view.</p>
      <h4>Privacy</h4>
      <p><b>Nothing is shown at an individual level.</b> Members appear only as counts. The one per-attribute view (category mix) breaks a Role out only when <b>__KTHRESH__+</b> contributors share it; otherwise they collapse into a single combined bar. The only attribute used is the directory <b>Role</b> (job title) that a teammate's post carries — never names, never country, never file names.</p>
      <h4>Value model</h4>
      <p>Time saved = Σ run tasks × the research band per task category (minutes saved/run). <b>Value = expert-equivalent hours × hourly rate</b> (default $__RATE__/hr; adjust live). <b>Speed multiplier</b> = expert ÷ modeled hands-on hours. All figures come from the posts; the dashboard only re-totals and re-prices them.</p>
      <h4>Value pillars</h4>
      <p><b>Revenue Growth</b> (top-line), <b>Cost Reduction</b> (cost base), <b>Risk Mitigation</b> (protect value), <b>Transformation</b> (new ways of working / AI adoption). Shared crosswalk across all three ROI skills.</p>
      <h4>Research bands (minutes: low / typical / high per run)</h4>
      <p>Analysis &amp; Research 30/67/92 · Write or debug code 30/56/96 · Document &amp; content 12/24/42 · Meeting 12/31/43 · Email 3/7/12 · Communication 2/4/6 · Specialized 10/25/40 · General 2/5/8. Sources: Stanford-WB (SSRN 5136877), Microsoft Research 2026 (DiD n=72,186), Noy &amp; Zhang (Science 2023), Cambon et al. (MSR 2024), Cui et al. (CACM 2024), Brynjolfsson, Li &amp; Raymond (QJE 2025), Forrester TEI 2024.</p>
    </div></details>
  </div>

  <footer class="foot">Generated by Microsoft Copilot Cowork · Cowork ROI Team Dashboard skill · anonymized &amp; team-safe — numbers only, no names. Modeled estimates of tool-assisted time savings, not audited financials or performance metrics.</footer>
</div>
<script type="application/json" id="cw-data">__DATA__</script>
<script>__JS__</script>
</body>
</html>
"""

def main(a):
    data = json.load(open(a.inp, encoding="utf-8"))
    html = (TEMPLATE.replace("__CSS__", CSS).replace("__JS__", JS)
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__TEAM__", data["meta"].get("team", "Team"))
            .replace("__GENERATED__", str(data["meta"].get("generated", "")))
            .replace("__RATE__", str(data["meta"].get("defaultRate", 72)))
            .replace("__KTHRESH__", str(data["meta"].get("kThreshold", 3))))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build_dashboard] wrote {a.out} ({len(html)} bytes)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/team_data.json")
    ap.add_argument("--out", default="output/cowork-team-roi-dashboard.html")
    main(ap.parse_args())
