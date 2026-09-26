import React, { useEffect, useRef, useState } from 'react';
import Recorder from './Recorder.jsx';
import AudioPlayer from './AudioPlayer.jsx';
import SupportSection from './SupportSection.jsx';
import { persianDigits } from './persian.js';
import './your-story.css';
import { completedActivity } from './activity.js';

const COPY = {
  fa: { title: 'داستان تو', subtitle: 'انتخاب کن و ببین قصه به کجا می‌رسد.', start: 'شروع داستان', continue: 'ادامهٔ داستان',
    choose: 'حالا تو چه کار می‌کنی؟', read: 'خودم می‌خوانم', listen: 'گوش می‌دهم', noAudio: 'هنوز خوانشی برای این صحنه منتشر نشده است.',
    restart: 'یه راه دیگه امتحان کن', list: 'داستان‌ها', path: 'قصهٔ تو',
    badge: 'نشان تو', record: 'دوست داری قصه رو با صدای خودت بخونی؟', audioLoading: 'داریم صدا رو پیدا می‌کنیم…', loading: 'داستان‌ها آماده می‌شوند…', error: 'داستان بارگذاری نشد. دوباره صفحه را باز کن.',
    empty: 'هنوز داستانی منتشر نشده است.', home: 'فهرست داستان‌ها', language: 'زبان',
    outro: 'دوست داری ببینی با انتخابی دیگر چه اتفاقی می‌افتد؟' },
  azb: { title: 'سنین قصه‌ن', subtitle: 'سئچ و گؤر قصه هارا گئدیر.', start: 'قصه‌نی باشلا', continue: 'قصه‌یه داوام ائت',
    choose: 'ایندی سن نه ائدَرسَن؟', read: 'اؤزوم اوخویورام', listen: 'دینله‌ییرَم', noAudio: 'بو صحنه اوچون هله اوخویوش یاییملانماییب.',
    restart: 'باشقا یولو سِنا', list: 'قصه‌لر', path: 'سنین قصه‌ن',
    badge: 'سنین نشانین', record: 'قصه‌نی اؤز سسین‌لَن اوخوماغا نه دئییرسن؟', audioLoading: 'سس آختاریلیر…', loading: 'قصه‌لر هازيرلانير…', error: 'قصه آچیلْمادی. صفحه‌نی یئنی‌دن آچ.',
    empty: 'هله قصه یاییملانماییب.', home: 'قصه‌لرین لیستی', language: 'دیل',
    outro: 'باشقا یول سئچسَن، گؤرَسَن نه اولار؟' },
};
const STORAGE = 'fidibo-your-story-progress-v1';
const ENDING_EMOJI = { HAPPY: '🌈', OPEN: '🌙', SAD: '🌧️', EXIT: '🍃' };
function childTitle(node, id, language) {
  if (ENDING_EMOJI[id]) return `${language === 'fa' ? 'پایان' : 'سون'} ${ENDING_EMOJI[id]}`;
  return node.title.replace(/^[SF]\d+\s*(?:[-—–:]\s*)?/, '').trim();
}
function readSaved() { try { return JSON.parse(localStorage.getItem(STORAGE) || '{}'); } catch { return {}; } }
function art(key) { return key?.startsWith('upload:') ? `/api/assets/${key.slice(7)}` : '/your-story-cover.svg'; }

