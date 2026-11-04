# LinkedIn Post & Profile Performance Analysis
**Profile:** Mihir Mithani (`mihir-mithani-82b358248`)
**Post analyzed:** "OpenROAD Flow GUI v2" (posted ~7 hrs before this report)
**Data source:** Apify `harvestapi` LinkedIn connectors (profile scraper + profile-posts scraper). Observed metrics = scraped directly. Predicted metrics = model estimate.

---

## 1. Profile Analysis

| Metric | Value | Notes |
|---|---|---|
| Followers | **577** | Small, early-career network |
| Connections | **573** | Near 1:1 follower/connection ratio — typical of a non-creator profile |
| Verified | Yes | Adds mild trust signal |
| Premium / Influencer | No / No | No algorithmic distribution boost from these badges |
| Headline | "Bridging silicon and intelligence \| VLSI Physical Design Intern @ Microcircuits Innovations \| Robotics RL + GPU Kernels \| B.Tech ICT, Marwadi '27" | Keyword-rich, clear niche positioning |
| Location | Rajkot, Gujarat, India | |
| Current role | VLSI Intern, Microcircuits Innovations Pvt. Ltd. (2 mos) | Final-year student, ICT, Marwadi University (2023–2027) |
| About section | Present, detailed, keyword-dense, includes email + achievements | Strong |
| Certifications | 9 (mostly NVIDIA DLI, Google) | Builds technical authority |
| Featured projects | 10 listed on profile | Strong portfolio depth |
| Recommendations received | 0 | Weakens third-party credibility |
| Website link | Personal portfolio linked in profile actions | Good |

**Industry/niche:** VLSI physical design, ASIC/EDA tooling, GPU programming (CUDA), robotics/RL — a narrow, technical, semiconductor-adjacent niche.

**Posting frequency & consistency:** 16 self-authored posts identified in the last ~4 months (Apr 2 – Jul 26, 2026) → **≈1 post/week**, reasonably consistent, though bursty (e.g., 3 posts on a single day for a "Day 1/2/3" CUDA series, two posts on Jul 10).

**Average engagement on recent posts (own posts, n=16):**

| | Avg | Range |
|---|---|---|
| Likes | 17.4 | 2 – 83 |
| Comments | 1.4 | 0 – 10 |
| Shares | 0.06 | 0 – 1 |
| Total engagement | ~18.8/post | — |
| Engagement rate vs. followers | ~3.3% | Above the typical 2% LinkedIn benchmark, but on a very small base |

**Audience quality:** Niche-relevant but junior — the "People also viewed"/similar-profile signals returned by the scraper are almost entirely fellow ICT students and VLSI interns at the same university, not senior engineers or recruiters. This suggests his current audience is peer-heavy rather than senior-industry-heavy.

**Personal branding indicators:** Strong stylistic consistency — nearly every post opens with a stylized quote (unicode bold italic) followed by a project changelog or learning recap. This is a recognizable, repeatable format (good for brand recall), though it is starting to read as a template rather than a story.

---

## 2. Post Analysis (Target Post)

| Field | Observed Value |
|---|---|
| Post URL | `.../mihir-mithani-82b358248_openroad-eda-asic-activity-7486986245718474752-PoDF` |
| Media type | **Text-only** (no image, carousel, video, or document detected) |
| Publish time | 2026-07-26, 03:30 UTC → **~9:00 AM IST, Sunday** |
| Hashtags | `#OpenROAD #EDA #ASIC #VLSI` (4, all niche/low-volume) |
| Mentions | None |
| External links | **None present in post text** — the post says `git clone ... && python main.py` but the actual repo URL is missing (his prior v1 post on the same project did include a real `lnkd.in` link) |
| Content length | ~230 words / long-form, uses bullet-style feature list |
| CTA | Weak/soft ("Feedback/PRs welcome... feel free to contact") — no direct question |
| Reactions (at capture) | 2 |
| Comments (at capture) | 0 |
| Reposts (at capture) | 0 |
| Post age at capture | ~7 hours |

