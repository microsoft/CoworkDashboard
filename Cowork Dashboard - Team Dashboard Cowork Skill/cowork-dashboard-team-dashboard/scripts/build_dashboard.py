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
  Impact & Value    — task categories ($), roles (+ skills as collapsible detail),
                      deliverables by FILE FORMAT.
  How Cowork is used— business process accordion: each row EXPANDS to its deliverable formats + skills
                      (skills nest in a sub-expand when long); category mix (k-anon), analyzed->produced.
  Disclaimer        — "modeled tool-impact, not performance" note lives in the blue header (small print).
  Glossary & method — definitions, the value model, privacy rule, sources.

Every $ figure = hours x rate, computed live in the browser (live rate control).
Usage: python build_dashboard.py --in working/team_data.json --out output/cowork-team-roi-dashboard.html
"""
import json, argparse, re

CSS = r"""
:root{--bg:#f3f4f8;--panel:#fff;--ink:#1f2329;--muted:#5d6470;--faint:#8a909c;--line:#e4e7ee;
--brand:#0f6cbd;--brand-d:#0b5394;--soft:#eaf3fb;--good:#107c10;--shadow:0 1px 2px rgba(16,24,40,.06),0 4px 16px rgba(16,24,40,.06);
/* Analyzed -> Produced (input/output columns) — two colors NOT in the task category palette: a warm amber-GOLD (not olive) for inputs analyzed, magenta for outputs produced. Keeps this section distinct from the task categories. */
--io-in:#d99c1e;--io-out:#b4009e;
--c0:#0f6cbd;--c1:#2e8b57;--c2:#ca5010;--c3:#8764b8;--c4:#0099bc;--c5:#c4314b;--c6:#7a7574;--c7:#498205;--donut-edge:rgba(0,0,0,.16);}
@media (prefers-color-scheme:dark){:root{--bg:#16181d;--panel:#1f2228;--ink:#e9ebef;--muted:#a7adb8;--faint:#7c828d;--line:#2c3038;--brand:#4aa3e8;--brand-d:#74b9ee;--soft:#1b2a39;--shadow:0 1px 2px rgba(0,0,0,.4);--donut-edge:rgba(255,255,255,.26);}}
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
section.block{margin:24px 0 0;scroll-margin-top:120px}
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
.catsw{display:inline-block;width:10px;height:10px;border-radius:3px;margin-inline-end:8px;vertical-align:middle;flex:none}
.footnote{font-size:11.5px;color:var(--faint);margin-top:9px;line-height:1.5}.footnote b{color:var(--muted)}
.pill{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;background:var(--soft);color:var(--brand-d);font-weight:600;margin:1px 3px 1px 0}
.insights{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.ins{display:flex;gap:11px;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--brand);border-radius:10px;padding:12px 14px;box-shadow:var(--shadow)}
.ins .ic{font-size:18px;line-height:1.2}.ins .tx{font-size:13px}.ins .tx b{font-weight:700}
.ins.insgroup{flex-direction:column;gap:11px}
.insgroup .ig-h{font-size:13px;font-weight:700;color:var(--ink)}
.insgroup .ig-rows{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.insgroup .ig-row{display:flex;gap:9px;align-items:flex-start}
.insgroup .ig-row .ic{font-size:17px;line-height:1.2}.insgroup .ig-row .tx{font-size:12.5px}.insgroup .ig-row .tx b{font-weight:700}
.insgroup .ig-cat{font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700;margin-bottom:3px}
.insgroup .ig-cat.navlink{display:inline-flex;align-items:center;gap:4px;background:none;border:0;padding:0;cursor:pointer;font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;font-weight:700;color:var(--faint)}
.insgroup .ig-cat.navlink:hover,.insgroup .ig-cat.navlink:focus-visible{color:var(--ink);text-decoration:underline;text-decoration-style:dotted;text-decoration-color:var(--faint);outline:none}
.insgroup .ig-cat.navlink .ig-arrow{font-size:11px;opacity:.75}
/* Glossary hover tooltip: a term with a dotted underline pops its definition (from the Glossary) on hover/focus. */
.gloss{position:relative;cursor:help;border-bottom:1px dotted currentColor}
.gloss>.gtip{position:absolute;top:calc(100% + 6px);inset-inline-start:0;z-index:70;width:220px;max-width:70vw;background:var(--ink);color:var(--panel);border-radius:8px;padding:8px 10px;font-size:12px;font-weight:400;line-height:1.45;text-transform:none;letter-spacing:normal;box-shadow:var(--shadow);display:none;white-space:normal}
.gloss:hover>.gtip,.gloss:focus>.gtip,.gloss:focus-within>.gtip{display:block}
/* Inline cross-reference link — jumps to the named section/tab. */
.xref{display:inline;background:none;border:0;padding:0;margin:0;font:inherit;color:inherit;cursor:pointer;text-decoration:underline dotted;text-decoration-color:var(--faint);text-underline-offset:2px}
.xref:hover,.xref:focus-visible{text-decoration-color:var(--ink);outline:none}
.insgroup .ig-name{font-size:14px;font-weight:700;color:var(--ink);margin-bottom:1px}
.insgroup .ig-val{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.donut-wrap{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.legend{display:flex;flex-direction:column;gap:7px;font-size:12.5px}.legend .li{display:flex;align-items:center;gap:9px}
.legend .sw{width:12px;height:12px;border-radius:3px;flex:none;box-shadow:inset 0 0 0 1px var(--donut-edge)}.legend .lt{flex:1}.legend .lv{color:var(--muted);font-variant-numeric:tabular-nums}
.stackrow{display:grid;grid-template-columns:200px 1fr;align-items:center;gap:11px;padding:6px 0}
.stackbar{display:flex;height:22px;border-radius:6px;overflow:hidden;background:var(--bg)}.stackseg{height:100%;display:flex;align-items:center;justify-content:center;overflow:hidden}.segpct{font-size:9px;font-weight:700;color:#fff;text-shadow:0 1px 1px rgba(0,0,0,.45);white-space:nowrap;line-height:1}
/* Cowork-fit waterfall: one part-to-whole bar of graded tasks (High/Medium/Low), each an expandable row below. */
.wf-cap{font-size:13px;color:var(--muted);margin:0 0 8px}.wf-cap b{color:var(--ink);font-size:16px;font-weight:750}
.wf-bar{display:flex;height:34px;border-radius:8px;overflow:hidden;background:var(--bg)}
.wf-seg{height:100%;display:flex;align-items:center;justify-content:center}.wf-seg span{font-size:12.5px;font-weight:700;color:#fff;text-shadow:0 1px 1px rgba(0,0,0,.4)}
.wf-leg{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:10px;font-size:12px;color:var(--muted)}
.wf-li{display:inline-flex;align-items:center;gap:6px}
.wf-dot{width:10px;height:10px;border-radius:3px;display:inline-block;flex:none}
.wf-svg{width:100%;height:auto;display:block;overflow:visible;margin:2px 0 4px}
.wf-svg .wfv{font-size:13px;font-weight:750;fill:var(--ink)}
.wf-svg .wfl{font-size:12.5px;font-weight:650;fill:var(--ink)}
.wf-svg .wfs{font-size:11px;fill:var(--muted)}
.wf-svg .wfc{stroke:var(--faint);stroke-width:1;stroke-dasharray:3 3;opacity:.7}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden;background:var(--bg)}
.seg-btn{appearance:none;-webkit-appearance:none;border:0;background:transparent;color:var(--muted);font:inherit;font-size:13px;font-weight:650;padding:7px 15px;cursor:pointer}
.seg-btn+.seg-btn{border-inline-start:1px solid var(--line)}
.seg-btn.on{background:var(--c1);color:#fff}
.ov-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 16px}
.ov-tl{font-size:13px;color:var(--muted);font-weight:650}
.kpi.metric-sel{outline:2px solid var(--c1);outline-offset:1px}
.ranklist{list-style:none;margin:0;padding:0}
.rk-row{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:13px;padding:11px 4px;border-bottom:1px solid var(--line)}
.rk-row:last-child{border-bottom:none}
.rk-badge{width:25px;height:25px;border-radius:50%;background:var(--bg);border:1px solid var(--line);color:var(--c0);font-weight:750;font-size:12.5px;display:flex;align-items:center;justify-content:center;flex:none}
.rk-nm{font-weight:600;font-size:14px}
.rk-v{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.rk-v b{color:var(--ink)}
.io2{display:grid;grid-template-columns:1fr 1fr;gap:26px}.io2 h4{font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);margin:0 0 10px}
.svgtrend{width:100%;height:150px}.trend-empty{font-size:12.5px;color:var(--muted);margin-top:8px}
details.meth{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);margin-bottom:12px;scroll-margin-top:120px}
details.meth summary{cursor:pointer;padding:14px 18px;font-weight:700;font-size:14px;list-style:none}
details.meth summary::-webkit-details-marker{display:none}
details.meth summary::before{content:'\25B8';margin-inline-end:9px;color:var(--brand);display:inline-block;transition:.15s}
details.meth[open] summary::before{transform:rotate(90deg)}
details.meth .mbody{padding:0 18px 16px;font-size:13px;color:var(--muted)}details.meth .mbody h4{color:var(--ink);font-size:13px;margin:13px 0 5px}details.meth a{color:var(--brand)}
details.meth .mbody ul{margin:4px 0 12px;padding-inline-start:20px}details.meth .mbody li{margin:3px 0}
details.drill{margin-top:13px;border-top:1px dashed var(--line);padding-top:9px}
details.drill>summary{cursor:pointer;font-size:12.5px;font-weight:650;color:var(--brand);list-style:none;user-select:none}
details.drill>summary::-webkit-details-marker{display:none}
details.drill>summary::before{content:'\25B8';margin-inline-end:7px;display:inline-block;transition:.15s;color:var(--brand)}
details.drill[open]>summary::before{transform:rotate(90deg)}
details.drill .dbody{padding-top:11px}
.dgrp{margin:0 0 15px}.dgrp .dgrp-h{font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.3px;margin:0 0 5px}
/* Expandable business-process accordion (each row opens to its deliverable formats + skills). */
.acct{border:1px solid var(--line);border-radius:11px;overflow:hidden}
.acct-h,.acct-tot,.acct-row>summary{display:grid;grid-template-columns:1fr 96px 92px 72px;gap:10px;align-items:center;padding:10px 14px;font-size:13px}
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
@media (max-width:860px){.acct-h,.acct-tot,.acct-row>summary{grid-template-columns:1fr 56px 66px 52px;gap:6px;font-size:12px}}
footer.foot{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-size:11.5px;color:var(--faint)}
@media (max-width:860px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2,.io2,.insights{grid-template-columns:1fr}.insgroup .ig-rows{grid-template-columns:1fr}.row{grid-template-columns:118px 1fr 132px}.row.rc{grid-template-columns:118px 1fr 46px}.row .rv{white-space:normal}.stackrow{grid-template-columns:120px 1fr}.helppop{max-width:78vw}}
@media print{body{background:#fff}.controls,.banner,.tabs{display:none}.tab-panel{display:block!important}
.card,.kpi,details.meth{box-shadow:none;border-color:#ccc}details.meth summary{display:none}details.meth .mbody{display:block!important}
details.drill .dbody{display:block!important}.acct-row>.acct-body{display:block!important}
header.top{background:var(--brand)!important}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}section.block{break-inside:avoid}}
"""

JS = r"""
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
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark">
<title>Cowork Team Dashboard</title>
<style>__CSS__</style>
</head>
<body>
<header class="top"><div class="wrap">
  <div class="brand"><svg width="22" height="22" viewBox="0 0 23 23" aria-hidden="true"><rect x="1" y="1" width="10" height="10" fill="#F25022"></rect><rect x="12" y="1" width="10" height="10" fill="#7FBA00"></rect><rect x="1" y="12" width="10" height="10" fill="#00A4EF"></rect><rect x="12" y="12" width="10" height="10" fill="#FFB900"></rect></svg><span class="nm">Microsoft Copilot Cowork</span></div>
  <h1>Cowork Team Dashboard</h1>
  <p class="sub">__TEAM__ Impact &amp; how Cowork is used</p>
  <p class="gen">Generated __GENERATED__ · <span id="ctxline"></span></p>
  <p class="disc">Use the information in this report to gauge the impact of Cowork on your team, <b>not as individual or team performance scores</b>. Treat these as directional estimates of tool-assisted time savings, and read them with team context in mind (e.g., project phase, seasonality). Anonymized &amp; team-level only: nothing is shown per person.</p>
  <p class="disc" style="margin-top:7px">New to this report? The <button type="button" class="xref" data-goto="method"><i>How to read + Glossary</i></button> tab explains every number, tab and control &mdash; and every section title has a clickable <b>?</b> for a quick explanation.</p>
  <p class="disc" style="margin-top:7px">Use the <b>Period selector, Hourly rate box, and Recapture rate box</b> below to pick the reporting window, the hourly rate (default $__RATE__/hr), and the productivity recapture rate (default __RECAP__%). Value / cost-reduction figures = effective recaptured hours × hourly rate and recompute instantly; time-saved hours and counts stay the same.</p>
</div></header>
<div class="wrap">
  <div class="controls">
    <div class="ctl"><label for="snapSel">Period</label><select id="snapSel"></select></div>
    <div class="ctl"><label for="rateInput">Hourly rate</label><div class="rate-in"><span>$</span><input id="rateInput" type="number" min="1" step="1" inputmode="numeric"><span>/hr</span></div></div>
    <div class="ctl"><label for="recapInput">Recapture rate</label><div class="rate-in"><input id="recapInput" type="number" min="0" max="100" step="5" inputmode="numeric"><span>%</span></div></div>
    <div class="ctl"><label>Show impact as</label><div class="seg" id="ovSeg" role="group" aria-label="Show impact as Assisted Time or Assisted Value"><button type="button" class="seg-btn on" data-metric="time">Assisted Time</button><button type="button" class="seg-btn" data-metric="value">Assisted Value</button></div></div>
    <div class="spacer"></div>
    <button class="btn" id="resetBtn" type="button">Reset</button>
    <button class="btn primary" id="printBtn" type="button">Save / Print PDF</button>
  </div>
  <div class="tabs">
    <button class="tab-btn on" type="button" data-tab="overview">Overview</button>
    <button class="tab-btn" type="button" data-tab="impact">Impact &amp; Value</button>
    <button class="tab-btn" type="button" data-tab="work">How Cowork is used</button>
    <button class="tab-btn" type="button" data-tab="method" style="font-style:italic">How to read + Glossary</button>
  </div>

  <div class="tab-panel on" id="tab-overview">
    <section class="block"><h2 class="sec"><span class="dot"></span>What the data says<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">A plain-language reading of the team's posts, generated automatically. It re-words itself when you change the hourly rate below.</span></h2><p class="sec-note">The four highlights below summarize the team's Cowork impact at a glance: the total time reclaimed and its dollar value, the task category driving the most savings, the business process where Cowork is applied most, and the type of business value it advances most — so you can quickly see where the impact is concentrated.</p><div class="insights" id="ov-insights"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Team impact at a glance<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The headline totals for the selected period. <b>Value</b> = manual hours &times; the hourly rate in the control bar, so it recomputes whenever you change the rate.</span></h2><div class="kpis" id="ov-kpis"></div><p class="sec-note" style="margin-top:12px"><b>About the ranges:</b> under <b>Time saved</b> and <b>Value / cost reduction</b> the headline is the typical (mid-point) estimate; the low&ndash;high range beside it is the conservative-to-optimistic span from the research time bands (each task category carries a low / typical / high band &mdash; see <button type="button" class="xref" data-goto="method" data-scroll="sec-bands"><i>How to read</i></button>).</p></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Where Cowork is applied — top business processes<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The business processes the team uses Cowork for most, ranked by the selected measure (time saved or value). This is a preview — the full <b>How Cowork is used</b> tab expands every process into its deliverables and the skills behind them.</span></h2><p class="sec-note">The business processes where Cowork does the most work for the team — the clearest signal of how it's actually being used. Open the full breakdown to drill into each one.</p><div class="card" id="ov-proc"></div></section>
  </div>

  <div class="tab-panel" id="tab-impact">
    <section class="block"><h2 class="sec"><span class="dot"></span>Where the time went — by task category<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The <b>method</b> used, task by task. Each task is sorted by its output file type and goal keywords (e.g., spreadsheets &rarr; Analysis; code / HTML &rarr; Write or debug code). Each category carries a research time band (minutes saved per run); time saved = run tasks &times; band. The <b>reach</b> line shows how many contributors used it. Full mapping is on the <b>How to read</b> tab.</span></h2><p class="sec-note">Understand how much time is saved by the team across each task category. Refer to the <button type="button" class="xref" data-goto="method" data-scroll="sec-bands"><i>How to read</i></button> section to understand the research-based time ranges for each category.</p><p class="sec-note" style="margin-top:8px">Each task category row shows <b>how many contributors</b> used it — e.g., &ldquo;used by 4 of 5 contributors&rdquo; — so you can see where usage is concentrated vs. spread, not just the volume of hours. This is an aggregate count and never names anyone. To protect a small team, when <b>fewer than __KTHRESH__</b> people used a category the exact number is withheld and shown as &ldquo;used by &lt;__KTHRESH__ contributors&rdquo;.</p><div class="card" id="im-categories"></div></section>
    <section class="block"><div class="grid2">
      <div class="card"><h3>Roles Cowork stood in for</h3><p class="hint">Roles a services firm would have billed — expand for the specific skills behind them.</p><div id="im-roles"></div></div>
      <div class="card"><h3>Outputs produced — by format</h3><p class="hint">Every output the team produced with Cowork, by file type. Note that outputs count each file and version, so this may be higher than the &ldquo;Deliverables&rdquo; count on the <button type="button" class="xref" data-goto="overview"><i>Overview</i></button> tab, which counts distinct deliverables. Per-item detail sits under &ldquo;<button type="button" class="xref" data-goto="work" data-scroll="wk-proc">Work by business process</button>&rdquo; on the <button type="button" class="xref" data-goto="work"><i>How Cowork is used</i></button> tab.</p><div id="im-deliv"></div></div>
    </div></section>
  </div>

  <div class="tab-panel" id="tab-work">
    <section class="block"><h2 class="sec"><span class="dot"></span>Work by business process<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">What the team actually does with Cowork, grouped into the shared canonical process set. <b>Click any row</b> to expand its deliverables and the skills behind them. Deliverables with a de-identified name list individually; ones a post carried only by file type collapse into a single row (e.g., &ldquo;HTML &middot; 5 deliverables&rdquo;).</span></h2><p class="sec-note">The business processes the team used Cowork for, ranked by time saved. <b>Click any process to expand it</b> and see the deliverables it produced and the skills behind them.</p><p class="sec-note" style="margin-top:8px">Named deliverables (e.g., &ldquo;Team ROI dashboard&rdquo;) list on their own row. A row that shows only a format (e.g., &ldquo;HTML&rdquo;) is a deliverable whose name wasn't included in that teammate's post. All type-only deliverables of one format collapse into a single row — e.g., &ldquo;HTML &middot; 5 deliverables&rdquo; — with their hours and value summed.</p><div class="card" id="wk-proc"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Cowork fit — how well the work suited Cowork<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">Every task is graded <b>High / Medium / Low</b> on how well it fit Cowork's agentic, cross-app strengths. <b>High</b> = work only Cowork can do (builds &amp; packaged skills, executed automations/connectors, many-source synthesis); <b>Low</b> = a single-app Copilot could have done it. <b>Click a fit level</b> to see the tasks in it — de-identified to business process &amp; method, never a person or file.</span></h2><p class="sec-note">A composition of graded hours by how well the work fit Cowork, shown as a waterfall — the bands add up to all graded time. <b>Click High, Medium or Low</b> below to expand the tasks in that band.</p><div class="card" id="wk-fit"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Category mix<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">How each contributor group splits its time across categories. A role only breaks out when <b>__KTHRESH__+</b> people share it; otherwise everyone is combined into one bar — no individual is ever shown.</span></h2><p class="sec-note">How saved time splits across task categories — grouped by Role where privacy allows.</p><div class="card" id="wk-stack"></div></section>
  </div>

  <div class="tab-panel" id="tab-method">
    <details class="meth" open><summary>Glossary of terms</summary><div class="mbody" id="gloss-body">
      <p><b>Active days</b> — Person-days with at least one Cowork task in the window.</p>
      <p><b>Anonymity</b> — A role or attribute is shown separately only when at least __KTHRESH__ contributors share it; otherwise contributors are combined. Nothing is ever shown per person.</p>
      <p><b>Business process</b> — The business need served by the work &mdash; e.g., Business Value &amp; ROI Analytics.</p>
      <p><b>Contributors</b> — The number of teammates who posted their de-identified stats this period. Never named.</p>
      <p><b>Cowork fit</b> — How well a task suited Cowork's agentic, cross-app strengths, graded High / Medium / Low. High = work only Cowork can do (builds &amp; packaged skills, executed automations, many-source synthesis); Low = a single-app Copilot could have done it. Shown as a quantified waterfall on the <i>How Cowork is used</i> tab.</p>
      <p><b>Deliverables</b> — The count of <i>distinct</i> pieces of work produced.</p>
      <p><b>Hands-on time</b> — The actual time the team spent working with Cowork.</p>
      <p><b>Outputs</b> — Every output file and version created. May be higher than deliverables because it counts each file and version.</p>
      <p><b>Reach</b> — How many contributors used a given task category. Withheld as &ldquo;&lt;__KTHRESH__&rdquo; when fewer than __KTHRESH__ share it.</p>
      <p><b>Research time band</b> — The low / typical / high minutes of manual time saved per run for a task category, drawn from published studies (see &ldquo;<button type="button" class="xref" data-goto="method" data-scroll="sec-bands">Research bands &amp; sources</button>&rdquo; below).</p>
      <p><b>Run tasks</b> — A single unit of work run with Cowork — one discrete request or action (e.g., analyzing a file, drafting a document). Run tasks are grouped into sessions.</p>
      <p><b>Sessions</b> — Distinct Cowork chats run across the team. A session may contain one or multiple run tasks.</p>
      <p><b>Skills</b> — The specific capabilities behind roles (e.g., Data Visualization, Python).</p>
      <p><b>Task category</b> — How the work was done (the method) &mdash; e.g., Analysis &amp; Research, Write or debug code. Each carries a research time band (see &ldquo;<button type="button" class="xref" data-goto="method" data-scroll="sec-bands">Research bands &amp; sources</button>&rdquo; below).</p>
      <p><b>Team speed multiplier</b> — How much faster the work went: estimated hours without Cowork &divide; actual hands-on with Cowork hours.</p>
      <p><b>Time saved</b> — Manual hours Cowork saved this period: for each task, run tasks &times; the research time band for its category. The headline is the typical estimate, with a low&ndash;high range alongside.</p>
      <p><b>Recapture rate</b> — The share of time saved the team can realistically harvest into productive output. Set in the control bar (default __RECAP__%). It scales every value figure but leaves time-saved hours and counts unchanged.</p>
      <p><b>Effective time recaptured</b> — Time saved &times; the recapture rate — the productive hours the team actually reclaims. This is what the value figure prices.</p>
      <p><b>Value / cost reduction</b> — Effective time recaptured priced out: time saved &times; recapture rate &times; the hourly rate in the control bar. Recomputes whenever you change the rate or the recapture rate.</p>
    </div></details>


    <details class="meth"><summary>How task categories are derived</summary><div class="mbody">
      <p>Each task is sorted into up to two categories from three signals:</p>
      <p style="margin-bottom:3px"><b>1 · Output file type</b></p>
      <ul>
        <li>spreadsheets (.xlsx / .csv / .json) &rarr; Analysis &amp; Research</li>
        <li>code &amp; web (.py / .html / .sql / .js) &rarr; Write or debug code</li>
        <li>documents (.docx / .pdf / .pptx / images) &rarr; Document &amp; content creation</li>
        <li>packaged skills (.zip / .skill) &rarr; Specialized workflows</li>
      </ul>
      <p style="margin-bottom:3px"><b>2 · Goal keywords</b></p>
      <ul>
        <li>&ldquo;analyze / research / ROI / benchmark&rdquo; &rarr; Analysis</li>
        <li>&ldquo;debug / refactor / script / API / automation&rdquo; &rarr; Write or debug code</li>
        <li>&ldquo;email / inbox / reply&rdquo; &rarr; Email</li>
        <li>&ldquo;meeting / transcript / standup / agenda&rdquo; &rarr; Meeting</li>
      </ul>
      <p style="margin-bottom:3px"><b>3 · Input signal</b></p>
      <ul>
        <li>if the sources are data files, or there are 3 or more of them &rarr; Analysis</li>
      </ul>
      <p>A task with no saved file and no signal falls to General assistance / Other. When more than one matches, they rank (code &rsaquo; analysis &rsaquo; specialized &rsaquo; document &rsaquo; communication &rsaquo; meeting &rsaquo; email &rsaquo; general) and the top two are kept.</p>
    </div></details>


    <details class="meth"><summary>Privacy &amp; anonymity</summary><div class="mbody">
      <p><b>Nothing is shown at an individual level.</b> Members appear only as counts. The one per-attribute view (category mix) breaks a Role out only when <b>__KTHRESH__+</b> contributors share it; otherwise they collapse into a single combined bar. The only attribute used is the directory <b>Role</b> (job title) that a teammate's post carries — never names, never country, never file names or prompts.</p>
    </div></details>

    <details class="meth"><summary>Value model</summary><div class="mbody">
      <ul>
        <li><b>Time saved</b> = Count of run tasks × the research band (minutes saved/run).</li>
        <li><b>Recapture rate</b> = the share of time saved the team realistically converts into productive output (default __RECAP__%; adjustable in the control bar).</li>
        <li><b>Effective time recaptured</b> = time saved × recapture rate.</li>
        <li><b>Value / cost reduction</b> = effective recaptured hours × hourly rate (default $__RATE__/hr) = time saved × recapture rate × rate.</li>
        <li><b>Speed multiplier</b> = manual hours ÷ modeled hands-on hours.</li>
      </ul>
      <p>All figures come from the posts; the dashboard only re-totals and re-prices them.</p>
    </div></details>

    <details class="meth" id="sec-bands"><summary>Research bands &amp; sources</summary><div class="mbody">
      <p>Each task category carries a research-anchored time band — the minutes of manual time saved per run, at a low / typical / high estimate.<sup>†</sup> Time saved = run tasks &times; the band for that category.</p>
      <table class="dt" style="margin-top:11px">
        <thead><tr><th>Task category</th><th class="r">Low</th><th class="r">Typical</th><th class="r">High</th></tr></thead>
        <tbody>
          <tr><td><span class="catsw" style="background:var(--c0)"></span>Analysis &amp; Research</td><td class="r">30</td><td class="r">67</td><td class="r">92</td></tr>
          <tr><td><span class="catsw" style="background:var(--c1)"></span>Write or debug code</td><td class="r">30</td><td class="r">56</td><td class="r">96</td></tr>
          <tr><td><span class="catsw" style="background:var(--c2)"></span>Document &amp; content creation</td><td class="r">12</td><td class="r">24</td><td class="r">42</td></tr>
          <tr><td><span class="catsw" style="background:var(--c3)"></span>Meeting workflows</td><td class="r">12</td><td class="r">31</td><td class="r">43</td></tr>
          <tr><td><span class="catsw" style="background:var(--c5)"></span>Email workflows</td><td class="r">3</td><td class="r">7</td><td class="r">12</td></tr>
          <tr><td><span class="catsw" style="background:var(--c7)"></span>Communication workflows</td><td class="r">2</td><td class="r">4</td><td class="r">6</td></tr>
          <tr><td><span class="catsw" style="background:var(--c4)"></span>Specialized workflows</td><td class="r">10</td><td class="r">25</td><td class="r">40</td></tr>
          <tr><td><span class="catsw" style="background:var(--c6)"></span>General assistance / Other</td><td class="r">2</td><td class="r">5</td><td class="r">8</td></tr>
        </tbody>
      </table>
      <p class="footnote"><sup>†</sup> Minutes of manual time saved per run (low / typical / high). <b>Sources:</b> Stanford-WB (SSRN 5136877), Microsoft Research 2026 (DiD n=72,186), Noy &amp; Zhang (Science 2023), Cambon et al. (MSR 2024), Cui et al. (CACM 2024), Brynjolfsson, Li &amp; Raymond (QJE 2025), Forrester TEI 2024.</p>
    </div></details>
  </div>

  <footer class="foot">Generated by Microsoft Copilot Cowork · Cowork Team Report Team Dashboard skill · anonymized &amp; team-safe — numbers only, no names. Modeled estimates of tool-assisted time savings, not audited financials or performance metrics.</footer>
</div>
<script type="application/json" id="cw-data">__DATA__</script>
<script>__JS__</script>
</body>
</html>
"""

def extract_glossary(template):
    m = re.search(r'id="gloss-body">(.*?)</div></details>', template, re.S)
    if not m:
        return {}
    g = {}
    for pm in re.finditer(r"<p><b>(.*?)</b>\s*\u2014\s*(.*?)</p>", m.group(1), re.S):
        term = re.sub(r"<[^>]+>", "", pm.group(1)).strip()
        definition = re.sub(r"</?i>", "", pm.group(2)).strip()
        if term:
            g[term.lower()] = definition
    return g

def main(a):
    data = json.load(open(a.inp, encoding="utf-8"))
    glossary = extract_glossary(TEMPLATE)
    html = (TEMPLATE.replace("__CSS__", CSS).replace("__JS__", JS)
            .replace("__GLOSSARY__", json.dumps(glossary, ensure_ascii=False))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__TEAM__", data["meta"].get("team", "Team"))
            .replace("__GENERATED__", str(data["meta"].get("generated", "")))
            .replace("__RATE__", str(data["meta"].get("defaultRate", 72)))
            .replace("__RECAP__", str(int(round(float(data["meta"].get("defaultRecapture", 0.70)) * 100))))
            .replace("__KTHRESH__", str(data["meta"].get("kThreshold", 3))))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build_dashboard] wrote {a.out} ({len(html)} bytes)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/team_data.json")
    ap.add_argument("--out", default="output/cowork-team-roi-dashboard.html")
    main(ap.parse_args())
