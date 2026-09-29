import React, { useEffect, useState } from 'react';
import BookApp from './BookApp.jsx';
import DiscoveryApp from './DiscoveryApp.jsx';
import YourStoryApp from './YourStoryApp.jsx';
import DiscoveryAdmin from './DiscoveryAdmin.jsx';
import YourStoryAdmin from './YourStoryAdmin.jsx';
import ResearchApp from './ResearchApp.jsx';
import SupportSettings from './SupportSettings.jsx';
import { FidiboHome, Welcome, QuickEntry, AvatarPicker, ParentDashboard, SupportPage, Icon, Sparks, AVATARS as DESIGN_AVATARS } from './Experience.jsx';
import { completedActivity } from './activity.js';

const AVATARS = DESIGN_AVATARS;
const LINKS = [ ['child','خانه','home'], ['stories','قصه','book'], ['craft','کاردستی','craft'], ['discover','کشف','search'] ];
const fa = n => String(n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[+d]);
const asset = key => key?.startsWith('upload:') ? `/api/assets/${key.slice(7)}` : '';
async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, { credentials: 'same-origin', ...options,
    headers: { ...(options.method && options.method !== 'GET' ? {'X-Admin-Action':'1'} : {}),
      ...(options.body && !(options.body instanceof FormData) ? {'Content-Type':'application/json'} : {}), ...(options.headers||{}) } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(response.status === 401 ? 'اطلاعات ورود درست نیست.'
    : response.status === 409 ? 'این شماره قبلاً ثبت شده است؛ از بخش ورود استفاده کنید.'
    : response.status === 422 ? 'شمارهٔ موبایل، رمز یا تاریخ انتخاب‌شده را بررسی کنید.'
    : typeof data.detail === 'string' ? data.detail : 'درخواست انجام نشد.');
  return data;
}
const json = value => JSON.stringify(value);

export function ChildNav({ active }) {
  return <nav className="u-child-nav" aria-label="بخش‌های کودک">{LINKS.map(([path,title,icon]) =>
    <a key={path} href={`/${path}`} aria-current={active === path ? 'page' : undefined}><Icon name={icon}/>{title}</a>)}
  </nav>;
}

function Entry() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { Promise.allSettled([request('/child/me'), request('/parent/me'), request('/admin/me')]).then(([kid,parent,expert]) => {
    if (kid.status === 'fulfilled') location.replace('/child');
    else if (parent.status === 'fulfilled') location.replace('/parent');
    else if (expert.status === 'fulfilled') location.replace('/expert');
  }); }, []);
  async function enter(e) { e.preventDefault(); setBusy(true); setError('');
    try { await request('/child/login', {method:'POST',body:json({code:code.replace(/[۰-۹]/g,c=>String('۰۱۲۳۴۵۶۷۸۹'.indexOf(c)))})}); location.assign('/child'); }
    catch(err) { setError(err.message); setBusy(false); }
  }
  return <main className="u-entry" dir="rtl"><div className="u-entry-card">
    <img className="u-entry-hero" src="/onb1.webp" alt="" />
    <div className="u-entry-body"><img className="u-logo" src="/fidibo-kids-logo.png" alt=""/><h1>فیدیبو کیدز</h1>
      <p>قصه بخوان، بساز و کشف کن!</p><div className="u-entry-options"><form onSubmit={enter}>
        <label htmlFor="child-code">ورود کودک با کد چهاررقمی</label><div className="u-code-row"><input id="child-code" inputMode="numeric" pattern="[0-9۰-۹]{4}" maxLength="4" autoComplete="one-time-code" value={code} onChange={e=>setCode(e.target.value)} placeholder="کد کودک" required />
          <button disabled={busy}>بریم! ←</button></div>{error && <p role="alert" className="u-error">{error}</p>}</form>
        <a className="u-parent-link" href="/parent">فضای والد ←</a><a className="u-expert-link" href="/expert">ورود کارشناس فیدیبو کیدز</a></div></div>
  </div></main>;
}

