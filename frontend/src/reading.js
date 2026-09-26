/** Keep one Reading ordinal across pages and map it to the selected language. */
export function readingForLanguage(readingId, language) {
  const match = /^(fa|azb)_([1-4])$/.exec(readingId || '');
  return match && ['fa', 'azb'].includes(language) ? `${language}_${match[2]}` : null;
}

export function resolvePlayback(readingId, available, continuePlaying = false) {
  const selected = available.find((item) => item.id === readingId) || null;
  return { selected, missing: Boolean(readingId && !selected),
    shouldPlay: Boolean(selected && continuePlaying) };
}