export default function YourStoryApp() {
  const [language, setLanguage] = useState('fa');
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [storyId, setStoryId] = useState(null);
  const [run, setRun] = useState(null);
  const [mode, setMode] = useState('read');
  const [readings, setReadings] = useState([]);
  const [audioLoading, setAudioLoading] = useState(false);
  const recorder = useRef(null);
  const sceneHeading = useRef(null);
  const t = COPY[language];
  const story = stories.find(item => item.id === storyId);
  const node = story?.content.nodes[run?.node];
  const terminal = node && !node.choices;
  useEffect(() => { if (node) sceneHeading.current?.focus({ preventScroll: true }); }, [storyId, run?.node]);

  useEffect(() => { document.title = `${t.title} | فیدیبو کیدز`; }, [t.title]);
  useEffect(() => {
    let active = true; setLoading(true); setError('');
    fetch(`/api/your-story/stories?language=${language}`).then(async response => {
      if (!response.ok) throw new Error('load'); return response.json();
    }).then(data => { if (active) { setStories(data.stories); setLoading(false); } })
      .catch(() => { if (active) { setLoading(false); setError(t.error); } });
    return () => { active = false; };
  }, [language]);
  useEffect(() => {
    if (!story || !run) return;
    const saved = readSaved()[story.id];
    // A publication changes the wording and graph; a previous run belongs to its own version.
    if (saved?.revision === story.revision_id && story.content.nodes[saved.node]) setRun(saved);
    else if (saved?.language !== language && story.content.nodes[saved?.node]) {
      const translated = { ...saved, language, revision: story.revision_id };
      setRun(translated);
      try { localStorage.setItem(STORAGE, JSON.stringify({ ...readSaved(), [story.id]: translated })); } catch { /* private browsing */ }
    } else if (run.revision !== story.revision_id) setRun(null);
  }, [story?.revision_id, storyId]);
  useEffect(() => {
    if (!story || !node || mode !== 'listen') return;
    let active = true; setAudioLoading(true);
    fetch(`/api/your-story/readings?story_id=${encodeURIComponent(story.id)}&scene_id=${encodeURIComponent(run.node)}&language=${language}`)
      .then(r => r.json()).then(data => { if (active) { setReadings(data.readings || []); setAudioLoading(false); } })
      .catch(() => { if (active) { setReadings([]); setAudioLoading(false); } });
    return () => { active = false; };
  }, [story?.id, run?.node, language, mode]);

  function leaveAllowed() { return !recorder.current || recorder.current.canLeave(); }
  function selectStory(item) {
    if (!leaveAllowed()) return;
    const saved = readSaved()[item.id];
    const valid = saved && (saved.revision === item.revision_id || saved.language !== language) && item.content.nodes[saved.node];
    setStoryId(item.id); setRun(valid ? { ...saved, language, revision: item.revision_id } : null); setMode('read');
  }
  function begin() {
    if (!leaveAllowed()) return;
    const next = { node: 'S1', history: ['S1'], language, revision: story.revision_id };
    setRun(next); setMode('read');
    try { localStorage.setItem(STORAGE, JSON.stringify({ ...readSaved(), [story.id]: next })); } catch { /* private browsing */ }
  }
  function choose(choice) {
    if (!leaveAllowed()) return;
    const next = { ...run, node: choice.to, history: [...run.history, choice.to] };
    if (!story.content.nodes[choice.to]?.choices) completedActivity('story', `your-story:${story.id}:${choice.to}`);
    setRun(next); setMode('read'); setReadings([]);
    try { localStorage.setItem(STORAGE, JSON.stringify({ ...readSaved(), [story.id]: next })); } catch { /* private browsing */ }
    window.scrollTo({ top: 0, behavior: 'auto' });
  }
  function home() { if (leaveAllowed()) { setStoryId(null); setRun(null); setMode('read'); } }
  function switchLanguage(next) { if (next !== language && leaveAllowed()) { setLanguage(next); setMode('read'); setReadings([]); } }

  return <div className="ys-app" dir="rtl"><header className="ys-header">
    <a className="ys-brand" href="/stories"><img src="/fidibo-kids-logo.png" alt="" /><strong>فیدیبو کیدز</strong><span>/ {t.title}</span></a>
    <nav aria-label={t.home}><button onClick={home}>{t.list}</button></nav>
    <div className="ys-languages" role="group" aria-label={t.language}>
      <button aria-pressed={language === 'fa'} onClick={() => switchLanguage('fa')}>فارسی</button>
      <button aria-pressed={language === 'azb'} onClick={() => switchLanguage('azb')}>ترکی</button>
    </div></header>
    <main className="ys-main">{loading ? <p role="status">{t.loading}</p> : error ? <p role="alert">{error}</p> : !story ? <>
      <section className="ys-hero"><div><span className="ys-eyebrow">فیدیبو کیدز</span><h1>{t.title}</h1><p>{t.subtitle}</p></div>
        <img src="/your-story-cover.svg" alt="" /></section>
      <div className="ys-grid">{stories.map(item => <button className="ys-story-card" key={item.id} onClick={() => selectStory(item)}>
        <img src={art(item.content.nodes.S1.art_key)} alt="" /><span><strong>{item.content.title}</strong>
          <small>{item.content.description}</small><b>{readSaved()[item.id]?.revision === item.revision_id ? t.continue : t.start} ←</b></span>
      </button>)}</div>{!stories.length && <p>{t.empty}</p>}</> : !run ? <section className="ys-intro">
        <img src={art(story.content.nodes.S1.art_key)} alt=""/><div><span className="ys-eyebrow">{t.title}</span>
          <h1>{story.content.title}</h1><p>{story.content.description}</p><button className="ys-primary" onClick={begin}>{t.start} ←</button></div>
      </section> : node ? <><div className="ys-trail"><span>{t.path}</span><span aria-hidden="true">{run.history.map((id,i) =>
        <span className={i === run.history.length - 1 ? 'ys-trail-current' : ''} key={i}>●</span>)}</span></div>
      <article className="ys-scene"><div className="ys-visual"><img src={art(node.art_key)} alt="" /></div>
        <div className="ys-paper"><span className="ys-eyebrow">{story.content.title}</span><h1 ref={sceneHeading} tabIndex={-1}>{childTitle(node, run.node, language)}</h1>
          <div className="ys-modes" role="group" aria-label={t.listen}>
            <button aria-pressed={mode === 'read'} onClick={() => { if (leaveAllowed()) setMode('read'); }}>{t.read}</button>
            <button aria-pressed={mode === 'listen'} onClick={() => { if (leaveAllowed()) { setReadings([]); setMode('listen'); } }}>{t.listen}</button></div>
          {mode === 'listen' && (audioLoading ? <p className="ys-muted" role="status">{t.audioLoading}</p> : readings.length ?
            <AudioPlayer key={`${run.node}:${language}`} src={readings[0].audio_url} locale={language} />
            : <p className="ys-muted">{t.noAudio}</p>)}
          <p className="ys-prose">{node.text}</p>
          {terminal ? <div className="ys-terminal">
              {node.badge && <p className="ys-badge">{t.badge}: «{node.badge}»</p>}
              <p>{t.outro}</p><button className="ys-primary" onClick={begin}>{t.restart} ←</button></div>
            : <section className="ys-choices"><h2>{t.choose}</h2><div className="ys-choice-list">
              {node.choices.map((choice,index) => <button key={choice.id} onClick={() => choose(choice)}>
                <span aria-hidden="true">{persianDigits(index + 1)}</span><strong>{choice.text}</strong><b aria-hidden="true">←</b></button>)}</div></section>}
          <details className="ys-record"><summary>{t.record}</summary><Recorder ref={recorder} key={`${story.id}:${run.node}:${language}`} language={language}
            stepId={story.id} pageId={run.node} revisionId={story.revision_id} submitUrl="/api/your-story/submissions"
            draftNamespace="your-story" /></details>
        </div></article></> : <p role="alert">{t.error}</p>}</main>
    <footer className="ys-footer"><SupportSection language={language} /></footer>
  </div>;
}