---

## 3. LinkedIn Algorithm Evaluation

| Ranking Factor | Score (0–10) | Why |
|---|---|---|
| Hook quality (first 2–3 lines) | 5 | Movie-quote opener is a recognizable personal-brand device but doesn't create curiosity or state a concrete outcome up front |
| Readability | 6 | Clear line breaks and bullets; heavy use of stylized unicode bold text can render oddly on some devices/screen readers |
| Formatting | 6 | Good use of whitespace and a structured feature list, but visually dense |
| Dwell-time potential | 5 | Long text drives "see more" clicks (good), but no image/GIF/video to anchor attention — a real miss for a UI-focused release |
| Storytelling | 4 | Reads as a changelog/announcement rather than a narrative arc |
| Educational value | 5 | Useful to a narrow technical audience, but not framed as a broadly applicable lesson |
| Originality | 8 | Genuine, original personal project — not curated/reposted content |
| Engagement-bait detection | 9 | No manipulative bait tactics ("comment YES," forced tagging) — clean |
| Use of hashtags | 6 | Relevant and non-spammy, but all 4 are extremely low-search-volume niche tags |
| Link placement | 2 | Critical flaw: the call-to-action references cloning a repo but supplies no actual link |
| Conversation potential | 4 | No direct question to prompt replies |
| Shareability | 4 | Niche developer-tool update; limited appeal outside VLSI/EDA circles |
| Authority/expertise signals | 7 | Deep technical specificity (stdlib Python, Tkinter, ORFS stage automation) signals real hands-on expertise |

**Composite Algorithm-Friendliness read:** roughly average, dragged down mainly by the missing link and lack of visual media — both are easy fixes.

---

## 4. Reach Prediction

| Metric | Prediction | Confidence |
|---|---|---|
| Expected impressions | 800 – 1,500 | Medium |
| Estimated unique reach | 700 – 1,300 | Medium |
| Expected engagement rate | ~1.5% – 2.5% | Medium |
| Predicted final reactions | 8 – 16 | Medium |
| Predicted final comments | 0 – 2 | Medium |
| Predicted final reposts | 0 – 1 | High |
| Probability of reaching 2nd-degree audience | ~25–35% (Low–Medium) | Low |
| Probability of LinkedIn "recommending" beyond network | ~15–20% (Low) | Low |

*Why confidence is capped at Medium:* the post was only ~7 hours old at capture with just 2 reactions — early velocity is the strongest real-world predictor of eventual reach, and this is currently below his own account average pace, not a large enough sample to be certain, and Apify data doesn't expose true impression counts (LinkedIn only shows those to the author in-app).

---

## 5. Audience Analysis

- **Primary audience:** VLSI/ASIC physical design engineers, EDA tooling enthusiasts, embedded/robotics students, IEEE student members, NVIDIA DLI alumni.
- **Secondary audience:** Semiconductor recruiters/hiring managers, professors/mentors at Marwadi University, open-source Python developers.
- **Most likely to engage:** Peers in the same VLSI/robotics cohort (based on his connection graph skewing toward fellow students/interns) rather than senior engineers.
- **Match to existing audience:** Strong — the post is squarely inside his stated niche and headline.
- **Appeal beyond existing followers:** Limited. Compare to a same-week post in his feed by a semiconductor commentator connecting AI to chip-design careers, which reached 184 likes/11 comments by tapping a broader "AI is changing your job" anxiety — a wider hook than a tool changelog can achieve on its own.

---

## 6. Virality Assessment

| Tier | Likelihood |
|---|---|
| Poor performer | Moderate |
| **Average performer** | **Most likely** |
| High performer | Low |
| Viral within niche | Low |
| Viral beyond niche | Very low |

