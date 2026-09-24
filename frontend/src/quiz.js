// One question from each available category, with fresh answer positions.
const CATEGORIES = ['recall', 'infer', 'think'];

function randomIndex(length, random) { return Math.floor(random() * length); }

function shuffled(values, random) {
  const result = [...values];
  for (let i = result.length - 1; i > 0; i--) {
    const j = randomIndex(i + 1, random);
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export function makeQuiz(questions, previous = {}, random = Math.random) {
  const items = [];
  for (const category of CATEGORIES) {
    const candidates = questions.filter((question) => question.category === category);
    if (!candidates.length) continue;
    const alternatives = candidates.filter((question) => question.id !== previous.ids?.[category]);
    const question = (alternatives.length ? alternatives : candidates)[randomIndex(
      alternatives.length || candidates.length, random
    )];
    let optionIds = shuffled(question.options.map((option) => option.id), random);
    const previousPosition = previous.positions?.[question.id];
    if (optionIds.length > 1 && optionIds.indexOf(question.answer_id) === previousPosition) {
      optionIds = [...optionIds.slice(1), optionIds[0]];
    }
    items.push({ id: question.id, category, optionIds });
  }
  return {
    items,
    memory: {
      ids: Object.fromEntries(items.map((item) => [item.category, item.id])),
      positions: Object.fromEntries(items.map((item) => [
        item.id, item.optionIds.indexOf(questions.find((q) => q.id === item.id).answer_id),
      ])),
    },
  };
}
