
const RAW=JSON.parse(document.getElementById('cw-data').textContent);
const RATE0=RAW.meta.defaultRate, KMIN=RAW.meta.kThreshold||3;
const RECAP0=(RAW.meta.defaultRecapture!=null?RAW.meta.defaultRecapture:0.70);
const CAT_COLOR={'Analysis & Research':'var(--c0)','Write or debug code':'var(--c1)','Document & content creation':'var(--c2)','Meeting workflows':'var(--c3)','Specialized workflows':'var(--c4)','General assistance / Other':'var(--c6)','Email workflows':'var(--c5)','Communication workflows':'var(--c7)'};
const PAL=['var(--c0)','var(--c1)','var(--c2)','var(--c3)','var(--c4)','var(--c5)','var(--c6)','var(--c7)'];
// Cowork-fit grade palette: High = green, Medium = gold, Low = neutral grey.
const FIT_META={H:{label:'High fit',color:'var(--c1)'},M:{label:'Medium fit',color:'var(--c2)'},L:{label:'Low fit',color:'var(--c5)'}};
// Deliverable types → concrete file formats (types like Text/File/Deck/Document overlap; formats don't).
const FMT={'Deck':'PPTX','Slides':'PPTX','Presentation':'PPTX','Slide deck':'PPTX','Document':'Word','Doc':'Word','Word':'Word','Spreadsheet':'Excel / CSV','Excel':'Excel / CSV','CSV':'Excel / CSV','Web page':'HTML','Webpage':'HTML','Web':'HTML','HTML':'HTML','Text':'Text / MD','Markdown':'Text / MD','Image':'Image','PDF':'PDF','File':'File (other)'};
const fmtLabel=t=>FMT[t]||t;
// Glossary map (built from the Glossary tab at build time) → hover tooltips on matching KPI labels.
const GLOSSARY=__GLOSSARY__;
function glossLabel(t){const d=GLOSSARY[String(t).toLowerCase()];return d?`<span class="gloss" tabindex="0">${t}<span class="gtip">${d}</span></span>`:t;}
// Display-only remap of grouped process labels (taxonomy files stay byte-for-byte identical).
const PROC_LABEL={'Skill Development':'Cowork Skill Development'};
const procLabel=n=>PROC_LABEL[n]||n;
const posted=RAW.members.filter(m=>m.posted);
const state={snapshot:RAW.snapshots[RAW.snapshots.length-1].id,rate:RATE0,recap:RECAP0,tab:'overview',metric:'time'};
const el=id=>document.getElementById(id);
const money=v=>'$'+Math.round(v).toLocaleString('en-US');
const hrs=h=>h.toFixed(1)+' h';
const pct=(n,d)=>d>0?Math.round(n/d*100):0;
const wk=h=>(h/40).toFixed(1);
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
// Global measure: honors the Assisted Time / Assisted Value toggle so every chart shows one basis.
const measure=(h,RE)=>state.metric==='value'?money(h*RE):hrs(h);
const measLabel=()=>state.metric==='value'?'Value':'Hours';
function snapIds(){return state.snapshot==='ALL'?RAW.snapshots.map(s=>s.id):[state.snapshot];}
function snapLabel(){if(state.snapshot==='ALL')return 'All snapshots';const s=RAW.snapshots.find(x=>x.id===state.snapshot);return s.label+(s.periodStart?' ('+s.periodStart+' → '+s.periodEnd+')':'');}
function activeMembers(){const ids=snapIds();return posted.filter(m=>ids.some(id=>m.reports[id]));}
function memberReports(m){return snapIds().map(id=>m.reports[id]).filter(Boolean);}

