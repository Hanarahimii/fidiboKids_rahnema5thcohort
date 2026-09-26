import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { persianDigits } from './persian.js';
import AudioPlayer from './AudioPlayer.jsx';

const LABEL = {
  fa: {
    title: 'صدای قصهٔ تو', start: 'شروع ضبط', pause: 'مکث', resume: 'ادامهٔ ضبط', finish: 'پایان ضبط',
    preview: 'اول صدای خودت را بشنو', discard: 'حذف این ضبط', again: 'دوباره ضبط کن',
    recording: 'در حال ضبط…', paused: 'ضبط مکث کرده', saving: 'نگهداری پیش‌نویس…',
    ready: 'صدایت فقط در این مرورگر نگه داشته شده و هنوز ارسال نشده است.',
    unsaved: 'مرورگر نتوانست پیش‌نویس را ذخیره کند. از این صفحه خارج نشو؛ ارسال را دوباره امتحان کن.',
    consent: 'با ارسال این صدا برای بررسی پژوهشی موافقم. می‌دانم تا زدن دکمهٔ «ارسال»، صدا از این مرورگر خارج نمی‌شود.',
    send: 'ارسال صدا برای پژوهش', sending: 'در حال ارسال…', success: 'صدایت دریافت شد و منتظر بررسی است. ممنون!',
    failure: 'ارسال انجام نشد. ضبطت باقی مانده؛ اینترنت را بررسی کن و دوباره بزن.',
    stale: 'متن این صفحه تغییر کرده است. ضبط را حذف کن و با متن تازه دوباره بخوان.',
    permission: 'برای ضبط، دسترسی میکروفن را در مرورگر اجازه بده.', unsupported: 'این مرورگر امکان ضبط صدا ندارد. Chrome یا Edge را امتحان کن.',
    empty: 'صدایی ضبط نشد؛ دوباره تلاش کن.', localFailure: 'ذخیرهٔ محلی این مرورگر در دسترس نیست.',
    stay: 'ضبط را تمام کن یا حذف کن و سپس صفحه را عوض کن.',
    leave: 'ضبطت در همین مرورگر نگه داشته می‌شود. می‌خواهی به صفحهٔ دیگری بروی؟',
    danger: 'این ضبط حذف شود؟ بعد از حذف دیگر قابل بازیابی نیست.',
    newRecording: 'ضبط قبلی حذف و ضبط تازه شروع شود؟', tooShort: 'کمی بیشتر بخوان و بعد ضبط را تمام کن.',
    sentId: 'شمارهٔ دریافت',
  },
  azb: {
    title: 'سنین قصه سسین', start: 'سس یازماغا باشلا', pause: 'دایان', resume: 'داوام ائت', finish: 'سس یازماغی بیتیر',
    preview: 'اؤنجَه اؤز سسینی دینله', discard: 'بو سسی سیل', again: 'یئنی‌دن سس یاز',
    recording: 'سس یازیلیر…', paused: 'سس یازماق دایانیب', saving: 'قارالاما ساخ‌لانیر…',
    ready: 'سسین یالنیز بو براوزرده ساخ‌لانیب و هله گؤندَریلمَییب.',
    unsaved: 'براوزر سسی ساخ‌لایا بیلمَدی. بو صفحه‌دن چیخما؛ یئنی‌دن گؤندَرمَیه چالیش.',
    consent: 'بو سسین آراشدیرما اوچون گؤندَریلمَسینه راز‌یام. «گؤندَر» دؤگمَسینه باسمایینجا سس براوزردن چیخمَز.',
    send: 'آراشدیرما اوچون سسی گؤندَر', sending: 'گؤندَریلی‌ر…', success: 'سسین آلین‌دی و باخیلماسی‌نی گؤزله‌ییر. ساغ اول!',
    failure: 'سس گؤندَریلمَدی. سسین قالیب؛ اینترنتی یوخلا و یئنی‌دن سِنا.',
    stale: 'بو صفحه‌نین متنی دَییشیب. سسی سیل و یئنی متنی اوخو.',
    permission: 'سس یازماق اوچون میکروفونا ایجازه وئر.', unsupported: 'بو براوزر سس یازماغی باجارمیر. Chrome یا Edge سِنا.',
    empty: 'سس یازیلمادی؛ یئنی‌دن سِنا.', localFailure: 'بو براوزرده یئرلی ساخ‌لاما ایشله‌میر.',
    stay: 'اؤنجَه سس یازماغی بیتیر یا سسی سیل، سونرا صفحه‌نی دَییش.',
    leave: 'سسین بو براوزرده ساخ‌لاناجاق. باشقا صفحه‌یه گئدَسن؟',
    danger: 'بو سس سیلینسین؟ سونرا گَری گَتیریلمَز.', newRecording: 'قاباقکی سس سیلینیب یئنی سس یازیلسین؟',
    tooShort: 'بیر آز دا اوخو، سونرا ضبطی بیتیر.', sentId: 'گؤندَریش نومرَه‌سی',
  },
};

