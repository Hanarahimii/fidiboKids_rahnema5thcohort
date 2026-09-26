import React, { useEffect, useState } from 'react';
import { persianDigits } from './persian.js';
import './discovery.css';

const LANGS = [['fa','فارسی'],['azb','ترکی']];
const STATES = {draft:'پیش‌نویس',published:'منتشرشده',archived:'بایگانی'};
const empty = () => ({title:'',intro:{text:'',art_key:''},intro_questions:[],choice_prompt:'',
  branches:[],badge:{title:'',art_key:''}});
const newQuestion = () => ({id:`q-${crypto.randomUUID().slice(0,8)}`,prompt:'',art_key:'',answer_id:'o1',
  options:[1,2,3].map((n)=>({id:`o${n}`,text:'',art_key:''}))});
const newBranch = () => ({id:`b-${crypto.randomUUID().slice(0,8)}`,label:'',text:'',art_key:'',
  badge:{title:'',art_key:''},questions:[newQuestion()]});
function getPath(object,path) { return path.reduce((at,p)=>at?.[p],object); }
function putPath(object,path,value) { const parent=getPath(object,path.slice(0,-1));parent[path.at(-1)]=value; }

export default function DiscoveryAdmin({api,Login}) {
  const [auth,setAuth]=useState(null);
  const [topics,setTopics]=useState([]);
  const [selected,setSelected]=useState(null);
  const [values,setValues]=useState(null);
  const [dirty,setDirty]=useState(false);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState('');
  const [error,setError]=useState('');
  const [showArchived,setShowArchived]=useState(false);
  const [tab,setTab]=useState('content');
  const [recordings,setRecordings]=useState([]);
  useEffect(()=>{api('/admin/me').then(()=>setAuth(true)).catch(()=>setAuth(false));},[]);
  useEffect(()=>{if(auth)refresh();},[auth]);
  async function refresh(){try{setTopics((await api('/admin/discovery/topics')).topics);}catch(e){setError(e.message);}}
  async function refreshRecordings(){try{setRecordings((await api('/admin/discovery/recordings')).recordings);}catch(e){setError(e.message);}}
  function openData(data){setSelected(data);setValues({fa:Object.keys(data.locales.fa).length?structuredClone(data.locales.fa):empty(),
    azb:Object.keys(data.locales.azb).length?structuredClone(data.locales.azb):empty()});
    setDirty(false);setError('');setNotice('');setTab('content');}
  async function open(id){if(dirty&&!window.confirm('تغییرات ذخیره‌نشده از بین بروند؟'))return;
    try{openData(await api(`/admin/discovery/topics/${id}`));}catch(e){setError(e.message);}}
  function edit(lang,path,value){setValues(old=>{const next=structuredClone(old);putPath(next[lang],path,value);return next;});setDirty(true);}
  function editBoth(path,value){setValues(old=>{const next=structuredClone(old);
    for(const [lang] of LANGS)putPath(next[lang],path,value);return next;});setDirty(true);}
  function changeArrays(path,transform){setValues(old=>{const next=structuredClone(old);
    for(const [lang] of LANGS){const list=getPath(next[lang],path);transform(list);}
    return next;});setDirty(true);}
  function move(path,index,direction){changeArrays(path,(list)=>{
    const other=index+direction;if(other>=0&&other<list.length)[list[index],list[other]]=[list[other],list[index]];});}
  async function upload(path,file){if(!file)return;setBusy(true);setError('');
    try{const form=new FormData();form.append('file',file);
      const result=await api('/admin/assets',{method:'POST',body:form});editBoth(path,result.art_key);
      setNotice('تصویر انتخاب شد. موضوع را ذخیره و منتشر کنید.');
    }catch(e){setError(e.message);}finally{setBusy(false);}}
  async function create(){if(dirty&&!window.confirm('تغییرات ذخیره‌نشده از بین بروند؟'))return;
    setBusy(true);try{openData(await api('/admin/discovery/topics',{method:'POST'}));await refresh();setShowArchived(false);
      setNotice('موضوع تازه ساخته شد. محتوا را در هر دو زبان تکمیل کنید.');}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function save(){if(!selected)return null;setBusy(true);setError('');try{
    const result=await api(`/admin/discovery/topics/${selected.id}`,{method:'PUT',body:JSON.stringify({
      locales:values,base_revisions:selected.latest_revision_ids})});openData(result);await refresh();
    setNotice('پیش‌نویس ذخیره شد؛ محتوای کتاب هنوز تغییر نکرده است.');return result;
    }catch(e){setError(e.message);return null;}finally{setBusy(false);}}
  async function publish(){let current=selected;if(dirty){current=await save();if(!current)return;}
    setBusy(true);setError('');try{openData(await api(`/admin/discovery/topics/${current.id}/publish`,{method:'POST'}));
      await refresh();setNotice('موضوع با هر دو زبان منتشر شد.');}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function status(action){if(dirty){setError('اول پیش‌نویس را ذخیره کنید.');return;}
    if(action==='archive'&&!window.confirm('موضوع از لاین کشف پنهان شود؟'))return;
    setBusy(true);try{openData(await api(`/admin/discovery/topics/${selected.id}/status/${action}`,{method:'POST'}));
      if(action==='restore')setShowArchived(false);await refresh();setNotice(action==='archive'?'موضوع بایگانی شد.':'موضوع به پیش‌نویس برگشت؛ برای نمایش دوباره منتشر کنید.');}
    catch(e){setError(e.message);}finally{setBusy(false);}}
  async function remove(){if(!window.confirm('این موضوع بایگانی‌شده و همهٔ نسخه‌هایش برای همیشه حذف شود؟'))return;
    setBusy(true);try{await api(`/admin/discovery/topics/${selected.id}`,{method:'DELETE'});
      setSelected(null);setValues(null);await refresh();setNotice('موضوع حذف شد.');}
    catch(e){setError('اگر موضوع ضبط دارد، برای حفظ سابقهٔ صوت فقط می‌توان آن را بایگانی کرد. '+e.message);}finally{setBusy(false);}}
  async function reorder(direction){if(dirty){setError('اول تغییرها را ذخیره کنید.');return;}
    setBusy(true);try{openData(await api(`/admin/discovery/topics/${selected.id}/move`,{
      method:'POST',body:JSON.stringify({direction})}));await refresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function review(id,action){setBusy(true);try{await api(`/admin/discovery/recordings/${id}/${action}`,{method:'POST'});
    await refreshRecordings();setNotice('وضعیت ضبط ثبت شد.');}catch(e){setError(e.message);}finally{setBusy(false);}}
  function imageField(path,title){const key=getPath(values.fa,path);
    return <div className="admin-image"><span>{title}</span>{key&&<img src={`/api/assets/${key.slice(7)}`} alt={title}/>}
      <input aria-label={title} type="file" accept="image/png,image/jpeg,image/webp" disabled={busy}
        onChange={(e)=>{upload(path,e.target.files?.[0]);e.target.value='';}}/>
      {key&&<button disabled={busy} onClick={()=>editBoth(path,'')}>برداشتن تصویر</button>}</div>;}
  function bilingual(path,title,multiline=false){return <div><strong>{title}</strong><div className="locales">{LANGS.map(([lang,label])=>
    <label key={lang}>{label}{multiline?<textarea rows="5" value={getPath(values[lang],path)||''}
      onChange={(e)=>edit(lang,path,e.target.value)}/>:<input value={getPath(values[lang],path)||''}
      onChange={(e)=>edit(lang,path,e.target.value)}/>}</label>)}</div></div>;}
  function questions(path,title){const list=getPath(values.fa,path);
    return <fieldset><legend>{title}</legend><div className="admin-section-heading"><span>کلید پاسخ قابل تغییر است.</span>
      <button onClick={()=>changeArrays(path,(items)=>items.push(newQuestion()))}>افزودن سؤال</button></div>
      {list.map((q,index)=><div className="admin-question" key={q.id}><div className="admin-section-heading">
        <strong>سؤال {persianDigits(index+1)}</strong><div>
          <button onClick={()=>move(path,index,-1)} disabled={index===0}>↑</button>
          <button onClick={()=>move(path,index,1)} disabled={index===list.length-1}>↓</button>
          <button onClick={()=>changeArrays(path,(arr)=>arr.splice(index,1))}>حذف</button></div></div>
        {bilingual([...path,index,'prompt'],'صورت سؤال')}
        {imageField([...path,index,'art_key'],'عکس سؤال (اختیاری)')}
        {q.options.map((option,i)=><div className="admin-option" key={option.id}><input type="radio" name={`correct-${q.id}`}
          aria-label={`پاسخ درست گزینهٔ ${persianDigits(i+1)}`} checked={q.answer_id===option.id}
          onChange={()=>editBoth([...path,index,'answer_id'],option.id)}/>
          {LANGS.map(([lang,label])=><label key={lang}>گزینهٔ {persianDigits(i+1)} · {label}
            <input value={getPath(values[lang],[...path,index,'options',i,'text'])||''}
              onChange={(e)=>edit(lang,[...path,index,'options',i,'text'],e.target.value)}/></label>)}</div>)}
      </div>)}</fieldset>;
  }
  if(auth===null)return <p>در حال بارگذاری…</p>;
  if(!auth)return <Login onLogin={()=>setAuth(true)}/>;
  return <div className="discover-admin" dir="rtl"><header className="discover-admin-header">
    <img src="/fidibo-kids-logo.png" alt="" width="44" height="44"/><h1>پنل لاین کشف</h1>
    <a href="/discover" target="_blank" rel="noopener noreferrer">دیدن تجربهٔ کودک ↗</a>
    <a href="/">پنل قصه ↗</a><button onClick={async()=>{await api('/admin/logout',{method:'POST'});setAuth(false);}}>خروج</button></header>
    <div className="discover-admin-shell"><aside className="discover-admin-nav"><h2>موضوع‌ها</h2>
      <button onClick={create} disabled={busy}>＋ موضوع تازه</button>
      <label><input type="checkbox" checked={showArchived} onChange={(e)=>setShowArchived(e.target.checked)}/> فقط بایگانی‌ها</label>
      {topics.filter(x=>!showArchived||x.status==='archived').map(x=><button key={x.id}
        className={selected?.id===x.id?'active':''} onClick={()=>open(x.id)}>
        {persianDigits(x.position)} · {x.title}<small> · {STATES[x.status]}</small></button>)}
      <button className={tab==='recordings'?'active':''} onClick={()=>{
        if(dirty&&!window.confirm('تغییرات ذخیره‌نشده از بین بروند؟'))return;
        setTab('recordings');setDirty(false);refreshRecordings();}}>بررسی صداهای کشف</button></aside>
      <main className="discover-admin-editor">{error&&<p role="alert" className="notice error">{error}</p>}
        {notice&&<p role="status" className="notice success">{notice}</p>}
        {tab==='recordings'?<><h2>ضبط‌های ارسال‌شده</h2><p>فایل خام فقط در پنل شنیده می‌شود؛ انتشار نسخهٔ قابل پخش را در کتاب فعال می‌کند.</p>
          <button onClick={refreshRecordings}>تازه‌سازی فهرست</button>{recordings.map(r=><article className="admin-recording" key={r.id}>
            <strong>{topics.find(x=>x.id===r.topic_id)?.title||r.topic_id} · {r.scene_id==='intro'?'روایت آغازین':`شاخه ${r.scene_id}`}</strong>
            <p>{r.language==='fa'?'فارسی':'ترکی'} · {r.status==='published'?'منتشرشده':r.status==='pending'?'در انتظار':'ردشده'} · {persianDigits(r.submitted_at)}</p>
            <audio controls src={`/api/admin/discovery/recordings/${r.id}/audio`} preload="none"/>
            <div className="discover-admin-actions"><button disabled={busy} onClick={()=>review(r.id,'publish')}>انتشار خوانش</button>
              {r.status==='published'&&<button disabled={busy} onClick={()=>review(r.id,'unpublish')}>لغو انتشار</button>}
              <button disabled={busy} onClick={()=>review(r.id,'reject')}>رد ضبط</button></div>
          </article>)}{!recordings.length&&<p>هنوز ضبطی ارسال نشده است.</p>}</>
          :!selected||!values?<><h2>یک موضوع را انتخاب کنید</h2><p>برای ساخت موضوع تازه از دکمهٔ فهرست استفاده کنید.</p></>
          :<><div className="admin-section-heading"><h2>ویرایش موضوع · {STATES[selected.status]}</h2>
              <div><button onClick={()=>reorder('up')}>↑</button><button onClick={()=>reorder('down')}>↓</button></div></div>
            <div className="discover-admin-actions"><button className="primary" onClick={save} disabled={busy||selected.status==='archived'}>ذخیرهٔ پیش‌نویس</button>
              <button onClick={publish} disabled={busy||selected.status==='archived'}>انتشار دو‌زبانه</button>
              {selected.status==='archived'?<><button onClick={()=>status('restore')} disabled={busy}>بازگردانی</button>
                <button className="danger" onClick={remove} disabled={busy}>حذف دائمی بایگانی</button></>
                :<button className="danger" onClick={()=>status('archive')} disabled={busy}>بایگانی</button>}</div>
            {bilingual(['title'],'عنوان موضوع')}
            <fieldset><legend>روایت آغازین</legend>{bilingual(['intro','text'],'متن روایت',true)}
              {imageField(['intro','art_key'],'تصویر روایت (اختیاری؛ تصویر موضوع جایگزین می‌شود)')}</fieldset>
            {questions(['intro_questions'],'سؤال‌های فهم روایت')}
            {bilingual(['choice_prompt'],'پرسش انتخاب شخصی')}
            <fieldset><legend>شاخه‌ها</legend><button onClick={()=>changeArrays(['branches'],items=>items.push(newBranch()))}>＋ افزودن شاخه</button>
              {values.fa.branches.map((branch,index)=><fieldset key={branch.id}><legend>شاخهٔ {persianDigits(index+1)}</legend>
                <div className="admin-section-heading"><span>ترتیب شاخه را از همین‌جا تغییر دهید.</span><div>
                  <button onClick={()=>move(['branches'],index,-1)} disabled={index===0}>↑</button>
                  <button onClick={()=>move(['branches'],index,1)} disabled={index===values.fa.branches.length-1}>↓</button>
                  <button onClick={()=>changeArrays(['branches'],items=>items.splice(index,1))}>حذف شاخه</button></div></div>
                {bilingual(['branches',index,'label'],'متن انتخاب کودک')}
                {bilingual(['branches',index,'text'],'متن روایت شاخه',true)}
                {imageField(['branches',index,'art_key'],'تصویر شاخه')}
                {questions(['branches',index,'questions'],'سؤال‌های این شاخه')}
                {bilingual(['branches',index,'badge','title'],'متن نشان این شاخه')}
                {imageField(['branches',index,'badge','art_key'],'تصویر نشان (اختیاری)')}</fieldset>)}</fieldset>
            <fieldset><legend>نشان کلی موضوع</legend>{bilingual(['badge','title'],'متن نشان کلی')}
              {imageField(['badge','art_key'],'تصویر نشان کلی (اختیاری)')}</fieldset>
            <div className="discover-admin-actions"><button className="primary" onClick={save} disabled={busy||selected.status==='archived'}>ذخیرهٔ پیش‌نویس</button>
              <button onClick={publish} disabled={busy||selected.status==='archived'}>انتشار دو‌زبانه</button></div>
          </>}</main></div></div>;
}