function KidHome({ child, onAvatar }) {
  const [data,setData]=useState(null),[error,setError]=useState('');
  const [banners,setBanners]=useState({});
  useEffect(()=>{Promise.all([request('/your-story/stories?language=fa'),request('/discovery/topics?language=fa'),request('/crafts')]).then(([a,b,c])=>setData({stories:a.stories,topics:b.topics,crafts:c.crafts})).catch(e=>setError(e.message));request('/book/banners').then(d=>setBanners(d.home||{})).catch(()=>{});},[]);
  return <div className="u-kid-home" dir="rtl"><header className="u-kid-hero"><Sparks/><div><p>سلام،</p><h1>دوست قشنگم!</h1><span>امروز چی دوست داری؟</span></div><button className="u-kid-avatar-button" onClick={onAvatar} aria-label="تغییر آواتار"><img className="u-kid-avatar" src={AVATARS[child.avatar]} alt="آواتار من"/></button></header><main className="u-kid-content"><div className="u-lane-grid">{[['stories','story','book','قصه'],['craft','craft','craft','کاردستی'],['discover','discover','search','کشف']].map(([href,cl,icon,title])=><a key={href} className={'u-lane '+cl} href={'/'+href}><Icon name={icon} size={28}/><strong>{title}</strong></a>)}</div>
  <h2>بریم قصه بخونیم <Icon name="book"/></h2><a className="x-continue" href="/book"><img src={banners.fish||'/api/book/art/cover'} alt=""/><div><strong>ماهی سیاه کوچولو</strong><small>بخوان، گوش بده و ماجرا رو کشف کن</small></div></a>
  <h2>برات انتخاب شده <Icon name="spark"/></h2>{error&&<p className="x-error" role="alert">{error} <button onClick={()=>location.reload()}>تلاش دوباره</button></p>}{!data&&!error&&<p role="status">در حال بارگذاری…</p>}<div className="u-content-grid">{data?.crafts.map(item=><a className="u-content-card" key={item.id} href="/craft"><div className="u-card-picture pink">{banners.craft||asset(item.content.art_key)?<img src={banners.craft||asset(item.content.art_key)} alt=""/>:<Icon name="craft" size={70}/>}</div><strong>{item.content.title}</strong><small>کاردستی · {item.content.duration}</small></a>)}{data?.stories.map(item=><a className="u-content-card" key={item.id} href="/your-story"><div className="u-card-picture"><img src={asset(item.content.nodes?.S1?.art_key)||'/your-story-cover.svg'} alt=""/></div><strong>{item.content.title}</strong><small>قصه · با انتخاب‌های تو</small></a>)}</div><h2>کشف‌های جدید <Icon name="search"/></h2><div className="u-discover-grid">{data?.topics.map(item=><a key={item.id} href={'/discover?topic='+encodeURIComponent(item.id)}><Icon name="search"/><strong>{item.content.title}</strong></a>)}</div><a className="x-child-support" href="/support"><span>برای بزرگ‌ترها · بازخورد و حمایت</span><Icon name="heart" size={19}/></a></main></div>;
}

function Stories() {
  const [stories,setStories]=useState([]);
  useEffect(()=>{request('/your-story/stories?language=fa').then(data=>setStories(data.stories)).catch(()=>{});},[]);
  return <main className="u-stories" dir="rtl"><div className="u-stories-head"><h1>قصه‌ها</h1><p>کدوم قصه رو امروز می‌خونی؟</p></div><div className="u-content-grid">
    <a className="u-content-card" href="/book"><div className="u-card-picture"><img src="/api/book/art/cover" alt=""/></div><strong>ماهی سیاه کوچولو</strong><small>بخوان، گوش بده و جواب بده</small></a>
    {stories.map(item=><a className="u-content-card" key={item.id} href="/your-story"><div className="u-card-picture green"><img src={asset(item.content.nodes?.S1?.art_key)||'/your-story-cover.svg'} alt=""/></div><strong>{item.content.title}</strong><small>داستان تو · با انتخاب‌های تو</small></a>)}
  </div></main>;
}

