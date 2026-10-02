const RAW=JSON.parse(document.getElementById('cw-data').textContent);
const RATE0=RAW.meta.defaultRate, KMIN=RAW.meta.kThreshold;
const RECAP0=RAW.meta.defaultRecapture;
const CAT_COLOR={'Analysis & Research':'var(--c0)','Write or debug code':'var(--c1)','Document & content creation':'var(--c2)','Meeting workflows':'var(--c3)','Specialized workflows':'var(--c4)','General assistance / Other':'var(--c6)','Email workflows':'var(--c5)','Communication workflows':'var(--c7)'};
const FIT_META={H:{label:'High fit',color:'var(--c1)'},M:{label:'Medium fit',color:'var(--c2)'},L:{label:'Low fit',color:'var(--c5)'}};
const state={snapshot:RAW.snapshots[RAW.snapshots.length-1].id,rate:RATE0,recap:RECAP0,metric:'time'};
const el=id=>document.getElementById(id);
const money=v=>'$'+Math.round(v).toLocaleString('en-US');
const hrs=h=>Number(h||0).toFixed(1)+' h';
const pct=(n,d)=>d>0?Math.round(n/d*100):0;
const wk=h=>(h/40).toFixed(1);
const esc=s=>String(s).replace(/[&<>"'`]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#x27;','`':'&#x60;'}[c]));
const measure=(h,rate)=>state.metric==='value'?money(h*rate):hrs(h);
const measLabel=()=>state.metric==='value'?'Value':'Hours';
const procLabel=n=>n;
const fmtLabel=t=>t;
const active=()=>RAW.aggregates[state.snapshot]||RAW.aggregates[RAW.snapshots[RAW.snapshots.length-1].id];
const sortH=a=>a.slice().sort((x,y)=>y.hours-x.hours);

function glossLabel(text){
  const definitions=JSON.parse(document.getElementById('cw-glossary').textContent);
  const definition=definitions[String(text).toLowerCase()];
  return definition?`<span class="gloss" tabindex="0">${esc(text)}<span class="gtip">${esc(definition)}</span></span>`:esc(text);
}
function barRow(label,percent,color,value){
  return `<div class="row"><div class="rl" title="${esc(label)}">${esc(label)}</div><div class="rbar"><div class="rfill" style="width:${percent}%;background:${color}"></div></div><div class="rv">${value}</div></div>`;
}
function renderProcessDetail(process,rate,data){
  const formats=data.processDetails.filter(item=>item.process===process);
  if(!formats.length)return '<div class="sec-note">No process detail met the minimum contributor threshold.</div>';
  const list=formats.map(item=>`<div class="dlv"><span class="dlv-nm" title="${esc(item.type)}">${esc(item.type)} · ${item.count} deliverables</span><span class="fmt-tag">${esc(item.type)}</span><span class="dlv-v">${measure(item.hours,rate)}</span></div>`).join('');
  const skills={};
  formats.forEach(item=>item.skills.forEach(skill=>skills[skill.name]=(skills[skill.name]||0)+skill.count));
  const pills=Object.keys(skills).sort().map(name=>`<span class="pill">${esc(name)} · ${skills[name]}</span>`).join('');
  return `<div class="dlv-list">${list}</div>${pills?`<div class="skline"><span class="sklbl">Skills used</span>${pills}</div>`:''}`;
}

function render(){
  const data=active(),R=state.rate,RC=state.recap,RE=R*RC,H=data.head;
  const categories=sortH(data.categories),totalCategoryHours=categories.reduce((sum,item)=>sum+item.hours,0);
  const processes=sortH(data.processes),totalProcessHours=processes.reduce((sum,item)=>sum+item.hours,0);
  el('ctxline').textContent=`${snapshotLabel()} · ${data.contributors} contributors · $${R}/hr · ${Math.round(RC*100)}% recapture`;
  el('ov-kpis').innerHTML=[
    {label:'Time saved',value:hrs(H.timeTyp),sub:`≈ ${wk(H.timeTyp)} weeks · range ${hrs(H.timeLow)}–${hrs(H.timeHigh)}`,hero:true,selected:state.metric==='time'},
    {label:'Effective time recaptured',value:hrs(H.timeTyp*RC),sub:`${Math.round(RC*100)}% recapture of time saved · drives value`,hero:true},
    {label:'Value / cost reduction',value:money(H.expertH*RE),sub:`${Math.round(RC*100)}% recapture × $${R}/hr · range ${money(H.timeLow*RE)}–${money(H.timeHigh*RE)}`,hero:true,selected:state.metric==='value'},
    {label:'Team speed multiplier',value:(H.assistedH>0?H.expertH/H.assistedH:0).toFixed(1)+'×',sub:`${hrs(H.assistedH)} hands-on compared to ${hrs(H.expertH)} without Cowork`},
    {label:'Contributors',value:data.contributors,sub:'posted this period',hero:true},
    {label:'Sessions',value:H.sessions,sub:`${H.runTasks} run tasks across ${H.sessions} sessions`},
    {label:'Deliverables',value:H.deliverables,sub:'produced'},
    {label:'Active days',value:H.activeDays,sub:`person-days · ${(H.activeDays?H.expertH/H.activeDays:0).toFixed(1)} h/day`}
  ].map(item=>`<div class="kpi${item.hero?' hero':''}${item.selected?' metric-sel':''}"><div class="k-l">${glossLabel(item.label)}</div><div class="k-v">${item.value}</div><div class="k-s">${item.sub}</div></div>`).join('');

  const byValue=state.metric==='value';
  const timeText=`Cowork helped the team save about <b>${H.timeTyp.toFixed(1)} hours of total time</b> over this time period. At a <b>${Math.round(RC*100)}% recapture rate</b>, that is <b>${hrs(H.timeTyp*RC)}</b> of effective time recaptured, worth an estimated <b>${money(H.expertH*RE)}.</b>`;
  const valueText=`Cowork delivered an estimated <b>${money(H.expertH*RE)}</b> in value / cost reduction over this time period — from <b>${hrs(H.timeTyp*RC)}</b> of effective time recaptured at <b>$${R}/hr</b>.`;
  const highlights=[];
  if(categories[0])highlights.push({title:'Task Category',tab:'impact',target:'im-categories',name:categories[0].name,value:`${measure(categories[0].hours,RE)} · ${pct(categories[0].hours,totalCategoryHours)}% of shown total`});
  if(processes[0])highlights.push({title:'Business Process',tab:'work',target:'wk-proc',name:processes[0].name,value:`${measure(processes[0].hours,RE)} · ${pct(processes[0].hours,totalProcessHours)}% of shown total`});
  const headline=`<div class="ins" style="grid-column:1/-1"><div class="ic">${byValue?'💰':'⏱️'}</div><div class="tx">${byValue?valueText:timeText}</div></div>`;
  const group=highlights.length?`<div class="ins insgroup" style="grid-column:1/-1"><div class="ig-h">Where did we ${byValue?'drive the most value':'save the most time'}:</div><div class="ig-rows">${highlights.map(item=>`<div class="ig-row"><div class="tx"><button type="button" class="ig-cat navlink" data-goto="${item.tab}" data-scroll="${item.target}" title="Go to ${esc(item.title)}">${esc(item.title)}<span class="ig-arrow" aria-hidden="true">↗</span></button><div class="ig-name">${esc(item.name)}</div><div class="ig-val">${item.value}</div></div></div>`).join('')}</div></div>`:'';
  el('ov-insights').innerHTML=headline+group;

  const topProcesses=processes.slice(0,5);
  el('ov-proc').innerHTML=topProcesses.length
    ? `<ol class="ranklist">${topProcesses.map((item,index)=>`<li class="rk-row"><span class="rk-badge">${index+1}</span><span class="rk-nm">${esc(item.name)}</span><span class="rk-v"><b>${measure(item.hours,RE)}</b> · ${pct(item.hours,totalProcessHours)}% of shown total</span></li>`).join('')}</ol><div class="sec-note" style="margin-top:10px">Only processes supported by at least ${KMIN} contributors are shown.</div>`
    : '<div class="sec-note">No business-process data met the minimum contributor threshold.</div>';

  const maxCategory=Math.max(1,...categories.map(item=>item.hours));
  const categoryRows=categories.map(item=>{
    const reach=item.contributors>=KMIN?`used by ${item.contributors} contributors`:`used by &lt;${KMIN} contributors`;
    return barRow(item.name,item.hours/maxCategory*100,'var(--c0)',`<b>${measure(item.hours,RE)}</b> · ${item.tasks} run tasks · ${pct(item.hours,totalCategoryHours)}%`)
      +`<div style="margin:-4px 0 6px 191px"><span style="font-size:11px;color:var(--faint)">${reach}</span></div>`;
  }).join('');
  const visibleTasks=categories.reduce((sum,item)=>sum+item.tasks,0);
  const categoryNote=`<div class="sec-note">Breakdowns are shown only when at least ${KMIN} contributors support the category; lower-support categories are excluded.</div>`;
  const categoryTotal=`<div class="row" style="border-top:2px solid var(--line);margin-top:6px;padding-top:9px"><div class="rl"><b>Shown categories</b></div><div class="rbar" style="background:none"></div><div class="rv"><b>${measure(totalCategoryHours,RE)}</b> · ${visibleTasks} run tasks</div></div>`;
  el('im-categories').innerHTML=categoryNote+categoryRows+categoryTotal;

  const serviceRoles=sortH(data.roles);
  const maxRole=Math.max(1,...serviceRoles.slice(0,10).map(item=>item.hours));
  const roleRows=serviceRoles.slice(0,10).map(item=>barRow(item.name,item.hours/maxRole*100,'var(--c0)',`<b>${measure(item.hours,RE)}</b>`)).join('');
  const skills=data.skills.slice().sort((a,b)=>b.hours-a.hours);
  const skillTable=skills.length?`<details class="drill"><summary>Skills supported by ${KMIN}+ contributors — ${skills.length}</summary><div class="dbody"><table class="dt"><thead><tr><th>Skill</th><th class="r">Deliverables</th><th class="r">Sessions</th><th class="r">${measLabel()}</th></tr></thead><tbody>${skills.map(item=>`<tr><td>${esc(item.name)}</td><td class="r">${item.deliverables}</td><td class="r">${item.sessions}</td><td class="r">${measure(item.hours,RE)}</td></tr>`).join('')}</tbody></table></div></details>`:'';
  el('im-roles').innerHTML=(roleRows||'<div class="sec-note">No role data met the minimum contributor threshold.</div>')+skillTable;

  const outputs=data.deliverables.slice().sort((a,b)=>b.count-a.count);
  const outputTotal=outputs.reduce((sum,item)=>sum+item.count,0);
  el('im-deliv').innerHTML=`<table class="dt"><thead><tr><th>Format</th><th class="r">Count</th></tr></thead><tbody>${outputs.map(item=>`<tr><td><b>${esc(fmtLabel(item.name))}</b></td><td class="r">${item.count}</td></tr>`).join('')}<tr class="tot"><td>Shown formats</td><td class="r">${outputTotal}</td></tr></tbody></table><p class="sec-note" style="margin-top:10px">Formats with fewer than ${KMIN} contributing people are excluded.</p>`;

  const processRows=processes.map(item=>`<details class="acct-row"><summary><span class="ap">${esc(procLabel(item.name))}</span><span class="r">${item.sessions}</span><span class="r">${measure(item.hours,RE)}</span><span class="r">${pct(item.hours,totalProcessHours)}%</span></summary><div class="acct-body">${renderProcessDetail(item.name,RE,data)}</div></details>`).join('');
  const processTotal=`<div class="acct-tot"><span>Shown processes</span><span class="r">${processes.reduce((sum,item)=>sum+item.sessions,0)}</span><span class="r">${measure(totalProcessHours,RE)}</span><span class="r">—</span></div>`;
  el('wk-proc').innerHTML=`<div class="sec-note">Process rows and details require at least ${KMIN} contributing people; individual deliverable names and task-level records are never included.</div><div class="acct"><div class="acct-h"><span>Business process</span><span class="r">Sessions</span><span class="r">${measLabel()}</span><span class="r">% shown time</span></div>${processRows}${processTotal}</div>`;

  renderFit(data,RE);
  renderCategoryMix(data,RE);
}

function renderFit(data,rate){
  const section=el('wk-fit');
  const fit=data.fit,order=['H','M','L'];
  if(!fit.length){section.innerHTML=`<div class="sec-note">No Cowork-fit grade has support from at least ${KMIN} contributors.</div>`;return;}
  const byGrade={};fit.forEach(item=>byGrade[item.grade]=item);
  const total=fit.reduce((sum,item)=>sum+item.count,0);
  const totalHours=fit.reduce((sum,item)=>sum+item.hours,0);
  const maxCount=total||1,W=900,chartHeight=300,padTop=30,padBottom=54,padLeft=8,padRight=8;
  const steps=[{label:'Shown graded tasks',count:total,hours:totalHours,color:'var(--c0)',top:total,bottom:0}];
  let remaining=total;
  order.forEach(grade=>{
    if(!byGrade[grade])return;
    const item=byGrade[grade];
    steps.push({label:FIT_META[grade].label,count:item.count,hours:item.hours,color:FIT_META[grade].color,grade,top:remaining,bottom:remaining-item.count});
    remaining-=item.count;
  });
  const slot=(W-padLeft-padRight)/steps.length,width=Math.min(130,slot*.6);
  const yOf=value=>padTop+(1-value/maxCount)*(chartHeight-padTop-padBottom);
  let svg='';
  steps.forEach((step,index)=>{
    const center=padLeft+slot*index+slot/2,x=center-width/2,top=yOf(step.top),bottom=yOf(step.bottom),height=Math.max(2,bottom-top);
    if(index<steps.length-1){const nextY=yOf(steps[index+1].top);svg+=`<line class="wfc" x1="${(x+width).toFixed(1)}" y1="${nextY.toFixed(1)}" x2="${(padLeft+slot*(index+1)+slot/2-width/2).toFixed(1)}" y2="${nextY.toFixed(1)}"/>`;}
    svg+=`<rect x="${x.toFixed(1)}" y="${top.toFixed(1)}" width="${width.toFixed(1)}" height="${height.toFixed(1)}" rx="4" fill="${step.color}"><title>${esc(step.label)}: ${step.count} tasks · ${hrs(step.hours)} · ${money(step.hours*rate)}</title></rect><text class="wfv" x="${center.toFixed(1)}" y="${(top-8).toFixed(1)}" text-anchor="middle">${step.count}</text><text class="wfl" x="${center.toFixed(1)}" y="${(chartHeight-padBottom+20).toFixed(1)}" text-anchor="middle">${esc(step.label)}</text><text class="wfs" x="${center.toFixed(1)}" y="${(chartHeight-padBottom+37).toFixed(1)}" text-anchor="middle">${pct(step.count,maxCount)}% · ${measure(step.hours,rate)}</text>`;
  });
  const gradeRows=order.map(grade=>{
    const item=byGrade[grade];if(!item)return '';
    const detail=data.fitDetails.filter(row=>row.grade===grade);
    const list=detail.map(row=>`<div class="dlv"><span class="dlv-nm">${esc(row.process)}</span><span class="fmt-tag">${esc(row.category)}</span><span class="dlv-v">${row.count} tasks · ${measure(row.hours,rate)}</span></div>`).join('');
    return `<details class="acct-row"><summary><span class="ap"><span class="wf-dot" style="background:${FIT_META[grade].color};margin-inline-end:7px"></span>${FIT_META[grade].label}</span><span class="r">${item.count}</span><span class="r">${pct(item.count,total)}%</span><span class="r">${measure(item.hours,rate)}</span></summary><div class="acct-body"><div class="dlv-list">${list||'<div class="sec-note">No process/category detail met the minimum contributor threshold.</div>'}</div></div></details>`;
  }).join('');
  section.innerHTML=`<div class="wf-cap"><b>${total}</b> graded tasks in supported cohorts · ${measure(totalHours,rate)} — composition by task count</div><svg class="wf-svg" viewBox="0 0 ${W} ${chartHeight}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Cowork fit composition waterfall">${svg}</svg><div class="sec-note">Only grades and process/category combinations supported by at least ${KMIN} contributors are included.</div><div class="acct" style="margin-top:14px"><div class="acct-h"><span>Cowork fit</span><span class="r">Tasks</span><span class="r">% tasks</span><span class="r">${measLabel()}</span></div>${gradeRows}<div class="acct-tot"><span>Shown grades</span><span class="r">${total}</span><span class="r">100%</span><span class="r">${measure(totalHours,rate)}</span></div></div>`;
}

function renderCategoryMix(data,rate){
  const groups=data.roleGroups;
  const rows=groups.map(group=>{
    const total=group.categories.reduce((sum,item)=>sum+item.hours,0)||1;
    const segments=group.categories.map(item=>{
      const width=item.hours/total*100;
      return `<div class="stackseg" style="width:${width}%;background:${CAT_COLOR[item.name]||'var(--c6)'}" title="${esc(item.name)}: ${measure(item.hours,rate)} · ${Math.round(width)}%">${width>=10?`<span class="segpct">${Math.round(width)}%</span>`:''}</div>`;
    }).join('');
    return `<div class="stackrow"><div class="rl" style="font-size:12.5px">${esc(group.name)} · ${group.contributors}</div><div class="stackbar">${segments}</div></div>`;
  }).join('');
  const totals={};data.categories.forEach(item=>totals[item.name]=item.hours);
  const sum=Object.values(totals).reduce((total,value)=>total+value,0)||1;
  const legend=data.categories.map(item=>`<div class="li"><span class="sw" style="background:${CAT_COLOR[item.name]||'var(--c6)'}"></span><span class="lt" style="font-size:12px">${esc(item.name)} <span style="color:var(--muted)">(${pct(item.hours,sum)}% · ${measure(item.hours,rate)})</span></span></div>`).join('');
  el('wk-stack').innerHTML=(rows||'<div class="sec-note">No role cohort met the minimum contributor threshold.</div>')+`<div class="legend" style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:6px 14px">${legend}</div><div class="sec-note" style="margin-top:10px">Role groups and category segments are shown only with support from at least ${KMIN} contributors; smaller residual role groups are combined only when the pool itself meets that threshold.</div>`;
}

function snapshotLabel(){
  if(state.snapshot==='ALL')return 'All snapshots';
  const selected=RAW.snapshots.find(item=>item.id===state.snapshot);
  return selected?selected.label+(selected.periodStart?` (${selected.periodStart} → ${selected.periodEnd})`:''):'Selected period';
}
function showTab(name,scrollId){
  document.querySelectorAll('.tab-btn').forEach(button=>button.classList.toggle('on',button.getAttribute('data-tab')===name));
  document.querySelectorAll('.tab-panel').forEach(panel=>panel.classList.toggle('on',panel.id==='tab-'+name));
  if(scrollId)requestAnimationFrame(()=>{const target=el(scrollId);if(target)target.scrollIntoView({behavior:'smooth',block:'start'});});
}
function build(){
  const selector=el('snapSel');
  RAW.snapshots.forEach(snapshot=>{const option=document.createElement('option');option.value=snapshot.id;option.textContent=snapshot.label+(snapshot.periodEnd?' · '+snapshot.periodEnd:'');selector.appendChild(option);});
  if(RAW.snapshots.length>1){const option=document.createElement('option');option.value='ALL';option.textContent='All snapshots';selector.appendChild(option);}
  selector.value=state.snapshot;
  selector.addEventListener('change',()=>{state.snapshot=selector.value;render();});
  const rate=el('rateInput');rate.value=state.rate;rate.addEventListener('input',()=>{const value=Number.parseFloat(rate.value);state.rate=Number.isFinite(value)&&value>0?value:0;render();});
  const recapture=el('recapInput');recapture.value=Math.round(state.recap*100);recapture.addEventListener('input',()=>{const value=Number.parseFloat(recapture.value);state.recap=Number.isFinite(value)&&value>=0?value/100:0;render();});
  const metricButtons=document.querySelectorAll('#ovSeg .seg-btn');
  const syncMetric=()=>metricButtons.forEach(button=>button.classList.toggle('on',button.getAttribute('data-metric')===state.metric));
  metricButtons.forEach(button=>button.addEventListener('click',()=>{state.metric=button.getAttribute('data-metric');syncMetric();render();}));
  el('resetBtn').addEventListener('click',()=>{state.rate=RATE0;state.recap=RECAP0;state.snapshot=RAW.snapshots[RAW.snapshots.length-1].id;state.metric='time';selector.value=state.snapshot;rate.value=RATE0;recapture.value=Math.round(RECAP0*100);syncMetric();render();});
  el('printBtn').addEventListener('click',()=>window.print());
  document.querySelectorAll('.tab-btn').forEach(button=>button.addEventListener('click',()=>showTab(button.getAttribute('data-tab'))));
  document.addEventListener('click',event=>{const link=event.target.closest&&event.target.closest('[data-goto]');if(link){event.preventDefault();showTab(link.getAttribute('data-goto'),link.getAttribute('data-scroll')||'');}});
  document.querySelectorAll('.help').forEach(button=>button.addEventListener('click',event=>{event.stopPropagation();const popup=button.nextElementSibling;const open=popup&&popup.classList.contains('on');document.querySelectorAll('.helppop.on').forEach(item=>item.classList.remove('on'));if(popup&&!open)popup.classList.add('on');}));
  document.addEventListener('click',()=>document.querySelectorAll('.helppop.on').forEach(item=>item.classList.remove('on')));
}
build();render();
