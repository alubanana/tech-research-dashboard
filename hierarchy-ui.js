const HIERARCHY=DATA.hierarchy;
const hierarchyState={theme:'daily-ai',betTheme:''};
const themeForDirection=id=>HIERARCHY.themes.find(t=>t.primaryDirections.includes(id));
const themeCompanies=t=>COMPANIES.filter(c=>c.directions.some(id=>t.directions.includes(id)));
const themeProduct=id=>HIERARCHY.products.find(p=>p.id===id);
const techButton=id=>{const d=DATA.directions.find(d=>d.id===id);return '<button data-detail="'+esc(id)+'">'+esc(d.name)+'</button>';};
function hierarchyEvidence(e){
 const source=e.sourceId?SYS.sources.find(s=>s.id===e.sourceId):DATA.directions.find(d=>d.id===e.direction)?.signals.find(r=>r.date===e.date);
 return '<div class="theme-evidence-item">'+esc(e.label)+' '+(source?link(source.url,'来源'):'')+'<time title="'+esc(e.kind)+'">'+esc(e.date)+'</time></div>';
}
function hierarchyCompanyRows(cs){return cs.map(c=>{
 const s=PRESENTATION.companies[c.id],v=c.valuation;
 return '<tr><td><div class="home-company-name">'+companyButton(c)+starCompany(c)+'</div></td><td title="'+esc(c.founders)+'">'+esc(s.founders)+'</td><td><a class="home-value" href="'+esc(v.url)+'" target="_blank" rel="noopener noreferrer">'+esc(v.amount)+'</a><div class="cell-sub">'+esc(v.basis)+'</div>'+(/媒体|未确认/.test(v.status)?'<div class="valuation-state">'+esc(v.status)+'</div>':'')+(v.date?'<time>'+esc(v.date)+'</time>':'')+'</td><td><strong>'+esc(s.round)+'</strong><div class="cell-sub">'+esc(c.capital.amount)+'</div>'+(s.roundNote?'<div class="cell-sub">'+esc(s.roundNote)+'</div>':'')+(s.dateLabel||c.capital.date?'<time>'+esc(s.dateLabel||c.capital.date)+'</time>':'')+'</td><td>'+esc(s.investors)+(s.investorNote?'<div class="cell-sub">'+esc(s.investorNote)+'</div>':'')+'</td></tr>';
 }).join('');}
