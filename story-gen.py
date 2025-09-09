from moviepy.editor import ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random
import string
import datetime

# Video settings
WIDTH, HEIGHT = 720, 1280
# Layout constants (approximate iPhone 15 look)
STATUS_BAR_H = 44
HEADER_H = 64
CHAT_TOP_Y = STATUS_BAR_H + HEADER_H
TOP_PADDING = 24
BOTTOM_SAFE = 34  # home indicator height
# Dark mode colors inspired by iMessage
CHAT_BG = (0, 0, 0)            # iOS Messages dark background (OLED black)
BLUE = (10, 132, 255)          # systemBlue in dark mode
GREY = (44, 44, 46)            # received bubble dark
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TEXT_DARK = (255, 255, 255)
TEXT_SUBTLE = (142, 142, 147)  # secondary label gray
NAV_BG = (0, 0, 0)
SEPARATOR = (44, 44, 46)
KEYBOARD_BG = (22, 22, 24)
KEY_FILL = (58, 58, 60)
KEY_HL = (72, 72, 74)

# Typography
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 40)
    SMALL_FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 26)
except Exception:
    FONT = ImageFont.load_default()
    SMALL_FONT = ImageFont.load_default()

# Who is the device owner (blue bubbles on right)
ME_NAME = "Alex"  # change to your name to control who types on keyboard

# Example dialogue script
dialogue = [
    ("Alex", "Hey, did you hear that noise?"),
    ("Sam", "No, what happened?"),
    ("Alex", "Check your phone... someone’s typing from your account 😳"),
]

