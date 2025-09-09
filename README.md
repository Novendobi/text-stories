# Text Stories — iMessage Style Video Generator

Create engaging, realistic iMessage-style chat videos from simple scripts. This repo includes two renderers:

- `story-gen.py` — simple two-person demo with basic typing bubbles.
- `story-gen2.py` — advanced, dark‑mode iPhone 15–style UI, realistic keyboard typing for “your” messages, group chat support, scrolling, and emoji rendering.

## Features

- Realistic iMessage UI (dark mode): status bar, nav bar, bubbles with tails, keyboard, input bar, home indicator.
- Group chats with any number of participants; left‑side bubbles can show sender names.
- Realistic typing:
  - Your messages (blue/right) animate keyboard presses and progressive input text.
  - Others (grey/left) show iMessage typing dots.
- Auto‑scrolling to avoid overlaps with keyboard/input bar.
- Emoji support via Pilmoji + color emoji fonts.
- Scriptable: load conversations from JSON; choose who “you” are.

See `AGENT.md` for a focused guide aimed at LLM/agent workflows generating conversation scripts and hashtags for social content.

## Content Agents

This project targets short‑form content creation and attention farming for social media. If you’re an agent (or using an LLM) to generate conversations, follow these principles:

- **Goal:** Create scroll‑stopping, emotionally charged text stories tailored for virality.
- **Variety:** Cover any scenario, culture, or locale (breakups, school drama, wedding planning, Nigerian/Lagos chaos, US prom night, K‑drama vibes, etc.).
- **Names:** Treat participant names as fluid; swap freely to fit the setting.
- **Structure:** Hook in the first 1–2 messages, escalate tension, add a twist, resolve or cliffhang.
- **Pacing:** Keep messages short, alternate senders frequently, and use realistic timing.
- **Voice:** Use slang, emoji, and regionalisms appropriately; stay culturally respectful.
- **Length:** 12–40 messages per story is a good sweet spot for TikTok/Reels.

When an agent outputs a conversation, it should also output a platform‑ready hashtag set.

- **Hashtags:** Provide 8–15 tags mixing broad + niche + locale + theme.
- Examples: `#TextStory #iMessage #ChatStory #StoryTime #LagosTraffic #NaijaTok #BreakupStory #HighSchoolDrama #PromNight #KDrama #FYP #Viral #POV #Relationships #PlotTwist`

Recommended agent deliverables:

- `script` (JSON): conversation as described below.
- `pitch` (1–2 lines): why it hooks viewers.
- `hashtags` (list of strings): platform‑optimized tags.

## Requirements

- Python 3.10+
- `ffmpeg` — moviepy uses `imageio[ffmpeg]`, which bundles a downloader, but having system ffmpeg is recommended.

Python packages (see `requirements.txt`):

- moviepy==1.0.3
- Pillow==10.4.0
- numpy>=1.26.0
- imageio[ffmpeg]>=2.31.0
- pilmoji>=2.0.0
- emoji<2.0.0 (required for pilmoji 2.x compatibility)

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Recommended (Linux): install a color emoji font for best emoji rendering.

```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-color-emoji
```

## Quick Start

Run the advanced renderer with the built-in demo:

```bash
python story-gen2.py
```

Render from a JSON script and set yourself as the blue/right sender:

```bash
python story-gen2.py --script examples/chat.json --me Alex --output my_story.mp4
```

If needed, force a local color emoji font (Linux path shown):

```bash
EMOJI_FONT_PATH="/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf" python story-gen2.py -s examples/chat.json
```

## JSON Script Format

You can provide either an object with a `messages` array or a bare list. Object format (recommended):

```json
{
  "me": "Alex",
  "title": "Close Friends",
  "messages": [
    { "sender": "Alex", "text": "Babe, you free later? 😅" },
    { "sender": "Grace", "text": "Yep! Just parked." },
    { "sender": "Alex", "text": "Okay, cool. One sec..." },
    { "sender": "Taylor", "text": "Wait, should I still come?" },
    { "sender": "Alex", "text": "Actually hold off tonight, I’ll text you." }
  ]
}
```

Optional fields you can include (ignored by the renderer but useful for agents/workflows):

