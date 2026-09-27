import React, { useState, useEffect } from 'react';

const AMOUNTS = [100_000, 200_000, 300_000];
const TEXT = {
  fa: {
    eyebrow: 'برای بزرگ‌ترها', title: 'از ساخت قصه‌های بعدی حمایت کنید',
    body: 'اگر از این تجربه خوشتان آمد و دوست دارید کتاب‌های تعاملی بیشتری برای کودکان ساخته شود، مبلغ حمایتی دلخواهتان را انتخاب کنید.',
    custom: 'مبلغ دلخواه', example: 'مثلاً ۱۵۰٬۰۰۰', toman: 'تومان', selected: 'مبلغ انتخابی',
    invalid: 'لطفاً مبلغی بزرگ‌تر از صفر وارد کنید.',
    button: 'حمایت از ادامهٔ پروژه', pending: 'درگاه پرداخت هنوز متصل نشده است؛ فعلاً هیچ مبلغی دریافت نمی‌شود.',
  },
  azb: {
    eyebrow: 'بؤیوکلر اوچون', title: 'یئنی قصه‌لرین یارانماسینا دستک اولون',
    body: 'بو تجربه‌نی بَیَندینیزسه و اوشاقلار اوچون داها چوخ اینتراکتیو کیتاب یارانماسینی ایسته‌ییرسینیزسه، دستک مبلغینی سئچین.',
    custom: 'اؤز مبلغینیز', example: 'مَسَلَن ۱۵۰٬۰۰۰', toman: 'تومن', selected: 'سئچیلن مبلغ',
    invalid: 'لطفاً صفیردان بؤیوک مبلغ یازین.',
    button: 'پروژه‌یه دستک اول', pending: 'اؤدَمه درگاهی هَنوز قوشولماییب؛ ایندی هیچ بیر مبلغ آلینمیر.',
  },
};

function numberFromInput(value) {
  const digits = String(value).replace(/[۰-۹]/g, (ch) => String(ch.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (ch) => String(ch.charCodeAt(0) - 0x0660))
    .replace(/[\s,،٬]/g, '');
  return /^\d+$/.test(digits) && Number.isSafeInteger(Number(digits)) ? Number(digits) : 0;
}

export default function SupportSection({ language, context = 'story' }) {
  const [paymentUrl,setPaymentUrl] = useState('');
  useEffect(()=>{fetch('/api/edition').then(r=>r.json()).then(d=>setPaymentUrl(d.donation_url||'')).catch(()=>{});},[]);
  const [selected, setSelected] = useState(100_000);
  const [custom, setCustom] = useState('');
  const t = TEXT[language] || TEXT.fa;
  const heading = context === 'discovery'
    ? (language === 'azb' ? 'یئنی کشف تجربه‌لرینه دستک اولون' : 'از ساخت تجربه‌های تازهٔ کشف حمایت کنید') : t.title;
  const description = context === 'discovery'
    ? (language === 'azb'
      ? 'بو تجربه‌نی بَیَندینیزسه و اوشاقلار اوچون داها چوخ کشف موضوعو ایسته‌ییرسینیزسه، دستک مبلغینی سئچین.'
      : 'اگر از این تجربه خوشتان آمد و دوست دارید موضوع‌های بیشتری برای کشف و یادگیری کودکان ساخته شود، مبلغ حمایتی دلخواهتان را انتخاب کنید.')
    : t.body;
  const amount = selected === 'custom' ? numberFromInput(custom) : selected;
  const format = (value) => new Intl.NumberFormat('fa-IR').format(value);
  return <section className="support-section" aria-labelledby="support-heading">
    <div className="support-intro"><span className="cover-kicker">{t.eyebrow}</span>
      <h2 id="support-heading">{heading}</h2><p>{description}</p></div>
    <div className="support-choices" role="group" aria-label={t.selected}>
      {AMOUNTS.map((value) => <button key={value} type="button" aria-pressed={selected === value}
        className={selected === value ? 'active' : ''} onClick={() => setSelected(value)}>
        {format(value)} {t.toman}</button>)}
      <button type="button" aria-pressed={selected === 'custom'}
        className={selected === 'custom' ? 'active' : ''} onClick={() => setSelected('custom')}>{t.custom}</button>
    </div>
    {selected === 'custom' && <label className="support-custom">{t.custom} ({t.toman})
      <input inputMode="numeric" type="text" value={custom} aria-describedby="support-status"
        onChange={(event) => setCustom(event.target.value)} placeholder={t.example} />
    </label>}
    <div className="support-action"><span aria-live="polite">{amount > 0
      ? `${t.selected}: ${format(amount)} ${t.toman}` : t.invalid}</span>
      <button className="book-primary" type="button" disabled={!paymentUrl || amount<=0} onClick={()=>location.assign(paymentUrl)}>{t.button}</button></div>
    <p id="support-status" className="support-pending" role="status">{paymentUrl?'مبلغ نهایی را در صفحهٔ پرداخت انتخاب و تأیید کنید. پرداخت خارج از کیدز انجام می‌شود.':t.pending}</p>
  </section>;
}
