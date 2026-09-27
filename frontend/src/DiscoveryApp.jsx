import React, { useEffect, useRef, useState } from 'react';
import Recorder from './Recorder.jsx';
import AudioPlayer from './AudioPlayer.jsx';
import SupportSection from './SupportSection.jsx';
import { persianDigits } from './persian.js';
import './discovery.css';
import { completedActivity } from './activity.js';

const T = {
  fa: { eyebrow: 'فیدیبو کیدز · کشف', title: 'دنیای کشف', subtitle: 'می‌پرسم، صبر می‌کنم، خیال می‌کنم.',
    choose: 'یک موضوع برای کشف انتخاب کن', go: 'شروع کن', back: 'بازگشت', home: 'موضوع‌ها',
    collection: 'نشان‌های من', intro: 'یک اتفاق کوچک', check: 'حالا ببینیم فهمیدی',
    next: 'بعدی', continue: 'برو به انتخاب خودت', correct: 'آفرین، درست گفتی!',
    wrong: 'یک بار دیگر فکر کن و گزینهٔ دیگری را انتخاب کن.',
    personal: 'تو کدام را انتخاب می‌کنی؟', choiceHelp: 'اینجا پاسخ درست یا غلطی وجود ندارد. هر شاخه را می‌توانی تجربه کنی.',
    story: 'ماجرای تو', done: 'این نشان مال توست!', other: 'شاخهٔ دیگری را هم ببین',
    topics: 'موضوع بعدی', badges: 'نشان‌های به‌دست‌آمده', emptyBadges: 'هنوز نشانی نگرفته‌ای. یک شاخه را تا پایان برو.',
    listen: 'گوش می‌دهم', read: 'خودم می‌خوانم', audioEmpty: 'هنوز خوانشی برای این بخش منتشر نشده است.',
    loading: 'در حال آماده کردن کشف…', error: 'محتوا باز نشد. صفحه را دوباره بارگذاری کن.',
    allSeen: 'تجربه‌شده', storyNote: 'با رسیدن به انتهای این شاخه، نشانش را می‌گیری.',
    noTopics: 'هنوز موضوعی منتشر نشده است.',
  },
  azb: { eyebrow: 'فیدیبو کیدز · کشف', title: 'کشف دنیاسی', subtitle: 'سوروشورام، گؤزله‌ییرَم، خیال ائدیرَم.',
    choose: 'کشف اوچون بیر موضوع سئچ', go: 'باشلا', back: 'گَری قاییت', home: 'موضوعلار',
    collection: 'منیم نشانلاریم', intro: 'بالاجا بیر اولای', check: 'گَل گؤرَک نَه اؤیرَندین',
    next: 'سونراکی', continue: 'اؤز سئچیمینه گئت', correct: 'آفرین، دوغرو جواب وئردین!',
    wrong: 'بیر ده دؤشون و باشقا سئچیمه باخ.',
    personal: 'سن هانسی‌سینی سئچَرسَن؟', choiceHelp: 'بورادا دوغرو یا یانلیش جواب یوخدو. هَر شاخه‌نی گؤرَ بیلَرسَن.',
    story: 'سنین ماجران', done: 'بو نشان سنین‌دیر!', other: 'باشقا شاخه‌یه ده باخ',
    topics: 'سونراکی موضوع', badges: 'قازاندیغین نشانلار', emptyBadges: 'هله نشانین یوخدو. بیر شاخه‌نین سونونا گئت.',
    listen: 'دینله‌ییرَم', read: 'اؤزوم اوخویورام', audioEmpty: 'بو بؤلوم اوچون هله اوخویوش یاییملانماییب.',
    loading: 'کشف هازیرلانیر…', error: 'محتوا آچیلمادی. صفحه‌نی یئنی‌دن آچ.',
    allSeen: 'گؤرولوب', storyNote: 'بو شاخه‌نین سونونا چاتاندا نشانینی آلاجاقسان.',
    noTopics: 'هله موضوع یاییملانماییب.',
  },
};

