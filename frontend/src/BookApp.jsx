import React, { useEffect, useRef, useState } from 'react';
import { makeQuiz } from './quiz.js';
import Recorder from './Recorder.jsx';
import AudioPlayer from './AudioPlayer.jsx';
import SupportSection from './SupportSection.jsx';
import { readingForLanguage, resolvePlayback } from './reading.js';
import { persianDigits } from './persian.js';
import './book.css';
import { completedActivity } from './activity.js';

const COPY = {
  fa: {
    title: 'ماهی سیاه کوچولو', subtitle: 'یک سفر، هزار سؤال تازه', enter: 'شروع قصه', map: 'نقشهٔ قصه‌ها',
    steps: 'گام داستان', start: 'شروع این گام', continue: 'ادامهٔ قصه', previous: 'صفحهٔ قبل', next: 'صفحهٔ بعد',
    read: 'خودم می‌خوانم', listen: 'گوش می‌دهم', recordSoon: 'این صفحه را با صدای خودت بخوان.',
    recordingLater: 'ضبط تو تا زمان ارسال در همین مرورگر می‌ماند.', emptyAudio: 'هنوز خوانشی برای این صفحه منتشر نشده.',
    missingReading: 'این خوانش برای این صفحه هنوز آماده نیست.', reading: 'خوانش', lesson: 'چه یاد گرفتیم؟',
    chooseReading: 'یکی از خوانش‌های موجود را انتخاب کن.', autoplayBlocked: 'برای ادامهٔ صدا روی دکمهٔ پخش بزن.',
    audioFailure: 'صدا بارگذاری نشد. دوباره تلاش کن.',
    quiz: 'بیا فکر کنیم!', correct: 'آفرین، درست گفتی!', incorrect: 'یک بار دیگر به قصه فکر کن.',
    nextQuestion: 'سؤال بعدی', result: 'پایان سؤال‌ها', questions: 'از', answer: 'پاسخ درست',
    retry: 'دوباره بازی می‌کنم', finishStep: 'پایان این گام', stepDone: 'آفرین! این گام را تمام کردی.',
    nextStep: 'گام بعدی', rateTitle: 'قصه را دوست داشتی؟', rateHint: 'به این قصه از یک تا پنج ستاره بده.',
    thanks: 'ممنون از نظرت!', rate: 'ثبت ستاره‌ها', completed: 'خوانده‌شده', page: 'صفحه',
    loading: 'قصه دارد باز می‌شود…', failure: 'قصه باز نشد. دوباره تلاش کن.', retryLoad: 'تلاش دوباره',
    noQuestions: 'هنوز سؤالی برای این صفحه منتشر نشده.',
    headerSubtitle: 'کتاب تعاملی «ماهی سیاه کوچولو»',
    goCover: 'رفتن به جلد کتاب',
    coverKicker: 'داستان تعاملی · بخوان و کشف کن',
    coverDescription: 'ماجرای یک پرسش بزرگ، یک سفر دور و یک دنیای تازه. قصه را بخوان، صدایت را ثبت کن یا به خوانش‌ها گوش بده.',
    coverCredit: 'اقتباس آزاد آموزشی از قصه‌ی صمد بهرنگی. تصویرها نو هستند و از روی چاپ اصلی بازسازی شده‌اند.',
    mapKicker: 'مسیر داستان', mapDescription: 'از هر گام شروع کن و ماجرای ماهی را پیش ببر.',
    footerLine: 'فیدیبو کیدز · بخوان، بپرس، کشف کن', imageFallback: 'تصویر قصه',
    category: { recall: 'یادآوری', infer: 'فکر کردن', think: 'نظر تو' },
    of: 'از',
  },
  azb: {
    title: 'بالاجا قارا ماهی', subtitle: 'بیر سفر، مین یئنی سؤال', enter: 'قصه‌یه باشلا', map: 'قصه‌لرین خریطه‌سی',
    steps: 'قصه‌نین آددیمی', start: 'بو آددیما باشلا', continue: 'قصه‌یه داوام ائت', previous: 'اؤنجه‌کی صفحه', next: 'سونراکی صفحه',
    read: 'اؤزوم اوخویورام', listen: 'دینله‌ییرم', recordSoon: 'بو صفحه‌نی اؤز سسینله اوخو.',
    recordingLater: 'سسین گؤندَرمَیَنَجَن بو براوزرده قالار.', emptyAudio: 'بو صفحه اوچون هله اوخویوش یاییملانماییب.',
    missingReading: 'بو اوخویوش بو صفحه اوچون هله حاضر دئییل.', reading: 'اوخویوش', lesson: 'نَه اویرَندیک؟',
    chooseReading: 'وار اولان اوخویوشلاردان بیرینی سئچ.', autoplayBlocked: 'سسین داوامی اوچون دینله‌مه دؤگمَسینه باس.',
    audioFailure: 'سس آچیل‌مادی. یئنی‌دن سِنا.',
    quiz: 'گَل بیرلیکده فیکیر ائدَک!', correct: 'آفرین، دوغرو جواب وئردین!', incorrect: 'قصه‌یه بیر ده فیکیر ائت.',
    nextQuestion: 'سونراکی سؤال', result: 'سؤاللارین سونو', questions: 'دان', answer: 'دوغرو جواب',
    retry: 'بیر ده اویناییرام', finishStep: 'بو آددیمین سونو', stepDone: 'آفرین! بو آددیمی بیتیر‌دین.',
    nextStep: 'سونراکی آددیم', rateTitle: 'قصه‌نی بَیَندین؟', rateHint: 'قصه‌یه بیر‌دن بئشَه قَدَر اولدوز وئر.',
    thanks: 'فیکرین اوچون ساغ اول!', rate: 'اولدوزلاری یاز', completed: 'اوخونموش', page: 'صفحه',
    loading: 'قصه آچیلیر…', failure: 'قصه آچیلمادی. بیر ده سِنا.', retryLoad: 'بیر ده سِنا',
    noQuestions: 'بو صفحه اوچون هله سؤال یوخدو.',
    headerSubtitle: '«بالاجا قارا ماهی» اینتراکتیو کیتابی',
    goCover: 'کیتابین اوزونه قاییت',
    coverKicker: 'اینتراکتیو قصه · اوخو و کشف ائت',
    coverDescription: 'بیر بؤیوک سؤال، اوزون بیر سفر و یئنی بیر دنیا. قصه‌نی اوخو، سسینی یاز یا اوخویوشلاری دینله.',
    coverCredit: 'صمد بهرنگینین قصه‌سیندن آزاد اؤیره‌دیجی اویغولاما. رَسملر یئنیدیر و ائلک چاپ‌دان یئنی‌دن چکیلیب.',
    mapKicker: 'قصه‌نین یولو', mapDescription: 'ایستَدیگین آددیمدان باشلا و ماهینین سفرینه داوام ائت.',
    footerLine: 'فیدیبو کیدز · اوخو، سوروش، کشف ائت', imageFallback: 'قصه‌نین رَسمی',
    category: { recall: 'یادا سالما', infer: 'فیکیر ائتمک', think: 'سنین فیکرین' },
    of: 'دان',
  },
};