- `locale`: e.g., `"NG"`, `"US"`, `"KR"`
- `language`: e.g., `"en"`, `"yo"`, `"ha"`, `"ko"`
- `tone`: e.g., `"drama"`, `"comedy"`, `"thriller"`
- `hashtags`: array of hashtag strings (the agent’s output)
- `notes`: any planning metadata (beats, twist, pacing cues)

Bare list is also accepted:

```json
[
  ["Alex", "Hey"],
  ["Sam", "What’s up?"],
  ["Alex", "All good 😎"]
]
```

Place your scripts anywhere and pass with `--script`.

## CLI Options (`story-gen2.py`)

- `--script, -s`: Path to JSON script file.
- `--me`: Your sender name (blue bubbles on right; keyboard typing).
- `--title`: Header title override (otherwise computed from participants).
- `--output, -o`: Output video filename (default: `imessage_story.mp4`).
- `--fps`: Frames per second (default: `24`).

## How “You” Are Determined

- `--me` CLI arg takes priority.
- If absent, the script’s `me` value is used.
- Otherwise, falls back to the default in the code (currently "Alex").

Messages from “you” render on the right in blue and use keyboard typing. Others render on the left with typing dots.

## Emoji Rendering

`story-gen2.py` uses Pilmoji for colored emojis. It tries the following, in order:

1. `EMOJI_FONT_PATH` env var via `EmojiFontSource` if provided.
2. Common system paths (e.g., `/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf`).
3. Pilmoji built-in sources (e.g., `NotoEmojiSource`, `AppleEmojiSource`) if available.
4. Pilmoji default source.

If you see tofu squares:

- Ensure Pilmoji imports cleanly (requires `emoji<2.0.0`).
- Install a color emoji font (Linux): `sudo apt-get install -y fonts-noto-color-emoji`.
- Run with `EMOJI_FONT_PATH="/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"`.

## Customization Notes

- Adjust typing speed in `typing_keyboard` (per‑keystroke durations).
- Tune bubble display duration in the main render loop.
- Alter colors, paddings, and sizes near the top of `story-gen2.py`.
- Group title is computed from participants; override with `--title` or in JSON `title`.

## The Simple Demo (`story-gen.py`)

The original `story-gen.py` shows a lightweight flow with:

- Basic status bar/bubbles.
- Simple typing indicator.
- Hardcoded sample dialogue.

Use `story-gen2.py` for production content; keep `story-gen.py` for quick experiments.

## Troubleshooting

- Emoji show as blocks:
  - Install a color emoji font (Linux): `sudo apt-get install -y fonts-noto-color-emoji`.
  - Ensure `emoji<2.0.0` is installed (Pilmoji 2.x compat).
  - Provide `EMOJI_FONT_PATH` and re‑run.
- MoviePy/ffmpeg issues:
  - Ensure `ffmpeg` is available in PATH or let `imageio` download a portable one.
- Layout overlaps:
  - `story-gen2.py` auto‑scrolls based on dynamic input bar height; if customizing sizes, keep viewport math aligned with `compute_input_layout`.

## Examples

See `examples/chat.json` (create your own) and run:

```bash
python story-gen2.py -s examples/chat.json --me Alex -o story.mp4
```

Agent‑friendly output template (example):

```json
{
  "me": "Sandra",
  "title": "Third Mainland Bridge",
  "locale": "NG",
  "tone": "drama",
  "messages": [
    { "sender": "Sandra", "text": "Babe traffic is mad 😭" },
    { "sender": "Chidi", "text": "Where you dey now?" },
    { "sender": "Sandra", "text": "Almost Oworonshoki. Wait—my ex just texted 😳" },
    { "sender": "Ex", "text": "I’m at the same bus stop." },
    { "sender": "Sandra", "text": "Chidi, abeg no vex, I go call you. 🙏" }
  ],
  "hashtags": [
    "#TextStory", "#iMessage", "#LagosTraffic", "#NaijaTok", "#StoryTime",
    "#RelationshipDrama", "#POV", "#FYP", "#Viral", "#PlotTwist"
  ]
}
```

---

Questions or ideas for enhancements (timestamps, delivered/read receipts, avatars, richer keyboard)? Open an issue or propose a PR.
# text-stories
