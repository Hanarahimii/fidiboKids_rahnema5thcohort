import React, { useEffect, useState } from 'react';

const TEXT = {
  fa: {
    eyebrow: 'برای بزرگ‌ترها', title: 'از ساخت قصه‌های بعدی حمایت کنید',
    body: 'اگر از این تجربه خوشتان آمد، یکی از راه‌های حمایت را انتخاب کنید.',
    gateway: 'درگاه حمایت', gatewayDetail: 'درگاه برای حمایت و دونیشن (۵٪ کارمزد درگاه به‌طور خودکار کسر می‌شود)',
    direct: 'پرداخت با بلو', directDetail: 'پرداخت مستقیم از طریق بلو',
    card: 'شماره کارت', cardDetail: 'شماره کارت در کلیپ‌بورد شما ذخیره می‌شود — به نام حنانه رحیمی زارچی',
    missing: 'لینک‌های حمایت هنوز توسط کارشناس ثبت نشده‌اند.', copied: 'شماره کارت کپی شد.',
    copyFailed: 'کپی خودکار انجام نشد؛ شماره کارت را از پنل حمایت بردارید.',
  },
  azb: {
    eyebrow: 'بؤیوکلر اوچون', title: 'یئنی قصه‌لرین یارانماسینا دستک اولون',
    body: 'بو تجربه‌نی بَیَندینیزسه، دستک یوللاریندان بیرینی سئچین.',
    gateway: 'دستک درگاهی', gatewayDetail: 'دستک و دونیشن درگاهی (۵٪ درگاه کارمزدی خودکار چیخیلیر)',
    direct: 'بلو ایله اؤدَمه', directDetail: 'بلو آراسی ایله بیراواسطه اؤدَمه',
    card: 'کارت نومره‌سی', cardDetail: 'کارت نومره‌سی کلیپ‌بورددا ساخلالانیر — حنانه رحیمی زارچی آدینا',
    missing: 'دستک لینک‌لری هله ثبت اولونماییب.', copied: 'کارت نومره‌سی کپی اولدو.',
    copyFailed: 'کپی خودکار انجام نشد؛ شماره کارت را از پنل حمایت بردارید.',
  },
};

export default function SupportSection({ language, context = 'story' }) {
  const [links, setLinks] = useState(null);
  const [status, setStatus] = useState('');
  useEffect(() => {
    let active = true;
    fetch('/api/support-links', { cache: 'no-store' }).then(response => {
      if (!response.ok) throw Error('load');
      return response.json();
    }).then(data => { if (active) setLinks(data); }).catch(() => { if (active) setLinks({gateway_url:'', direct_url:'', card_number:''}); });
    return () => { active = false; };
  }, []);
  const t = TEXT[language] || TEXT.fa;
  const heading = context === 'discovery'
    ? (language === 'azb' ? 'یئنی کشف تجربه‌لرینه دستک اولون' : 'از ساخت تجربه‌های تازهٔ کشف حمایت کنید') : t.title;
  const options = [
    {key:'gateway', title:t.gateway, detail:t.gatewayDetail, url:links?.gateway_url},
    {key:'direct', title:t.direct, detail:t.directDetail, url:links?.direct_url},
    {key:'card', title:t.card, detail:t.cardDetail, url:links?.card_number ? '#support-card' : '', copy:true},
  ];
  function copyCard(event) {
    event.preventDefault();
    if (!links?.card_number) return;
    if (!navigator.clipboard?.writeText) { setStatus(t.copyFailed); return; }
    navigator.clipboard.writeText(links.card_number).then(() => setStatus(t.copied)).catch(() => setStatus(t.copyFailed));
  }
  return <section className="support-section" aria-labelledby="support-heading">
    <div className="support-intro"><span className="cover-kicker">{t.eyebrow}</span>
      <h2 id="support-heading">{heading}</h2><p>{t.body}</p></div>
    <div className="support-link-options">{options.map(option => option.url
      ? <a key={option.key} className="support-link-option" href={option.url} target={option.copy ? undefined : "_blank"} rel={option.copy ? undefined : "noopener noreferrer"}
          onClick={option.copy ? copyCard : undefined}>
          <span><strong>{option.title}</strong><small>{option.detail}</small></span><span aria-hidden="true">{option.copy ? '⧉' : '↗'}</span></a>
      : <div key={option.key} className="support-link-option unavailable" aria-disabled="true">
          <span><strong>{option.title}</strong><small>{option.detail}</small></span><span aria-hidden="true">—</span></div>)}</div>
    {!options.some(option => option.url) && <p className="support-pending">{t.missing}</p>}
    {status && <p className="support-pending" role="status">{status}</p>}
  </section>;
}