function Craft({ crafts }) {
  const [index,setIndex] = useState(-1);
  const craft = crafts[0]?.content;
  if (!craft) return <main className="u-craft-view"><h1>کاردستی</h1><p>فعلاً کاردستی منتشر نشده است.</p></main>;
  const picture = key => asset(key) ? <img src={asset(key)} alt=""/> : <span aria-hidden="true">{craft.icon}</span>;
  return <main className="u-craft-view" dir="rtl"><div className="u-craft-head"><button onClick={()=>index < 0 ? location.assign('/child') : setIndex(-1)} aria-label="بازگشت">→</button><h1>{craft.title}</h1></div>
    {index < 0 ? <div className="u-craft-intro"><div className="u-craft-illustration">{picture(craft.art_key)}</div><h2>{craft.title}</h2>
      <p>{fa(craft.steps.length)} مرحله · {craft.duration}</p><div className="u-craft-tip">📦 {craft.steps[0].text}</div><button className="u-craft-cta" onClick={()=>setIndex(0)}>شروع کاردستی! ✂️</button></div>
      : index >= craft.steps.length ? <div className="u-craft-intro"><span className="u-complete">🎉</span><h2>آفرین! تموم شد!</h2><p>کاردستی تو آماده‌ست!</p><button className="u-craft-cta" onClick={()=>setIndex(-1)}>بازگشت</button></div>
      : <div className="u-craft-step" key={index}><div className="u-progress"><span style={{width:`${(index+1)/craft.steps.length*100}%`}} /></div><small>{fa(index+1)} / {fa(craft.steps.length)}</small>
        <div className="u-craft-illustration">{asset(craft.steps[index].art_key) ? <img src={asset(craft.steps[index].art_key)} alt=""/> : <span aria-hidden="true">{craft.steps[index].icon}</span>}</div>
        <h2>{craft.steps[index].title}</h2><p>{craft.steps[index].text}</p><div className="u-craft-actions">{index > 0 && <button onClick={()=>setIndex(index-1)}>مرحلهٔ قبل</button>}<button className="u-craft-cta" onClick={()=>{if(index===craft.steps.length-1) completedActivity('craft',crafts[0].id);setIndex(index+1);}}>{index === craft.steps.length-1 ? 'تموم شد! 🎉' : 'مرحلهٔ بعد ←'}</button></div></div>}
  </main>;
}

function ChildSpace({ route, edition }) {
 const [state,setState]=useState({loading:true,child:null}),[crafts,setCrafts]=useState([]),[picking,setPicking]=useState(false),[error,setError]=useState('');
 useEffect(()=>{request('/child/me').then(d=>setState({loading:false,child:d.child})).catch(()=>{location.replace(edition.mode==='child-test'?'/':'/welcome');});if(route==='craft')request('/crafts').then(d=>setCrafts(d.crafts)).catch(e=>setError(e.message));},[route]);
 if(state.loading)return <p className="u-loading">در حال آماده‌سازی…</p>;
 if(!state.child.avatar||picking)return <AvatarPicker onChoose={async avatar=>{const d=await request('/child/avatar',{method:'PUT',body:json({avatar})});setState({loading:false,child:d.child});setPicking(false);document.title='خانهٔ کودک | فیدیبو کیدز';}}/>;
 return <div className="u-child-space">{error?<p className="x-error" role="alert">{error}<button onClick={()=>location.reload()}>تلاش دوباره</button></p>:route==='child'?<KidHome child={state.child} onAvatar={()=>setPicking(true)}/>:route==='stories'?<Stories/>:route==='craft'?<Craft crafts={crafts}/>:route==='book'?<BookApp/>:route==='discover'?<DiscoveryApp/>:<YourStoryApp/>}<ChildNav active={['your-story','book'].includes(route)?'stories':route}/></div>;
}

