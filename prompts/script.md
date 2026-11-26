Write the script.

Topic: {title}
The question: {question}
Suggested hook: {hook}
The answer (payoff): {payoff}
Visual gags you may use: {metaphors}

VERIFIED CLAIMS (the only facts you may use; cite their ids on every line that uses them):
{claims}

STRUCTURE (one line = one or two short sentences; sections in this order):
1. hook (exactly 1 line, max {hook_words} words, ~0-2 s): present tense, the strangest true fact. No greeting, no
   "did you know", no channel talk. A person in a place, or one brutal number.
2. suspense (2-4 lines, ~2-10 s): something unusual is happening, but DO NOT explain why. Clues, contradictions,
   "But here's the strange part." Give a big number a tiny human-scale jab. Make the question obvious.
3. build (2-4 lines, ~10-20 s): who, what, when, where. Start small and human; a bare date or place helps.
4. escalation (2-4 lines, ~20-35 s): events, evidence, consequences, contradictions. Include ONE deadpan skit here or
   in the build: 2-4 lines of dialogue between two characters, about 4 words each, speaker "A" or "B", punchline last
   and shortest (e.g. "How many did we hit?" / "Define hit." / "Out of?" / "Don't ask.").
5. reveal (1-3 lines, ~35-45 s): THE ANSWER, using the payoff claim. It must answer the hook directly.
6. ending (1 line): a memorable close that returns to the opening image (reuse a word from the hook). No summary,
   no moral, no "subscribe", no question to the audience.

VOICE (from the house style):
- Short sentences: median about 6 words, almost all under 12. Fragments carry weight: "Too late." "Nobody laughed."
- Present tense for scenes, past tense for results. Words a 12-year-old knows; define any technical term in one sentence.
- One sentence, one picture: every sentence names something that can be drawn.
- Write numbers and years as digits exactly as in the claims (1932, 20,000, $2.3 million). Every number must come from a claim you cite.
- Mark 2-4 lines as "card": true: the twist, the complication, the hardest line (max 9 words; they become black text cards).
- Total {words_min}-{words_max} words (40-50 seconds at a natural pace).
- Title: 5-10 words, the concrete subject + a superlative or contradiction, no colon, no question mark, honest.
- hero_object: ONE drawable object that stands for the whole story (it appears in every section and ends the video).

Return JSON:
{"title": "...", "hero_object": "...",
 "lines": [{"section": "hook", "speaker": "narrator", "text": "...", "claims": ["C1"], "card": false}]}
