import React, { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import { persianDigits } from './persian.js';

export function displayTime(seconds) {
  const safe = Number.isFinite(seconds) && seconds >= 0 ? Math.floor(seconds) : 0;
  return `${persianDigits(Math.floor(safe / 60))}:${persianDigits(String(safe % 60).padStart(2, '0'))}`;
}

/** Localized controls while preserving the underlying HTMLAudioElement for continuation. */
const AudioPlayer = forwardRef(function AudioPlayer({ src, onPlay, onError, label = 'پخش صدا' }, ref) {
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

  return <div className="fd-audio" role="group" aria-label={label}>
    <audio ref={element} src={src} preload="metadata" aria-hidden="true" tabIndex={-1}
      onLoadedMetadata={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
      onDurationChange={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
      onTimeUpdate={(event) => setPosition(event.currentTarget.currentTime)}
      onPlay={() => { setPlaying(true); setFailure(false); onPlay?.(); }}
      onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)}
      onError={() => { setFailure(true); setPlaying(false); onError?.(); }} />
    <button type="button" className="fd-audio-toggle" onClick={toggle}>{playing ? 'مکث' : 'پخش'}</button>
    <input type="range" aria-label="جابه‌جایی در صدا" min="0" max={duration || 1} step="0.1"
      value={Math.min(position, duration || 1)} disabled={!duration} aria-valuetext={displayTime(position)}
      onChange={(event) => { if (element.current) element.current.currentTime = Number(event.target.value); }} />
    <span className="fd-audio-time" aria-label={`زمان پخش: ${displayTime(position)} از ${displayTime(duration)}`}>
      {displayTime(position)} / {displayTime(duration)}</span>
    {failure && <p className="fd-audio-error" role="alert">صدا پخش نشد. دوباره تلاش کنید.</p>}
  </div>;
});

export default AudioPlayer;