function CraftAdmin({api}) {
  const [item,setItem] = useState(null), [value,setValue] = useState(null), [notice,setNotice] = useState(''), [busy,setBusy] = useState(false);
  useEffect(()=>{api('/admin/crafts').then(data=>{setItem(data.crafts[0]);setValue(structuredClone(data.crafts[0]?.content));});},[api]);
  if(!value)return <p>کاردستی در حال بارگذاری است…</p>;
  const set=(field,v)=>setValue(old=>({...old,[field]:v}));
  async function upload(file,stepIndex) { if(!file)return;setBusy(true);try {const form=new FormData();form.append('file',file);
      const key=(await api('/admin/assets',{method:'POST',body:form})).art_key;
      if(stepIndex===undefined)set('art_key',key);
      else setValue(old=>({...old,steps:old.steps.map((s,i)=>i===stepIndex?{...s,art_key:key}:s)}));
    } catch(e){setNotice(e.message);} finally {setBusy(false);} }
  async function save() {setBusy(true);try{await api(`/admin/crafts/${item.id}`,{method:'PUT',body:json(value)});setNotice('کاردستی ذخیره شد.');}catch(e){setNotice(e.message);}finally{setBusy(false);} }
  return <section className="u-editor" dir="rtl"><h2>کاردستی · {value.title}</h2><p>فقط همین عنوان از پروتوتایپ منتقل شده است. متن و تصویر هر مرحله را می‌توان ویرایش کرد.</p>
    <label>عنوان<input value={value.title} onChange={e=>set('title',e.target.value)}/></label><label>زمان<input value={value.duration} onChange={e=>set('duration',e.target.value)}/></label><label>نماد<input maxLength="8" value={value.icon} onChange={e=>set('icon',e.target.value)}/></label>
    <label>تصویر کاردستی<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload(e.target.files[0])}/></label>{asset(value.art_key)&&<><img className="u-admin-preview" src={asset(value.art_key)} alt="تصویر کاردستی"/><button onClick={()=>set('art_key','')}>برداشتن تصویر</button></>}
    {value.steps.map((step,i)=><fieldset key={i}><legend>مرحلهٔ {fa(i+1)}</legend><label>عنوان<input value={step.title} onChange={e=>setValue(old=>({...old,steps:old.steps.map((s,n)=>n===i?{...s,title:e.target.value}:s)}))}/></label>
      <label>متن<textarea value={step.text} onChange={e=>setValue(old=>({...old,steps:old.steps.map((s,n)=>n===i?{...s,text:e.target.value}:s)}))}/></label>
      <label>نماد<input maxLength="8" value={step.icon} onChange={e=>setValue(old=>({...old,steps:old.steps.map((s,n)=>n===i?{...s,icon:e.target.value}:s)}))}/></label>
      <label>تصویر<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload(e.target.files[0],i)}/></label>{asset(step.art_key)&&<><img className="u-admin-preview" src={asset(step.art_key)} alt="تصویر مرحله"/><button onClick={()=>setValue(old=>({...old,steps:old.steps.map((s,n)=>n===i?{...s,art_key:''}:s)}))}>برداشتن تصویر</button></>}</fieldset>)}
    {notice&&<p role="status">{notice}</p>}<button className="u-primary" disabled={busy} onClick={save}>ذخیرهٔ کاردستی</button>
    <button onClick={async()=>{await api(`/admin/crafts/${item.id}/status/${item.status==='published'?'draft':'published'}`,{method:'POST'});setItem({...item,status:item.status==='published'?'draft':'published'});}}>{item.status==='published'?'برداشتن از نمایش کودک':'انتشار'}</button>
  </section>;
}

