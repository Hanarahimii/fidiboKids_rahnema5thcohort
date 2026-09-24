import React, { useEffect, useState } from 'react';
import { persianDigits } from './persian.js';
import AudioPlayer from './AudioPlayer.jsx';
import './research.css';

const STATUS = {
  pending: 'تازه رسیده', review: 'در حال بررسی', screened_out: 'کنار گذاشته‌شده',
  shortlisted: 'نامزد انتخاب', selected: 'انتخاب‌شده', published: 'منتشرشده', rejected: 'ردشده',
};
const NEXT = {
  pending: ['review', 'screened_out', 'rejected'], review: ['shortlisted', 'screened_out', 'rejected'],
  screened_out: ['review', 'rejected'], shortlisted: ['review', 'rejected'],
  selected: ['review', 'shortlisted', 'rejected'], published: [], rejected: ['review'],
};
const formatTime = (value) => value ? new Date(value).toLocaleString('fa-IR') : '—';
const formatLength = (ms) => `${(ms / 1000).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} ثانیه`;
const readingLabel = (id) => id ? `خوانش ${persianDigits(id.split('_')[1])}` : '';
const audioFormat = { 'audio/webm': 'وب‌ام', 'audio/ogg': 'اوگ',
  'audio/mp4': 'ام‌پی‌فور', 'audio/wav': 'ویو' };
function eventNote(value) {
  if (!value) return 'بدون یادداشت';
  return persianDigits(value
    .replace(/^Published in (?:fa|azb)_[1-4]$/, 'در کتاب منتشر شد')
    .replace(/^Publication removed$/, 'انتشار از کتاب برداشته شد')
    .replace(/^Replaced in (?:fa|azb)_[1-4]$/, 'با صدای دیگری جایگزین شد')
    .replace(/Reading (?:fa|azb)_([1-4])/g, 'خوانش $1'));
}