def draw_status_bar(draw):
    """Draw fake iOS status bar at top."""

    # Time
    def current_time_str():
        now = datetime.datetime.now()
        try:
            return now.strftime("%-I:%M %p")
        except Exception:
            return now.strftime("%I:%M %p").lstrip("0")

    time_str = current_time_str()
    # iOS places time at top-left inside apps (dark mode)
    draw.text((12, (STATUS_BAR_H-28)//2), time_str, font=FONT, fill=WHITE)

    # Minimal battery (dark mode)
    bx = WIDTH - 80
    draw.rectangle([bx, 12, bx+50, 32], outline=WHITE, width=2)
    draw.rectangle([bx+52, 17, bx+56, 27], fill=WHITE)
    draw.rectangle([bx+5, 17, bx+40, 27], fill=WHITE)

def draw_header(draw, title="Sam"):
    """Draw conversation header under the status bar."""
    header_h = HEADER_H
    y0 = STATUS_BAR_H
    draw.rectangle([0, y0, WIDTH, y0+header_h], fill=NAV_BG)
    tw = draw.textlength(title, font=FONT)
    draw.text(((WIDTH - tw) // 2, y0 + (header_h-40)//2), title, font=FONT, fill=WHITE)
    # Left back chevron + 'Messages' text in blue
    cx = 22
    cy = y0 + header_h//2
    draw.polygon([(cx, cy), (cx+12, cy-10), (cx+12, cy+10)], fill=BLUE)
    draw.text((cx+20, cy-14), "Messages", font=SMALL_FONT, fill=BLUE)
    # Right info circle with 'i'
    r0 = [WIDTH-48, y0+header_h//2-14, WIDTH-20, y0+header_h//2+14]
    draw.ellipse(r0, outline=BLUE, width=2)
    draw.text((WIDTH-36, y0+header_h//2-10), "i", font=SMALL_FONT, fill=BLUE)
    # Subtle divider (dark)
    draw.line([0, y0+header_h, WIDTH, y0+header_h], fill=SEPARATOR, width=2)

def compute_group_title(participants):
    others = [p for p in participants if p != ME_NAME]
    if not others:
        return ME_NAME
    title = ", ".join(others[:3])
    if len(others) > 3:
        title += f" +{len(others)-3}"
    return title

def wrap_text(draw, text, max_width):
    lines = []
    words = text.split(" ")
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=FONT) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def bubble_size(draw, text, max_width):
    padding = 20
    lines = wrap_text(draw, text, max_width)
    text_width = max(draw.textlength(l, font=FONT) for l in lines) if lines else 0
    text_height = max(1, len(lines)) * 50
    return (text_width + padding * 2, text_height + padding * 2, lines)

def draw_bubble(draw, text, side, y_offset, name=None, max_width=None):
    padding = 20
    max_width = max_width or (WIDTH - 250)
    bubble_w, bubble_h, lines = bubble_size(draw, text, max_width)
    if side == "left":
        x0 = 16
        color = GREY
        txt_color = TEXT_DARK
    else:
        x0 = WIDTH - bubble_w - 16
        color = BLUE
        txt_color = WHITE
    y0 = y_offset

    # Name label for group chats on left side
    if name and side == "left":
        name_y = y0 - 24
        draw.text((x0+6, name_y), name, font=SMALL_FONT, fill=TEXT_SUBTLE)

    draw.rounded_rectangle([x0, y0, x0+bubble_w, y0+bubble_h], 28, fill=color)
    # tail
    if side == "left":
        tail = [(x0+18, y0+bubble_h-8), (x0-2, y0+bubble_h+8), (x0+18, y0+bubble_h-24)]
        draw.polygon(tail, fill=color)
    else:
        x1 = x0 + bubble_w
        tail = [(x1-18, y0+bubble_h-8), (x1+2, y0+bubble_h+8), (x1-18, y0+bubble_h-24)]
        draw.polygon(tail, fill=color)

    y_text = y0 + padding
    for l in lines:
        draw.text((x0+padding, y_text), l, font=FONT, fill=txt_color)
        y_text += 50
    return bubble_w, bubble_h

def draw_chat_base(draw, title="Chat"):
    draw_status_bar(draw)
    draw_header(draw, title=title)
    # nothing else; divider added in header

def draw_home_indicator(draw):
    # iPhone home indicator line (when keyboard not visible)
    cx = WIDTH//2
    y = HEIGHT - 12
    draw.rounded_rectangle([cx-60, y-3, cx+60, y+3], 3, fill=(80,80,85))

def render_chat_frame(history, typing=None, title="Chat", input_text=None, highlight_key=None):
    """Render a full chat screen with history and optional typing or keyboard."""
    img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
    draw = ImageDraw.Draw(img)
    draw_chat_base(draw, title=title)
    # Determine viewport bottom depending on keyboard visibility
    keyboard_visible = input_text is not None
    if keyboard_visible:
        bar_h = 52
        bar_y = KB_TOP - bar_h - 8
        viewport_bottom = bar_y - 8
    else:
        viewport_bottom = HEIGHT - BOTTOM_SAFE - 10
    # Compute scroll offset if content exceeds viewport
    content_bottom = CHAT_TOP_Y + TOP_PADDING
    for msg in history:
        bw, bh, _ = bubble_size(draw, msg['text'], WIDTH - 250)
        content_bottom = max(content_bottom, msg['y'] + bh)
    if typing and typing.get('type') == 'dots':
        content_bottom = max(content_bottom, typing['y'] + 80)
    shift = max(0, content_bottom + 12 - viewport_bottom)

    # draw history bubbles (with scroll shift)
    for msg in history:
        draw_bubble(draw, msg['text'], msg['side'], msg['y'] - shift, name=msg.get('name'))
    # typing indicator bubble for others
    if typing and typing.get('type') == 'dots':
        bubble_width, bubble_height = 150, 80
        x0 = 16
        y0 = typing['y'] - shift
        color = GREY
        draw.rounded_rectangle([x0, y0, x0+bubble_width, y0+bubble_height], 28, fill=color)
        for j in range(typing.get('dots', 0)):
            draw.ellipse([x0+30+j*30, y0+30, x0+50+j*30, y0+50], fill=(200,200,205))
        if typing.get('name'):
            draw.text((x0+6, y0-24), typing['name'], font=SMALL_FONT, fill=TEXT_SUBTLE)
    # keyboard + input for me
    if input_text is not None:
        draw_input_bar(draw, input_text)
        draw_keyboard(draw, highlight=highlight_key)
    else:
        draw_home_indicator(draw)
    return img

def typing_indicator(name, y_offset=CHAT_TOP_Y + TOP_PADDING + 40, title="Chat", history=None):
    """Typing dots animation for 'name' (others)."""
    history = history or []
    frames = []
    for i in range(1, 4):
        img = render_chat_frame(
            history,
            typing={"type": "dots", "name": name, "y": y_offset, "dots": i},
            title=title
        )
        frames.append(ImageClip(np.array(img)).set_duration(0.375))
    return concatenate_videoclips(frames)

# --- Keyboard typing animation for sender side ---

# Define a simple QWERTY keyboard layout for highlighting
KEY_ROWS = [
    "QWERTYUIOP",
    "ASDFGHJKL",
    "ZXCVBNM"
]

def _compute_key_positions():
    positions = {}
    margin_side = 18
    key_w, key_h = 54, 68
    h_gap, v_gap = 8, 10
    keyboard_height = key_h * 3 + v_gap * 2 + 56  # extra for special row
    kb_top = HEIGHT - keyboard_height - 8
    # Base x for each row (center rows)
    for r, row in enumerate(KEY_ROWS):
        total_w = len(row) * key_w + (len(row)-1)*h_gap
        x_start = (WIDTH - total_w)//2
        y = kb_top + r*(key_h + v_gap)
        for i, ch in enumerate(row):
            x = x_start + i*(key_w + h_gap)
            positions[ch] = (x, y, x+key_w, y+key_h)
            positions[ch.lower()] = (x, y, x+key_w, y+key_h)
    # Special row: emoji | dictate | space | return
    row_y = kb_top + 3*(key_h + v_gap)
    emoji_w = 60
    dictate_w = 60
    return_w = 90
    space_w = WIDTH - margin_side*2 - (emoji_w + dictate_w + return_w + h_gap*3)
    x = margin_side
    positions[':emoji:'] = (x, row_y, x+emoji_w, row_y+key_h)
    x += emoji_w + h_gap
    positions[':dictate:'] = (x, row_y, x+dictate_w, row_y+key_h)
    x += dictate_w + h_gap
    positions[' '] = (x, row_y, x+space_w, row_y+key_h)
    x += space_w + h_gap
    positions[':return:'] = (x, row_y, x+return_w, row_y+key_h)
    return positions, kb_top, key_h

KEY_POSITIONS, KB_TOP, KEY_H = _compute_key_positions()

def draw_keyboard(draw, highlight=None):
    # Keyboard background (dark)
    draw.rectangle([0, KB_TOP-12, WIDTH, HEIGHT], fill=KEYBOARD_BG)
    # Draw keys
    for ch, rect in KEY_POSITIONS.items():
        x0,y0,x1,y1 = rect
        if ch.islower():
            continue
        # subtle shadow
        draw.rounded_rectangle([x0, y0+2, x1, y1+2], 14, fill=(0,0,0))
        fill = KEY_FILL
        if highlight and (ch == highlight or ch.lower() == (highlight or '').lower()):
            fill = KEY_HL
        draw.rounded_rectangle([x0, y0, x1, y1], 14, fill=fill)
        if ch == ':emoji:':
            draw.ellipse([x0+18, y0+16, x0+40, y0+38], outline=(160,160,165), width=2)
        elif ch == ':dictate:':
            # microphone icon
            draw.rectangle([x0+26, y0+18, x0+34, y0+36], fill=(160,160,165))
            draw.ellipse([x0+24, y0+12, x0+36, y0+22], fill=(160,160,165))
            draw.rectangle([x0+29, y0+36, x0+31, y0+44], fill=(160,160,165))
        elif ch == ':return:':
            draw.text((x0+12, y0+20), "return", font=SMALL_FONT, fill=WHITE)
        elif ch != ' ':
            tx = (x0 + x1)//2 - 10
            ty = (y0 + y1)//2 - 14
            draw.text((tx, ty), ch, font=SMALL_FONT, fill=WHITE)
    # Space bar label
    sx0, sy0, sx1, sy1 = KEY_POSITIONS[' ']
    draw.text(((sx0+sx1)//2 - 20, (sy0+sy1)//2 - 14), "space", font=SMALL_FONT, fill=(160,160,165))

def draw_input_bar(draw, text):
    # Input bar above keyboard (dark)
    bar_h = 52
    bar_y = KB_TOP - bar_h - 8
    margin = 12
    # input field
    draw.rounded_rectangle([margin, bar_y, WIDTH - margin - 56, bar_y + bar_h], 18, fill=(28,28,30))
    # Camera icon placeholder
    draw.rectangle([margin+10, bar_y+14, margin+26, bar_y+30], outline=(160,160,165), width=2)
    # Send circular button
    cx0 = WIDTH - margin - 44
    draw.ellipse([cx0, bar_y+4, cx0+40, bar_y+44], fill=BLUE)
    # Up arrow
    ax = cx0+20
    ay = bar_y+14
    draw.polygon([(ax, ay), (ax-8, ay+10), (ax-2, ay+10), (ax-2, ay+24), (ax+2, ay+24), (ax+2, ay+10), (ax+8, ay+10)], fill=WHITE)
    # Text inside input
    draw.text((margin + 40, bar_y + 10), text, font=FONT, fill=WHITE)

def typing_keyboard(text, title="Chat", history=None):
    """Animate fast typing on keyboard with progressive input text, including history."""
    history = history or []
    frames = []
    typed = ""
    display_text = text[:160]
    for ch in display_text:
        typed += ch
        highlight = ch if ch in KEY_POSITIONS else None
        img = render_chat_frame(history, title=title, input_text=typed, highlight_key=highlight)
        dur = random.uniform(0.035, 0.070) if ch.strip() else random.uniform(0.055, 0.095)
        frames.append(ImageClip(np.array(img)).set_duration(dur))
    if frames:
        frames[-1] = frames[-1].set_duration(frames[-1].duration + 0.2)
    return concatenate_videoclips(frames)

# Build conversation with multi-participant support
# Dialogue format: [(name, text), ...]
participants = list(dict.fromkeys([n for n, _ in dialogue]))
group_title = compute_group_title(participants)

clips = []
history = []  # list of {name, text, side, y}
y_offset = CHAT_TOP_Y + TOP_PADDING + 40

for name, text in dialogue:
    side = "right" if name == ME_NAME else "left"
    if side == "right":
        clips.append(typing_keyboard(text, title=group_title, history=history))
    else:
        clips.append(typing_indicator(name, y_offset=y_offset, title=group_title, history=history))

    # After typing, render a static frame showing the new message added to history
    # Measure bubble height to advance y offset
    tmp_img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
    tmp_draw = ImageDraw.Draw(tmp_img)
    bubble_w, bubble_h, _ = bubble_size(tmp_draw, text, WIDTH - 250)

    history.append({
        "name": name if side == "left" and len(participants) > 2 else None,
        "text": text,
        "side": side,
        "y": y_offset
    })

    frame_img = render_chat_frame(history, title=group_title)
    clips.append(ImageClip(np.array(frame_img)).set_duration(2))

    y_offset += bubble_h + 16

final = concatenate_videoclips(clips, method="compose")
final.write_videofile("imessage_story.mp4", fps=24)