function HomeSettings({api}) {
  const [home,setHome]=useState(null), [notice,setNotice]=useState(''), [busy,setBusy]=useState(false);
  const refresh=()=>api('/admin/banners').then(data=>setHome(data.home)).catch(e=>setNotice(e.message));
  useEffect(refresh,[]);
  async function change(slot,file) {setBusy(true);setNotice('');try {
    let art_key=null;
    if(file){const form=new FormData();form.append('file',file);art_key=(await api('/admin/assets',{method:'POST',body:form})).art_key;}
    await api(`/admin/banners/home:${slot}`,{method:'PUT',body:json({art_key})});await refresh();setNotice('تصویر صفحهٔ اصلی ذخیره شد.');
  }catch(e){setNotice(e.message);}finally{setBusy(false);}}
  const names={hero:'تصویر خوشامدگویی',fish:'کارت ماهی سیاه کوچولو',craft:'کارت کاردستی'};
  return <section className="u-editor" dir="rtl"><h2>تصاویر صفحهٔ اصلی کودک</h2><p>تصویر تازه پس از ذخیره در خانهٔ کودک دیده می‌شود.</p>
    {home&&Object.entries(names).map(([key,name])=><fieldset key={key}><legend>{name}</legend>
      {home[key]&&<img className="u-admin-preview" src={asset(home[key])} alt={name}/>}
      <label>بارگذاری تصویر<input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={e=>{change(key,e.target.files?.[0]);e.target.value='';}}/></label>
      {home[key]&&<button disabled={busy} onClick={()=>change(key,null)}>برداشتن تصویر</button>}</fieldset>)}
    {notice&&<p role="status">{notice}</p>}</section>;
}