export default function ResearchApp({ api, Login }) {
  const [authenticated, setAuthenticated] = useState(null);
  const [filters, setFilters] = useState({ language: '', status: '', step_id: '' });
  const [result, setResult] = useState({ items: [], total: 0, summary: [], readings: { fa: [], azb: [] } });
  const [availableSteps, setAvailableSteps] = useState([]);
  const [detail, setDetail] = useState(null);
  const [note, setNote] = useState('');
  const [readingId, setReadingId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [audioError, setAudioError] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api('/admin/me').then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)); }, []);
  useEffect(() => { if (authenticated) refresh(); }, [authenticated, filters.language, filters.status, filters.step_id]);
  useEffect(() => { if (authenticated) api('/admin/steps').then((data) => setAvailableSteps(data.steps))
    .catch(() => setAvailableSteps([])); }, [authenticated]);
  async function refresh() {
    const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
    setLoading(true);
    try { setResult(await api(`/research/submissions?${params}`)); setError(''); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }
  async function open(id) {
    setError(''); setNotice(''); setAudioError(false);
    try {
      const value = await api(`/research/submissions/${id}`);
      setDetail(value); setNote(value.review_note); setReadingId(value.target_reading_id || `${value.language}_1`);
    } catch (err) { setError(err.message); }
  }
  async function act(action, data, message) {
    if (!detail || busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const value = await api(`/research/submissions/${detail.id}/${action}`,
        { method: 'POST', ...data && { body: JSON.stringify(data) } });
      setDetail(value); setNote(value.review_note); setReadingId(value.target_reading_id || `${value.language}_1`);
      setNotice(message); await refresh();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  function updateStatus(status) { act('review', { status, note }, `وضعیت به «${STATUS[status]}» تغییر کرد.`); }
  async function signOut() {
    try { await api('/admin/logout', { method: 'POST' }); setAuthenticated(false); setDetail(null); }
    catch (err) { setError(err.message); }
  }
  if (authenticated === null) return <div className="loading">در حال بارگذاری…</div>;
  if (!authenticated) return <Login onLogin={() => setAuthenticated(true)} />;
  const statusCounts = Object.fromEntries(Object.keys(STATUS).map((status) => [status,
    result.summary.filter((item) => item.status === status).reduce((sum, item) => sum + item.count, 0)]));
  return <div className="research-app" dir="rtl">
    <header className="research-header"><div><span className="research-mark"><img src="/fidibo-kids-logo.png" alt="" /></span><strong>پژوهش فیدیبو کیدز</strong><small>بررسی و انتشار صدا</small></div>
      <nav><a href="/book" target="_blank" rel="noopener noreferrer">کتاب کودک ↗</a><a href="/">پنل محتوا</a><button onClick={signOut}>خروج</button></nav></header>
    <main className="research-main"><section className="research-intro"><p>خوانش‌های رسیده</p><h1>صداها را بشنو، بررسی کن و خوانش‌ها را بساز</h1>
      <span>فایل خام فقط در این صفحه با ورود ادمین قابل شنیدن است. انتشار، نسخهٔ جداگانه‌ای برای کتاب می‌سازد.</span></section>
      <div className="research-stats">{['pending', 'review', 'shortlisted', 'selected', 'published'].map((status) =>
        <div key={status}><strong>{persianDigits(statusCounts[status] || 0)}</strong><span>{STATUS[status]}</span></div>)}</div>
      <div className="research-layout"><aside className="research-list-panel"><div className="research-list-head"><h2>فهرست فایل‌ها</h2><span>{persianDigits(result.total)} نتیجه</span></div>
        <div className="research-filters"><label>زبان<select value={filters.language} onChange={(e) => setFilters({ ...filters, language: e.target.value })}>
          <option value="">هر دو زبان</option><option value="fa">فارسی</option><option value="azb">ترکی</option></select></label>
          <label>وضعیت<select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">همه</option>{Object.entries(STATUS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
          <label className="research-step-filter">گام<select value={filters.step_id} onChange={(e) => setFilters({ ...filters, step_id: e.target.value })}>
            <option value="">همهٔ گام‌ها</option>{availableSteps.map((step) => <option key={step.id} value={step.id}>{step.titles.fa}</option>)}
          </select></label></div>
        <div className="research-results">{loading && <p className="research-empty">در حال خواندن…</p>}
          {!loading && !result.items.length && <p className="research-empty">در این فیلتر صدایی پیدا نشد.</p>}
          {result.items.map((item) => <button className={`research-item ${detail?.id === item.id ? 'active' : ''}`} key={item.id} onClick={() => open(item.id)}>
            <div><b>{item.language === 'fa' ? 'فارسی' : 'ترکی'} · {item.step_title || 'گام داستان'} · صفحهٔ {persianDigits(item.page_position)}</b><span className={`research-badge ${item.status}`}>{STATUS[item.status]}</span></div>
            <small>{formatLength(item.duration_ms)} · {formatTime(item.submitted_at)}</small>
            {!item.is_current_revision && <small className="research-stale">متن صفحه تغییر کرده</small>}
          </button>)}</div>
          {result.total > result.items.length && <p className="research-empty">۵۰۰ مورد اول نمایش داده می‌شود؛ برای پیدا کردن بقیه از فیلترها استفاده کنید.</p>}
        </aside>
        <section className="research-detail">{!detail ? <div className="research-welcome"><h2>یکی از صداها را انتخاب کن</h2><p>اطلاعات صفحه، پیش‌نمایش خصوصی و مسیر بررسی اینجا دیده می‌شود.</p></div>
          : <><div className="research-detail-head"><div><p>شمارهٔ دریافت</p><code dir="ltr">{persianDigits(detail.id)}</code><h2>{detail.step_title}</h2>
                <span className="research-page">صفحهٔ {persianDigits(detail.page_position)} · {detail.language === 'fa' ? 'فارسی' : 'ترکی'}</span></div>
              <span className={`research-badge ${detail.status}`}>{STATUS[detail.status]}</span></div>
            {error && <div className="notice error" role="alert">{error}</div>}
            {notice && <div className="notice success">{notice}</div>}
            {!detail.is_current_revision && <div className="research-warning">متن منتشرشدهٔ این صفحه پس از ضبط تغییر کرده است. صدای این نسخه را نمی‌توان منتشر کرد.</div>}
            <div className="research-facts"><span>زمان دریافت: {formatTime(detail.submitted_at)}</span><span>مدت: {formatLength(detail.duration_ms)}</span>
              <span>اندازه: {persianDigits(Math.round(detail.file_size_bytes / 1024))} کیلوبایت</span><span>قالب صوت: {audioFormat[detail.mime_type] || 'صوتی'}</span></div>
            <section className="research-text"><h3>متنی که خوانده شده</h3><p>{detail.recorded_text}</p></section>
            <section className="research-audio"><h3>شنیدن خصوصی فایل خام</h3><AudioPlayer key={detail.id} label="شنیدن خصوصی فایل خام"
              src={detail.raw_url} onError={() => setAudioError(true)} /><small>این فایل خام در کتاب کودک منتشر نمی‌شود.</small>
              {audioError && <p className="research-warning">فایل خام باز نشد؛ وجود فایل ضبط‌شده را بررسی کنید.</p>}</section>
            <section className="research-actions"><h3>بررسی و یادداشت</h3><label>یادداشت پژوهشگر<textarea value={note} onChange={(e) => setNote(e.target.value)} rows="3" maxLength="4000" /></label>
              <button disabled={busy || note === detail.review_note} onClick={() => updateStatus(detail.status)}>ذخیرهٔ یادداشت</button>
              <div className="research-action-buttons">{NEXT[detail.status].map((status) => <button key={status} disabled={busy}
                onClick={() => updateStatus(status)}>{STATUS[status]}</button>)}</div></section>
            {['shortlisted', 'selected'].includes(detail.status) && <section className="research-selection"><h3>جایگاه خوانش</h3><p>یک خوانش از همین زبان انتخاب کن. این هویت در صفحه‌های دیگر کتاب هم همین شماره را دارد.</p>
              <div><select value={readingId} onChange={(e) => setReadingId(e.target.value)}>
                {(result.readings[detail.language] || []).map((reading) => <option key={reading.id} value={reading.id}>{readingLabel(reading.id)}</option>)}</select>
                <button disabled={busy || !detail.is_current_revision} onClick={() => act('select', { reading_id: readingId, note }, 'جایگاه خوانش ثبت شد.')}>ثبت انتخاب</button></div></section>}
            {detail.status === 'selected' && <section className="research-publication"><h3>انتشار در کتاب کودک</h3>
              {detail.replacing_submission_id && <p className="research-warning">این جایگاه اکنون یک صدای منتشرشده دارد. انتشار این صدا، خوانش قبلی را جایگزین می‌کند.</p>}
              <button className="publish-button" disabled={busy || !detail.is_current_revision} onClick={() => {
                if (window.confirm(`صدای این صفحه در ${readingLabel(detail.target_reading_id)} منتشر شود؟`))
                  act('publish', null, 'نسخهٔ جداگانهٔ صوت منتشر شد. در کتاب کودک قابل شنیدن است.');
              }}>انتشار {readingLabel(detail.target_reading_id)} در کتاب</button></section>}
            {detail.status === 'published' && <section className="research-publication"><p>این صدا در «{readingLabel(detail.published_reading_id)}» برای همین صفحه منتشر شده است.</p>
              <button disabled={busy} onClick={() => {
                if (window.confirm('این خوانش از کتاب کودک پنهان شود؟ فایل خام و سابقهٔ داوری باقی می‌مانند.'))
                  act('unpublish', null, 'صدا از کتاب کودک برداشته شد.');
              }}>لغو انتشار</button></section>}
            <section className="research-history"><h3>سابقهٔ تصمیم‌ها</h3>{!detail.events.length && <p>هنوز تصمیمی ثبت نشده است.</p>}
              {detail.events.map((event, index) => <div key={index}><b>{STATUS[event.new_status]}</b><small>{formatTime(event.occurred_at)}</small><span>{eventNote(event.note)}</span></div>)}</section>
          </>}</section></div>
    </main>
  </div>;
}
