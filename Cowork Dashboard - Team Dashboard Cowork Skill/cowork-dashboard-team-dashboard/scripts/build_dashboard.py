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
  Impact & Value    — value pillars, task categories ($), roles (+ skills as collapsible detail),
                      deliverables by FILE FORMAT.
  How Cowork is used— business process accordion: each row EXPANDS to its deliverable formats + skills
                      (skills nest in a sub-expand when long); category mix (k-anon), analyzed->produced.
  Disclaimer        — "modeled tool-impact, not performance" note lives in the blue header (small print).
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
header.top .disc{font-size:11px;line-height:1.45;opacity:.9;margin:10px 0 0;max-width:940px}header.top .disc b{font-weight:700}
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
h2.sec{font-size:16px;font-weight:700;margin:0 0 3px;display:flex;align-items:center;gap:9px;position:relative;flex-wrap:wrap}
h2.sec .dot{width:9px;height:9px;border-radius:3px;background:var(--brand)}
.sec-note{font-size:12.5px;color:var(--muted);margin:0 0 13px}
/* Click-to-reveal "?" helper next to a section title — a short plain-language explanation, in-page. */
.help{width:17px;height:17px;border-radius:50%;border:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:10.5px;font-weight:700;line-height:1;cursor:pointer;padding:0;display:inline-flex;align-items:center;justify-content:center;flex:none}
.help:hover{border-color:var(--brand);color:var(--brand)}
.helppop{position:absolute;top:28px;inset-inline-start:0;z-index:40;max-width:460px;background:var(--panel);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);padding:11px 14px;font-size:12.5px;font-weight:400;color:var(--muted);line-height:1.5;display:none}
.helppop.on{display:block}.helppop b{color:var(--ink);font-weight:650}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi .k-l{font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700}
.kpi .k-v{font-size:25px;font-weight:750;margin:5px 0 2px;letter-spacing:-.3px}.kpi .k-s{font-size:12px;color:var(--muted)}
.kpi.hero{background:linear-gradient(135deg,var(--soft),var(--panel));border-color:#cfe3f5}
@media (prefers-color-scheme:dark){.kpi.hero{border-color:#274a68}}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px 18px 15px;box-shadow:var(--shadow)}
.card h3{font-size:14px;margin:0 0 4px;font-weight:700}.card .hint{font-size:11.5px;color:var(--faint);margin:0 0 12px}
/* Fixed value column (232px) so the gray track is the SAME length on every row; .rc = count rows (narrow value). */
.row{display:grid;grid-template-columns:180px 1fr 232px;align-items:center;gap:11px;padding:5px 0}
.row.rc{grid-template-columns:180px 1fr 56px}
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
details.drill{margin-top:13px;border-top:1px dashed var(--line);padding-top:9px}
details.drill>summary{cursor:pointer;font-size:12.5px;font-weight:650;color:var(--brand);list-style:none;user-select:none}
details.drill>summary::-webkit-details-marker{display:none}
details.drill>summary::before{content:'\25B8';margin-inline-end:7px;display:inline-block;transition:.15s;color:var(--brand)}
details.drill[open]>summary::before{transform:rotate(90deg)}
details.drill .dbody{padding-top:11px}
.dgrp{margin:0 0 15px}.dgrp .dgrp-h{font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.3px;margin:0 0 5px}
/* Expandable business-process accordion (each row opens to its deliverable formats + skills). */
.acct{border:1px solid var(--line);border-radius:11px;overflow:hidden}
.acct-h,.acct-tot,.acct-row>summary{display:grid;grid-template-columns:1fr 92px 78px 92px 66px;gap:10px;align-items:center;padding:10px 14px;font-size:13px}
.acct-h{background:var(--bg);font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700}
.acct-h .r,.acct-row>summary .r,.acct-tot .r{text-align:right;font-variant-numeric:tabular-nums}
.acct-row{border-top:1px solid var(--line)}
.acct-row>summary{cursor:pointer;list-style:none;user-select:none}
.acct-row>summary::-webkit-details-marker{display:none}
.acct-row>summary .ap{position:relative;padding-inline-start:17px;font-weight:600}
.acct-row>summary .ap::before{content:'\25B8';position:absolute;inset-inline-start:0;top:0;color:var(--brand);transition:transform .15s}
.acct-row[open]>summary .ap::before{transform:rotate(90deg)}
.acct-row[open]>summary{background:var(--soft)}
.acct-row>.acct-body{padding:13px 14px 15px;background:var(--bg);border-top:1px dashed var(--line)}
.acct-tot{border-top:2px solid var(--line);background:var(--bg);font-weight:700}
.skline{margin-top:11px;font-size:12.5px}.skline .sklbl{display:inline-block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;color:var(--faint);margin:0 8px 4px 0}
details.drill.sub{margin-top:11px;border-top:1px dashed var(--line);padding-top:9px}details.drill.sub>summary{font-size:12px}
/* Flattened per-process deliverable list: distinct deliverables, one level indented, format inline. */
.dlv-list{margin-inline-start:16px;border-inline-start:2px solid var(--line);padding-inline-start:12px}
.dlv{display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid var(--line)}
.dlv:last-child{border-bottom:none}
.dlv-nm{font-size:13px;overflow:hidden;text-overflow:ellipsis}
.fmt-tag{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;color:var(--brand-d);background:var(--soft);border-radius:6px;padding:2px 8px;white-space:nowrap}
.dlv-v{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
@media (max-width:860px){.acct-h,.acct-tot,.acct-row>summary{grid-template-columns:1fr 50px 56px 66px 44px;gap:6px;font-size:12px}}
footer.foot{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-size:11.5px;color:var(--faint)}
@media (max-width:860px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2,.io2,.insights{grid-template-columns:1fr}.row{grid-template-columns:118px 1fr 132px}.row.rc{grid-template-columns:118px 1fr 46px}.row .rv{white-space:normal}.stackrow{grid-template-columns:120px 1fr}.helppop{max-width:78vw}}
@media print{body{background:#fff}.controls,.banner,.tabs{display:none}.tab-panel{display:block!important}
.card,.kpi,details.meth{box-shadow:none;border-color:#ccc}details.meth summary{display:none}details.meth .mbody{display:block!important}
details.drill .dbody{display:block!important}.acct-row>.acct-body{display:block!important}
header.top{background:var(--brand)!important}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}section.block{break-inside:avoid}}
"""

JS = r"""
const RAW=JSON.parse(document.getElementById('cw-data').textContent);
const RATE0=RAW.meta.defaultRate, KMIN=RAW.meta.kThreshold||3;
const PILL_COLOR={'Transformation':'var(--t)','Revenue Growth':'var(--rg)','Cost Reduction':'var(--cr)','Risk Mitigation':'var(--rm)'};
const CAT_COLOR={'Analysis & Research':'var(--c0)','Write or debug code':'var(--c1)','Document & content creation':'var(--c2)','Meeting workflows':'var(--c3)','Specialized workflows':'var(--c4)','General assistance / Other':'var(--c6)','Email workflows':'var(--c5)','Communication workflows':'var(--c7)'};
const PAL=['var(--c0)','var(--c1)','var(--c2)','var(--c3)','var(--c4)','var(--c5)','var(--c6)','var(--c7)'];
// Deliverable types → concrete file formats (types like Text/File/Deck/Document overlap; formats don't).
const FMT={'Deck':'PPTX','Slides':'PPTX','Presentation':'PPTX','Slide deck':'PPTX','Document':'Word','Doc':'Word','Word':'Word','Spreadsheet':'Excel / CSV','Excel':'Excel / CSV','CSV':'Excel / CSV','Web page':'HTML','Webpage':'HTML','Web':'HTML','HTML':'HTML','Text':'Text / MD','Markdown':'Text / MD','Image':'Image','PDF':'PDF','File':'File (other)'};
const fmtLabel=t=>FMT[t]||t;
// Display-only remap of grouped process labels (taxonomy files stay byte-for-byte identical).
const PROC_LABEL={'Skill Development':'Cowork Skill Development'};
const procLabel=n=>PROC_LABEL[n]||n;
const posted=RAW.members.filter(m=>m.posted);
const state={snapshot:RAW.snapshots[RAW.snapshots.length-1].id,rate:RATE0,tab:'overview'};
const el=id=>document.getElementById(id);
const money=v=>'$'+Math.round(v).toLocaleString('en-US');
const hrs=h=>h.toFixed(1)+' h';
const pct=(n,d)=>d>0?Math.round(n/d*100):0;
const wk=h=>(h/40).toFixed(1);
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function snapIds(){return state.snapshot==='ALL'?RAW.snapshots.map(s=>s.id):[state.snapshot];}
function snapLabel(){if(state.snapshot==='ALL')return 'All snapshots';const s=RAW.snapshots.find(x=>x.id===state.snapshot);return s.label+(s.periodStart?' ('+s.periodStart+' → '+s.periodEnd+')':'');}
function activeMembers(){const ids=snapIds();return posted.filter(m=>ids.some(id=>m.reports[id]));}
function memberReports(m){return snapIds().map(id=>m.reports[id]).filter(Boolean);}

function aggregate(members){
  const a={n:members.length,head:{timeTyp:0,timeLow:0,timeHigh:0,expertH:0,assistedH:0,sessions:0,runTasks:0,deliverables:0,activeDays:0},
    cat:{},pil:{},proc:{},role:{},skill:{},deliv:{},delivDetail:[],inputs:{},outputs:{},inA:0,outP:0};
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
    (r.deliverablesDetail||[]).forEach(d=>a.delivDetail.push(d));
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
// Reach = how many active contributors used a task category. Aggregate count only — identities never shown.
// Privacy floor: below KMIN (k-anonymity) the exact count is withheld and shown as "<K".
function catReach(members,name){let c=0;members.forEach(m=>{if(memberReports(m).some(r=>(r.categories||[]).some(k=>k.name===name&&((k.hours||0)>0||(k.tasks||0)>0))))c++;});return c;}
function reachLabel(count,total){return count>=KMIN?`used by ${count} of ${total} contributors`:`used by &lt;${KMIN} contributors`;}
// Per-process detail shown inside each expandable business-process row: the distinct DELIVERABLES the
// process produced (file format shown inline on each) + the SKILLS behind them (skills collapse into a
// sub-expand when the list is long).
function procDetailHTML(items,R){
  if(!items||!items.length)
    return `<div class="sec-note">No per-item detail for this process in the current posts. Deliverable names are de-identified by the Member skill (no file names); the list appears here when a teammate's post carries it.</div>`;
  // Distinct NAMED deliverables list individually; UNNAMED ones (a teammate's post carried only the
  // file type, not a de-identified name) collapse into ONE row per format, e.g. "HTML · 5 deliverables".
  const named=[],byfmt={};
  items.forEach(d=>{
    const nm=(d.name&&String(d.name).trim())?String(d.name).trim():'';
    if(nm){named.push({nm:nm,tag:fmtLabel(d.type),hours:d.hours||0});}
    else{const f=fmtLabel(d.type);const o=byfmt[f]||(byfmt[f]={fmt:f,count:0,hours:0});o.count++;o.hours+=(d.hours||0);}
  });
  const rows=named.concat(Object.keys(byfmt).map(k=>{const o=byfmt[k];
      return {nm:o.fmt,tag:o.count+' deliverable'+(o.count!==1?'s':''),hours:o.hours};}))
    .sort((a,b)=>(b.hours||0)-(a.hours||0));
  const list=rows.map(d=>`<div class="dlv"><span class="dlv-nm" title="${esc(d.nm)}">${esc(d.nm)}</span><span class="fmt-tag">${esc(d.tag)}</span><span class="dlv-v">${hrs(d.hours||0)} · ${money((d.hours||0)*R)}</span></div>`).join('');
  const sk={};items.forEach(d=>(d.skills||[]).forEach(s=>sk[s]=(sk[s]||0)+1));
  const skArr=Object.keys(sk).map(k=>({name:k,n:sk[k]})).sort((a,b)=>b.n-a.n);
  const skPills=skArr.map(s=>`<span class="pill">${esc(s.name)}${s.n>1?' ·'+s.n:''}</span>`).join('');
  const skBlock=!skArr.length?'':(skArr.length>6
     ? `<details class="drill sub"><summary>Skills used · ${skArr.length}</summary><div class="dbody">${skPills}</div></details>`
     : `<div class="skline"><span class="sklbl">Skills used</span>${skPills}</div>`);
  return `<div class="dlv-list">${list}</div>`+skBlock;
}

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
  if(procArr[0])ins.push({i:'🏭',t:`The biggest business process is <b>${procLabel(procArr[0].name)}</b> — <b>${pct(procArr[0].hours,totProcH)}%</b> of the work.`});
  if(pilArr[0])ins.push({i:'💼',t:`<b>${pilArr[0].name}</b> is the dominant value pillar at <b>${pct(pilArr[0].hours,totPilH)}%</b> of saved hours.`});
  el('ov-insights').innerHTML=ins.map(x=>`<div class="ins"><div class="ic">${x.i}</div><div class="tx">${x.t}</div></div>`).join('');

  // Impact & Value
  renderDonut('im-pillars',pilArr,totPilH,R);
  (function(){const mx=Math.max(1,...catArr.map(a=>a.hours)),N=mem.length;el('im-categories').innerHTML=catArr.map(c=>{
    const band=RAW.meta.categoryBands[c.name]?`band ${RAW.meta.categoryBands[c.name]} min/run &nbsp;·&nbsp; `:'';
    const sub=`<span style="font-size:11px;color:var(--faint)">${band}${reachLabel(catReach(mem,c.name),N)}</span>`;
    return barRow(c.name,c.hours/mx*100,CAT_COLOR[c.name]||'var(--c0)',`<b>${hrs(c.hours)}</b> · ${money(c.hours*R)} · ${c.tasks} tasks · ${pct(c.hours,totCatH)}%`)+`<div style="margin:-4px 0 6px 191px">${sub}</div>`;}).join('');})();
  (function(){const arr=sortH(toArr(A.role)),mx=Math.max(1,...arr.map(a=>a.hours));
    const roleHtml=arr.length?arr.map((x,i)=>barRow(x.name,x.hours/mx*100,PAL[i%PAL.length],`<b>${hrs(x.hours)}</b> · ${money(x.hours*R)}`)).join(''):'<div class="sec-note">No role data in these posts.</div>';
    const sk=sortH(toArr(A.skill));
    const skHtml=sk.length?`<details class="drill"><summary>Skills behind these roles — ${sk.length}</summary><div class="dbody"><table class="dt"><thead><tr><th>Skill</th><th class="r">Deliverables</th><th class="r">Sessions</th><th class="r">Hours</th><th class="r">Value</th></tr></thead><tbody>`+
      sk.map(s=>`<tr><td>${s.name}</td><td class="r">${s.deliverables}</td><td class="r">${s.sessions}</td><td class="r">${hrs(s.hours)}</td><td class="r">${money(s.hours*R)}</td></tr>`).join('')+
      `</tbody></table><div class="sec-note" style="margin-top:6px">The specific skills that make up the roles above — the same expertise, one level of detail down.</div></div></details>`:'';
    el('im-roles').innerHTML=roleHtml+skHtml;})();
  (function(){
    const bym={};sortH(toArr(A.deliv)).forEach(d=>{const f=fmtLabel(d.name);const o=bym[f]||(bym[f]={name:f,count:0,hours:0});o.count+=d.count;o.hours+=d.hours;});
    const arr=sortH(Object.keys(bym).map(k=>bym[k])),tc=arr.reduce((s,x)=>s+x.count,0),th=arr.reduce((s,x)=>s+x.hours,0);
    let html=`<table class="dt"><thead><tr><th>Format</th><th class="r">Count</th><th class="r">Hours</th><th class="r">Value</th></tr></thead><tbody>`+
      arr.map(d=>`<tr><td><b>${d.name}</b></td><td class="r">${d.count}</td><td class="r">${hrs(d.hours)}</td><td class="r">${money(d.hours*R)}</td></tr>`).join('')+
      `<tr class="tot"><td>Total</td><td class="r">${tc}</td><td class="r">${hrs(th)}</td><td class="r">${money(th*R)}</td></tr></tbody></table>`;
    el('im-deliv').innerHTML=html;})();

  // How Cowork is used — process leads
  (function(){
    const byp={};(A.delivDetail||[]).forEach(d=>{const p=d.process||'Other';(byp[p]=byp[p]||[]).push(d);});
    const head=`<div class="acct-h"><span>Business process</span><span class="r">Sessions</span><span class="r">Hours</span><span class="r">Value</span><span class="r">% time</span></div>`;
    const rows=procArr.map(p=>`<details class="acct-row"><summary><span class="ap">${procLabel(p.name)}</span><span class="r">${p.sessions}</span><span class="r">${hrs(p.hours)}</span><span class="r">${money(p.hours*R)}</span><span class="r">${pct(p.hours,totProcH)}%</span></summary><div class="acct-body">${procDetailHTML(byp[p.name]||[],R)}</div></details>`).join('');
    const tot=`<div class="acct-tot"><span>Total</span><span class="r">${procArr.reduce((s,x)=>s+x.sessions,0)}</span><span class="r">${hrs(totProcH)}</span><span class="r">${money(totProcH*R)}</span><span class="r">100%</span></div>`;
    el('wk-proc').innerHTML=`<div class="acct">${head}${rows}${tot}</div><div class="sec-note" style="margin-top:10px">Click any business process to expand the deliverable formats it produced and the skills behind them.</div>`;})();
  renderCatMix('wk-stack',mem,catArr.map(c=>c.name));
  (function(){const inA=Object.keys(A.inputs).map(k=>({t:k,c:A.inputs[k]})).sort((a,b)=>b.c-a.c),outP=Object.keys(A.outputs).map(k=>({t:k,c:A.outputs[k]})).sort((a,b)=>b.c-a.c);
    const mxi=Math.max(1,...inA.map(x=>x.c)),mxo=Math.max(1,...outP.map(x=>x.c));
    const col=(arr,mx,c)=>arr.map(x=>`<div class="row rc"><div class="rl">${x.t}</div><div class="rbar"><div class="rfill" style="width:${x.c/mx*100}%;background:${c}"></div></div><div class="rv"><b>${x.c}</b></div></div>`).join('')||'<div class="sec-note">—</div>';
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
  // "?" section helpers: click toggles the adjacent popover; clicking elsewhere closes any open one.
  document.querySelectorAll('.help').forEach(b=>b.addEventListener('click',e=>{
    e.stopPropagation();const pop=b.nextElementSibling;const on=pop&&pop.classList.contains('on');
    document.querySelectorAll('.helppop.on').forEach(p=>p.classList.remove('on'));
    if(pop&&!on)pop.classList.add('on');}));
  document.addEventListener('click',()=>document.querySelectorAll('.helppop.on').forEach(p=>p.classList.remove('on')));
}
build();render();
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark">
<title>Cowork Team Report — Team Dashboard</title>
<style>__CSS__</style>
</head>
<body>
<header class="top"><div class="wrap">
  <div class="brand"><svg width="22" height="22" viewBox="0 0 23 23" aria-hidden="true"><rect x="1" y="1" width="10" height="10" fill="#F25022"></rect><rect x="12" y="1" width="10" height="10" fill="#7FBA00"></rect><rect x="1" y="12" width="10" height="10" fill="#00A4EF"></rect><rect x="12" y="12" width="10" height="10" fill="#FFB900"></rect></svg><span class="nm">Microsoft Copilot Cowork</span></div>
  <h1>Cowork Team Report — Team Dashboard</h1>
  <p class="sub">__TEAM__ — team impact &amp; how Cowork is used</p>
  <p class="gen">Generated __GENERATED__ · <span id="ctxline"></span></p>
  <p class="disc"><b>Read as modeled tool-impact, not performance scores</b> — directional estimates of tool-assisted time savings, read with team context (project phase, seasonality), not individual performance. Anonymized &amp; team-level only: de-identified posts (no names, files, or prompts); nothing shown per person; a Role breaks out only when __KTHRESH__+ contributors share it.</p>
</div></header>
<div class="wrap">
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
    <button class="tab-btn" type="button" data-tab="method">How to read</button>
  </div>

  <div class="tab-panel on" id="tab-overview">
    <section class="block"><h2 class="sec"><span class="dot"></span>What the data says<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">A plain-language reading of the team's posts, generated automatically. It re-words itself when you change the hourly rate below.</span></h2><p class="sec-note">Auto-generated reading of the team's posts — updates with the rate control.</p><div class="insights" id="ov-insights"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Team impact at a glance<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The headline totals for the selected period. <b>Value</b> = expert-equivalent hours &times; the hourly rate in the control bar, so it recomputes whenever you change the rate.</span></h2><div class="kpis" id="ov-kpis"></div></section>
  </div>

  <div class="tab-panel" id="tab-impact">
    <section class="block"><h2 class="sec"><span class="dot"></span>Business value pillars<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">Which kind of business value the saved hours advanced — <b>Revenue Growth</b>, <b>Cost Reduction</b>, <b>Risk Mitigation</b>, or <b>Transformation</b> (new ways of working / AI adoption).</span></h2><p class="sec-note">Where the saved hours land. Value = hours × the rate above.</p><div class="card" id="im-pillars"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Where the time went — by task category<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The <b>method</b> used, task by task. Each task is sorted by its output file type and goal keywords (e.g. spreadsheets &rarr; Analysis; code / HTML &rarr; Write or debug code). Each category carries a research time band (minutes saved per run); time saved = tasks &times; band. The <b>reach</b> line shows how many contributors used it. Full mapping is on the <b>How to read</b> tab.</span></h2><p class="sec-note">With the research-anchored time bands (minutes saved per run), and how many contributors used each.</p><div class="card" id="im-categories"></div></section>
    <section class="block"><div class="grid2">
      <div class="card"><h3>Roles Cowork stood in for</h3><p class="hint">Roles a services firm would have billed — expand for the specific skills behind them.</p><div id="im-roles"></div></div>
      <div class="card"><h3>Deliverables produced — by format</h3><p class="hint">What the team shipped, as real file formats. Per-item detail sits under <i>Work by business process</i>.</p><div id="im-deliv"></div></div>
    </div></section>
  </div>

  <div class="tab-panel" id="tab-work">
    <section class="block"><h2 class="sec"><span class="dot"></span>Work by business process<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">What the team actually does with Cowork, grouped into the shared canonical process set. <b>Click any row</b> to expand its deliverables and the skills behind them. Deliverables with a de-identified name list individually; ones a post carried only by file type collapse into a single row (e.g. &ldquo;HTML &middot; 5 deliverables&rdquo;).</span></h2><p class="sec-note">Grouped into the shared canonical set (mirrors the Member skill). This is the spine of the tab — what the team actually does with Cowork. <b>Each row expands</b> — click a process to see the deliverables it produced and the skills behind them.</p><div class="card" id="wk-proc"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Category mix<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">How each contributor group splits its time across categories. A role only breaks out when <b>__KTHRESH__+</b> people share it; otherwise everyone is combined into one bar — no individual is ever shown.</span></h2><p class="sec-note">How saved time splits across task categories — grouped by Role where privacy allows.</p><div class="card" id="wk-stack"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Analyzed → Produced<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">How many source items the team fed in versus how many deliverables it produced, by type — a rough read on input effort vs. output.</span></h2><p class="sec-note">Inputs the team analyzed vs. deliverables produced, by type.</p><div class="card" id="wk-io"></div></section>
  </div>

  <div class="tab-panel" id="tab-trends">
    <section class="block"><h2 class="sec"><span class="dot"></span>Time saved over time<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">One point per posting cycle, so you can see whether the team's total impact is trending up over fortnights. Cowork is used for specific tasks, so this is a cycle-over-cycle total, not daily activity.</span></h2><p class="sec-note">Minimal by design — one point per posting cycle. Is team impact growing?</p><div class="card" id="tr-trend"></div></section>
  </div>

  <div class="tab-panel" id="tab-method">
    <details class="meth" open><summary>How to read this dashboard</summary><div class="mbody">
      <p>This tab explains every number, tab and control — it folds in the old one-page PDF, so the whole guide now lives inside the dashboard. It's built by aggregating the de-identified Cowork Team Report posts teammates publish to the team channel. Metric &amp; section titles match the <b>Copilot ROI Report</b> and <b>Copilot ROI Member</b> skills. Treat numbers as <b>directional</b> — Cowork isn't the only factor behind any change, so read them with team context (project phase, seasonality), not as performance scores. This is a small, homogeneous-team (v1) view.</p>
      <p style="margin-top:8px">Tip: every section title has a <b>?</b> next to it — click it for a quick explanation right where you're looking.</p>
    </div></details>

    <details class="meth"><summary>The five tabs — where to look for what</summary><div class="mbody">
      <h4>Overview</h4><p>Auto-insights + the KPI band. Start here.</p>
      <h4>Impact &amp; Value</h4><p>Value by pillar and task category ($), the roles Cowork stood in for, and deliverables by file format.</p>
      <h4>How Cowork is used</h4><p>The business processes the team runs (each row expands to its deliverables + skills), the category mix by contributor group, and analyzed &rarr; produced.</p>
      <h4>Trends</h4><p>Fortnight-over-fortnight movement — one point per posting cycle.</p>
      <h4>How to read</h4><p>This tab: plain-language definitions and the methodology.</p>
    </div></details>

    <details class="meth"><summary>The KPI band — what each headline number means</summary><div class="mbody">
      <p><b>Time saved</b> — expert-equivalent hours Cowork saved the team this period.<br>
      <b>Value / cost reduction</b> — those saved hours priced out (hours &times; hourly rate).<br>
      <b>Team speed multiplier</b> — how much faster: expert hours &divide; hands-on hours.<br>
      <b>Contributors</b> — how many teammates posted their stats this period.<br>
      <b>Sessions</b> — distinct Cowork chats run across the whole team.<br>
      <b>Deliverables</b> — files, decks, docs, web pages and other outputs made.<br>
      <b>Active days</b> — person-days with at least one Cowork task in the window.<br>
      <b>Hands-on time</b> — real time at the keyboard (the assisted clock).</p>
    </div></details>

    <details class="meth"><summary>The two controls</summary><div class="mbody">
      <p><b>Period</b> — pick the reporting window; every number on the page updates to match.<br>
      <b>Hourly rate</b> — change $/hr and all value / cost-reduction figures recompute instantly (default $__RATE__/hr). Only the pricing changes; hours and counts stay the same.</p>
    </div></details>

    <details class="meth"><summary>How task categories are derived</summary><div class="mbody">
      <p>Two different questions are answered by two different fields. <b>Business process</b> = <i>what</i> business need the work served. <b>Task category</b> = <i>how</i> the work was done (the method). Each task is sorted into up to two categories from three signals:</p>
      <p><b>1 · Output file type</b> — spreadsheets (.xlsx / .csv / .json) &rarr; Analysis &amp; Research · code &amp; web (.py / .html / .sql / .js) &rarr; Write or debug code · documents (.docx / .pdf / .pptx / images) &rarr; Document &amp; content creation · packaged skills (.zip / .skill) &rarr; Specialized workflows.<br>
      <b>2 · Goal keywords</b> — &ldquo;analyze / research / ROI / benchmark&rdquo; &rarr; Analysis · &ldquo;debug / refactor / script / API / automation&rdquo; &rarr; Write or debug code · &ldquo;email / inbox / reply&rdquo; &rarr; Email · &ldquo;meeting / transcript / standup / agenda&rdquo; &rarr; Meeting.<br>
      <b>3 · Input signal</b> — if the sources are data files, or there are 3 or more of them &rarr; Analysis.</p>
      <p>When more than one matches, they rank (code &rsaquo; analysis &rsaquo; specialized &rsaquo; document &rsaquo; communication &rsaquo; meeting &rsaquo; email &rsaquo; general) and the top two are kept. A task with no saved file and no signal falls to <b>General assistance / Other</b>. Each category then carries a research time band (below); time saved = tasks &times; band.</p>
    </div></details>

    <details class="meth"><summary>Deliverables — and why some show only a file format</summary><div class="mbody">
      <p>Under <b>Work by business process</b>, a deliverable with a de-identified name (e.g. &ldquo;Team ROI dashboard&rdquo;) lists on its own row. A row that shows only a format (e.g. &ldquo;HTML&rdquo;) is a deliverable whose <b>name wasn't included in that teammate's post</b> — the Member skill can post either a named line or a compact type-only line. It does <b>not</b> mean Cowork failed to recognize the work. To keep the list readable, all type-only deliverables of one format collapse into a single row — e.g. <b>&ldquo;HTML &middot; 5 deliverables&rdquo;</b> — with their hours and value summed.</p>
    </div></details>

    <details class="meth"><summary>How widespread is a category (reach)</summary><div class="mbody">
      <p>Each task-category row shows <b>how many contributors</b> used it — e.g. &ldquo;used by 4 of 5 contributors&rdquo; — so you can see where usage is concentrated vs. spread, not just the volume of hours. This is an aggregate count and never names anyone. To protect a small team, when <b>fewer than __KTHRESH__</b> people used a category the exact number is withheld and shown as &ldquo;used by &lt;__KTHRESH__ contributors&rdquo;.</p>
    </div></details>

    <details class="meth"><summary>Privacy &amp; anonymity</summary><div class="mbody">
      <p><b>Nothing is shown at an individual level.</b> Members appear only as counts. The one per-attribute view (category mix) breaks a Role out only when <b>__KTHRESH__+</b> contributors share it; otherwise they collapse into a single combined bar. The only attribute used is the directory <b>Role</b> (job title) that a teammate's post carries — never names, never country, never file names or prompts.</p>
    </div></details>

    <details class="meth"><summary>Value model</summary><div class="mbody">
      <p>Time saved = Σ run tasks × the research band per task category (minutes saved/run). <b>Value = expert-equivalent hours × hourly rate</b> (default $__RATE__/hr; adjust live). <b>Speed multiplier</b> = expert ÷ modeled hands-on hours. All figures come from the posts; the dashboard only re-totals and re-prices them.</p>
    </div></details>

    <details class="meth"><summary>Value pillars</summary><div class="mbody">
      <p><b>Revenue Growth</b> (top-line), <b>Cost Reduction</b> (cost base), <b>Risk Mitigation</b> (protect value), <b>Transformation</b> (new ways of working / AI adoption). Shared crosswalk across all three ROI skills.</p>
    </div></details>

    <details class="meth"><summary>Research bands &amp; sources</summary><div class="mbody">
      <p>Minutes saved per run (low / typical / high): Analysis &amp; Research 30/67/92 · Write or debug code 30/56/96 · Document &amp; content 12/24/42 · Meeting 12/31/43 · Email 3/7/12 · Communication 2/4/6 · Specialized 10/25/40 · General 2/5/8.</p>
      <p>Sources: Stanford-WB (SSRN 5136877), Microsoft Research 2026 (DiD n=72,186), Noy &amp; Zhang (Science 2023), Cambon et al. (MSR 2024), Cui et al. (CACM 2024), Brynjolfsson, Li &amp; Raymond (QJE 2025), Forrester TEI 2024.</p>
    </div></details>
  </div>

  <footer class="foot">Generated by Microsoft Copilot Cowork · Cowork Team Report Team Dashboard skill · anonymized &amp; team-safe — numbers only, no names. Modeled estimates of tool-assisted time savings, not audited financials or performance metrics.</footer>
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