const SOLAR_MONTHS=['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
function solarYearNow() {
  try {return Number(new Intl.DateTimeFormat('en-US-u-ca-persian',{year:'numeric'}).formatToParts(new Date()).find(p=>p.type==='year').value);}
  catch {return 1405;}
}
function esfandDays(year) {
  if (!year) return 29;
  try {
    const formatter=new Intl.DateTimeFormat('en-US-u-ca-persian',{year:'numeric',month:'numeric',day:'numeric',timeZone:'UTC'});
    for(let day=17;day<=23;day++) {
      const parts=Object.fromEntries(formatter.formatToParts(new Date(Date.UTC(Number(year)+622,2,day))).map(p=>[p.type,Number(p.value)]));
      if(parts.year===Number(year)&&parts.month===12&&parts.day===30)return 30;
    }
  }catch { /* older browsers keep Esfand at 29 days */ }
  return 29;
}
function SolarBirthPicker({value,onChange,optional=false}) {
  const parsed=/^(1[34]\d{2})-(\d{2})-(\d{2})$/.exec(value||'');
  const [year,setYear]=useState(parsed?.[1]||''),[month,setMonth]=useState(parsed?String(Number(parsed[2])):''),[day,setDay]=useState(parsed?String(Number(parsed[3])):'');
  const maxDay=Number(month)<=6?31:Number(month)<=11?30:esfandDays(year);
  const years=Array.from({length:solarYearNow()-1380+1},(_,i)=>solarYearNow()-i);
  function change(part,next){const y=part==='year'?next:year,m=part==='month'?next:month;
    const maximum=Number(m)<=6?31:Number(m)<=11?30:esfandDays(y);
    const d=part==='day'?next:part==='month'||Number(day)>maximum?'':day;
    setYear(y);setMonth(m);setDay(d);onChange(y&&m&&d?`${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`:'');}
  return <fieldset className="u-solar-picker"><legend>تاریخ تولد شمسی{optional?' (اختیاری)':''}</legend><div>
    <label>روز<select value={day} onChange={e=>change('day',e.target.value)}><option value="">روز</option>{Array.from({length:maxDay},(_,i)=><option key={i+1} value={i+1}>{fa(i+1)}</option>)}</select></label>
    <label>ماه<select value={month} onChange={e=>change('month',e.target.value)}><option value="">ماه</option>{SOLAR_MONTHS.map((name,i)=><option key={name} value={i+1}>{name}</option>)}</select></label>
    <label>سال<select value={year} onChange={e=>change('year',e.target.value)}><option value="">سال</option>{years.map(y=><option key={y} value={y}>{fa(y)}</option>)}</select></label>
  </div>{value&&<small>تاریخ انتخاب‌شده: {fa(value.replaceAll('-','/'))}</small>}</fieldset>;
}

function ParentHome({api,onChild}) {
  const [children,setChildren] = useState([]), [name,setName] = useState(''), [birth,setBirth] = useState(''), [selected,setSelected]=useState(''), [password,setPassword]=useState(''), [error,setError]=useState('');
  const [editing,setEditing]=useState(null);
  const [progress,setProgress]=useState([]);
  const refresh=()=>{api('/parent/children').then(data=>setChildren(data.children)).catch(e=>setError(e.message));
    api('/parent/progress').then(data=>setProgress(data.items)).catch(()=>{});};
  useEffect(refresh,[]);
  async function add(e){e.preventDefault();setError('');try{await api('/parent/children',{method:'POST',body:json({name,birth_date:birth})});setName('');setBirth('');refresh();}catch(err){setError(err.message);}}
  async function enter(e){e.preventDefault();setError('');try{await api('/parent/enter-child',{method:'POST',body:json({child_id:selected,password})});location.assign('/child');}catch(err){setError(err.message);}}
  async function update(e){e.preventDefault();setError('');try{await api(`/parent/children/${editing.id}`,{method:'PUT',body:json({name:editing.name,birth_date:editing.birth_date,avatar:editing.avatar,daily_limit_min:Number(editing.daily_limit_min)})});setEditing(null);refresh();}catch(err){setError(err.message);}}
  return <div className="u-parent-home" dir="rtl"><h1>خانواده و کودکان</h1><p>هر کودک کد ورود خودش را دارد. برای ورود به فضای او از اینجا، رمز فعلی بزرگسال لازم است.</p>
    <div className="u-child-cards">{children.map(c=><article key={c.id}><img src={AVATARS[c.avatar]||'/elephant-avatar.png'} alt=""/><div><strong>{c.name}</strong><small>کد ورود: {fa(c.entry_code)}</small><small>قصه {fa(progress.filter(p=>p.child_id===c.id&&p.lane==='story').length)} · کشف {fa(progress.filter(p=>p.child_id===c.id&&p.lane==='discovery').length)} · کاردستی {fa(progress.filter(p=>p.child_id===c.id&&p.lane==='craft').length)}</small></div><button onClick={()=>setSelected(c.id)}>ورود به فضای کودک</button><button onClick={()=>setEditing(c)}>ویرایش</button></article>)}</div>
    <form className="u-parent-form" onSubmit={add}><h2>افزودن کودک</h2><label>نام کودک<input value={name} onChange={e=>setName(e.target.value)} required/></label>
      <SolarBirthPicker key={birth?'selected':'new'} value={birth} onChange={setBirth} optional/><button className="u-primary">ساخت پروفایل</button></form>
    {selected&&<form className="u-switch" onSubmit={enter}><h2>ورود به فضای کودک</h2><label>رمز فعلی بزرگسال<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/></label>
      <button className="u-primary">ورود کودک</button><button type="button" onClick={()=>setSelected('')}>انصراف</button></form>}
    {editing&&<form className="u-switch" onSubmit={update}><h2>ویرایش {editing.name}</h2><label>نام<input value={editing.name} onChange={e=>setEditing({...editing,name:e.target.value})} required/></label>
      <SolarBirthPicker key={editing.id} value={editing.birth_date} onChange={birth_date=>setEditing(old=>({...old,birth_date}))} optional/><label>زمان پیشنهادی روزانه (دقیقه)<input type="number" min="5" max="240" value={editing.daily_limit_min} onChange={e=>setEditing({...editing,daily_limit_min:e.target.value})}/></label>
      <button className="u-primary">ذخیره</button><button type="button" onClick={()=>setEditing(null)}>انصراف</button></form>}
    {error&&<p role="alert" className="u-error">{error}</p>}</div>;
}

function ParentLogin({onLogin}) {
  const [phone,setPhone]=useState(''),[password,setPassword]=useState(''),[register,setRegister]=useState(false);
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function submit(e){e.preventDefault();setBusy(true);setError('');try{
    await request(register?'/parent/register':'/parent/login',{method:'POST',body:json({phone:phone.replace(/[۰-۹]/g,c=>String('۰۱۲۳۴۵۶۷۸۹'.indexOf(c))),password})});onLogin();
  }catch(err){setError(err.message);}finally{setBusy(false);}}
  return <main className="u-entry" dir="rtl"><form className="u-parent-login" onSubmit={submit}><a href="/">→ بازگشت</a><img src="/fidibo-kids-logo.png" alt=""/>
    <h1>{register?'ساخت حساب والد':'ورود والد'}</h1><p>فضای خانواده و پیشرفت کودک</p>
    <label>شمارهٔ موبایل<input type="tel" inputMode="numeric" autoComplete="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="۰۹۱۲۱۲۳۴۵۶۷" required/></label>
    <label>رمز حساب والد<input type="password" minLength="8" autoComplete={register?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)} required/></label>
    {error&&<p className="u-error" role="alert">{error}</p>}<button className="u-primary" disabled={busy}>{busy?'در حال بررسی…':register?'ساخت حساب':'ورود'}</button>
    <button type="button" className="u-form-switch" onClick={()=>{setRegister(!register);setError('');}}>{register?'حساب دارم؛ وارد می‌شوم':'حساب ندارم؛ ثبت‌نام می‌کنم'}</button>
    <small>شمارهٔ موبایل در این نسخهٔ محلی با پیامک تأیید نمی‌شود.</small></form></main>;
}

