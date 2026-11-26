Documentary: "{title}"
Question the video answers: {question}

Below is the Wikipedia article "{article_title}". List 10-16 ATOMIC claims needed to tell this story in 45 seconds:
who, what, when, where, the strange situation, the escalation, numbers, consequences, and THE ANSWER.

Rules:
- Each claim is one short factual sentence in your own words, with no fact that is not in its quote.
- "wiki_quote" is the exact sentence from the article that states it (copy it exactly, character for character).
- Keep numbers, dates and names exactly as the article gives them.
- role: hook (the strangest fact), mystery (what makes it puzzling), background, escalation, payoff (the answer / explanation), detail.
- At least one "payoff" claim and one "hook" claim.
- Skip anything the article marks as disputed, alleged, legendary or uncertain.

ARTICLE:
{article}

Return JSON: {"claims": [{"text": "...", "role": "hook", "wiki_quote": "..."}]}