const ICON = { curiosity: '◌', uncertainty: '◇', imagination: '✧' };
function art(key, topicId, branchId) { return key?.startsWith('upload:') ? `/api/assets/${key.slice(7)}`
  : `/discovery-art/${['curiosity','uncertainty','imagination'].includes(topicId) ? topicId : 'curiosity'}${['a','b','c'].includes(branchId) ? `-${branchId}` : ''}.svg`; }
function loadProgress() {
  try { return JSON.parse(localStorage.getItem('fidibo-discovery-progress') || '{}'); }
  catch { return {}; }
}
function loadResponses() {
  try { return JSON.parse(localStorage.getItem('fidibo-discovery-responses') || '{}'); }
  catch { return {}; }
}

export default function DiscoveryApp() {
  const [language, setLanguage] = useState(() => {
    try { return localStorage.getItem('book-language') === 'azb' ? 'azb' : 'fa'; }
    catch { return 'fa'; }
  });
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [screen, setScreen] = useState(new URLSearchParams(location.search).has('topic')?'intro':'home');
  const [topicId, setTopicId] = useState(new URLSearchParams(location.search).get('topic'));
  const [branchId, setBranchId] = useState(null);
  const [quizIndex, setQuizIndex] = useState(0);
  const [answer, setAnswer] = useState('');
  const [mode, setMode] = useState('read');
  const [readings, setReadings] = useState([]);
  const [progress, setProgress] = useState(loadProgress);
  const [, setResponses] = useState(loadResponses);
  const recorder = useRef(null);
  const t = T[language];
  const topic = topics.find((x) => x.id === topicId);
  const branch = topic?.content.branches.find((x) => x.id === branchId);
  useEffect(()=>{document.title=(topic?.content.title||'کشف')+' | فیدیبو کیدز';},[topic?.content.title]);
  const sceneId = screen === 'intro' ? 'intro' : screen === 'story' ? branchId : null;

  useEffect(() => {
    document.title = 'کشف | فیدیبو کیدز';
    const icon = document.querySelector('link[rel="icon"]'); if (icon) icon.href = '/discovery-favicon.svg';
  }, []);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(false); setReadings([]);
    fetch(`/api/discovery/topics?language=${language}`).then((res) => {
      if (!res.ok) throw Error('load'); return res.json();
    }).then((data) => { if (active) { setTopics(data.topics); setLoading(false); } })
      .catch(() => { if (active) { setError(true); setLoading(false); } });
    try { localStorage.setItem('book-language',language); } catch { /* private mode */ }
    return () => { active = false; };
  }, [language]);
  useEffect(() => {
    let active = true; setReadings([]);
    if (!topic || !sceneId || mode !== 'listen') return;
    fetch(`/api/discovery/readings?topic_id=${encodeURIComponent(topic.id)}&scene_id=${encodeURIComponent(sceneId)}&language=${language}`)
      .then((r) => r.json()).then((data) => { if (active) setReadings(data.readings || []); })
      .catch(() => { if (active) setReadings([]); });
    return () => { active = false; };
  }, [topic?.id, topic?.revision_id, sceneId, mode, language]);

  function navigate(next, nextTopic = topicId, nextBranch = branchId) {
    if (recorder.current && !recorder.current.canLeave()) return;
    setTopicId(nextTopic); setBranchId(nextBranch); setQuizIndex(0);setAnswer('');setMode('read');setScreen(next);
  }
  function changeLanguage(next) {
    if (next === language || (recorder.current && !recorder.current.canLeave())) return;
    setLanguage(next);setMode('read');setAnswer('');
  }
  function startQuiz(which) { navigate(which); }
  function remember(key,value) {
    setResponses(old=>{const next={...old,[key]:typeof value==='function'?value(old[key]):value};
      try { localStorage.setItem('fidibo-discovery-responses',JSON.stringify(next)); } catch { /* local-only prototype */ }
      return next;});
  }
  function chooseBranch(id) { remember(`${topicId}:choice`,id); navigate('story',topicId,id); }
  function advance(questions) {
    if (quizIndex + 1 < questions.length) { setQuizIndex(quizIndex+1);setAnswer('');return; }
    if (screen === 'intro_quiz') navigate('choices');
    else {
      const previous = progress[topicId] || [];
      const updated = {...progress,[topicId]:[...new Set([...previous,branchId])]};
      setProgress(updated);
      completedActivity('discovery', `${topicId}:${branchId}`);
      try { localStorage.setItem('fidibo-discovery-progress',JSON.stringify(updated)); } catch { /* private mode */ }
      navigate('badge');
    }
  }
  function sceneView(scene, intro) {
    const key = `${topic.id}:${sceneId}:${language}`;
    return <article className="discover-scene"><div className="discover-visual">
      <img src={art(scene.art_key,topic.id,intro?null:branchId)} alt={intro ? topic.content.title : branch.label} />
      <span>{intro ? t.intro : t.story}</span></div>
      <div className="discover-prose"><span className="discover-overline">{topic.content.title}</span>
        <h1>{intro ? t.intro : branch.label}</h1><p>{scene.text}</p>
        <div className="discover-tabs" role="group" aria-label={t.listen}>
          <button className={mode==='read'?'active':''} onClick={() => setMode('read')}>{t.read}</button>
          <button className={mode==='listen'?'active':''} onClick={() => {
            if (recorder.current && !recorder.current.canLeave()) return; setMode('listen');
          }}>{t.listen}</button></div>
        {mode==='read' ? <details className="u-record-drawer"><summary>{language==='fa'?'دوست داری این بخش رو با صدای خودت بخونی؟':'بو بؤلومو اؤز سسینله اوخوماق ایسته‌یرسن؟'}</summary><Recorder ref={recorder} key={key} language={language} stepId={topic.id}
          pageId={sceneId} revisionId={topic.revision_id} submitUrl="/api/discovery/submissions"
          draftNamespace="discovery" /></details>
          : readings.length ? <AudioPlayer key={`${key}:audio`} src={readings[0].audio_url} locale={language} />
            : <p className="discover-empty">{t.audioEmpty}</p>}
        <div className="discover-nav"><button onClick={() => navigate(intro?'home':'choices')}>→ {t.back}</button>
          <button className="discover-primary" onClick={() => startQuiz(intro?'intro_quiz':'branch_quiz')}>{t.check} ←</button></div>
      </div></article>;
  }
  function quizView(questions, scene) {
    const q = questions[quizIndex];
    if (!q) return null;
    return <article className="discover-quiz"><div className="discover-quiz-head"><span>{topic.content.title}</span>
      <span>{persianDigits(quizIndex+1)} / {persianDigits(questions.length)}</span></div>
      <div className="discover-quiz-layout"><img src={art(q.art_key || scene.art_key,topic.id,screen==='intro_quiz'?null:branchId)} alt={q.prompt} />
        <div><h1>{q.prompt}</h1><div className="discover-options">{q.options.map((option) => <button
          key={option.id} type="button" aria-pressed={answer===option.id} className={answer===option.id?'selected':''}
          onClick={() => {setAnswer(option.id); const key=`${topicId}:${screen==='intro_quiz'?'intro':branchId}:${q.id}`;
            remember(key,(previous)=>({option_id:option.id,correct:option.id===q.answer_id,
              attempts:(previous?.attempts||0)+1}));}}>
            {option.art_key && <img src={art(option.art_key,topic.id,branchId)} alt="" />}<span>{option.text}</span></button>)}</div>
        {answer && <div className={`discover-feedback ${answer===q.answer_id?'right':'retry'}`} role="status">
          {answer===q.answer_id?t.correct:t.wrong}</div>}
        <div className="discover-nav"><button onClick={() => navigate(screen==='intro_quiz'?'intro':'story')}>→ {t.back}</button>
          <button className="discover-primary" disabled={answer!==q.answer_id} onClick={() => advance(questions)}>
            {quizIndex+1===questions.length?(screen==='intro_quiz'?t.continue:t.done):t.next} ←</button></div></div></div>
    </article>;
  }
  return <div className="discover-app" dir="rtl"><header className="discover-header"><a href="/child" className="discover-brand"><img src="/fidibo-kids-logo.png" alt="" /><strong>فیدیبو کیدز</strong><span>/ {t.title}</span></a>
    <div className="discover-header-links"><button onClick={() => navigate('home',null,null)}>{t.home}</button>
      <button onClick={() => navigate('collection')}>{t.collection}</button></div>
    <div className="discover-language" role="group" aria-label={language==='fa'?'زبان':'دیل'}>
      <button aria-pressed={language==='fa'} onClick={() => changeLanguage('fa')}>فارسی</button>
      <button aria-pressed={language==='azb'} onClick={() => changeLanguage('azb')}>ترکی</button></div></header>
    <main className="discover-main">{loading?<p>{t.loading}</p>:error?<p role="alert">{t.error}</p>:<>
      {screen==='home' && <><section className="discover-hero"><span className="discover-overline">{t.eyebrow}</span>
        <h1>{t.title}</h1><p>{t.subtitle}</p><p className="discover-hero-hint">{t.choose}</p></section>
        <div className="discover-grid">{topics.map((item) => <button key={item.id} className="discover-topic"
          onClick={() => navigate('intro',item.id,null)}><div className="discover-topic-art"><img
            src={art(item.content.intro.art_key,item.id)} alt="" /></div><span className="discover-overline">
            {persianDigits(item.position)} / {persianDigits(topics.length)}</span><h2>{item.content.title}</h2>
          <span>{(progress[item.id]||[]).length>0?`${t.allSeen} · ${persianDigits(progress[item.id].length)}`:t.go} ←</span></button>)}</div>
        {!topics.length&&<p>{t.noTopics}</p>}</>}
      {screen==='intro'&&topic&&sceneView(topic.content.intro,true)}
      {screen==='intro_quiz'&&topic&&quizView(topic.content.intro_questions,topic.content.intro)}
      {screen==='choices'&&topic&&<section className="discover-choices"><span className="discover-overline">{topic.content.title}</span>
        <h1>{topic.content.choice_prompt}</h1><p>{t.choiceHelp}</p><div className="discover-grid">
          {topic.content.branches.map((item,index)=><button className="discover-choice" key={item.id}
            onClick={()=>chooseBranch(item.id)}><img src={art(item.art_key,topic.id,item.id)} alt="" />
            <span>{persianDigits(index+1)}</span><strong>{item.label}</strong>
            {(progress[topic.id]||[]).includes(item.id)&&<small>{t.allSeen} ✓</small>}</button>)}
        </div><button className="discover-quiet" onClick={()=>navigate('home')}>→ {t.home}</button></section>}
      {screen==='story'&&topic&&branch&&sceneView(branch,false)}
      {screen==='branch_quiz'&&topic&&branch&&quizView(branch.questions,branch)}
      {screen==='badge'&&topic&&branch&&<section className="discover-award"><div className="discover-award-icon">
        {branch.badge.art_key?<img src={art(branch.badge.art_key,topic.id)} alt=""/>:ICON[topic.id]||'✧'}</div>
        <span>{t.done}</span><h1>{branch.badge.title}</h1><p>{topic.content.badge.title}</p>
        <div className="discover-nav"><button onClick={()=>navigate('collection')}>{t.collection}</button>
          <button className="discover-primary" onClick={()=>navigate('choices')}>{t.other} ←</button></div></section>}
      {screen==='collection'&&<section className="discover-collection"><span className="discover-overline">{t.title}</span>
        <h1>{t.badges}</h1>{topics.some((item)=>(progress[item.id]||[]).length)?topics.map((item)=>
          (progress[item.id]||[]).length>0&&<div className="discover-badge-group" key={item.id}><h2>
            {item.content.title} · {item.content.badge.title}</h2><div className="discover-badge-list">
            {item.content.branches.filter((b)=>(progress[item.id]||[]).includes(b.id)).map((b)=><button
              key={b.id} onClick={()=>navigate('badge',item.id,b.id)}><span>{b.badge.art_key?<img src={art(b.badge.art_key,item.id)} alt=""/>:ICON[item.id]||'✧'}</span>
              <strong>{b.badge.title}</strong></button>)}</div></div>) :<p>{t.emptyBadges}</p>}
          <button className="discover-quiet" onClick={()=>navigate('home')}>→ {t.home}</button></section>}
    </>}</main><footer className="discover-footer"><SupportSection language={language} context="discovery"/>
      <p>{t.eyebrow}</p></footer></div>;
}