function ParentArea({api}) {
  const [auth,setAuth]=useState(null);
  useEffect(()=>{api('/parent/me').then(()=>setAuth(true)).catch(()=>setAuth(false));},[api]);
  useEffect(()=>{document.title='فضای والد | فیدیبو کیدز';},[]);
  if(auth===null)return <p className="u-loading">در حال بررسی ورود والد…</p>;
  if(!auth)return <ParentLogin onLogin={()=>setAuth(true)}/>;
  return <div className="u-parent-shell" dir="rtl"><aside className="u-parent-nav"><div className="u-parent-brand"><img src="/fidibo-kids-logo.png" alt=""/><div><strong>فیدیبو کیدز</strong><small>فضای والد</small></div></div>
    <nav><span className="u-nav-label">فرزندها و پیشرفت</span></nav><button className="u-signout" onClick={async()=>{await api('/parent/logout',{method:'POST'});setAuth(false);}}>خروج والد</button></aside>
    <main className="u-parent-work"><header><h1>فضای والد</h1><p>پروفایل کودک و روند فعالیت‌ها</p></header><div className="u-embedded"><ParentHome api={api}/></div></main></div>;
}

const SECTIONS = [['home','صفحهٔ اصلی کودک'],['story','محتوای قصه'],['your-story','قصه‌های «داستان تو»'],['discovery','محتوای کشف'],['craft','محتوای کاردستی'],['support','پیوندهای حمایت'],['feedback','بازخورد کاربران'],['audio','داوری صدا']];
function FeedbackAdmin({api}) {
 const [items,setItems]=useState([]),[loading,setLoading]=useState(false),[error,setError]=useState('');
 async function refresh(){setLoading(true);setError('');try{const data=await api('/admin/test-feedback');setItems(data.items||[]);}catch(e){setError(e.message);}finally{setLoading(false);}}
 useEffect(()=>{refresh();},[]);
 return <section className="admin-recording" dir="rtl"><div className="admin-section-heading"><div><h2>بازخورد کاربران</h2><p>امتیاز و نظرهای ثبت‌شده از صفحهٔ بازخورد و حمایت</p></div><button onClick={refresh} disabled={loading}>{loading?'در حال بارگذاری…':'تازه‌سازی'}</button></div>
  {error&&<p className="u-error" role="alert">{error}</p>}
  {!loading&&!items.length&&<p>هنوز بازخوردی ثبت نشده است.</p>}
  {items.length>0&&<div className="feedback-table-wrap"><table className="feedback-table"><thead><tr><th>امتیاز</th><th>نظر</th><th>زمان ثبت</th></tr></thead><tbody>{items.map(item=><tr key={item.source+'-'+item.id+'-'+item.created_at}><td><strong>{fa(item.rating)} از ۵</strong></td><td>{item.comment||'بدون توضیح'}</td><td>{new Date(item.created_at).toLocaleString('fa-IR')}</td></tr>)}</tbody></table></div>}
 </section>;
}

