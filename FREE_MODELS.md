# Free models (FreeLLMAPI)

Production never calls Claude, Anthropic, OpenAI paid APIs or any paid service. All AI work goes through
**FreeLLMAPI**, started *inside* each Make job (`tools/start_freellmapi.sh`) from the `FREELLMAPI_KEYS` secret. It only
holds the free-tier keys you give it and fails over between them. Same architecture as roblox-stories-bot and shorts-bot.

## Roles (config.yaml `freellm.roles`)

| Role | Used for | Calls per video (typical) |
|---|---|---|
| ideator | 10 documentary pitches | 1 |
| critic | idea scores; script review | 1 + 1-3 |
| research | claim extraction from the article; quote verification (4 claims per call) | 2-4 per researched topic |
| writer | script + rewrites + duration fix | 1-4 |
| director | storyboard (+1 revision) | 1-2 |
| judge | vision check of the contact sheet (skipped when no free vision model is ready) | 0-1 |

Text roles never name a model. The critic and the director ask for `fusion` first (FreeLLMAPI sends the prompt to
several free models and a judge model merges the answers: the strongest free reviewer/storyboarder). The others ask
for `auto:smart` (the strongest model that has a
healthy key under its rate limits right now), then `auto`. So only models **your** keys can reach are ever used, and a
model that was removed upstream is never picked. The judge needs a model that can see a picture, so it tries only the
ready models whose names match `roles.judge.vision`; with none, the measured QA gates decide alone. FreeLLMAPI
refusals that never reached a provider (model gone, every route cooling down) do not count against the budget. Every reply records the model that actually answered
(`X-Routed-Via`) in `out/<id>/models.json` and `data/freellm_usage.json`.

## Safety layers

1. FreeLLMAPI routes only to the free endpoints whose keys you added.
2. `freellm.deny` (`claude`, `anthropic`, `gpt-4o`, `gpt-4.1`, `gpt-5`, `o1-`, `o3-`, `o4-`) — removed from discovery
   **and** any reply routed to a denied model is discarded (it still counts against the budget). `config_check` refuses a
   deny list without `claude`.
3. Per video: `max_calls_per_video` (48) and `max_tokens_per_video` (400k).
4. Per month (UTC): `monthly_token_cap` (50M) and `monthly_request_cap` (6,000), counted in `data/freellm_usage.json`.
5. When anything runs out: `LLMUnavailable` → the run stops gracefully with a warning. No video is made from a
   fallback writer, because a documentary without research is not acceptable. (The offline storyboard director is the
   only offline fallback: it is deterministic and the facts it shows still come from the researched script.)

## Rough budget

A successful video uses ~12-20 requests and ~80-200k tokens (research articles are the large part). 8 videos/day ≈
100-160 requests/day ≈ 3,000-5,000/month — inside the caps and inside typical free tiers when several providers are
configured. Rejected topics cost requests too; that is the price of the research gate.

## Recommended keys (all have free tiers; check each provider's current terms)

- **Google AI Studio** (Gemini): best writer/director among free options and the usual free vision model for the judge.
- **Groq**, **Cerebras**, **OpenRouter (`:free` models only)**, **Mistral (free tier)**, **GitHub Models** — failover capacity.

Free tiers change. The provider limits are enforced by the providers; our caps make sure we stay far below them, and a
quota error (429) simply moves the request to the next model. To check keys and model routing without making a video,
run `python -m flatframe.llm --check` with `FREELLM_BASE_URL` / `FREELLM_API_KEY` set (e.g. after `bash tools/start_freellmapi.sh`).

## Image pinning

`freellmapi.lock` holds the image. Use **Actions → Pin FreeLLMAPI** with a release tag; it resolves the digest, starts
the exact image, checks `/api/ping`, and opens a PR. See SECURITY.md.

## Hand-picked topics

`prompts/curated_topics.json` holds ~40 hand-picked documentary stories, chosen because each has its own Wikipedia
article and wide independent coverage (so research can verify it). The idea stage uses them before brainstorming
(`ideas.use_curated`). They get no shortcut: research verifies every fact exactly like a brainstormed idea, and a topic
that fails is never tried again. When the list runs out, the free models brainstorm as before.
