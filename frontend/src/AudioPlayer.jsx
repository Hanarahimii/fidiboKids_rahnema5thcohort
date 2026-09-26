import React, { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import { persianDigits } from './persian.js';

export function displayTime(seconds) {
  const safe = Number.isFinite(seconds) && seconds >= 0 ? Math.floor(seconds) : 0;
  return `${persianDigits(Math.floor(safe / 60))}:${persianDigits(String(safe % 60).padStart(2, '0'))}`;
}

const LABEL = {
  fa: { play: 'پخش', pause: 'مکث', seek: 'جابه‌جایی در صدا', time: 'زمان پخش', of: 'از',
    error: 'صدا پخش نشد. دوباره تلاش کنید.' },
  azb: { play: 'دینله', pause: 'دایان', seek: 'سس‌ده یئری دَییش', time: 'سسین واختی', of: 'دان',
    error: 'سس پخش اولمادی. بیر ده سِنا.' },
};

/** Localized controls while preserving the underlying HTMLAudioElement for continuation. */
const AudioPlayer = forwardRef(function AudioPlayer({ src, onPlay, onError, label, locale = 'fa' }, ref) {
  const t = LABEL[locale] || LABEL.fa;
  const element = useRef(null);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [failure, setFailure] = useState(false);
  useImperativeHandle(ref, () => element.current, []);

  async function toggle() {
    if (!element.current) return;
    if (!element.current.paused) { element.current.pause(); return; }
    setFailure(false);
    try { await element.current.play(); }
    catch { setFailure(true); }
  }

  return <div className="fd-audio" role="group" aria-label={label || t.play}>
    <audio ref={element} src={src} preload="metadata" aria-hidden="true" tabIndex={-1}
      onLoadedMetadata={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
      onDurationChange={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
      onTimeUpdate={(event) => setPosition(event.currentTarget.currentTime)}
      onPlay={() => { setPlaying(true); setFailure(false); onPlay?.(); }}
      onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)}
      onError={() => { setFailure(true); setPlaying(false); onError?.(); }} />
    <button type="button" className="fd-audio-toggle" onClick={toggle}>{playing ? t.pause : t.play}</button>
    <input type="range" aria-label={t.seek} min="0" max={duration || 1} step="0.1"
      value={Math.min(position, duration || 1)} disabled={!duration} aria-valuetext={displayTime(position)}
      onChange={(event) => { if (element.current) element.current.currentTime = Number(event.target.value); }} />
    <span className="fd-audio-time" aria-label={`${t.time}: ${displayTime(position)} ${t.of} ${displayTime(duration)}`}>
      {displayTime(position)} / {displayTime(duration)}</span>
    {failure && <p className="fd-audio-error" role="alert">{t.error}</p>}
  </div>;
});

export default AudioPlayer;