function ExpertHub({api, Login, BookEditor}) {
  const [auth,setAuth]=useState(null), [tab,setTab]=useState('home');
  const [opened,setOpened]=useState(['home']);
  function open(key){setTab(key);setOpened(old=>old.includes(key)?old:[...old,key]);}
  useEffect(()=>{api('/admin/me').then(()=>setAuth(true)).catch(()=>setAuth(false));},[api]);
  useEffect(()=>{document.title=`${SECTIONS.find(([key])=>key===tab)?.[1]||'میزکار کارشناس'} | کارشناس فیدیبو کیدز`;},[tab]);
  if(auth===null)return <p className="u-loading">در حال بررسی ورود…</p>;
  if(!auth)return <Login onLogin={()=>setAuth(true)}/>;
  return <div className="u-parent-shell" dir="rtl"><aside className="u-parent-nav"><div className="u-parent-brand"><img src="/fidibo-kids-logo.png" alt=""/><div><strong>فیدیبو کیدز</strong><small>میزکار کارشناس</small></div></div>
      <nav aria-label="میزکار محتوا">{SECTIONS.map(([key,label])=><button key={key} aria-current={tab===key?'page':undefined} onClick={()=>open(key)}>{label}</button>)}</nav>
      <button className="u-signout" onClick={async()=>{await api('/admin/logout',{method:'POST'});setAuth(false);}}>خروج</button></aside>
      <main className="u-parent-work"><header><h1>{SECTIONS.find(([key])=>key===tab)?.[1]}</h1><p>مدیریت محتوای فیدیبو کیدز</p></header>
        {opened.map(key=><div className="u-embedded" key={key} hidden={tab!==key}>{key==='home'?<HomeSettings api={api}/> : key==='story'?<BookEditor/> : key==='your-story'?<YourStoryAdmin api={api} Login={Login}/>
          :key==='discovery'?<DiscoveryAdmin api={api} Login={Login}/> :key==='craft'?<CraftAdmin api={api}/> :key==='support'?<SupportSettings api={api}/> :key==='feedback'?<FeedbackAdmin api={api}/> : <ResearchApp api={api} Login={Login}/>}</div>)}
      </main></div>;
}
export default function UnifiedApp({api,Login,BookEditor}) {
 const route=location.pathname.split('/')[1], [edition,setEdition]=useState(null),[error,setError]=useState('');
 useEffect(()=>{request('/edition').then(setEdition).catch(e=>setError(e.message));},[]);
 useEffect(()=>{const titles={child:'خانهٔ کودک',stories:'قصه‌ها',book:'ماهی سیاه کوچولو',craft:'کاردستی',discover:'کشف','your-story':'داستان تو',parent:'داشبورد والدین',expert:'میزکار کارشناس',support:'بازخورد و حمایت',welcome:'ورود به کیدز'};document.title=route?`${titles[route]||'فیدیبو'} | فیدیبو کیدز`:'فیدیبو';
   const icon=document.querySelector('link[rel="icon"]');if(icon){icon.type='image/png';icon.href=route?'/fidibo-kids-favicon.png':'/fidibo-favicon.png';}
 },[route]);
 if(error)return <main className="x-phone x-center" dir="rtl"><p role="alert">{error}</p><button onClick={()=>location.reload()}>تلاش دوباره</button></main>;
 if(!edition)return <p className="u-loading">در حال آماده‌سازی…</p>;
 if(route==='expert')return <ExpertHub api={api} Login={Login} BookEditor={BookEditor}/>;
 if(route==='support')return <SupportPage edition={edition}/>;
 if(route==='parent')return edition.mode==='presentation'?<ParentDashboard/>:<QuickEntry/>;
 if(['child','stories','book','your-story','discover','craft'].includes(route))return <ChildSpace route={route} edition={edition}/>;
 if(edition.mode==='child-test')return <QuickEntry/>;
 if(route==='welcome')return <Welcome/>;
 return <FidiboHome/>;
}