function hierarchyHome(){
 const q=state.q.toLowerCase(),matches=t=>{
  const cs=themeCompanies(t),content=JSON.stringify([t,t.products.map(themeProduct),DATA.directions.filter(d=>t.directions.includes(d.id)),cs]);
  return (!q||content.toLowerCase().includes(q))&&(!state.favorites||t.directions.some(id=>saved.includes(id))||cs.some(c=>saved.includes('company:'+c.id)));
 };
 const themes=HIERARCHY.themes.filter(matches);if(!themes.length)return '<div class="empty">没有匹配的主线或公司</div>';
 const t=themes.find(t=>t.id===hierarchyState.theme)||themes[0];hierarchyState.theme=t.id;
 let cs=themeCompanies(t);if(q&&cs.some(homeCompanySearch))cs=cs.filter(homeCompanySearch);if(state.favorites)cs=cs.filter(c=>saved.includes('company:'+c.id)||c.directions.some(id=>saved.includes(id)));
 const rail=['生活与工作','基础设施'].map(kind=>{const ts=themes.filter(t=>t.kind===kind);return ts.length?'<div class="theme-group-label">'+kind+'</div>'+ts.map(th=>'<button class="theme-pick" data-theme="'+th.id+'" aria-pressed="'+(th.id===t.id)+'"><strong>'+esc(th.name)+'</strong><span>'+esc(th.adoption)+'</span></button>').join(''):'';}).join('');
 const paths=t.products.map(id=>{const p=themeProduct(id);return '<div class="product-path"><span>'+esc(p.name)+'</span><span>→</span><div class="company-chips">'+p.directions.map(techButton).join('')+'</div></div>';}).join('');
 return '<div class="theme-layout"><aside class="theme-rail" aria-label="变化主线">'+rail+'</aside><section class="theme-content"><div class="theme-title"><h2>'+esc(t.name)+'</h2><button class="quiet" data-theme-bets="'+t.id+'">查看赌注 ↗</button></div><p class="theme-question" title="'+esc(t.question)+'">'+esc(t.change)+'</p><div class="theme-observation"><span>已有证据</span><div>'+t.evidence.map(hierarchyEvidence).join('')+'</div><span>下一证据</span><p>'+esc(t.next)+'</p></div><div class="theme-section-title"><h3>产品与服务 → 技术路线</h3><span title="研究归类；点击技术查看原始证据">'+t.directions.length+' 项技术</span></div>'+paths+'<div class="theme-section-title"><h3>公司 <small>'+cs.length+'</small></h3><span>核查 '+DATA.companyData.checkedAt+'</span></div><div class="home-table-scroll theme-companies"><table class="home-company-table"><thead><tr><th>公司</th><th>创始人</th><th>估值</th><th>轮次／资本节点</th><th>核心投资方</th></tr></thead><tbody>'+hierarchyCompanyRows(cs)+'</tbody></table>'+(!cs.length?'<div class="theme-empty">暂无匹配公司</div>':'')+'</div></section></div>';
}
function hierarchyBetRow(b){
 const e=ResearchModel.estimate(betScores(b),{prior:b.prior}),mine=forecastJournal.filter(r=>r.bet===b.id&&r.lens===systemState.lens).at(-1);
 return '<div class="forecast-row"><button class="forecast-question" data-bet="'+b.id+'"><strong>'+esc(b.name)+'</strong><span>'+esc(betEvent(b))+'</span></button><div>'+oddsChart(e)+'<div class="odds-caption">'+pct(e.low)+'–'+pct(e.high)+' · 假设范围</div></div><div class="forecast-percent">'+pct(e.p)+'<span>'+(mine?'我的判断 '+pct(mine.p):'尚未记录个人判断')+'</span></div><button class="quiet" data-bet="'+b.id+'">查看／记录</button></div>';
}
betsView=function(){
 const consumer=systemState.lens==='consumer',themes=HIERARCHY.themes.filter(t=>!hierarchyState.betTheme||t.id===hierarchyState.betTheme);
 const groups=themes.map(t=>({t,bets:SYS.bets.filter(b=>t.primaryDirections.includes(b.direction)&&betScores(b))})).filter(g=>g.bets.length);
 const head='<div class="forecast-head"><span>截至2036-12-31的具体事件</span><span class="axis"><i>0</i><i>25</i><i>50</i><i>75</i><i>100%</i></span><span>事件概率</span><span>记录</span></div>';
 const milestones=SYS.milestones.filter(m=>themes.some(t=>t.primaryDirections.includes(m.parent)));
 return '<div class="system-top"><select id="bet-theme" class="bet-theme-select" aria-label="赌注主线"><option value="">全部主线</option>'+HIERARCHY.themes.map(t=>'<option value="'+t.id+'" '+(hierarchyState.betTheme===t.id?'selected':'')+'>'+esc(t.name)+'</option>').join('')+'</select><div class="segmented"><button data-lens="industry" aria-pressed="'+!consumer+'">具体应用</button><button data-lens="consumer" aria-pressed="'+consumer+'">大众直接使用</button></div><span class="model-status" title="人工参数与打分；各行对应不同事件。">人工假设 · 未校准</span><button class="quiet" data-method>算法与验证</button></div>'+groups.map(({t,bets})=>'<section class="bet-theme-group"><div class="bet-group-heading"><h2>'+esc(t.name)+'</h2><span>'+esc(t.kind)+'</span><button data-theme="'+t.id+'">主线与公司 ↗</button></div>'+head+bets.map(hierarchyBetRow).join('')+'</section>').join('')+(!groups.length?'<div class="theme-empty">该主线按实际服务、治疗或供电规模观察。<button class="quiet" data-lens="industry">查看具体应用</button></div>':'')+(milestones.length?'<h2 class="system-section">短期节点</h2><div class="milestones">'+milestones.map(m=>{const e=ResearchModel.estimate(m.scores,{prior:m.prior});return '<button data-milestone="'+m.id+'"><span>'+esc(m.name)+'</span><strong>'+pct(e.p)+'</strong><time>'+esc(m.deadline)+'</time></button>';}).join('')+'</div>':'')+'<div class="system-top" style="margin-top:26px"><h2>判断记录 <small>'+forecastJournal.length+'</small></h2><button class="quiet" data-export-forecasts>导出记录 ↓</button></div>'+journalView();
};
const technicalGraphView=graphView;
graphView=function(){
 const snap=SYS.snapshots.find(s=>s.id===systemState.graphSnapshot)||SYS.snapshots.at(-1),h=snap.hierarchy;
 const paths=h?h.themes.filter(t=>t.directions.includes(systemState.graphFocus)).map(t=>'<div class="theme-breadcrumb"><button data-theme="'+esc(t.id)+'">'+esc(t.name)+'</button><span>→</span><span>'+t.products.map(id=>h.products.find(p=>p.id===id)).filter(p=>p.directions.includes(systemState.graphFocus)).map(p=>esc(p.name)).join(' / ')+'</span><span>→</span><strong>'+esc(DATA.directions.find(d=>d.id===systemState.graphFocus).name)+'</strong></div>').join(''):'';
 return (h?'<div class="graph-lineage"><span>主线 → 产品与服务 → 技术路线 · 研究归类 '+esc(h.reviewedAt)+'</span>'+paths+'</div>':'')+technicalGraphView();
};
const technicalOpenDirection=openDirection;
openDirection=function(id){technicalOpenDirection(id);const t=themeForDirection(id);if(t)$('#dialog-meta').textContent=t.name+' / 技术路线 / '+DATA.directions.find(d=>d.id===id).stage;};
const hierarchyPreviousRender=render;
render=function(){
 $('#domain').hidden=false;$('#stage').hidden=false;
 if(state.view==='directions'){
  configureTools();$('#tools').hidden=false;$('#tools').style.display='flex';$('#domain').hidden=true;$('#stage').hidden=true;$('#search').placeholder='搜索主线、技术、公司、创始人、投资方…';
  $('h1').textContent='变化主线';$('.heading-side').textContent='4 条生活与工作主线 / 1 条基础设施 / 10 项技术';$('#checked').textContent='结构更新 '+HIERARCHY.reviewedAt;$('#coverage').textContent='技术核查 '+DATA.checkedAt+' · 公司核查 '+DATA.companyData.checkedAt;
  $('#content').innerHTML=hierarchyHome();document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.view==='directions'));return;
 }
 hierarchyPreviousRender();
 if(state.view==='company'){
  const c=COMPANIES.find(c=>c.id===state.company),themes=HIERARCHY.themes.filter(t=>c.directions.some(id=>t.directions.includes(id)));
  if(themes.length)$('#content').insertAdjacentHTML('afterbegin','<div class="theme-breadcrumb"><span>相关主线</span>'+themes.map(t=>'<button data-theme="'+t.id+'">'+esc(t.name)+'</button>').join('')+'</div>');
 }
};
document.addEventListener('click',e=>{
 const t=e.target.closest('[data-theme]');if(t){hierarchyState.theme=t.dataset.theme;if(state.view!=='directions'){state.q='';$('#search').value='';state.favorites=false;$('#favorites').setAttribute('aria-pressed','false');$('#favorites').textContent='仅看关注';}navigate('#view/directions');}
 const b=e.target.closest('[data-theme-bets]');if(b){hierarchyState.betTheme=b.dataset.themeBets;systemState.lens='industry';navigate('#view/bets');}
});
document.addEventListener('change',e=>{if(e.target.id==='bet-theme'){hierarchyState.betTheme=e.target.value;render();}});
