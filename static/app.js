const form = document.getElementById('ideaForm');
const idea = document.getElementById('idea');
const charCount = document.getElementById('charCount');
const generateBtn = document.getElementById('generateBtn');
let currentBlueprint = null;
let currentProjectId = null;

idea.addEventListener('input', () => charCount.textContent = `${idea.value.length} / 4000`);
function toast(message) {
  const el = document.getElementById('toast'); el.textContent = message; el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2800);
}
function esc(value='') {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function list(items) { return `<ul>${(items||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`; }
function card(label, title, body, wide=false) {
  return `<article class="bp-card ${wide?'wide':''}"><div class="bp-label">${label}</div>${title?`<h3>${esc(title)}</h3>`:''}${body}</article>`;
}
function renderBlueprint(b) {
  const budget = (b.budget_breakdown||[]).map(x=>`<div class="subitem"><strong>${esc(x.item)} · ${esc(x.amount)}</strong><p>${esc(x.note)}</p></div>`).join('');
  const weeks = (b.action_plan||[]).map(w=>`<div class="week"><strong>${esc(w.week)}</strong>${list(w.tasks)}</div>`).join('');
  const risks = (b.risks||[]).map(r=>`<div class="risk"><strong>${esc(r.risk)}</strong><p>${esc(r.mitigation)}</p></div>`).join('');
  const assumptions = list(b.assumptions);
  document.getElementById('blueprint').innerHTML =
    card('THE BIG PICTURE','Executive summary',`<p>${esc(b.executive_summary)}</p>`,true)+
    card('THE PROBLEM','What needs solving',`<p>${esc(b.problem)}</p>`)+
    card('YOUR SOLUTION','What you could build',`<p>${esc(b.solution)}</p>`)+
    card('REVENUE OPTIONS','Business model',list(b.business_model))+
    card('MONEY MATTERS','Indicative budget',budget)+
    card('WHO IT SERVES','Target customers',list(b.target_customers))+
    card('GET THE WORD OUT','Marketing strategy',list(b.marketing_strategy))+
    card('YOUR FIRST MONTH','4-week action roadmap',weeks,true)+
    card('THINK AHEAD','Risks & mitigations',risks)+
    card('MEASURE PROGRESS','Success metrics',list(b.success_metrics))+
    card('BE TRANSPARENT','Assumptions to validate',assumptions)+
    card('A QUICK REMINDER','Important note',`<p>${esc(b.disclaimer||'Validate assumptions before making decisions.')}</p>`,true);
  document.getElementById('resultTitle').textContent = b.project_title || 'Your blueprint';
  document.getElementById('results').classList.remove('hidden');
  document.getElementById('results').scrollIntoView({behavior:'smooth',block:'start'});
}
form.addEventListener('submit', async e => {
  e.preventDefault();
  if (idea.value.trim().length < 12) return toast('Add a little more detail about your idea.');
  generateBtn.disabled = true; generateBtn.innerHTML = '<span>✦</span> Building your blueprint… <b>◌</b>';
  try {
    const res = await fetch('/api/generate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      idea:idea.value, category:document.getElementById('category').value,
      budget:document.getElementById('budget').value, audience:document.getElementById('audience').value
    })});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Something went wrong.');
    currentBlueprint = data.blueprint; currentProjectId = data.id;
    const notice = document.getElementById('demoNotice');
    notice.textContent = data.blueprint.disclaimer || (data.demo ? 'Demo mode is active.' : 'Generated with Gemini AI. Review assumptions before acting.');
    notice.classList.remove('hidden');
    renderBlueprint(currentBlueprint); loadProjects(); toast('Your blueprint is ready!');
  } catch(err) { toast(err.message); }
  finally { generateBtn.disabled=false; generateBtn.innerHTML='<span>✦</span> Generate my blueprint <b>→</b>'; }
});
function downloadReport() {
  if (!currentBlueprint) return;
  const b=currentBlueprint;
  let lines=[b.project_title||'Dream-to-Reality AI Blueprint','='.repeat(45),'',b.executive_summary,''];
  const sections=[['Problem',b.problem],['Solution',b.solution],['Business model',b.business_model],['Budget breakdown',b.budget_breakdown],['Target customers',b.target_customers],['Marketing strategy',b.marketing_strategy],['Action plan',b.action_plan],['Risks',b.risks],['Success metrics',b.success_metrics],['Assumptions',b.assumptions],['Disclaimer',b.disclaimer]];
  for(const [title,value] of sections){lines.push(title.toUpperCase(),'-'.repeat(title.length));lines.push(typeof value==='string'?value:JSON.stringify(value,null,2));lines.push('');}
  const blob=new Blob([lines.join('\n')],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download='dream-to-reality-blueprint.txt';a.click();URL.revokeObjectURL(url);
}
document.getElementById('downloadBtn').addEventListener('click',downloadReport);
async function loadProjects(){
  const listEl=document.getElementById('projectsList');
  try{
    const res=await fetch('/api/projects'),items=await res.json();
    if(!items.length){listEl.innerHTML='<div class="empty-state"><span>✧</span><h3>Your next big thing starts here.</h3><p>Generate a blueprint and it will appear in your idea vault.</p></div>';return;}
    listEl.innerHTML=items.map(p=>`<div class="project-item" data-id="${p.id}"><div class="project-icon">✧</div><h3>${esc(p.title)}</h3><p>${esc(p.category||'General')} · ${new Date(p.created_at).toLocaleDateString()}</p></div>`).join('');
    listEl.querySelectorAll('.project-item').forEach(el=>el.addEventListener('click',()=>openProject(el.dataset.id)));
  }catch(e){listEl.innerHTML='<div class="empty-state">Could not load saved projects.</div>';}
}
async function openProject(id){
  try{
    const res=await fetch(`/api/projects/${id}`),data=await res.json();
    if(!res.ok) throw new Error(data.error);
    currentBlueprint=data.blueprint;currentProjectId=data.id;
    document.getElementById('demoNotice').textContent=currentBlueprint.disclaimer||'Saved blueprint loaded.';
    document.getElementById('demoNotice').classList.remove('hidden');
    renderBlueprint(currentBlueprint);toast('Saved blueprint opened.');
  }catch(e){toast(e.message);}
}
document.getElementById('refreshProjects').addEventListener('click',loadProjects);
loadProjects();