function aggregate(members){
  const a={n:members.length,head:{timeTyp:0,timeLow:0,timeHigh:0,expertH:0,assistedH:0,sessions:0,runTasks:0,deliverables:0,activeDays:0},
    cat:{},proc:{},role:{},skill:{},deliv:{},delivDetail:[],fit:[],inputs:{},outputs:{},inA:0,outP:0};
  let lowN=0,highN=0;
  members.forEach(m=>memberReports(m).forEach(r=>{
    const h=r.headline;for(const k in a.head){if(k!=='timeLow'&&k!=='timeHigh')a.head[k]+=(h[k]||0);}
    if(h.timeLow!=null){a.head.timeLow+=h.timeLow;lowN++;} if(h.timeHigh!=null){a.head.timeHigh+=h.timeHigh;highN++;}
    r.categories.forEach(c=>{const o=a.cat[c.name]||(a.cat[c.name]={tasks:0,hours:0});o.tasks+=c.tasks;o.hours+=c.hours;});
    r.processes.forEach(p=>{const o=a.proc[p.name]||(a.proc[p.name]={sessions:0,hours:0});o.sessions+=p.sessions;o.hours+=p.hours;});
    r.roles.forEach(x=>{const o=a.role[x.name]||(a.role[x.name]={hours:0});o.hours+=x.hours;});
    r.skills.forEach(x=>{const o=a.skill[x.name]||(a.skill[x.name]={deliverables:0,sessions:0,hours:0});o.deliverables+=x.deliverables;o.sessions+=x.sessions;o.hours+=x.hours;});
    r.deliverables.forEach(d=>{const o=a.deliv[d.type]||(a.deliv[d.type]={count:0,hours:0,skills:new Set()});o.count+=d.count;o.hours+=d.hours;(d.skills||[]).forEach(s=>o.skills.add(s));});
    (r.deliverablesDetail||[]).forEach(d=>a.delivDetail.push(d));
    (r.coworkFit||[]).forEach(f=>a.fit.push(f));
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
  // file type, not a de-identified name) collapse into ONE row per format, e.g., "HTML · 5 deliverables".
  const named=[],byfmt={};
  items.forEach(d=>{
    const nm=(d.name&&String(d.name).trim())?String(d.name).trim():'';
    if(nm){named.push({nm:nm,tag:fmtLabel(d.type),hours:d.hours||0});}
    else{const f=fmtLabel(d.type);const o=byfmt[f]||(byfmt[f]={fmt:f,count:0,hours:0});o.count++;o.hours+=(d.hours||0);}
  });
  const rows=named.concat(Object.keys(byfmt).map(k=>{const o=byfmt[k];
      return {nm:o.fmt,tag:o.count+' deliverable'+(o.count!==1?'s':''),hours:o.hours};}))
    .sort((a,b)=>(b.hours||0)-(a.hours||0));
  const list=rows.map(d=>`<div class="dlv"><span class="dlv-nm" title="${esc(d.nm)}">${esc(d.nm)}</span><span class="fmt-tag">${esc(d.tag)}</span><span class="dlv-v">${measure(d.hours||0,R)}</span></div>`).join('');
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
  const RC=(state.recap!=null?state.recap:1),RE=R*RC;
  const teamSpeed=H.assistedH>0?H.expertH/H.assistedH:0;
  const catArr=sortH(toArr(A.cat)),totCatH=catArr.reduce((s,x)=>s+x.hours,0);
  const procArr=sortH(toArr(A.proc)),totProcH=procArr.reduce((s,x)=>s+x.hours,0);
  el('ctxline').textContent=`${snapLabel()} · ${mem.length} contributor${mem.length===1?'':'s'} · $${R}/hr · ${Math.round(RC*100)}% recapture`;

  // Overview KPIs
  el('ov-kpis').innerHTML=[
    {l:'Time saved',v:hrs(H.timeTyp),s:`≈ ${wk(H.timeTyp)} weeks · range ${hrs(H.timeLow)}–${hrs(H.timeHigh)}`,h:1,sel:state.metric==='time'},
    {l:'Effective time recaptured',v:hrs(H.timeTyp*RC),s:`${Math.round(RC*100)}% recapture of time saved · drives value`,h:1},
    {l:'Value / cost reduction',v:money(H.expertH*RE),s:`${Math.round(RC*100)}% recapture × $${R}/hr · range ${money(H.timeLow*RE)}–${money(H.timeHigh*RE)}`,h:1,sel:state.metric==='value'},
    {l:'Team speed multiplier',v:teamSpeed.toFixed(1)+'×',s:`${hrs(H.assistedH)} hands-on compared to ${hrs(H.expertH)} without Cowork`,h:1},
    {l:'Contributors',v:mem.length,s:`posted this period`,h:1},
    {l:'Sessions',v:H.sessions,s:`${H.runTasks} run tasks across ${H.sessions} sessions`},{l:'Deliverables',v:H.deliverables,s:'produced'},
    {l:'Active days',v:H.activeDays,s:`person-days · ${(H.activeDays?H.expertH/H.activeDays:0).toFixed(1)} h/day`},
  ].map(k=>`<div class="kpi${k.h?' hero':''}${k.sel?' metric-sel':''}"><div class="k-l">${glossLabel(k.l)}</div><div class="k-v">${k.v}</div><div class="k-s">${k.s}</div></div>`).join('');

  const ovVal=state.metric==='value';
  const headTime=`Cowork helped the team save about <b>${H.timeTyp.toFixed(1)} hours of total time</b> over this time period, enabling tasks to be completed <b>${teamSpeed.toFixed(1)}× faster.</b> At a <b>${Math.round(RC*100)}% recapture rate</b>, that is <b>${hrs(H.timeTyp*RC)}</b> of effective time recaptured, worth an estimated <b>${money(H.expertH*RE)}.</b>`;
  const headVal=`Cowork delivered an estimated <b>${money(H.expertH*RE)}</b> in value / cost reduction over this time period — from <b>${hrs(H.timeTyp*RC)}</b> of effective time recaptured (a <b>${Math.round(RC*100)}% recapture rate</b> on ${hrs(H.timeTyp)} saved) priced at <b>$${R}/hr</b>, with work completed <b>${teamSpeed.toFixed(1)}× faster.</b>`;
  const headline=`<div class="ins" style="grid-column:1/-1"><div class="ic">${ovVal?'💰':'⏱️'}</div><div class="tx">${ovVal?headVal:headTime}</div></div>`;
  const where=[];
  if(catArr[0])where.push({i:'🎯',h:'Task Category',goto:'impact',scroll:'im-categories',name:catArr[0].name,val:`${measure(catArr[0].hours,RE)} · ${pct(catArr[0].hours,totCatH)}% of total`});
  if(procArr[0])where.push({i:'🏭',h:'Business Process',goto:'work',scroll:'wk-proc',name:procLabel(procArr[0].name),val:`${measure(procArr[0].hours,RE)} · ${pct(procArr[0].hours,totProcH)}% of total`});
  const group=where.length?`<div class="ins insgroup" style="grid-column:1/-1"><div class="ig-h">Where did we ${ovVal?'drive the most value':'save the most time'}:</div><div class="ig-rows">${where.map(x=>`<div class="ig-row"><div class="ic">${x.i}</div><div class="tx"><button type="button" class="ig-cat navlink" data-goto="${x.goto}" data-scroll="${x.scroll}" title="Go to ${x.h}">${x.h}<span class="ig-arrow" aria-hidden="true">↗</span></button><div class="ig-name">${x.name}</div><div class="ig-val">${x.val}</div></div></div>`).join('')}</div></div>`:'';
  el('ov-insights').innerHTML=headline+group;

  // Overview — top business processes (attention-grabbing preview of the full "How Cowork is used" tab).
  (function(){const el0=el('ov-proc');if(!el0)return;
    const arr=procArr.slice(0,5);
    if(!arr.length){el0.innerHTML='<div class="sec-note">No business-process data in these posts yet.</div>';return;}
    const rows=arr.map((p,i)=>`<li class="rk-row"><span class="rk-badge">${i+1}</span><span class="rk-nm">${procLabel(p.name)}</span><span class="rk-v"><b>${measure(p.hours,RE)}</b> · ${pct(p.hours,totProcH)}% of total</span></li>`).join('');
    const more=`<div class="sec-note" style="margin-top:10px">${procArr.length>5?`Top 5 of ${procArr.length} business processes — `:''}<button type="button" class="xref" data-goto="work" data-scroll="wk-proc">open the full breakdown</button> to expand each process into its deliverables and the skills behind them.</div>`;
    el0.innerHTML=`<ol class="ranklist">${rows}</ol>`+more;})();

  // Impact & Value
  (function(){const mx=Math.max(1,...catArr.map(a=>a.hours)),N=mem.length;const catRows=catArr.map(c=>{
    const sub=`<span style="font-size:11px;color:var(--faint)">${reachLabel(catReach(mem,c.name),N)}</span>`;
    return barRow(c.name,c.hours/mx*100,'var(--c0)',`<b>${measure(c.hours,RE)}</b> · ${c.tasks} run tasks · ${pct(c.hours,totCatH)}%`)+`<div style="margin:-4px 0 6px 191px">${sub}</div>`;}).join('');
    const totTasks=catArr.reduce((s,x)=>s+(x.tasks||0),0);
    const totalRow=`<div class="row" style="border-top:2px solid var(--line);margin-top:6px;padding-top:9px"><div class="rl"><b>Total</b></div><div class="rbar" style="background:none"></div><div class="rv"><b>${measure(totCatH,RE)}</b> · ${totTasks} run tasks</div></div>`;
    el('im-categories').innerHTML=catRows+totalRow;})();
  (function(){const arrAll=sortH(toArr(A.role)),arr=arrAll.slice(0,10),mx=Math.max(1,...arr.map(a=>a.hours));
    const roleHtml=arr.length?arr.map((x,i)=>barRow(x.name,x.hours/mx*100,'var(--c0)',`<b>${measure(x.hours,RE)}</b>`)).join(''):'<div class="sec-note">No role data in these posts.</div>';
    const moreNote=arrAll.length>10?`<div class="sec-note" style="margin-top:8px">Showing the top 10 of ${arrAll.length} roles by hours.</div>`:'';
    const sk=sortH(toArr(A.skill));
    const skHtml=sk.length?`<details class="drill"><summary>Skills behind these roles — ${sk.length}</summary><div class="dbody"><table class="dt"><thead><tr><th>Skill</th><th class="r">Deliverables</th><th class="r">Sessions</th><th class="r">${measLabel()}</th></tr></thead><tbody>`+
      sk.map(s=>`<tr><td>${s.name}</td><td class="r">${s.deliverables}</td><td class="r">${s.sessions}</td><td class="r">${measure(s.hours,RE)}</td></tr>`).join('')+
      `</tbody></table><div class="sec-note" style="margin-top:6px">The specific skills that make up the roles above — the same expertise, one level of detail down.</div></div></details>`:'';
    el('im-roles').innerHTML=roleHtml+moreNote+skHtml;})();
  (function(){
    const bym={};toArr(A.deliv).forEach(d=>{const f=fmtLabel(d.name);const o=bym[f]||(bym[f]={name:f,count:0});o.count+=d.count;});
    const arr=Object.keys(bym).map(k=>bym[k]).sort((a,b)=>b.count-a.count),tc=arr.reduce((s,x)=>s+x.count,0);
    let html=`<table class="dt"><thead><tr><th>Format</th><th class="r">Count</th></tr></thead><tbody>`+
      arr.map(d=>`<tr><td><b>${d.name}</b></td><td class="r">${d.count}</td></tr>`).join('')+
      `<tr class="tot"><td>Total</td><td class="r">${tc}</td></tr></tbody></table>`;
    html+=`<p class="sec-note" style="margin-top:10px">Counts every output file and version the team produced with Cowork, by file format.</p>`;
    el('im-deliv').innerHTML=html;})();

  // How Cowork is used — process leads
  (function(){
    const byp={};(A.delivDetail||[]).forEach(d=>{const p=d.process||'Other';(byp[p]=byp[p]||[]).push(d);});
    const head=`<div class="acct-h"><span>Business process</span><span class="r">Sessions</span><span class="r">${measLabel()}</span><span class="r">% time</span></div>`;
    const rows=procArr.map(p=>`<details class="acct-row"><summary><span class="ap">${procLabel(p.name)}</span><span class="r">${p.sessions}</span><span class="r">${measure(p.hours,RE)}</span><span class="r">${pct(p.hours,totProcH)}%</span></summary><div class="acct-body">${procDetailHTML(byp[p.name]||[],RE)}</div></details>`).join('');
    const tot=`<div class="acct-tot"><span>Total</span><span class="r">${procArr.reduce((s,x)=>s+x.sessions,0)}</span><span class="r">${measure(totProcH,RE)}</span><span class="r">100%</span></div>`;
    el('wk-proc').innerHTML=`<div class="acct">${head}${rows}${tot}</div>`;})();
  renderCatMix('wk-stack',mem,catArr.map(c=>c.name),RE);
  // Cowork fit — quantified waterfall (Total → High / Medium / Low) with click-to-expand task lists.
  (function(){
    const fit=A.fit||[];const sec=el('wk-fit');if(!sec)return;
    if(!fit.length){sec.innerHTML='<div class="sec-note">No Cowork-fit data in these posts yet. Once contributors post from the latest member skill, graded tasks appear here.</div>';return;}
    const gradedMembers=mem.filter(m=>memberReports(m).some(r=>(r.coworkFit||[]).length)).length;
    const order=['H','M','L'],grp={H:[],M:[],L:[]};
    fit.forEach(f=>{if(grp[f.grade])grp[f.grade].push(f);});
    const total=fit.length,totH=fit.reduce((s,x)=>s+(x.hours||0),0);
    // Composition waterfall (task counts): All graded → High → Medium → Low; bands sum to the task total, so
    // bar heights and the shown percentages both read off task counts (measure = hours or value per the toggle).
    const gH={H:0,M:0,L:0};fit.forEach(f=>{if(gH[f.grade]!=null)gH[f.grade]+=(f.hours||0);});
    const gN={H:grp.H.length,M:grp.M.length,L:grp.L.length};
    const mx=total||1;
    const steps=[{lab:'All graded',cnt:total,val:totH,top:total,bot:0,color:'var(--c0)',sub:'100% · '+measure(totH,RE)}];
    let run=total;
    order.forEach(g=>{const c=gN[g];if(c<=0)return;steps.push({lab:FIT_META[g].label,cnt:c,val:gH[g],top:run,bot:run-c,color:FIT_META[g].color,sub:pct(c,mx)+'% · '+measure(gH[g],RE)});run-=c;});
    const W=900,Hh=300,padT=30,padB=54,padL=8,padR=8,nS=steps.length,slot=(W-padL-padR)/nS,bw=Math.min(130,slot*0.6),yOf=v=>padT+(1-v/mx)*(Hh-padT-padB);
    let svg='';
    steps.forEach((s,i)=>{const cx=padL+slot*i+slot/2,x=cx-bw/2,yT=yOf(s.top),yB=yOf(s.bot),hh=Math.max(2,yB-yT);
      if(i<nS-1){const ny=yOf(steps[i+1].top);svg+=`<line class="wfc" x1="${(x+bw).toFixed(1)}" y1="${ny.toFixed(1)}" x2="${(padL+slot*(i+1)+slot/2-bw/2).toFixed(1)}" y2="${ny.toFixed(1)}"/>`;}
      svg+=`<rect x="${x.toFixed(1)}" y="${yT.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" rx="4" fill="${s.color}"><title>${esc(s.lab)}: ${s.cnt} task${s.cnt===1?'':'s'} · ${hrs(s.val)} · ${money(s.val*RE)}</title></rect>`;
      svg+=`<text class="wfv" x="${cx.toFixed(1)}" y="${(yT-8).toFixed(1)}" text-anchor="middle">${s.cnt}</text>`;
      svg+=`<text class="wfl" x="${cx.toFixed(1)}" y="${(Hh-padB+20).toFixed(1)}" text-anchor="middle">${esc(s.lab)}</text>`;
      svg+=`<text class="wfs" x="${cx.toFixed(1)}" y="${(Hh-padB+37).toFixed(1)}" text-anchor="middle">${s.sub}</text>`;});
    const bar=`<div class="wf-cap"><b>${total}</b> graded task${total===1?'':'s'} · ${measure(totH,RE)} — composition by task count</div><svg class="wf-svg" viewBox="0 0 ${W} ${Hh}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Cowork fit composition waterfall">${svg}</svg>`;
    const head=`<div class="acct-h"><span>Cowork fit</span><span class="r">Tasks</span><span class="r">% tasks</span><span class="r">${measLabel()}</span></div>`;
    const rows=order.map(g=>{const items=grp[g];if(!items.length)return '';const n=items.length,h=items.reduce((s,x)=>s+(x.hours||0),0);
      const list=items.slice().sort((a,b)=>(b.hours||0)-(a.hours||0)).map(x=>`<div class="dlv"><span class="dlv-nm" title="${esc(procLabel(x.process||'—'))}">${esc(procLabel(x.process||'—'))}</span><span class="fmt-tag">${esc(x.category||'—')}</span><span class="dlv-v">${measure(x.hours||0,RE)}</span></div>`).join('');
      return `<details class="acct-row"><summary><span class="ap"><span class="wf-dot" style="background:${FIT_META[g].color};margin-inline-end:7px"></span>${FIT_META[g].label}</span><span class="r">${n}</span><span class="r">${pct(n,total)}%</span><span class="r">${measure(h,RE)}</span></summary><div class="acct-body"><div class="dlv-list">${list}</div></div></details>`;}).join('');
    const tot=`<div class="acct-tot"><span>Total</span><span class="r">${total}</span><span class="r">100%</span><span class="r">${measure(totH,RE)}</span></div>`;
    const cov=gradedMembers<mem.length?`<p class="sec-note" style="margin-top:8px">Cowork-fit graded on ${gradedMembers} of ${mem.length} contributors&rsquo; posts; ungraded tasks from older posts aren&rsquo;t shown here.</p>`:'';
    sec.innerHTML=bar+`<div class="acct" style="margin-top:14px">${head}${rows}${tot}</div>`+cov;})();
}

// k-anonymity: a Role breaks out only when >= KMIN members share it; else combine.
function renderCatMix(id,mem,cats,RE){
  const groups={};mem.forEach(m=>{const r=m.role||'Unspecified';(groups[r]=groups[r]||[]).push(m);});
  let bars=[],pooled=[];
  Object.keys(groups).forEach(r=>{groups[r].length>=KMIN?bars.push({label:r,members:groups[r]}):pooled=pooled.concat(groups[r]);});
  if(pooled.length)bars.push({label:bars.length?'Other contributors (combined)':'Team (combined)',members:pooled});
  const rows=bars.map(b=>{const cm={};b.members.forEach(m=>memberReports(m).forEach(r=>r.categories.forEach(k=>cm[k.name]=(cm[k.name]||0)+k.hours)));
    const tot=Object.values(cm).reduce((s,v)=>s+v,0)||1;
    const segs=cats.filter(c=>cm[c]).map(c=>{const sp=cm[c]/tot*100;return `<div class="stackseg" style="width:${sp}%;background:${CAT_COLOR[c]||'var(--c6)'}" title="${c}: ${measure(cm[c],RE)} · ${Math.round(sp)}%">${sp>=10?`<span class="segpct">${Math.round(sp)}%</span>`:''}</div>`;}).join('');
    return `<div class="stackrow"><div class="rl" style="font-size:12.5px">${b.label} · ${b.members.length}</div><div class="stackbar">${segs}</div></div>`;}).join('');
  const overall={};mem.forEach(m=>memberReports(m).forEach(r=>r.categories.forEach(k=>overall[k.name]=(overall[k.name]||0)+k.hours)));
  const oTot=Object.values(overall).reduce((s,v)=>s+v,0)||1;
  const leg=cats.map(c=>`<div class="li"><span class="sw" style="background:${CAT_COLOR[c]||'var(--c6)'}"></span><span class="lt" style="font-size:12px">${c} <span style="color:var(--muted)">(${pct(overall[c]||0,oTot)}% · ${measure(overall[c]||0,RE)})</span></span></div>`).join('');
  el(id).innerHTML=rows+`<div class="legend" style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:6px 14px">${leg}</div>`+
    `<div class="sec-note" style="margin-top:10px">Individual roles are shown only when <b>${KMIN}+</b> people share it — otherwise contributors are combined.</div>`;
}
function showTab(name,scrollId){
  state.tab=name;
  document.querySelectorAll('.tab-btn').forEach(x=>x.classList.toggle('on',x.getAttribute('data-tab')===name));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('on',p.id==='tab-'+name));
  if(scrollId){requestAnimationFrame(()=>{const t=el(scrollId);if(!t)return;const d=(t.tagName==='DETAILS')?t:(t.closest&&t.closest('details.meth'));if(d)d.open=true;const tgt=(t.tagName==='DETAILS')?t:((t.closest&&t.closest('.block'))||t);tgt.scrollIntoView({behavior:'smooth',block:'start'});});}
}
function build(){
  const ss=el('snapSel');RAW.snapshots.forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.label+(s.periodEnd?' · '+s.periodEnd:'');ss.appendChild(o);});
  if(RAW.snapshots.length>1){const o=document.createElement('option');o.value='ALL';o.textContent='All snapshots';ss.appendChild(o);}
  ss.value=state.snapshot;ss.addEventListener('change',()=>{state.snapshot=ss.value;render();});
  const ri=el('rateInput');ri.value=state.rate;ri.addEventListener('input',()=>{const v=parseFloat(ri.value);state.rate=(isFinite(v)&&v>0)?v:0;render();});
  const rc=el('recapInput');rc.value=Math.round(state.recap*100);rc.addEventListener('input',()=>{const v=parseFloat(rc.value);state.recap=(isFinite(v)&&v>=0)?v/100:0;render();});
  el('resetBtn').addEventListener('click',()=>{state.rate=RATE0;state.recap=RECAP0;state.snapshot=RAW.snapshots[RAW.snapshots.length-1].id;state.metric='time';ss.value=state.snapshot;ri.value=RATE0;rc.value=Math.round(RECAP0*100);syncOvSeg();render();});
  const ovBtns=document.querySelectorAll('#ovSeg .seg-btn');function syncOvSeg(){ovBtns.forEach(b=>b.classList.toggle('on',b.getAttribute('data-metric')===state.metric));}
  ovBtns.forEach(b=>b.addEventListener('click',()=>{state.metric=b.getAttribute('data-metric');syncOvSeg();render();}));
  el('printBtn').addEventListener('click',()=>window.print());
  document.querySelectorAll('.tab-btn').forEach(b=>b.addEventListener('click',()=>showTab(b.getAttribute('data-tab'))));
  // Deep-link: clicking a labeled header in the Overview 'Where did we save' card jumps to that tab + section.
  document.addEventListener('click',e=>{const nav=e.target.closest&&e.target.closest('[data-goto]');if(nav){e.preventDefault();showTab(nav.getAttribute('data-goto'),nav.getAttribute('data-scroll')||'');}});
  // "?" section helpers: click toggles the adjacent popover; clicking elsewhere closes any open one.
  document.querySelectorAll('.help').forEach(b=>b.addEventListener('click',e=>{
    e.stopPropagation();const pop=b.nextElementSibling;const on=pop&&pop.classList.contains('on');
    document.querySelectorAll('.helppop.on').forEach(p=>p.classList.remove('on'));
    if(pop&&!on)pop.classList.add('on');}));
  document.addEventListener('click',()=>document.querySelectorAll('.helppop.on').forEach(p=>p.classList.remove('on')));
}
build();render();
