import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import BookApp from './BookApp.jsx';
import ResearchApp from './ResearchApp.jsx';
import DiscoveryApp from './DiscoveryApp.jsx';
import DiscoveryAdmin from './DiscoveryAdmin.jsx';
import YourStoryApp from './YourStoryApp.jsx';
import YourStoryAdmin from './YourStoryAdmin.jsx';
import UnifiedApp from './UnifiedApp.jsx';
import { persianDigits } from './persian.js';
import './styles.css';
import './fidibo.css';
import './unified.css';
import './experience.css';

const LABELS = { story: 'صفحهٔ داستان', lesson: 'صفحهٔ درس', quiz: 'صفحهٔ سؤال' };
const STATES = { draft: 'پیش‌نویس', published: 'منتشرشده', archived: 'بایگانی' };
const LANGUAGES = [['fa', 'فارسی'], ['azb', 'ترکی']];
const CATEGORY = { recall: 'یادآوری', infer: 'استنباط', think: 'فکرکردنی' };

async function api(path, options = {}) {
  const request = { credentials: 'same-origin', ...options, headers: { ...(options.headers || {}) } };
  if (options.method && options.method !== 'GET') request.headers['X-Admin-Action'] = '1';
  if (options.body && !(options.body instanceof FormData)) request.headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api${path}`, request);
  let data;
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) {
    const detail = data.detail;
    const explanations = {
      401: 'برای ادامه دوباره وارد پنل شوید یا رمز را بررسی کنید.',
      403: 'برای انجام این کار دسترسی لازم را ندارید.',
      404: 'مورد انتخاب‌شده پیدا نشد. صفحه را دوباره بارگذاری کنید.',
      413: 'حجم فایل بیش از اندازهٔ مجاز است.',
      415: 'قالب این فایل پشتیبانی نمی‌شود. تصویر پی‌ان‌جی، جی‌پگ یا وب‌پی انتخاب کنید.',
      422: 'اطلاعات این بخش کامل یا معتبر نیست. فیلدها و فایل انتخابی را بررسی کنید.',
    };
    if (response.status === 401 && detail === 'Wrong password') throw new Error('رمز درست نیست.');
    if (response.status === 409) throw new Error(detail?.includes?.('another tab')
      ? 'این صفحه در زبانهٔ دیگری تغییر کرده است. آن را دوباره بارگذاری کنید.'
      : detail?.includes?.('has recordings')
        ? 'این صفحه ضبط‌های پژوهشی دارد و برای حفظ سابقهٔ صدا قابل حذف دائمی نیست.'
      : 'این عمل با وضعیت فعلی صفحه یا صدا سازگار نیست. اطلاعات تازه را بارگذاری کنید.');
    throw new Error(explanations[response.status] || `درخواست انجام نشد. کد خطا: ${persianDigits(response.status)}`);
  }
  return data;
}

function blank(kind) {
  return kind === 'quiz' ? { questions: [] } : { text: '', art_key: '' };
}

function fromPage(page) {
  return {
    fa: Object.keys(page.locales.fa).length ? structuredClone(page.locales.fa) : blank(page.kind),
    azb: Object.keys(page.locales.azb).length ? structuredClone(page.locales.azb) : blank(page.kind),
  };
}

function mergeQuestions(locales) {
  const fa = locales.fa.questions || [];
  const azb = locales.azb.questions || [];
  return fa.map((q, index) => ({
    id: q.id, category: q.category, number: q.number, answer_id: q.answer_id, art_key: q.art_key || '',
    prompts: { fa: q.prompt, azb: azb[index]?.prompt || '' },
    options: q.options.map((o, i) => ({
      id: o.id, art_key: o.art_key || '',
      labels: { fa: o.text, azb: azb[index]?.options[i]?.text || '' },
    })),
  }));
}

function quizPayload(questions, language) {
  return { questions: questions.map((q) => ({
    id: q.id, category: q.category, number: q.number, answer_id: q.answer_id,
    prompt: q.prompts[language], art_key: q.art_key || '',
    options: q.options.map((o) => ({ id: o.id, text: o.labels[language], art_key: o.art_key })),
  })) };
}

function Art({ artKey, compact = false }) {
  if (artKey?.startsWith('upload:')) {
    return <img className={`art ${compact ? 'compact' : ''}`} src={`/api/assets/${artKey.slice(7)}`} alt="تصویر صفحه" />;
  }
  return <div className={`art art-placeholder ${compact ? 'compact' : ''}`}>
    <span>تصویر {artKey ? 'قصه' : 'صفحه'}</span>
  </div>;
}

function BannerEditor() {
  const [banners, setBanners] = useState(null);
  const [busySlot, setBusySlot] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => { let active = true;
    api('/admin/banners').then((data) => { if (active) setBanners(data); })
      .catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  async function update(slot, file) {
    setBusySlot(slot); setError(''); setNotice('');
    try {
      let artKey = null;
      if (file) {
        const form = new FormData(); form.append('file', file);
        artKey = (await api('/admin/assets', { method: 'POST', body: form })).art_key;
      }
      await api(`/admin/banners/${encodeURIComponent(slot)}`, {
        method: 'PUT', body: JSON.stringify({ art_key: artKey }),
      });
      setBanners(await api('/admin/banners'));
      setNotice(file ? 'بنر ذخیره شد. صفحهٔ کتاب را دوباره باز کنید تا تصویر تازه را ببینید.' : 'تصویر پیش‌فرض کتاب بازگردانده شد.');
    } catch (e) { setError(e.message); }
    finally { setBusySlot(''); }
  }
  const items = banners ? [{ slot: 'cover', title: 'بنر جلد کتاب', art_key: banners.cover },
    ...banners.steps.map((step) => ({ slot: `step:${step.id}`, title: `بنر گام «${step.title}»`, art_key: step.art_key }))] : [];
  return <section className="banner-editor"><div className="editor-head"><div><p className="eyebrow">تنظیمات تصویری کتاب</p>
    <h1>بنرهای کتاب</h1><p>تصویر جلد و کارت هر گام را از همین‌جا تغییر دهید. نتیجه پس از ذخیره در کتاب دیده می‌شود.</p></div></div>
    {error && <div className="notice error" role="alert">{error}</div>}
    {notice && <div className="notice success" role="status">{notice}</div>}
    {!banners && !error && <p>بنرها در حال بارگذاری هستند…</p>}
    <div className="banner-grid">{items.map((item) => <article className="banner-item" key={item.slot}>
      <div className="banner-item-image">{item.art_key ? <img src={`/api/assets/${item.art_key.slice(7)}`} alt={item.title} />
        : item.slot === 'cover' ? <img src="/api/book/art/cover" alt="تصویر پیش‌فرض جلد" />
          : <span>تصویر پیش‌فرض گام نمایش داده می‌شود</span>}</div>
      <div className="banner-item-body"><h2>{item.title}</h2><p>یک عکس افقی با کیفیت مناسب انتخاب کنید. تصویر در دو زبان مشترک است.</p>
        <div className="banner-actions"><label className="upload-button">{busySlot === item.slot ? 'در حال ذخیره…' : 'انتخاب و ذخیرهٔ تصویر'}
          <input type="file" accept="image/png,image/jpeg,image/webp" disabled={Boolean(busySlot)} hidden
            onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ''; if (file) update(item.slot, file); }} />
        </label>{item.art_key && <button disabled={Boolean(busySlot)} onClick={() => update(item.slot, null)}>بازگشت به تصویر پیش‌فرض</button>}</div>
      </div></article>)}</div>
    <p className="banner-help">فایل‌های پی‌ان‌جی، جی‌پگ یا وب‌پی تا ۵ مگابایت پذیرفته می‌شوند. نسبت تصویر پیشنهادی جلد ۱۶ به ۹ و کارت گام ۳ به ۲ است.</p>
  </section>;
}

function Login({ onLogin }) {
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await api('/admin/login', { method: 'POST', body: JSON.stringify({ password }) }); onLogin(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><div className="login-card">
    <div className="brand-symbol"><img src="/fidibo-kids-logo.png" alt="" /></div><p className="eyebrow">فیدیبو کیدز · کارشناسی محتوا</p>
    <h1>ورود کارشناس</h1><p>رمز فعلی پنل محتوا را وارد کنید.</p>
    <form onSubmit={submit}><label>رمز کارشناس<input type="password" autoComplete="current-password" value={password}
      onChange={(e) => setPassword(e.target.value)} required autoFocus /></label>
      {error && <div className="notice error">{error}</div>}
      <button className="primary full" disabled={busy}>{busy ? 'در حال ورود…' : 'ورود'}</button></form>
  </div></main>;
}

function App() {
  const [authenticated, setAuthenticated] = useState(null);
  const [steps, setSteps] = useState([]);
  const [stepId, setStepId] = useState('ask');
  const [page, setPage] = useState(null);
  const [locales, setLocales] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [dirty, setDirty] = useState(false);
  const [previewLanguage, setPreviewLanguage] = useState('fa');
  const [previewMode, setPreviewMode] = useState('read');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [mobileList, setMobileList] = useState(false);
  const [showBanners, setShowBanners] = useState(false);
  const [showArchivedOnly, setShowArchivedOnly] = useState(false);

  useEffect(() => { api('/admin/me').then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)); }, []);
  useEffect(() => { if (authenticated) refresh(); }, [authenticated]);

  async function refresh() {
    try { const data = await api('/admin/steps'); setSteps(data.steps); }
    catch (e) { setError(e.message); }
  }
  function openPage(data) {
    setShowBanners(false);
    setPage(data); const next = fromPage(data); setLocales(next); setQuestions(data.kind === 'quiz' ? mergeQuestions(next) : []);
    setDirty(false); setError(''); setNotice(''); setMobileList(false); setStepId(data.step_id);
  }
  async function selectPage(id) {
    if (dirty && !window.confirm('تغییرات ذخیره‌نشده دارید. بدون ذخیره از صفحه خارج می‌شوید؟')) return;
    try { openPage(await api(`/admin/pages/${id}`)); } catch (e) { setError(e.message); }
  }
  function chooseStep(id) {
    if (id === stepId && !showBanners) return;
    if (dirty && !window.confirm('تغییرات ذخیره‌نشده دارید. بدون ذخیره از این گام خارج می‌شوید؟')) return;
    setShowBanners(false); setStepId(id); setPage(null); setLocales(null); setQuestions([]); setDirty(false);
    setError(''); setNotice(''); setMobileList(false);
  }
  async function create(kind) {
    if (dirty && !window.confirm('تغییرات ذخیره‌نشده دارید. صفحهٔ تازه ساخته شود؟')) return;
    setError(''); setBusy(true);
    try {
      const data = await api('/admin/pages', { method: 'POST', body: JSON.stringify({ step_id: stepId, kind }) });
      await refresh(); openPage(data); setShowArchivedOnly(false);
      setNotice('صفحهٔ پیش‌نویس ساخته شد. متن هر دو زبان را وارد کنید.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  function changeText(language, field, value) {
    setLocales((previous) => ({ ...previous, [language]: { ...previous[language], [field]: value } })); setDirty(true);
  }
  function changeQuestions(updater) { setQuestions((previous) => updater(structuredClone(previous))); setDirty(true); }
  function addQuestion() {
    changeQuestions((list) => [...list, {
      id: `q-${crypto.randomUUID().slice(0, 8)}`, category: 'recall', number: list.length + 1, answer_id: 'o1',
      art_key: '', prompts: { fa: '', azb: '' }, options: [1, 2, 3].map((n) => ({
        id: `o${n}`, art_key: '', labels: { fa: '', azb: '' },
      })),
    }]);
  }
  async function uploadImage(file) {
    if (!file) return;
    setError(''); setBusy(true);
    const form = new FormData(); form.append('file', file);
    try {
      const result = await api('/admin/assets', { method: 'POST', body: form });
      setLocales((previous) => ({ fa: { ...previous.fa, art_key: result.art_key },
        azb: { ...previous.azb, art_key: result.art_key } }));
      setDirty(true); setNotice('تصویر برای هر دو زبان انتخاب شد. برای ثبت آن «ذخیرهٔ پیش‌نویس» را بزنید.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function uploadQuestionImage(file, questionId) {
    if (!file) return;
    setError(''); setNotice(''); setBusy(true);
    const form = new FormData(); form.append('file', file);
    try {
      const uploaded = await api('/admin/assets', { method: 'POST', body: form });
      changeQuestions((list) => { const question = list.find((item) => item.id === questionId);
        if (question) question.art_key = uploaded.art_key; return list; });
      setNotice('تصویر سؤال انتخاب شد؛ برای نمایش در کتاب، صفحه را ذخیره و منتشر کنید.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function save() {
    if (!page) return null;
    setError(''); setBusy(true);
    try {
      const content = page.kind === 'quiz' ? {
        fa: quizPayload(questions, 'fa'), azb: quizPayload(questions, 'azb'),
      } : locales;
      const data = await api(`/admin/pages/${page.id}`, { method: 'PUT', body: JSON.stringify({
        locales: content, base_revisions: page.latest_revision_ids,
      }) });
      openPage(data); await refresh(); setNotice('پیش‌نویس ذخیره شد. هنوز منتشر نشده است.'); return data;
    } catch (e) { setError(e.message); return null; }
    finally { setBusy(false); }
  }
  async function publish() {
    let target = page;
    if (dirty) { target = await save(); if (!target) return; }
    setError(''); setBusy(true);
    try {
      const data = await api(`/admin/pages/${target.id}/publish`, { method: 'POST' });
      openPage(data); await refresh(); setNotice('صفحه با محتوای هر دو زبان منتشر شد.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function lifecycle(action) {
    if (dirty) { setError('ابتدا تغییرات را ذخیره کنید.'); return; }
    if (action === 'archive' && !window.confirm('صفحه از کتاب پنهان می‌شود. داده‌ها و نسخه‌ها باقی می‌مانند. ادامه؟')) return;
    setBusy(true); setError('');
    try {
      const data = await api(`/admin/pages/${page.id}/${action}`, { method: 'POST' });
      openPage(data); if (action === 'restore') setShowArchivedOnly(false);
      await refresh(); setNotice(action === 'archive' ? 'صفحه بایگانی شد.' : 'صفحه به پیش‌نویس برگشت. برای نمایش دوباره منتشر کنید.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function deleteArchived() {
    if (!page || page.status !== 'archived' || busy) return;
    if (!window.confirm('این صفحهٔ بایگانی‌شده و همهٔ نسخه‌های متن و سؤال‌هایش برای همیشه حذف شوند؟ این کار قابل بازگشت نیست.')) return;
    const id = page.id;
    setBusy(true); setError(''); setNotice('');
    try {
      await api(`/admin/pages/${id}`, { method: 'DELETE' });
      setPage(null); setLocales(null); setQuestions([]); setDirty(false);
      await refresh(); setNotice('صفحهٔ بایگانی‌شده برای همیشه حذف شد.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function move(direction) {
    if (dirty) { setError('ابتدا تغییرات را ذخیره کنید.'); return; }
    try {
      await api(`/admin/pages/${page.id}/move`, { method: 'POST', body: JSON.stringify({ direction }) });
      await refresh(); openPage(await api(`/admin/pages/${page.id}`));
    } catch (e) { setError(e.message); }
  }
  async function signOut() {
    await api('/admin/logout', { method: 'POST' }); setAuthenticated(false); setPage(null);
  }
  function openBanners() {
    if (dirty && !window.confirm('تغییرات ذخیره‌نشده دارید. به تنظیمات بنر بروید؟')) return;
    setDirty(false); setPage(null); setShowBanners(true); setMobileList(false); setError(''); setNotice('');
  }
  function toggleArchiveFilter(next) {
    if (next && page && page.status !== 'archived') {
      if (dirty && !window.confirm('تغییرات ذخیره‌نشده دارید. بدون ذخیره به فهرست بایگانی بروید؟')) return;
      setPage(null); setLocales(null); setQuestions([]); setDirty(false);
    }
    setShowArchivedOnly(next);
  }
  if (authenticated === null) return <div className="loading">در حال بارگذاری…</div>;
  if (!authenticated) return <Login onLogin={() => setAuthenticated(true)} />;

  const currentStep = steps.find((s) => s.id === stepId);
  const preview = page?.kind === 'quiz' ? quizPayload(questions, previewLanguage) : locales?.[previewLanguage];
  return <div className="app-shell">
    <header className="topbar"><div className="brand-symbol small"><img src="/fidibo-kids-logo.png" alt="" /></div><div className="top-title"><strong>فیدیبو کیدز</strong><span>پنل مدیریت کتاب</span></div>
      <button className="mobile-toggle" onClick={() => setMobileList(!mobileList)}>فهرست گام‌ها</button>
      <div className="top-spacer"/><a className="book-open-link" href="/book" target="_blank" rel="noopener noreferrer">دیدن کتاب کودک ↗</a>
      <a className="book-open-link" href="/research">بررسی صداها ↗</a>
      <a className="book-open-link" href="/discover/admin">پنل کشف ↗</a>
      <a className="book-open-link" href="/your-story/admin">پنل داستان تو ↗</a>
      <span className="phase">{showBanners ? 'مدیریت بنرها' : 'محتوای کتاب'}</span><button className="text-button" onClick={signOut}>خروج</button>
    </header>
    <div className="workspace">
      <aside className={`sidebar ${mobileList ? 'show' : ''}`}>
        <div className="side-head"><p className="eyebrow">ساختار کتاب</p><h2>گام‌ها و صفحه‌ها</h2>
          <button className={`banner-nav ${showBanners ? 'active' : ''}`} onClick={openBanners}>ویرایش بنرهای کتاب</button>
          <label className="archived-filter"><input type="checkbox" checked={showArchivedOnly}
            onChange={(e) => toggleArchiveFilter(e.target.checked)} /> فقط صفحه‌های بایگانی‌شده</label></div>
        <div className="steps-list">{steps.map((step) => <div className="step-group" key={step.id}>
          <button className={`step-button ${stepId === step.id ? 'active' : ''}`} onClick={() => chooseStep(step.id)}>
            <span>{step.titles.fa}</span><small>{persianDigits(step.pages.length)} صفحه</small>
          </button>
          {stepId === step.id && <div className="page-list">{step.pages.filter((item) => !showArchivedOnly || item.status === 'archived').map((item) => <button
            className={`page-link ${page?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => selectPage(item.id)}>
            <span className="page-index">{persianDigits(item.position)}</span><span className="page-name">{LABELS[item.kind]}</span>
            {item.status === 'archived' && <span className="archived-tag">بایگانی</span>}
            <span className={`state-dot ${item.status}`} title={STATES[item.status]} />
          </button>)}{showArchivedOnly && !step.pages.some((item) => item.status === 'archived') &&
            <p className="archived-empty">در این گام صفحهٔ بایگانی‌شده‌ای نیست.</p>}</div>}
        </div>)}</div>
        <div className="side-actions"><p>افزودن به «{currentStep?.titles.fa}»</p>
          <button onClick={() => create('story')} disabled={busy}>＋ داستان</button>
          <button onClick={() => create('lesson')} disabled={busy}>＋ درس</button>
          <button onClick={() => create('quiz')} disabled={busy}>＋ سؤال</button>
        </div>
      </aside>
      <main className="main-panel">
        {showBanners ? <BannerEditor /> : !page ? <div className="welcome">
          {error && <div className="notice error" role="alert">{error}</div>}
          {notice && <div className="notice success" role="status">{notice}</div>}
          <h1>صفحه‌ای را انتخاب کنید</h1>
          <p>از فهرست سمت راست یک صفحه را باز کنید، یا با دکمه‌های پایین فهرست صفحهٔ تازه بسازید.</p></div> : <>
          <div className="editor-head"><div><p className="eyebrow">{currentStep?.titles.fa} / {LABELS[page.kind]}</p>
            <h1>{page.kind === 'story' ? 'متن و تصویر داستان' : page.kind === 'lesson' ? 'درس این گام' : 'بانک سؤال‌های این صفحه'}</h1>
            <div className="meta"><span className={`badge ${page.status}`}>{STATES[page.status]}</span>
              {page.has_unpublished_changes && <span className="badge changed">تغییرات منتشرنشده</span>}</div>
          </div><div className="order-buttons"><button title="یک جایگاه بالاتر" onClick={() => move('up')}>↑</button>
            <button title="یک جایگاه پایین‌تر" onClick={() => move('down')}>↓</button></div></div>
          {error && <div className="notice error" role="alert">{error}</div>}
          {notice && <div className="notice success">{notice}</div>}
          <div className="editor-grid"><section className="form-column">
            {page.kind === 'quiz' ? <div className="question-list"><div className="section-head"><div><h2>سؤال‌ها</h2>
              <p>برای هر سؤال، متن فارسی و ترکی و سه گزینه را وارد کنید. پاسخ درست با شناسهٔ گزینه ثبت می‌شود.</p></div>
              <button onClick={addQuestion}>＋ افزودن سؤال</button></div>
              {questions.map((q, index) => <div className="question-card" key={q.id}>
                <div className="question-title"><strong>سؤال {persianDigits(index + 1)}</strong>
                  <button className="danger-link" onClick={() => changeQuestions((list) => list.filter((x) => x.id !== q.id))}>حذف سؤال</button></div>
                <div className="two-fields"><label>دسته<select value={q.category} onChange={(e) => changeQuestions((list) => {
                  list[index].category = e.target.value; return list;
                })}>{Object.entries(CATEGORY).map(([key, value]) => <option value={key} key={key}>{value}</option>)}</select></label>
                <label>شماره در دسته<input type="number" min="1" value={q.number} onChange={(e) => changeQuestions((list) => {
                  list[index].number = Number(e.target.value); return list;
                })} /></label></div>
                {LANGUAGES.map(([lang, title]) => <label key={lang}>صورت سؤال · {title}<textarea rows="2" value={q.prompts[lang]}
                  onChange={(e) => changeQuestions((list) => { list[index].prompts[lang] = e.target.value; return list; })} /></label>)}
                <div className="question-image-field"><div className="question-image-preview">{q.art_key
                  ? <Art artKey={q.art_key} compact /> : <span>تصویر اختصاصی هنوز انتخاب نشده است.</span>}</div>
                  <div><label>تصویر این سؤال
                    <input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy}
                      onChange={(e) => { uploadQuestionImage(e.target.files?.[0], q.id); e.target.value = ''; }} />
                  </label><p>پی‌ان‌جی، جی‌پگ یا وب‌پی تا ۵ مگابایت؛ در هر دو زبان یکسان است. اگر تصویری انتخاب نکنید، تصویر داستان این گام نمایش داده می‌شود.</p>
                  {q.art_key && <button type="button" disabled={busy} onClick={() => changeQuestions((list) => {
                    list[index].art_key = ''; return list;
                  })}>برداشتن تصویر اختصاصی</button>}</div></div>
                <div className="option-heading">گزینه‌ها <span>دایرهٔ کنار گزینه، پاسخ درست را تعیین می‌کند.</span></div>
                {q.options.map((option, optionIndex) => <div className="option-row" key={option.id}>
                  <input type="radio" name={`correct-${q.id}`} checked={q.answer_id === option.id} aria-label={`پاسخ درست گزینه ${optionIndex + 1}`}
                    onChange={() => changeQuestions((list) => { list[index].answer_id = option.id; return list; })} />
                  <span className="option-index">{persianDigits(optionIndex + 1)}</span>
                  {LANGUAGES.map(([lang, title]) => <label key={lang}>{title}<input value={option.labels[lang]}
                    onChange={(e) => changeQuestions((list) => { list[index].options[optionIndex].labels[lang] = e.target.value; return list; })} /></label>)}
                </div>)}
              </div>)}
            </div> : <>
              <div className="section-head"><div><h2>محتوای دو‌زبانه</h2><p>هر زبان جداگانه نسخه‌بندی می‌شود. شناسهٔ صفحه ثابت می‌ماند.</p></div></div>
              {LANGUAGES.map(([lang, title]) => <section className="locale-card" key={lang}>
                <div className="locale-title"><span className="language-tag">زبان</span><h3>{title}</h3></div>
                <label>متن صفحه<textarea rows="7" value={locales[lang].text || ''} placeholder={`متن ${title} را اینجا بنویسید`}
                  onChange={(e) => changeText(lang, 'text', e.target.value)} /></label>
              </section>)}
              <section className="locale-card"><div className="locale-title"><h3>تصویر صفحه</h3></div>
                <p>یک تصویر برای هر دو زبان بارگذاری می‌شود. پی‌ان‌جی، جی‌پگ یا وب‌پی تا ۵ مگابایت.</p>
                <div className="image-picker"><Art artKey={locales.fa.art_key} compact />
                  <label className="upload-button">انتخاب و بارگذاری تصویر<input type="file" accept="image/png,image/jpeg,image/webp"
                    onChange={(e) => { uploadImage(e.target.files?.[0]); e.target.value = ''; }} hidden /></label></div>
              </section>
            </>}
            <div className="action-row"><button className="primary" disabled={busy || page.status === 'archived'} onClick={save}>
              {busy ? 'لطفاً صبر کنید…' : 'ذخیرهٔ پیش‌نویس'}</button>
              <button className="publish-button" disabled={busy || page.status === 'archived'} onClick={publish}>انتشار دو‌زبانه</button>
              {page.status === 'archived' ? <><button disabled={busy} onClick={() => lifecycle('restore')}>بازگردانی</button>
                  <button className="delete-archived" disabled={busy} onClick={deleteArchived}>حذف دائمی صفحهٔ بایگانی‌شده</button></>
                : <button className="danger-link" onClick={() => lifecycle('archive')}>بایگانی صفحه</button>}
            </div>
          </section><section className="preview-column"><div className="preview-sticky"><div className="section-head"><div><h2>پیش‌نمایش</h2>
            <p>{dirty ? 'نمای تغییرات ذخیره‌نشده' : 'نمای آخرین نسخهٔ ذخیره‌شده'}</p></div></div>
            <div className="segmented">{LANGUAGES.map(([lang, title]) => <button key={lang} className={previewLanguage === lang ? 'active' : ''}
              onClick={() => setPreviewLanguage(lang)}>{title}</button>)}</div>
            {page.kind === 'story' && <div className="segmented secondary"><button className={previewMode === 'read' ? 'active' : ''}
              onClick={() => setPreviewMode('read')}>خودم می‌خوانم</button><button className={previewMode === 'listen' ? 'active' : ''}
              onClick={() => setPreviewMode('listen')}>گوش می‌دهم</button></div>}
            <div className="book-preview" dir="rtl">{page.kind === 'quiz' ? <>
              <h3>بیا فکر کنیم!</h3>
              {preview.questions?.length ? preview.questions.map((q, index) => <div className="preview-question" key={q.id}>
                <strong>{persianDigits(index + 1)}. {q.prompt || 'متن سؤال هنوز وارد نشده'}</strong>
                {q.art_key && <Art artKey={q.art_key} compact />}
                {q.options.map((o) => <div className={`preview-option ${o.id === q.answer_id ? 'answer' : ''}`} key={o.id}>
                  {o.text || 'گزینهٔ خالی'}{o.id === q.answer_id && <small>پاسخ درست</small>}</div>)}
              </div>) : <p className="empty">هنوز سؤالی اضافه نشده است.</p>}</> : <>
              <Art artKey={preview.art_key} /><div className="preview-text">{previewMode === 'listen'
                ? <><p>هنوز خوانشی برای این صفحه منتشر نشده.</p>
                  <small>انتشار صوت در مرحلهٔ داوری فعال می‌شود.</small></>
                : (preview.text || 'متن این زبان هنوز وارد نشده است.')}</div>
            </>}</div>
            <p className="preview-foot">جایگاه {persianDigits(page.position)} در این گام · {STATES[page.status]}</p>
          </div></section></div>
        </>}
      </main>
    </div>
  </div>;
}

createRoot(document.getElementById('root')).render(
  <UnifiedApp api={api} Login={Login} BookEditor={App} />
);
