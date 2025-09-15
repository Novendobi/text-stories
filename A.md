# Agent Guide — Text Stories for Social Content

Purpose: Generate short, viral, culturally diverse iMessage-style text conversations for social media videos (TikTok, Reels, Shorts). Optimize for attention, watch time, and shareability.

What to Produce
- A compelling conversation script (JSON) that the renderer consumes.
- A 1–2 line pitch explaining the hook and twist.
- A set of 8–15 hashtags tailored to the topic, locale, and platform.
- Always deliver the conversation in chat wrapped in a single fenced code block.

Story Intent and Structure (non‑negotiable)
- Point: Every story must have a clear, nameable purpose viewers can state in one line (e.g., “Breakup because he lied about receipts,” “Wedding vendor scam exposed”). If this isn’t obvious, rewrite.
- Structure: Use a compact three‑act arc:
  - Act I (Hook + Setup, 2–4 msgs): Start with a concrete, relatable trigger.
  - Act II (Escalation + Evidence, 6–20 msgs): Raise stakes with specifics, evidence (receipts described in text), contradictions, or third‑party interjections.
  - Act III (Reveal + Resolution/Cliff, 3–8 msgs): Deliver a reveal/admission/twist; end with a consequence or crisp cliffhanger.
- Relatability: Ground in real details (times, places, slang) that fit the locale.
- Comment bait: Include a moral gray area or decision point people will debate.

Chat Title Rules (very important)
- For a 1:1 chat, the `title` MUST be the other person’s contact name (not a theme or location). Example: "Amara".
- For a group chat, the `title` SHOULD be the group name or a participants list (excluding `me`) like "Amara, Jordan, Tife".
- Do NOT use creative themes/locations in `title` (e.g., "Third Mainland Bridge"). Put those in the `pitch` or `notes` instead.

Creative Principles
- Hook fast: Ensure the first 1–2 messages stop the scroll.
- Escalate stakes: Add tension, misdirection, or a twist mid-way.
- Keep pace: Short messages, frequent sender alternation, realistic timing.
- Cultural range: Any country/culture/scene is fair game (e.g., Lagos traffic, Nigerian family chaos, US prom night, school drama, wedding planning, K‑drama vibes). Use slang and regionalisms respectfully.
- Names are fluid: Swap names freely to match setting and vibe.
- Length: 12–40 messages is a good sweet spot for short video content.
- Emoji: Use sparingly but purposefully; they help convey tone.

Scenario Blueprints (adapt culturally)
- Breakup (evidence‑driven): Trigger → evidence/contradictions → admission/consequence or twist. One party can be clearly wrong; make it legible via facts in‑chat.
- School/Exam shock: Trigger (“name missing”), rules nuance via registrar/friend, path forward or twist.
- Wedding chaos: Trigger (double‑booked, ex in chat), vendor receipts/family pressure, new plan or cutoff.
- City chaos (e.g., Lagos): Trigger (driver left with rings), live location, checkpoint, resolution/lesson.

Relatability Triggers
- Accusation, surprise, deadline, confession, betrayal, discovery (transactions, locations, AirTags, DMs).

Comment‑Bait Levers
- Who’s at fault? Who knew what when? Evidence vs excuses. Culture vs partner expectations.

Attention Hooks (pick one to start your opening line)
- Accusation: “Why did you post that about me?”
- Surprise: “You won’t believe who just walked in…”
- Deadline: “You have 10 minutes before I call her.”
- Confession: “I need to tell you something before you see it online.”
- Betrayal: “Wait… you were with him last night?”
- Discovery: “Your AirTag is moving. Not with you.”

Required Output Format (JSON)
Return your result inside one code block as a single JSON object with the following fields:

- me: string — the sender name to render as “you” (right, blue bubble).
- title: string — header label (chat name or person). See Chat Title Rules.
- type: string — "direct" for a 1:1 chat or "group" for a group chat.
- contact: string — required for `type="direct"` when you want to force which person is the main 1:1 contact (the other side). If omitted, the renderer infers the first non‑`me` sender.
- messages: array of objects — each with sender and text strings. Example:
  - { "sender": "Name", "text": "Message text…" }
- pitch: string — 1–2 lines explaining the hook/twist.
- hashtags: array of strings — 8–15 tags for reach (broad + niche + locale + theme).

Example Envelope
```
{
  "me": "Alex",
  "title": "Sam",
  "type": "direct",
  "contact": "Sam",
  "messages": [
    { "sender": "Alex", "text": "You won’t believe who just walked in…" },
    { "sender": "Sam", "text": "Who?? Don’t leave me hanging 😭" }
  ],
  "pitch": "Hook: Mystery at prom. Twist: ex shows with your best friend. Stakes: public fallout.",
  "hashtags": ["#TextStory", "#ChatStory", "#PromNight", "#HighSchoolDrama", "#PlotTwist", "#FYP"]
}
```

Advanced (Optional Fields)
- locale: string, e.g., "NG", "US", "KR" (renderer ignores; workflows may use).
- language: string, e.g., "en", "yo", "ko".
- tone: string, e.g., "drama", "comedy", "thriller".
- notes: arbitrary metadata for beats/pacing (ignored by renderer).

Story Patterns to Try
- Breakup/reconciliation, mistaken identity, last‑minute cancellation, family pressure, job/visa news, exam shock, wedding chaos, Lagos traffic fiasco, K‑drama misunderstandings, festival night out, prom night twist, roommate betrayals, friend‑group politics.

Hashtag Guidance
- Mix broad (#TextStory, #StoryTime, #POV, #Viral, #FYP) with niche (#LagosTraffic, #PromNight, #KDrama), plus culture/locale tags (#NaijaTok, #BlackTikTok, #DesiTok, #KoreanTok).
- 8–15 total; prioritize relevance over volume.

Quality Checklist
- [ ] Clear one‑line point/logline (what this is about).
- [ ] Hook in first 1–2 messages with a concrete trigger.
- [ ] Escalation uses specifics/evidence (not vague arguing).
- [ ] Wrong party (if applicable) is clearly wrong for stated reasons.
- [ ] Resolution or cliffhanger closes the arc (no drift).
- [ ] Title follows Chat Title Rules; direct vs group set correctly (type/contact).
- [ ] 12–40 concise messages; natural language for locale.
- [ ] Includes pitch and hashtag set; return JSON in one fenced code block.