async function bookApi(path, options = {}) {
  const response = await fetch(`/api/book${path}`, { ...options, headers: {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}),
  } });
  if (!response.ok) throw new Error(`Book request failed: ${response.status}`);
  return response.json();
}

function artUrl(key) {
  if (!key) return null;
  return key.startsWith('upload:') ? `/api/assets/${key.slice(7)}` : `/api/book/art/${key}`;
}

function Illustration({ artKey, className = '', source = null, alt = 'تصویر قصه', fallbackLabel = 'تصویر قصه' }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [artKey, source]);
  const src = source || artUrl(artKey);
  return <div className={`book-illustration ${className}`}>
    {src && !failed ? <img src={src} alt={alt} onError={() => setFailed(true)} />
      : <div className="book-art-fallback" aria-hidden="true"><span>{fallbackLabel}</span></div>}
  </div>;
}

function readStored(key, fallback) {
  try { const value = localStorage.getItem(key); return value ? JSON.parse(value) : fallback; }
  catch { return fallback; }
}
function saveStored(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } }

export default function BookApp() {
  const params = new URLSearchParams(location.search);
  const [language, setLanguage] = useState(() => {
    const choice = params.get('language') || readStored('book-language', 'fa');
    return choice === 'azb' ? 'azb' : 'fa';
  });
  const [screen, setScreen] = useState(() => params.get('page') ? 'page' : params.get('view') === 'map' ? 'map' : 'cover');
  const [stepId, setStepId] = useState(() => params.get('step'));
  const [pageId, setPageId] = useState(() => params.get('page'));
  const [steps, setSteps] = useState([]);
  const [banners, setBanners] = useState({ cover: null, steps: {} });
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [mode, setMode] = useState('read');
  const [readingId, setReadingId] = useState(() => {
    const ordinal = readStored('book-reading-ordinal', null);
    return [1, 2, 3, 4].includes(ordinal) ? `${language}_${ordinal}` : null;
  });
  const [readings, setReadings] = useState([]);
  const [readingsState, setReadingsState] = useState('idle');
  const [readingsFor, setReadingsFor] = useState('');
  const [readingsRetry, setReadingsRetry] = useState(0);
  const [audioRetry, setAudioRetry] = useState(0);
  const [audioNotice, setAudioNotice] = useState('');
  const [audioError, setAudioError] = useState(false);
  const [quizSession, setQuizSession] = useState(null);
  const [quizIndex, setQuizIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [completed, setCompleted] = useState(() => readStored('book-completed', []));
  const [stars, setStars] = useState(0);
  const [rated, setRated] = useState(false);
  const [ratingError, setRatingError] = useState(false);
  const audioRef = useRef(null);
  const continuePlaybackRef = useRef(false);
  const recorderRef = useRef(null);
  const copy = COPY[language];

  useEffect(() => {
    let active = true; setLoading(true); setFailure(false);
    bookApi(`/steps?language=${language}`).then((data) => {
      if (active) { setSteps(data.steps); setLoading(false); }
    }).catch(() => { if (active) { setFailure(true); setLoading(false); } });
    saveStored('book-language', language);
    return () => { active = false; };
  }, [language, reloadKey]);

  useEffect(() => {
    let active = true;
    bookApi('/banners').then((data) => {
      if (active) setBanners({ cover: data.cover, steps: data.steps || {} });
    }).catch(() => { /* Original illustrations remain available. */ });
    return () => { active = false; };
  }, [reloadKey]);

  const step = steps.find((item) => item.id === stepId);
  const page = step?.pages.find((item) => item.id === pageId);
  useEffect(()=>{document.title=(screen==='cover'?copy.title:screen==='map'?'نقشهٔ قصه':page?.kind==='quiz'?'پرسش‌های قصه':page?.kind==='lesson'?'چه یاد گرفتیم؟':step?.title||copy.title)+' | فیدیبو کیدز';},[screen,page?.kind,step?.title,copy.title]);
  const pageIndex = step?.pages.findIndex((item) => item.id === pageId) ?? -1;
  const quizIllustration = page?.kind === 'quiz'
    ? step.pages.slice(0, pageIndex).reverse().find((item) => item.kind === 'story')?.content.art_key
      || step.pages.find((item) => item.kind === 'story')?.content.art_key : null;
  const readingContext = page ? `${page.id}:${language}` : '';
  const readyReadings = readingsState === 'ready' && readingsFor === readingContext;
  const playback = resolvePlayback(readingId, readyReadings ? readings : []);

  useEffect(() => {
    if (!loading && !failure && screen === 'page' && !page) setScreen('map');
  }, [loading, failure, screen, page]);

  useEffect(() => {
    const query = new URLSearchParams(); query.set('language', language);
    if (screen === 'page' && stepId && pageId) { query.set('step', stepId); query.set('page', pageId); }
    else if (screen === 'map') query.set('view', 'map');
    history.replaceState(null, '', `${location.pathname}?${query}`);
  }, [language, screen, stepId, pageId]);

  useEffect(() => {
    if (!page || page.kind !== 'quiz' || quizSession?.pageId === page.id) return;
    const previous = readStored(`quiz-previous:${page.id}`, {});
    const generated = makeQuiz(page.content.questions || [], previous);
    saveStored(`quiz-previous:${page.id}`, generated.memory);
    setQuizSession({ pageId: page.id, items: generated.items });
    setQuizIndex(0); setAnswers({});
  }, [page?.id, page?.kind, page?.content?.questions, quizSession?.pageId]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      try { audioRef.current.currentTime = 0; } catch { /* no seekable metadata yet */ }
    }
    if (screen !== 'page' || page?.kind !== 'story' || mode !== 'listen') {
      setReadings([]); setReadingsFor(''); setReadingsState('idle'); return;
    }
    let active = true; setReadingsFor(''); setReadingsState('loading'); setAudioError(false); setAudioNotice('');
    bookApi(`/readings?page_id=${encodeURIComponent(page.id)}&language=${language}`)
      .then((data) => { if (active) { setReadings(data.readings); setReadingsFor(`${page.id}:${language}`); setReadingsState('ready'); } })
      .catch(() => { if (active) { continuePlaybackRef.current = false; setReadings([]); setReadingsFor(''); setReadingsState('error'); } });
    return () => { active = false; };
  }, [screen, page?.id, page?.kind, language, mode, readingsRetry]);

  useEffect(() => {
    if (!readyReadings || screen !== 'page' || page?.kind !== 'story' || mode !== 'listen'
        || !continuePlaybackRef.current) return;
    const action = resolvePlayback(readingId, readings, true);
    continuePlaybackRef.current = false;
    if (action.missing) { setAudioNotice(copy.missingReading); return; }
    if (!action.shouldPlay || !audioRef.current) return;
    let active = true;
    const playbackPromise = audioRef.current.play();
    if (playbackPromise?.catch) playbackPromise.catch((error) => {
      if (!active) return;
      if (error?.name === 'NotAllowedError') setAudioNotice(copy.autoplayBlocked);
      else { setAudioError(true); setAudioNotice(copy.audioFailure); }
    });
    return () => { active = false; };
  }, [readyReadings, readings, readingId, page?.id, screen, mode, language]);

  function stopAudio() {
    continuePlaybackRef.current = false;
    if (audioRef.current) {
      audioRef.current.pause();
      try { audioRef.current.currentTime = 0; } catch { /* no seekable metadata yet */ }
    }
    setAudioNotice(''); setAudioError(false);
  }
  function chooseReading(id) {
    stopAudio(); setReadingId(id); setAudioRetry(0);
    saveStored('book-reading-ordinal', Number(id.split('_')[1]));
  }

  function changeLanguage(next) {
    if (next === language) return;
    if (recorderRef.current && !recorderRef.current.canLeave()) return;
    stopAudio();
    setReadingId(readingForLanguage(readingId, next));
    setLanguage(next);
  }
  function goMap(alreadyChecked = false) {
    if (alreadyChecked !== true && recorderRef.current && !recorderRef.current.canLeave()) return;
    stopAudio(); setScreen('map'); setMode('read');
  }
  function openStep(id) {
    if (recorderRef.current && !recorderRef.current.canLeave()) return;
    const selected = steps.find((item) => item.id === id);
    if (!selected?.pages.length) return;
    stopAudio();
    setStepId(id); setPageId(selected.pages[0].id); setScreen('page'); setMode('read'); setQuizSession(null);
  }
  function visit(index) {
    if (!step) return;
    if (recorderRef.current && !recorderRef.current.canLeave()) return;
    if (index < 0) return goMap(true);
    if (index >= step.pages.length) { stopAudio(); return finishStep(); }
    const wasPlaying = mode === 'listen' && audioRef.current && !audioRef.current.paused && !audioRef.current.ended;
    stopAudio();
    const next = step.pages[index]; setPageId(next.id); setScreen('page'); setQuizSession(null);
    continuePlaybackRef.current = Boolean(wasPlaying && next.kind === 'story' && readingId);
    if (next.kind !== 'story') setMode('read');
  }
  function finishStep() {
    completedActivity('story', `fish:${stepId}`);
    const next = [...new Set([...completed, stepId])]; setCompleted(next); saveStored('book-completed', next);
    setScreen(steps.at(-1)?.id === stepId ? 'rating' : 'step_done');
  }
  function completeQuiz() {
    if (pageIndex + 1 < (step?.pages.length || 0)) visit(pageIndex + 1);
    else finishStep();
  }
  async function submitStars() {
    if (!stars) return;
    setRatingError(false);
    let clientId = readStored('book-rating-id', null);
    if (!clientId) { clientId = crypto.randomUUID(); saveStored('book-rating-id', clientId); }
    try {
      await bookApi('/ratings', { method: 'POST', body: JSON.stringify({ client_id: clientId, language, stars }) });
      setRated(true);
    } catch { setRatingError(true); }
  }
  function restartQuiz() {
    if (!page || page.kind !== 'quiz') return;
    const previous = readStored(`quiz-previous:${page.id}`, {});
    const generated = makeQuiz(page.content.questions || [], previous);
    saveStored(`quiz-previous:${page.id}`, generated.memory);
    setQuizSession({ pageId: page.id, items: generated.items }); setQuizIndex(0); setAnswers({});
  }

  return <div className="book-app" dir="rtl">
    <div className="sea-bubbles" aria-hidden="true"><i/><i/><i/><i/><i/></div>
    <header className="book-header"><button className="book-mark" onClick={() => {
      if (recorderRef.current && !recorderRef.current.canLeave()) return;
      stopAudio(); setScreen('cover');
    }} aria-label={copy.goCover}><img src="/fidibo-kids-logo.png" alt="" /></button>
      <div className="book-brand"><strong>فیدیبو کیدز</strong><small>{copy.headerSubtitle}</small></div>
      <div className="book-header-space" />
      {screen !== 'cover' && <button className="book-map-button" onClick={goMap} aria-label={copy.map}>⌂ <span>{copy.map}</span></button>}
      <div className="book-language" role="group" aria-label={language === 'fa' ? 'زبان کتاب' : 'کیتابین دیلی'}>
        <button className={language === 'fa' ? 'active' : ''} onClick={() => changeLanguage('fa')}>فارسی</button>
        <button className={language === 'azb' ? 'active' : ''} onClick={() => changeLanguage('azb')}>ترکی</button>
      </div>
    </header>

    {loading ? <div className="book-center"><div className="book-spinner" aria-hidden="true">···</div><p>{copy.loading}</p></div>
      : failure ? <div className="book-center"><p>{copy.failure}</p><button className="book-primary" onClick={() => setReloadKey((x) => x + 1)}>{copy.retryLoad}</button></div>
      : <main className="book-main">
        {screen === 'cover' && <div className="book-cover"><div className="cover-text"><span className="cover-kicker">{copy.coverKicker}</span>
          <h1>{copy.title}</h1><p>{copy.coverDescription}</p>
          <button className="book-primary big" onClick={goMap}>{copy.enter} <span>←</span></button>
          <div className="cover-credit">{copy.coverCredit}</div></div>
          <Illustration artKey="cover" source={banners.cover} alt={copy.title} fallbackLabel={copy.imageFallback}
            className={`cover-art ${banners.cover ? 'custom-banner' : ''}`} /></div>}

        {screen === 'map' && <section className="book-map"><div className="map-intro"><span className="cover-kicker">{copy.mapKicker}</span>
          <h1>{copy.map}</h1><p>{copy.mapDescription}</p></div>
          <div className="map-grid">{steps.map((item, index) => <button className="map-card" key={item.id} onClick={() => openStep(item.id)}>
            <div className="map-card-art"><Illustration source={banners.steps[item.id]} artKey={item.pages.find((p) => p.kind === 'story')?.content.art_key}
              className={banners.steps[item.id] ? 'custom-banner' : ''} alt={item.title} fallbackLabel={copy.imageFallback} /></div>
            <div className="map-card-body"><span className="map-number">{copy.steps} {persianDigits(index + 1)}</span><h2>{item.title}</h2>
              <span className="map-cta">{completed.includes(item.id) ? `✓ ${copy.completed}` : `${copy.start} ←`}</span></div>
          </button>)}</div></section>}

        {screen === 'page' && page && <section className="reader-shell"><div className="reader-trail">
          <span>{step.title}</span><span className="trail-separator">/</span><span>{page.kind === 'story'
            ? `${copy.page} ${persianDigits(step.pages.filter((p) => p.kind === 'story').findIndex((p) => p.id === page.id) + 1)} ${copy.of} ${persianDigits(step.pages.filter((p) => p.kind === 'story').length)}`
            : page.kind === 'lesson' ? copy.lesson : copy.quiz}</span>
          <div className="trail-progress"><span style={{ width: `${((pageIndex + 1) / step.pages.length) * 100}%` }}/></div>
        </div>
          {page.kind === 'story' && <><div className="reader-card"><Illustration artKey={page.content.art_key} className="reader-art" fallbackLabel={copy.imageFallback} />
            <div className="reader-content"><span className="reader-kicker">{step.title}</span>
              <div className="reader-modes"><button className={mode === 'read' ? 'active' : ''} onClick={() => {
                stopAudio(); setMode('read');
              }}>{copy.read}</button>
                <button className={mode === 'listen' ? 'active' : ''} onClick={() => {
                  if (recorderRef.current && !recorderRef.current.canLeave()) return;
                  stopAudio();
                  setMode('listen');
                }}>{copy.listen}</button></div>
              <p className="reader-text">{page.content.text}</p>
              {mode === 'read' ? <details className="u-record-drawer"><summary>{copy.recordSoon}</summary><Recorder ref={recorderRef} key={`${page.id}:${language}`} stepId={step.id}
                pageId={page.id} revisionId={page.revision_id} language={language} /></details>
                : <div className="listen-area">{readingsState === 'error' ? <div role="alert"><p>{copy.audioFailure}</p>
                    <button onClick={() => setReadingsRetry((old) => old + 1)}>{copy.retryLoad}</button></div>
                  : !readyReadings ? <p>{copy.loading}</p>
                  : readings.length === 0 ? <p className="audio-empty">{copy.emptyAudio}</p> : <>
                    <div className="reading-choices">{readings.map((item) => <button key={item.id}
                      className={readingId === item.id ? 'active' : ''} onClick={() => chooseReading(item.id)}>{copy.reading} {persianDigits(item.ordinal)}</button>)}</div>
                    {playback.selected
                      ? <><AudioPlayer key={`${page.id}-${language}-${readingId}-${audioRetry}`} ref={audioRef}
                          src={playback.selected.audio_url} label={`${copy.reading} ${persianDigits(playback.selected.ordinal)}`} locale={language}
                          onPlay={() => { setAudioError(false); setAudioNotice(''); }}
                          onError={() => { setAudioError(true); setAudioNotice(copy.audioFailure); }} />
                        {audioError && <button onClick={() => { setAudioError(false); setAudioRetry((old) => old + 1); }}>{copy.retryLoad}</button>}</>
                      : <p className="audio-empty" role="status">{playback.missing ? `${copy.missingReading} ${copy.chooseReading}` : copy.chooseReading}</p>}
                    {audioNotice && <p className="audio-notice" role="status">{audioNotice}</p>}</>}
                </div>}
            </div></div><div className="page-nav"><button onClick={() => visit(pageIndex - 1)}>→ {copy.previous}</button>
              <button className="book-primary" onClick={() => visit(pageIndex + 1)}>{copy.next} ←</button></div></>}

          {page.kind === 'lesson' && <><div className="lesson-card"><div className="lesson-art"><Illustration artKey={page.content.art_key} fallbackLabel={copy.imageFallback} /></div>
            <div className="lesson-text"><span className="cover-kicker">{copy.lesson}</span>
              <h2>{page.content.text}</h2></div></div><div className="page-nav"><button onClick={() => visit(pageIndex - 1)}>→ {copy.previous}</button>
              <button className="book-primary" onClick={() => visit(pageIndex + 1)}>{copy.quiz} ←</button></div></>}

          {page.kind === 'quiz' && <div className="quiz-shell"><div className="quiz-heading"><h1>{copy.quiz}</h1>
            <p>{quizSession?.items.length ? `${persianDigits(Math.min(quizIndex + 1, quizSession.items.length))} ${copy.questions} ${persianDigits(quizSession.items.length)}` : copy.noQuestions}</p></div>
            {quizSession?.items.length ? (() => {
              if (quizIndex >= quizSession.items.length) {
                const right = quizSession.items.filter((item) => {
                  const question = page.content.questions.find((q) => q.id === item.id);
                  return answers[item.id] === question?.answer_id;
                }).length;
                return <div className="quiz-result"><h2>{copy.result}</h2>
                  <p>{persianDigits(right)} {copy.questions} {persianDigits(quizSession.items.length)}</p>
                  <div className="quiz-result-actions"><button onClick={restartQuiz}>{copy.retry}</button>
                    <button className="book-primary" onClick={completeQuiz}>{copy.continue} ←</button></div></div>;
              }
              const item = quizSession.items[quizIndex];
              const question = page.content.questions.find((q) => q.id === item.id);
              if (!question) return <p>{copy.noQuestions}</p>;
              const selected = answers[item.id];
              return <div className="quiz-card" key={item.id}><span className="quiz-category">
                {copy.category[item.category]}</span>
                <h2>{question.prompt}</h2>
                <Illustration artKey={question.art_key || quizIllustration} className="quiz-illustration"
                  alt={question.prompt} fallbackLabel={copy.imageFallback} />
                <div className="quiz-options">{item.optionIds.map((id) => {
                  const option = question.options.find((o) => o.id === id);
                  const chosen = selected === id;
                  return <button key={id} disabled={Boolean(selected)}
                    className={`${chosen ? 'chosen' : ''} ${selected && id === question.answer_id ? 'right' : ''}`}
                    onClick={() => setAnswers((old) => ({ ...old, [item.id]: id }))}><span className="option-circle">◯</span>
                      {option?.art_key && <img className="quiz-option-image" src={artUrl(option.art_key)} alt="" />}{option?.text}</button>;
                })}</div>{selected && <div className={`quiz-feedback ${selected === question.answer_id ? 'yes' : 'no'}`}>
                  <span>{selected === question.answer_id ? copy.correct : copy.incorrect}</span>
                  {selected !== question.answer_id && <small>{copy.answer}: {question.options.find((o) => o.id === question.answer_id)?.text}</small>}
                  <button className="book-primary" onClick={() => setQuizIndex((x) => x + 1)}>
                    {quizIndex + 1 === quizSession.items.length ? copy.result : copy.nextQuestion} ←</button>
                </div>}</div>;
            })() : <button className="book-primary" onClick={completeQuiz}>{copy.continue}</button>}
            <button className="quiz-back" onClick={() => visit(pageIndex - 1)}>→ {copy.previous}</button></div>}
        </section>}

        {screen === 'step_done' && <div className="book-finish"><h1>{copy.stepDone}</h1>
          <div className="finish-actions"><button onClick={goMap}>{copy.map}</button><button className="book-primary" onClick={() => {
            const next = steps.findIndex((item) => item.id === stepId) + 1; if (steps[next]) openStep(steps[next].id);
          }}>{copy.nextStep} ←</button></div></div>}

        {screen === 'rating' && <div className="book-finish rating-screen"><h1>{rated ? copy.thanks : copy.rateTitle}</h1>
          {!rated && <><p>{copy.rateHint}</p><div className="rating-stars">{[1, 2, 3, 4, 5].map((value) => <button
            key={value} aria-label={`${persianDigits(value)} ${copy.rateTitle}`} className={value <= stars ? 'filled' : ''}
            onClick={() => setStars(value)}>★</button>)}</div><button className="book-primary" disabled={!stars} onClick={submitStars}>{copy.rate}</button>
            {ratingError && <p className="rating-error">{copy.failure}</p>}</>}
          <button onClick={goMap}>{copy.map}</button></div>}
      </main>}
    <footer className="book-footer"><SupportSection language={language} /><p>{copy.footerLine}</p></footer>
  </div>;
}
