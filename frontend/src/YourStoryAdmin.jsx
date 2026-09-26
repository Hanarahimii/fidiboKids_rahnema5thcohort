import React, { useEffect, useState } from 'react';
import { persianDigits } from './persian.js';
import './your-story.css';

const LANGS = [['fa','فارسی'],['azb','ترکی']];
const TERMINALS = new Set(['HAPPY','OPEN','SAD','EXIT']);
const ORDER = { S1: 1, F1: 2, S2: 3, F2: 4, F4: 5, S3: 6, F3: 7, S4: 8, HAPPY: 9, OPEN: 10, SAD: 11, EXIT: 12 };

export default function YourStoryAdmin({api, Login}) {
  const [auth,setAuth] = useState(null);
  const [stories,setStories] = useState([]);
  const [selected,setSelected] = useState(null);
  const [values,setValues] = useState(null);
  const [nodeId,setNodeId] = useState('S1');
  const [tab,setTab] = useState('content');
  const [recordings,setRecordings] = useState([]);
  const [busy,setBusy] = useState(false);
  const [dirty,setDirty] = useState(false);
  const [notice,setNotice] = useState('');
  const [error,setError] = useState('');
  useEffect(() => { api('/admin/me').then(() => setAuth(true)).catch(() => setAuth(false)); }, []);
  useEffect(() => { if(auth) refresh(); }, [auth]);
  async function refresh() { try { setStories((await api('/admin/your-story/stories')).stories); } catch(e) { setError(e.message); } }
  async function refreshRecordings() { try { setRecordings((await api('/admin/your-story/recordings')).recordings); } catch(e) { setError(e.message); } }
  function openData(item) { setSelected(item);setValues(structuredClone(item.locales));setNodeId('S1');setDirty(false);setError(''); }
  async function open(id) { if(dirty && !window.confirm('تغییرات ذخیره‌نشده از بین بروند؟')) return;
    try { openData(await api(`/admin/your-story/stories/${id}`)); } catch(e) {setError(e.message);} }
  function edit(fn) { setValues(old => { const next=structuredClone(old);fn(next);return next; });setDirty(true);setNotice(''); }
  function field(lang,key,value) { edit(next => { next[lang][key]=value; }); }
  function nodeField(lang,key,value) { edit(next => { next[lang].nodes[nodeId][key]=value; }); }
  function bothNode(key,value) { edit(next => LANGS.forEach(([lang]) => { next[lang].nodes[nodeId][key]=value; })); }
  function choiceField(lang,index,value) { edit(next => { next[lang].nodes[nodeId].choices[index].text=value; }); }
  function edge(index,target) { edit(next => LANGS.forEach(([lang]) => { next[lang].nodes[nodeId].choices[index].to=target; })); }
  async function upload(file) { if(!file)return;setBusy(true);setError('');
    try {const form=new FormData();form.append('file',file); const result=await api('/admin/assets',{method:'POST',body:form});
      bothNode('art_key',result.art_key);setNotice('تصویر بارگذاری شد؛ پیش‌نویس را ذخیره و منتشر کنید.');}
    catch(e){setError(e.message);}finally{setBusy(false);} }
  async function create() {if(dirty && !window.confirm('تغییرات ذخیره‌نشده از بین بروند؟'))return;
    setBusy(true);try{openData(await api('/admin/your-story/stories',{method:'POST'}));await refresh();
      setNotice('یک نسخهٔ قابل‌ویرایش از الگوی داستانی ساخته شد. متن‌ها و مسیرها را تغییر دهید.');}
    catch(e){setError(e.message);}finally{setBusy(false);} }
  async function save() {setBusy(true);setError('');try{const item=await api(`/admin/your-story/stories/${selected.id}`,
    {method:'PUT',body:JSON.stringify({locales:values,base_revisions:selected.latest_revision_ids})});
    openData(item);setNodeId(nodeId);await refresh();setNotice('پیش‌نویس ذخیره شد. نسخهٔ کودک تا زمان انتشار تغییر نمی‌کند.');return item;
  }catch(e){setError(e.message);return null;}finally{setBusy(false);} }
  async function publish() {let item=selected;if(dirty){item=await save();if(!item)return;}
    setBusy(true);setError('');try{openData(await api(`/admin/your-story/stories/${item.id}/publish`,{method:'POST'}));setNodeId(nodeId);
      await refresh();setNotice('هر دو زبان منتشر شدند.');}catch(e){setError(e.message);}finally{setBusy(false);} }
  async function lifecycle(operation) {if(dirty){setError('اول پیش‌نویس را ذخیره کنید.');return;}
    if(operation==='archive'&&!window.confirm('داستان از فهرست کودک پنهان شود؟'))return;
    setBusy(true);try{openData(await api(`/admin/your-story/stories/${selected.id}/status/${operation}`,{method:'POST'}));
      await refresh();setNotice(operation==='archive'?'داستان بایگانی شد.':'داستان به پیش‌نویس برگشت.');}
    catch(e){setError(e.message);}finally{setBusy(false);} }
  async function review(id,operation) {setBusy(true);try{await api(`/admin/your-story/recordings/${id}/${operation}`,{method:'POST'});
    await refreshRecordings();setNotice('وضعیت خوانش ثبت شد.');}catch(e){setError(e.message);}finally{setBusy(false);} }
  if(auth===null)return <p dir="rtl">در حال بارگذاری…</p>;
  if(!auth)return <Login onLogin={() => setAuth(true)}/>;
  const keys=values ? Object.keys(values.fa.nodes).sort((a,b)=>(ORDER[a]??100)-(ORDER[b]??100)||a.localeCompare(b)) : [];
  const active=values?.fa.nodes[nodeId];
  return <div className="ys-admin" dir="rtl"><header className="ys-admin-header"><img src="/fidibo-kids-logo.png" alt="" />
    <h1>پنل داستان تو</h1><a href="/your-story" target="_blank" rel="noopener noreferrer">دیدن تجربهٔ کودک ↗</a>
    <a href="/">پنل قصه ↗</a><button onClick={async()=>{await api('/admin/logout',{method:'POST'});setAuth(false);}}>خروج</button></header>
    <div className="ys-admin-layout"><aside className="ys-admin-aside"><h2>داستان‌ها</h2><button onClick={create} disabled={busy}>＋ داستان تازه</button>
      {stories.map(item => <button key={item.id} className={selected?.id===item.id?'active':''} onClick={()=>open(item.id)}>
        {item.title}<small>{item.status==='published'?'منتشرشده':item.status==='archived'?'بایگانی':'پیش‌نویس'}</small></button>)}
      <hr/><button className={tab==='recordings'?'active':''} onClick={()=>{setTab('recordings');refreshRecordings();}}>خوانش‌های دریافتی</button>
      <button onClick={()=>setTab('content')}>ویرایش داستان</button></aside>
      <main className="ys-admin-main">{error&&<p role="alert" className="ys-error">{error}</p>}{notice&&<p role="status" className="ys-success">{notice}</p>}
      {tab==='recordings'?<><h2>خوانش‌ها</h2>{recordings.map(item=><article className="ys-admin-recording" key={item.id}>
        <strong>{item.story_id} / {item.scene_id} / {item.language}</strong><p>وضعیت: {item.status} · {item.submitted_at}</p>
        <audio controls src={`/api/admin/your-story/recordings/${item.id}/audio`} preload="none" />
        <div className="ys-admin-actions"><button disabled={busy} onClick={()=>review(item.id,'publish')}>انتشار خوانش</button>
          <button disabled={busy} onClick={()=>review(item.id,'unpublish')}>برداشتن از انتشار</button>
          <button disabled={busy} onClick={()=>review(item.id,'reject')}>رد</button></div></article>)}
        {!recordings.length&&<p>هنوز خوانشی دریافت نشده است.</p>}</> : !selected ? <p>یک داستان را انتخاب کنید.</p> : <>
        <div className="ys-admin-title"><div><h2>{values.fa.title}</h2><p>ویرایش دو‌زبانه، تصویر، مسیرها و پایان‌ها</p></div>
          <div className="ys-admin-actions"><button disabled={busy||selected.status==='archived'} onClick={save}>ذخیرهٔ پیش‌نویس</button>
            <button className="primary" disabled={busy||selected.status==='archived'} onClick={publish}>انتشار دو‌زبانه</button>
            <button disabled={busy} onClick={()=>lifecycle(selected.status==='archived'?'restore':'archive')}>
              {selected.status==='archived'?'بازگردانی':'بایگانی'}</button></div></div>
        <div className="ys-admin-pair">{LANGS.map(([lang,label])=><section key={lang}><h3>{label}</h3>
          <label>نام داستان<input value={values[lang].title} onChange={e=>field(lang,'title',e.target.value)}/></label>
          <label>معرفی کوتاه<input value={values[lang].description} onChange={e=>field(lang,'description',e.target.value)}/></label></section>)}</div>
        <div className="ys-admin-nodes" role="group" aria-label="صحنه‌ها">{keys.map(key=><button key={key} className={key===nodeId?'active':''}
          onClick={()=>setNodeId(key)}>{key} · {values.fa.nodes[key].title.replace(/^(S\d|F\d)\s*[-—\u00a0]\s*/,'')}</button>)}</div>
        {active&&<section className="ys-admin-node"><h2>صحنهٔ {nodeId}</h2>
          <p>نوع: {nodeId==='EXIT'?'خروج قطعی':TERMINALS.has(nodeId)?'پایان':nodeId==='S4'?'انتخاب پایان':'تصمیم داستانی'}</p>
          <div className="ys-admin-pair">{LANGS.map(([lang,label])=><section key={lang}><h3>{label}</h3>
            <label>عنوان صحنه<input value={values[lang].nodes[nodeId].title} onChange={e=>nodeField(lang,'title',e.target.value)}/></label>
            <label>متن صحنه<textarea rows="8" value={values[lang].nodes[nodeId].text} onChange={e=>nodeField(lang,'text',e.target.value)}/></label>
            {TERMINALS.has(nodeId)&&nodeId!=='EXIT'&&<label>متن نشان<input value={values[lang].nodes[nodeId].badge||''}
              onChange={e=>nodeField(lang,'badge',e.target.value)}/></label>}</section>)}</div>
          <div className="ys-admin-art"><strong>تصویر مشترک دو زبان</strong>{active.art_key&&<img src={`/api/assets/${active.art_key.slice(7)}`} alt="پیش‌نمایش صحنه"/>}
            <input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} aria-label="بارگذاری تصویر صحنه"
              onChange={e=>{upload(e.target.files?.[0]);e.target.value='';}} />
            {active.art_key&&<button onClick={()=>bothNode('art_key','')}>برداشتن تصویر</button>}</div>
          {active.choices&&<div className="ys-admin-choices"><h3>سه انتخاب این صحنه</h3>
            <p>نقش انتخاب‌ها در پنل مشخص است؛ کودک فقط متن انتخاب را می‌بیند.</p>
            {active.choices.map((choice,index)=><fieldset key={choice.id}><legend>{persianDigits(index+1)} ·
              {choice.kind==='main'?' مسیر اصلی':choice.kind==='side'?' مسیر فرعی':choice.kind==='exit'?' خروج قطعی':' پایان'}</legend>
              <div className="ys-admin-pair">{LANGS.map(([lang,label])=><label key={lang}>{label}
                <textarea rows="3" value={values[lang].nodes[nodeId].choices[index].text}
                  onChange={e=>choiceField(lang,index,e.target.value)}/></label>)}</div>
              {choice.kind!=='exit'&&choice.kind!=='ending'&&<label>مقصد مشترک<select value={choice.to}
                onChange={e=>edge(index,e.target.value)}>{keys.filter(key=>key!=='EXIT').map(key=><option key={key} value={key}>{key}</option>)}</select></label>}
              <small>شناسه: {choice.id} · مقصد: {choice.to}</small></fieldset>)}</div>}
        </section>}</>}</main></div></div>;
}