const DB_NAME = 'kidsbook-local-recordings';
function openDraftDB() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) return reject(new Error('IndexedDB unavailable'));
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('drafts', { keyPath: 'key' });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function draftTransaction(mode, operation) {
  const db = await openDraftDB();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction('drafts', mode);
      const req = operation(tx.objectStore('drafts'));
      req.onerror = () => reject(req.error);
      tx.onabort = () => reject(tx.error);
      tx.onerror = () => reject(tx.error);
      tx.oncomplete = () => resolve(req.result);
    });
  } finally { db.close(); }
}
const loadDraft = (key) => draftTransaction('readonly', (store) => store.get(key));
const saveDraft = (value) => draftTransaction('readwrite', (store) => store.put(value));
const eraseDraft = (key) => draftTransaction('readwrite', (store) => store.delete(key));
const chooseMime = () => ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'].find(
  (type) => window.MediaRecorder.isTypeSupported(type)
);

const Recorder = forwardRef(function Recorder({ stepId, pageId, revisionId, language,
  submitUrl = '/api/book/submissions', draftNamespace = 'book' }, ref) {
  const t = LABEL[language] || LABEL.fa;
  const secondsLabel = language === 'azb' ? 'سانیه' : 'ثانیه';
  const draftKey = draftNamespace === 'book' ? `${pageId}:${language}`
    : `${draftNamespace}:${stepId}:${pageId}:${language}`;
  const [phase, setPhase] = useState('loading');
  const [draft, setDraft] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [saved, setSaved] = useState(false);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState(null);
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef(null);
  const stream = useRef(null);
  const pieces = useRef([]);
  const elapsed = useRef(0);
  const activeSince = useRef(null);
  const phaseRef = useRef('loading');
  const savedRef = useRef(false);
  const blobRef = useRef(null);
  const urlRef = useRef(null);
  function phaseTo(next) { phaseRef.current = next; setPhase(next); }
  function releaseStream() { stream.current?.getTracks().forEach((track) => track.stop()); stream.current = null; }
  function setPreview(blob) {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    blobRef.current = blob;
    urlRef.current = blob ? URL.createObjectURL(blob) : null;
    setPreviewUrl(urlRef.current);
  }
  function allowLeave() {
    if (['requesting', 'recording', 'paused', 'saving', 'sending'].includes(phaseRef.current)) {
      window.alert(t.stay); return false;
    }
    if (phaseRef.current === 'ready') {
      if (!savedRef.current) { window.alert(t.unsaved); return false; }
      return window.confirm(t.leave);
    }
    return true;
  }
  useImperativeHandle(ref, () => ({ canLeave: allowLeave }));

  useEffect(() => {
    let active = true;
    loadDraft(draftKey).then((value) => {
      if (!active) return;
      if (value?.blob) {
        setDraft(value); setPreview(value.blob); setSaved(true); savedRef.current = true;
        phaseTo('ready'); setSeconds(Math.round(value.durationMs / 1000));
      } else phaseTo('idle');
    }).catch(() => { if (active) { phaseTo('idle'); setError(t.localFailure); } });
    return () => { active = false; releaseStream(); if (urlRef.current) URL.revokeObjectURL(urlRef.current); };
  }, [draftKey]);

  useEffect(() => {
    if (phase !== 'recording') return undefined;
    const interval = setInterval(() => setSeconds(Math.round((elapsed.current + performance.now() - activeSince.current) / 1000)), 300);
    return () => clearInterval(interval);
  }, [phase]);

  useEffect(() => {
    const warn = (event) => {
      if (['requesting', 'recording', 'paused', 'saving', 'sending', 'ready'].includes(phaseRef.current)) {
        event.preventDefault(); event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, []);

  async function start() {
    if (draft && !window.confirm(t.newRecording)) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setError(t.unsupported); return; }
    const type = chooseMime();
    if (!type) { setError(t.unsupported); return; }
    setError('');
    phaseTo('requesting');
    let media;
    try { media = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { setError(t.permission); phaseTo(draft ? 'ready' : 'idle'); return; }
    try {
      const instance = new MediaRecorder(media, { mimeType: type });
      let failed = false;
      // Keep the old saved draft until the new recorder has actually started.
      pieces.current = []; elapsed.current = 0; activeSince.current = performance.now(); setSeconds(0);
      instance.ondataavailable = (event) => { if (event.data.size) pieces.current.push(event.data); };
      instance.onerror = () => {
        failed = true;
        releaseStream();
        if (draft) { setDraft(draft); setPreview(draft.blob); savedRef.current = true; setSaved(true); phaseTo('ready'); }
        else phaseTo('idle');
        setError(t.empty);
      };
      instance.onstop = async () => {
        releaseStream();
        if (failed) return;
        const durationMs = Math.round(elapsed.current);
        const blob = new Blob(pieces.current, { type: instance.mimeType.split(';')[0] });
        if (!blob.size || durationMs < 500) {
          if (draft) { setDraft(draft); setPreview(draft.blob); savedRef.current = true; setSaved(true); phaseTo('ready'); }
          else phaseTo('idle');
          setError(durationMs < 500 ? t.tooShort : t.empty); return;
        }
        const next = { key: draftKey, blob, durationMs, mime: blob.type,
          requestId: crypto.randomUUID(), stepId, pageId, language, revisionId };
        setPreview(blob); setDraft(next); phaseTo('saving');
        try { await saveDraft(next); savedRef.current = true; setSaved(true); }
        catch { savedRef.current = false; setSaved(false); setError(t.unsaved); }
        phaseTo('ready');
      };
      instance.start(250);
      stream.current = media; recorder.current = instance;
      setDraft(null); setPreview(null); savedRef.current = false; setSaved(false); setConsent(false); setReceipt(null);
      phaseTo('recording');
    } catch { media.getTracks().forEach((track) => track.stop()); phaseTo(draft ? 'ready' : 'idle'); setError(t.unsupported); }
  }
  function pause() {
    if (recorder.current?.state !== 'recording') return;
    elapsed.current += performance.now() - activeSince.current;
    recorder.current.pause(); phaseTo('paused'); setSeconds(Math.round(elapsed.current / 1000));
  }
  function resume() {
    if (recorder.current?.state !== 'paused') return;
    recorder.current.resume(); activeSince.current = performance.now(); phaseTo('recording');
  }
  function finish() {
    if (!recorder.current || !['recording', 'paused'].includes(recorder.current.state)) return;
    if (recorder.current.state === 'recording') elapsed.current += performance.now() - activeSince.current;
    phaseTo('saving'); recorder.current.stop();
  }
  async function discard() {
    if (!window.confirm(t.danger)) return;
    try { await eraseDraft(draftKey); }
    catch { setError(t.localFailure); return; }
    setDraft(null); setPreview(null); setConsent(false); savedRef.current = false; setSaved(false);
    setError(''); phaseTo('idle');
  }
  async function send() {
    if (!draft || !consent || phaseRef.current !== 'ready') return;
    phaseTo('sending'); setError('');
    const form = new FormData();
    Object.entries({ client_request_id: draft.requestId, step_id: draft.stepId, page_id: draft.pageId,
      language: draft.language, content_revision_id: draft.revisionId, duration_ms: String(draft.durationMs),
      consent: 'true', consent_version: 'research-v1' }).forEach(([key, value]) => form.append(key, value));
    form.append('file', draft.blob, `reading.${draft.mime === 'audio/mp4' ? 'm4a' : draft.mime.split('/')[1]}`);
    try {
      const response = await fetch(submitUrl, { method: 'POST', body: form });
      if (!response.ok) {
        setError(response.status === 409 ? t.stale : t.failure); phaseTo('ready'); return;
      }
      const result = await response.json();
      setReceipt(result.submission_id);
      try { await eraseDraft(draftKey); }
      catch { setError(t.localFailure); }
      setDraft(null); savedRef.current = false; setSaved(false); setConsent(false); phaseTo('sent');
    } catch { setError(t.failure); phaseTo('ready'); }
  }

  return <div className="recorder-box" aria-live="polite"><div className="recorder-title"><span className="recorder-symbol" aria-hidden="true"/><strong>{t.title}</strong>
    {phase === 'recording' && <span className="recording-pulse"/>}</div>
      {phase === 'loading' ? <p>{t.saving}</p> : <>
      {phase === 'requesting' && <p>{t.permission}</p>}
      {['idle', 'sent'].includes(phase) && <button onClick={start} className="book-primary">● {t.start}</button>}
      {phase === 'recording' && <div className="recorder-actions"><span>{t.recording} {persianDigits(seconds)} {secondsLabel}</span><button onClick={pause}>{t.pause}</button><button onClick={finish}>{t.finish}</button></div>}
      {phase === 'paused' && <div className="recorder-actions"><span>{t.paused} {persianDigits(seconds)} {secondsLabel}</span><button onClick={resume}>{t.resume}</button><button onClick={finish}>{t.finish}</button></div>}
      {phase === 'saving' && <p>{t.saving}</p>}
      {phase === 'sending' && <p>{t.sending}</p>}
      {phase === 'sent' && <p className="recorder-success">{t.success}<small>{t.sentId}: <bdi>{persianDigits(receipt)}</bdi></small></p>}
      {phase === 'ready' && draft && <><p className="recorder-local">{saved ? t.ready : t.unsaved} · {persianDigits(Math.round(draft.durationMs / 1000))} {secondsLabel}</p>
        <div className="recorder-preview"><strong>{t.preview}</strong><AudioPlayer src={previewUrl || undefined} locale={language} label={t.preview} /></div>
        {draft.revisionId !== revisionId && <p role="alert" className="recorder-error">{t.stale}</p>}
        <div className="recorder-actions"><button onClick={discard}>{t.discard}</button><button onClick={start}>{t.again}</button></div>
        <label className="recorder-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)}/><span>{t.consent}</span></label>
        <button className="book-primary recorder-send" disabled={!consent || draft.revisionId !== revisionId} onClick={send}>{t.send}</button>
      </>}
      {error && <p role="alert" className="recorder-error">{error}</p>}
    </>}
  </div>;
});
export default Recorder;
