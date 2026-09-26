import React, { useEffect, useState } from 'react';

export default function SupportSettings({ api }) {
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => {
    api('/admin/support-links').then(setDraft).catch(e => setError(e.message));
  }, [api]);
  async function save(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const updated = await api('/admin/support-links', { method:'PUT', body:JSON.stringify(draft) });
      setDraft(updated); setNotice('لینک‌های حمایت ذخیره شدند.');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  const change = (key, value) => setDraft(old => ({...old, [key]:value}));
  if (!draft) return <div className="u-editor">{error ? <p role="alert" className="u-error">{error}</p> : <p>در حال بارگذاری…</p>}</div>;
  return <form className="support-settings u-editor" onSubmit={save} dir="rtl">
    <h2>پیوندهای حمایت</h2>
    <p>هر گزینه فقط بعد از ثبت اطلاعات لازم در صفحهٔ حمایت فعال می‌شود. پیوندها باید با https:// آغاز شوند.</p>
    <label>لینک درگاه حمایت<input type="url" inputMode="url" placeholder="https://example.com/donate"
      value={draft.gateway_url} onChange={e=>change('gateway_url',e.target.value)} /></label>
    <label>لینک پرداخت مستقیم<input type="url" inputMode="url" placeholder="https://example.com/direct"
      value={draft.direct_url} onChange={e=>change('direct_url',e.target.value)} /></label>
    <label>شماره کارت پرداخت مستقیم<input inputMode="numeric" autoComplete="off" maxLength={24}
      placeholder="۱۶ رقم" value={draft.card_number} onChange={e=>change('card_number',e.target.value)} /></label>
    <p>با کلیک روی «پرداخت مستقیم»، شماره کارت در کلیپ‌بورد کاربر کپی می‌شود و لینک در زبانهٔ تازه باز می‌شود. برای فعال شدن این گزینه هم لینک و هم شماره کارت را ثبت کنید.</p>
    {error && <p role="alert" className="u-error">{error}</p>}
    {notice && <p role="status" className="u-success">{notice}</p>}
    <button className="u-primary" disabled={busy}>{busy ? 'در حال ذخیره…' : 'ذخیرهٔ پیوندها'}</button>
  </form>;
}
