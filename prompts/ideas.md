Pitch {n} documentary ideas.

Explore these areas, and also go beyond them:
{categories}

Each idea must be:
- TRUE and well documented (it has its own English Wikipedia article that cites outside sources).
- Genuinely surprising: a contradiction, an impossible-seeming situation, an unexpected consequence, a bizarre documented fact.
- Answerable: there is a satisfying, factual explanation or outcome to reveal at the end.
- Highly visual in flat 2D cartoon: places, objects, people or animals that can be drawn, and room for goofy visual exaggeration
  while the facts stay serious.
- Different from these past videos (no repeats, no near-repeats):
{avoid}

Hook rules: the hook is the first spoken line, at most {hook_words} words, present tense, no greeting, no "did you know",
no question that can be answered yes/no. Start with the strangest true thing. Hook patterns to vary: {patterns}.

Return JSON:
{"ideas": [{
  "title": "5-10 words, concrete subject, a superlative or contradiction, no colon, no question mark",
  "question": "the one plain question the video answers",
  "hook": "first line, max {hook_words} words",
  "hook_pattern": "one of the patterns",
  "payoff": "the factual answer revealed at the end, one sentence",
  "category": "one of the areas above, or a short new one",
  "wikipedia_title": "the exact English Wikipedia article title",
  "search": "a short search query for the article",
  "why_visual": "one sentence: what we will SEE",
  "visual_metaphors": ["2-3 drawable metaphors or goofy visual gags for the suspense part"]
}]}