**Reasoning:** Small (577-follower) account, niche 4-hashtag topic, no external link for readers to act on, no visual media, and early engagement pace (2 likes/7 hrs) trailing this account's own historical average (~18 total engagements/post). Nothing in the post design (hook, CTA, media) is built to trigger an algorithmic reach expansion beyond his direct network.

---

## 7. Improvement Suggestions

- **Better opening hook:** Replace the movie quote with a concrete before/after statement, e.g., "I shipped 6 fixes to my open-source chip-design GUI based on what broke in v1 — here's what changed."
- **Fix the link:** Add the actual repository URL — right now the CTA points to a command that can't be run.
- **Add visual media:** A screenshot or short GIF of the new UI (resizable panes, progress spinners) would meaningfully lift dwell time for a UI-centric release.
- **Better CTA:** End with one specific question ("What's the one QoL feature you'd want in v3?") instead of a generic "feel free to contact."
- **Better hashtags:** Keep 2–3 niche tags (#OpenROAD #VLSI) and add one broader-reach tag (#OpenSource or #Python) to widen discovery without losing relevance.
- **Better posting time:** Shift future posts to Tuesday–Thursday, ~8–10 AM or 12–1 PM IST, rather than Sunday morning, when professional audience activity is lower.
- **Additional keywords:** "RTL-to-GDSII," "physical design automation," "developer tools" — widens searchability beyond pure VLSI jargon.
- **Increase comments:** Ask a direct, answerable question at the end; direct-reply prompts outperform open-ended "thoughts?" asks.
- **Increase shares:** An explicit, specific repost ask ("Repost if you know a VLSI engineer who'd use this") tends to outperform passive availability of a repost button.
- **Increase dwell time:** Consider a short native document/PDF carousel walking through the GUI stage-by-stage — document posts tend to hold attention longer than plain text.
- **Content to trim/rewrite:** The Marvel-quote opener contributes little to comprehension; either cut it or make the tie-in explicit and brief.

---

## 8. Overall Scores

| Score | /100 |
|---|---|
| Algorithm Friendliness | 55 |
| Content Quality | 65 |
| Engagement Potential | 40 |
| Authority Score | 75 |
| Virality Score | 25 |

---

## 9. Final Verdict

**Biggest strengths:**
- Genuine, original, technically credible open-source project with real depth (custom GDSII parser, threaded subprocess execution, PDK-aware wizard).
- Consistent ~weekly posting cadence with a recognizable personal-brand format.
- Strong keyword alignment between headline, about section, and post content.

**Biggest weaknesses:**
- Missing repository link undermines the entire CTA.
- No visual media on a visually-driven UI release.
- Generic hook and soft CTA limit both hook-stage and comment-stage algorithm signals.
- Sunday-morning posting time and early engagement pace both below this account's own baseline.

**Estimated performance category:** Average performer, trending toward below-average without intervention (early velocity is currently the weakest signal).

**Top 5 actions to most improve reach (in priority order):**
1. Add the actual GitHub link (edit the post or pin it as the top comment) — this is the single highest-leverage, lowest-effort fix.
2. Add a screenshot or short GIF of the v2 interface.
3. Rewrite the opening two lines to lead with a concrete outcome rather than a quote.
4. Close with one specific, answerable question to drive comments.
5. Shift future posts of this type to a Tue–Thu mid-morning IST slot.

---

### Data limitations
- LinkedIn does not expose true "impressions" to non-authors via any scraper — all impression/reach figures above are **model-based estimates**, not observed data, and are flagged accordingly.
- The Apify posts endpoint returned some items authored by other people (a university department page, a semiconductor commentator, and another creator) mixed into the profile's recent activity feed — these were excluded from the "own post" engagement averages above since they were not authored by Mihir.
- Reactions/comments identity data were not scraped (cost/scope control), so "audience quality" above is inferred from the profile's own network composition (similar/related profiles), not from who actually engaged with this specific post.
