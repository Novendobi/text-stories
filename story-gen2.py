from moviepy.editor import ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random
import string
import datetime
import re
import os
import json
import argparse
try:
    from pilmoji import Pilmoji
    # Try optional sources if they exist in this Pilmoji version
    try:
        from pilmoji.source import EmojiFontSource  # accepts a font path
    except Exception:
        EmojiFontSource = None
    try:
        from pilmoji.source import NotoEmojiSource
    except Exception:
        NotoEmojiSource = None
    try:
        from pilmoji.source import AppleEmojiSource
    except Exception:
        AppleEmojiSource = None
    PILMOJI_AVAILABLE = True
except Exception as e:
    print(f"Pilmoji import failed: {e!r}")
    Pilmoji = None
    EmojiFontSource = None
    NotoEmojiSource = None
    AppleEmojiSource = None
    PILMOJI_AVAILABLE = False

# Try to locate a local color emoji font (Linux/macOS paths)
# Allow override via env var
ENV_EMOJI_FONT = os.environ.get("EMOJI_FONT_PATH")

EMOJI_FONT_CANDIDATES = [
    ENV_EMOJI_FONT,
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",            # Ubuntu/Debian
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/emoji/NotoColorEmoji.ttf",
    "/usr/local/share/fonts/NotoColorEmoji.ttf",
    "/System/Library/Fonts/Apple Color Emoji.ttc",                  # macOS
    "/System/Library/Fonts/Apple Color Emoji.ttf",                  # macOS alt
]
EMOJI_FONT_PATH = next((p for p in EMOJI_FONT_CANDIDATES if p and os.path.exists(p)), None)

# Video settings
WIDTH, HEIGHT = 720, 1280
# Layout constants (proper iPhone 15 look)
STATUS_BAR_H = 54  # Increased for proper spacing
HEADER_H = 88      # Increased for proper header
CHAT_TOP_Y = STATUS_BAR_H + HEADER_H
TOP_PADDING = 16
BOTTOM_SAFE = 34
INPUT_BAR_H = 44   # Minimum iOS input bar height
KEYBOARD_H = 291   # Standard iOS keyboard height

# Dark mode colors (exact iOS values)
CHAT_BG = (0, 0, 0)
BLUE = (0, 122, 255)  # More accurate iOS blue
GREY = (58, 58, 60)   # System gray 5
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TEXT_DARK = (255, 255, 255)
TEXT_SUBTLE = (152, 152, 157)  # System gray 2
NAV_BG = (28, 28, 30)  # System gray 6
SEPARATOR = (56, 56, 58)
KEYBOARD_BG = (0, 0, 0)  # Pure black like iOS
KEY_FILL = (77, 77, 79)
KEY_HL = (166, 166, 171)
INPUT_BG = (38, 38, 40)  # Darker input background

# Typography - more iOS-like sizing
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 34)  # Smaller
    SMALL_FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 28)
    TIME_FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 32)  # Time font
except Exception:
    FONT = ImageFont.load_default()
    SMALL_FONT = ImageFont.load_default()
    TIME_FONT = ImageFont.load_default()

# Random battery level (generated once per run)
BATTERY_LEVEL = random.randint(15, 100)

ME_NAME = "Alex"  # default; can be overridden by CLI or script file
DEFAULT_SCRIPT = "examples/chat.json"
dialogue = []  # loaded from JSON script

def load_script(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Accept either {"messages": [{"sender":, "text":}, ...], "me": "...", "title": "..."}
    # or a bare list of {sender,text}
    if isinstance(data, dict):
        messages = data.get('messages')
        if messages is None or not isinstance(messages, list):
            raise ValueError('JSON must contain a "messages" array of objects with sender/text')
        me = data.get('me')
        title = data.get('title')
        chat_type = data.get('type') or data.get('chat_type')
        contact = data.get('contact') or data.get('other')
    elif isinstance(data, list):
        messages = data
        me = None
        title = None
        chat_type = None
        contact = None
    else:
        raise ValueError('Unsupported script format')
    # Normalize to list of tuples
    normalized = []
    for m in messages:
        if isinstance(m, dict):
            sender = m.get('sender') or m.get('name')
            text = m.get('text')
        elif isinstance(m, (list, tuple)) and len(m) >= 2:
            sender, text = m[0], m[1]
        else:
            raise ValueError('Each message must be an object with sender/text or a 2-item array')
        if not isinstance(sender, str) or not isinstance(text, str):
            raise ValueError('sender and text must be strings')
        normalized.append((sender, text))
    return me, title, normalized, chat_type, contact

def parse_args():
    p = argparse.ArgumentParser(description='Render iMessage-style chat video from a JSON script')
    p.add_argument('--script', '-s', default=DEFAULT_SCRIPT, help=f'Path to JSON script file (default: {DEFAULT_SCRIPT})')
    p.add_argument('--me', help='Your sender name (blue bubbles)')
    p.add_argument('--title', help='Header title override (e.g., group name)')
    p.add_argument('--type', choices=['direct','group'], help='Conversation type: direct (1:1) or group')
    p.add_argument('--contact', help='Direct chat contact name (for type=direct)')
    p.add_argument('--output', '-o', default='imessage_story.mp4', help='Output video filename')
    p.add_argument('--fps', type=int, default=24, help='Output FPS')
    return p.parse_args()

def draw_status_bar(draw):
    """Minimal status bar: show current time only (clean iOS-like)."""
    def current_time_str():
        now = datetime.datetime.now()
        try:
            return now.strftime("%-I:%M")
        except Exception:
            return now.strftime("%I:%M").lstrip("0")
    time_str = current_time_str()
    time_width = draw.textlength(time_str, font=TIME_FONT)
    time_x = (WIDTH - time_width) // 2
    draw.text((time_x, 8), time_str, font=TIME_FONT, fill=WHITE)

def draw_header(draw, title="Sam"):
    """Draw conversation header with proper spacing."""
    y0 = STATUS_BAR_H
    
    # Header background
    draw.rectangle([0, y0, WIDTH, y0 + HEADER_H], fill=NAV_BG)
    
    # Back button (left)
    back_x = 16
    back_y = y0 + (HEADER_H - 32) // 2
    # Chevron
    draw.polygon([(back_x + 12, back_y + 8), (back_x + 4, back_y + 16), (back_x + 12, back_y + 24)], 
                 fill=BLUE)
    # "Messages" text
    draw.text((back_x + 24, back_y - 2), "Messages", font=SMALL_FONT, fill=BLUE)
    
    # Title (centered)
    title_width = draw.textlength(title, font=FONT)
    title_x = (WIDTH - title_width) // 2
    draw.text((title_x, y0 + (HEADER_H - 34) // 2), title, font=FONT, fill=WHITE)
    
    # Info button (right)
    info_x = WIDTH - 44
    info_y = y0 + (HEADER_H - 28) // 2
    draw.ellipse([info_x, info_y, info_x + 28, info_y + 28], outline=BLUE, width=2)
    # "i" centered in circle
    i_width = draw.textlength("i", font=SMALL_FONT)
    draw.text((info_x + (28 - i_width) // 2, info_y + 2), "i", font=SMALL_FONT, fill=BLUE)

def compute_group_title(participants):
    others = [p for p in participants if p != ME_NAME]
    if not others:
        return ME_NAME
    title = ", ".join(others[:3])
    if len(others) > 3:
        title += f" +{len(others)-3}"
    return title

_EMOJI_REGEX = re.compile(r"[\U0001F000-\U0001FAFF\U00002700-\U000027BF\U0001F900-\U0001F9FF]")

def _approx_textlength(draw, text, font):
    # Replace emoji with two 'M' characters to approximate width
    if not text:
        return 0
    approximated = _EMOJI_REGEX.sub("MM", text)
    return draw.textlength(approximated, font=font)

def wrap_text(draw, text, max_width):
    lines = []
    words = text.split(" ")
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if _approx_textlength(draw, test, FONT) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def bubble_size(draw, text, max_width):
    padding = 16
    lines = wrap_text(draw, text, max_width)
    text_width = max(draw.textlength(l, font=FONT) for l in lines) if lines else 0
    text_height = max(1, len(lines)) * 42  # Tighter line spacing
    return (text_width + padding * 2, text_height + padding * 2, lines)

def draw_bubble(img, draw, text, side, y_offset, name=None, max_width=None, clip_top=None):
    padding = 16
    max_width = max_width or (WIDTH - 100)  # More generous width
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

    # Name label for group chats
    if name and side == "left":
        name_y = y0 - 28
        if clip_top is None or name_y >= clip_top:
            draw.text((x0 + 6, name_y), name, font=SMALL_FONT, fill=TEXT_SUBTLE)

    # Bubble with proper iOS radius
    draw.rounded_rectangle([x0, y0, x0 + bubble_w, y0 + bubble_h], 20, fill=color)
    
    # Tail (smaller and more subtle)
    if side == "left":
        tail = [(x0 + 12, y0 + bubble_h - 6), (x0 - 4, y0 + bubble_h + 6), (x0 + 12, y0 + bubble_h - 18)]
        draw.polygon(tail, fill=color)
    else:
        x1 = x0 + bubble_w
        tail = [(x1 - 12, y0 + bubble_h - 6), (x1 + 4, y0 + bubble_h + 6), (x1 - 12, y0 + bubble_h - 18)]
        draw.polygon(tail, fill=color)

    # Text
    y_text = y0 + padding
    for l in lines:
        draw_text_with_emoji(img, draw, (x0 + padding, y_text), l, FONT, txt_color)
        y_text += 42

    return bubble_w, bubble_h

def draw_chat_base(draw, title="Chat"):
    draw_status_bar(draw)
    draw_header(draw, title=title)

def draw_home_indicator(draw):
    # iPhone home indicator
    cx = WIDTH // 2
    y = HEIGHT - 20
    draw.rounded_rectangle([cx - 67, y - 2, cx + 67, y + 2], 2, fill=(134, 134, 139))

MAX_INPUT_LINES = 6
INPUT_SIDE_MARGIN = 12
INPUT_FIELD_LEFT_ICON_W = 40  # space for camera/plus inside field
INPUT_INNER_PAD_X = 8
INPUT_INNER_PAD_Y = 8
INPUT_LINE_HEIGHT = 36

def _wrap_text_for_width(draw, text, max_width):
    """Word-wrap text to fit max_width using current FONT."""
    if not text:
        return [""]
    words = text.split(" ")
    lines = []
    line = ""
    for w in words:
        candidate = (line + " " + w).strip()
        if draw.textlength(candidate, font=FONT) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            # If a single word is longer than width, hard-wrap it
            if draw.textlength(w, font=FONT) > max_width:
                buf = ""
                for ch in w:
                    if draw.textlength(buf + ch, font=FONT) <= max_width:
                        buf += ch
                    else:
                        lines.append(buf)
                        buf = ch
                line = buf
            else:
                line = w
    if line:
        lines.append(line)
    return lines

def compute_input_layout(draw, text):
    """Compute dynamic input bar height, y-position, and wrapped lines."""
    field_width = WIDTH - INPUT_SIDE_MARGIN * 2 - 56  # leave space for send button
    text_area_width = field_width - INPUT_FIELD_LEFT_ICON_W - INPUT_INNER_PAD_X*2
    lines_full = _wrap_text_for_width(draw, text, text_area_width) if text else [""]
    lines = lines_full[-MAX_INPUT_LINES:]
    needed_h = INPUT_INNER_PAD_Y*2 + max(1, len(lines)) * INPUT_LINE_HEIGHT
    bar_h = max(INPUT_BAR_H, needed_h)
    bar_y = HEIGHT - KEYBOARD_H - bar_h - 8
    return {
        "bar_y": bar_y,
        "bar_h": bar_h,
        "field_width": field_width,
        "text_lines": lines,
        "text_area_width": text_area_width,
    }

def draw_input_bar(img, draw, text):
    """Draw input bar above keyboard with multi-line growth and wrapping."""
    layout = compute_input_layout(draw, text or "")
    bar_y = layout["bar_y"]
    bar_h = layout["bar_h"]
    field_width = layout["field_width"]
    lines = layout["text_lines"]

    # Background strip behind the input
    draw.rectangle([0, bar_y - 8, WIDTH, bar_y + bar_h + 8], fill=KEYBOARD_BG)

    # Input field
    margin = INPUT_SIDE_MARGIN
    draw.rounded_rectangle([margin, bar_y, margin + field_width, bar_y + bar_h],
                          22, fill=INPUT_BG, outline=(58, 58, 60), width=1)

    # Camera/plus icon inside field
    icon_x = margin + 12
    icon_y = bar_y + 12
    draw.ellipse([icon_x, icon_y, icon_x + 24, icon_y + 24], outline=(142, 142, 147), width=2)
    draw.line([icon_x + 12, icon_y + 6, icon_x + 12, icon_y + 18], fill=(142, 142, 147), width=2)
    draw.line([icon_x + 6, icon_y + 12, icon_x + 18, icon_y + 12], fill=(142, 142, 147), width=2)

    # Send button (right, vertically centered)
    send_x = WIDTH - margin - 44
    send_y = bar_y + (bar_h - 44) // 2
    draw.ellipse([send_x, send_y, send_x + 44, send_y + 44], fill=BLUE)

    # Up arrow (send icon)
    arrow_x = send_x + 22
    arrow_y = send_y + 12
    draw.polygon([(arrow_x, arrow_y), (arrow_x - 6, arrow_y + 8), (arrow_x - 2, arrow_y + 8),
                  (arrow_x - 2, arrow_y + 20), (arrow_x + 2, arrow_y + 20), (arrow_x + 2, arrow_y + 8),
                  (arrow_x + 6, arrow_y + 8)], fill=WHITE)

    # Draw wrapped text lines inside field
    if lines:
        text_x = margin + INPUT_FIELD_LEFT_ICON_W + INPUT_INNER_PAD_X
        text_y = bar_y + INPUT_INNER_PAD_Y
        for l in lines:
            draw_text_with_emoji(img, draw, (text_x, text_y), l, FONT, WHITE)
            text_y += INPUT_LINE_HEIGHT

EMOJI_WARNED = False
EMOJI_LOGGED = False

def draw_text_with_emoji(img, draw, pos, text, font, fill):
    global EMOJI_WARNED, EMOJI_LOGGED
    # Ensure integer coordinates for PIL/Pilmoji paste
    try:
        x, y = pos
        pos = (int(round(x)), int(round(y)))
    except Exception:
        pass
    if PILMOJI_AVAILABLE:
        # Prefer a concrete local emoji font source
        if EmojiFontSource and EMOJI_FONT_PATH:
            try:
                if not EMOJI_LOGGED:
                    print(f"Using EmojiFontSource: {EMOJI_FONT_PATH}")
                    EMOJI_LOGGED = True
                with Pilmoji(img, source=EmojiFontSource(EMOJI_FONT_PATH)) as pilmoji:
                    pilmoji.text(pos, text, font=font, fill=fill)
                    return
            except Exception:
                # Fall back to default pilmoji behavior
                if not EMOJI_WARNED:
                    print("Failed to use EmojiFontSource, falling back to other sources.")
                pass
        # Try built-in sources when present
        try:
            if NotoEmojiSource:
                if not EMOJI_LOGGED:
                    print("Using NotoEmojiSource()")
                    EMOJI_LOGGED = True
                with Pilmoji(img, source=NotoEmojiSource()) as pilmoji:
                    pilmoji.text(pos, text, font=font, fill=fill)
                    return
        except Exception:
            pass
        try:
            if AppleEmojiSource:
                if not EMOJI_LOGGED:
                    print("Using AppleEmojiSource()")
                    EMOJI_LOGGED = True
                with Pilmoji(img, source=AppleEmojiSource()) as pilmoji:
                    pilmoji.text(pos, text, font=font, fill=fill)
                    return
        except Exception:
            pass
        if not EMOJI_LOGGED:
            print("Using Pilmoji default source (may require network).")
            EMOJI_LOGGED = True
        with Pilmoji(img) as pilmoji:
            pilmoji.text(pos, text, font=font, fill=fill)
            return
    # Fallback without pilmoji
    if _EMOJI_REGEX.search(text) and not EMOJI_WARNED:
        print("Emoji still missing. Debug:")
        print(f"  PILMOJI_AVAILABLE={PILMOJI_AVAILABLE}")
        print(f"  EmojiFontSource={'yes' if EmojiFontSource else 'no'}")
        print(f"  EMOJI_FONT_PATH={EMOJI_FONT_PATH}")
        print("  Hint: set EMOJI_FONT_PATH=/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
        EMOJI_WARNED = True
    draw.text(pos, text, font=font, fill=fill)

# Updated keyboard layout with proper positioning
KEY_ROWS = [
    "QWERTYUIOP",
    "ASDFGHJKL", 
    "ZXCVBNM"
]

def _compute_key_positions():
    positions = {}
    kb_top = HEIGHT - KEYBOARD_H
    key_height = 54
    row_spacing = 12
    
    # Letter rows
    for r, row in enumerate(KEY_ROWS):
        key_width = 66 if r < 2 else 74  # Slightly wider for bottom row
        total_width = len(row) * key_width + (len(row) - 1) * 8
        x_start = (WIDTH - total_width) // 2
        
        # Offset middle row slightly
        if r == 1:
            x_start += 16
        elif r == 2:
            x_start += 32
            
        y = kb_top + 12 + r * (key_height + row_spacing)
        
        for i, char in enumerate(row):
            x = x_start + i * (key_width + 8)
            positions[char] = (x, y, x + key_width, y + key_height)
            positions[char.lower()] = (x, y, x + key_width, y + key_height)
    
    # Special bottom row
    y = kb_top + 12 + 3 * (key_height + row_spacing)
    
    # Shift key
    shift_width = 84
    positions['shift'] = (16, y, 16 + shift_width, y + key_height)
    
    # Delete key  
    delete_width = 84
    delete_x = WIDTH - 16 - delete_width
    positions['delete'] = (delete_x, y, delete_x + delete_width, y + key_height)
    
    # Space row
    space_y = y + key_height + row_spacing
    positions['123'] = (16, space_y, 90, space_y + key_height)
    positions['emoji'] = (98, space_y, 164, space_y + key_height)
    positions[' '] = (172, space_y, WIDTH - 172, space_y + key_height)
    positions['return'] = (WIDTH - 164, space_y, WIDTH - 16, space_y + key_height)
    
    return positions, kb_top

KEY_POSITIONS, KB_TOP = _compute_key_positions()

def draw_keyboard(draw, highlight=None):
    """Draw iOS-style keyboard."""
    # Keyboard background
    draw.rectangle([0, KB_TOP, WIDTH, HEIGHT], fill=KEYBOARD_BG)
    
    # Draw all keys
    for key_name, (x0, y0, x1, y1) in KEY_POSITIONS.items():
        if key_name.islower():
            continue
            
        # Key highlight
        fill_color = KEY_FILL
        if highlight and (key_name == highlight or key_name.lower() == highlight.lower()):
            fill_color = KEY_HL
            
        # Key background
        draw.rounded_rectangle([x0, y0, x1, y1], 8, fill=fill_color)
        
        # Key labels
        label_x = (x0 + x1) // 2
        label_y = (y0 + y1) // 2 - 14
        
        if key_name == 'shift':
            # Shift arrow
            draw.polygon([(label_x, label_y + 8), (label_x - 8, label_y + 16), 
                         (label_x - 4, label_y + 16), (label_x - 4, label_y + 20),
                         (label_x + 4, label_y + 20), (label_x + 4, label_y + 16), 
                         (label_x + 8, label_y + 16)], fill=WHITE)
        elif key_name == 'delete':
            # Delete icon (backspace)
            draw.polygon([(label_x - 8, label_y + 12), (label_x - 4, label_y + 8), 
                         (label_x + 8, label_y + 8), (label_x + 8, label_y + 16), 
                         (label_x - 4, label_y + 16)], fill=WHITE)
        elif key_name == '123':
            draw.text((label_x - 16, label_y), "123", font=SMALL_FONT, fill=WHITE)
        elif key_name == 'emoji':
            # Better emoji face
            face_size = 20
            face_x = label_x - face_size//2
            face_y = label_y + 8
            
            # Face outline
            draw.ellipse([face_x, face_y, face_x + face_size, face_y + face_size], 
                        outline=WHITE, width=2)
            
            # Eyes
            eye_size = 3
            left_eye_x = face_x + 5
            right_eye_x = face_x + 12
            eye_y = face_y + 6
            draw.ellipse([left_eye_x, eye_y, left_eye_x + eye_size, eye_y + eye_size], fill=WHITE)
            draw.ellipse([right_eye_x, eye_y, right_eye_x + eye_size, eye_y + eye_size], fill=WHITE)
            
            # Smile
            smile_x = face_x + 6
            smile_y = face_y + 10
            smile_width = 8
            smile_height = 6
            draw.arc([smile_x, smile_y, smile_x + smile_width, smile_y + smile_height], 
                    0, 180, fill=WHITE, width=2)
        elif key_name == 'return':
            draw.text((label_x - 24, label_y), "return", font=SMALL_FONT, fill=WHITE)
        elif key_name == ' ':
            # Space bar (no label needed)
            pass
        else:
            # Regular letter
            text_width = draw.textlength(key_name, font=FONT)
            draw.text((label_x - text_width // 2, label_y), key_name, font=FONT, fill=WHITE)

def render_chat_frame(history, typing=None, title="Chat", input_text=None, highlight_key=None):
    """Render a chat frame with proper layout."""
    img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
    draw = ImageDraw.Draw(img)
    
    # Draw content first; draw header/status last so they stay above content
    content_top = CHAT_TOP_Y + TOP_PADDING
    
    # Calculate available space
    keyboard_visible = input_text is not None
    if keyboard_visible:
        layout = compute_input_layout(draw, input_text or "")
        viewport_bottom = layout["bar_y"] - 12
    else:
        viewport_bottom = HEIGHT - BOTTOM_SAFE - 16
    
    # Calculate content height and scroll offset
    content_bottom = CHAT_TOP_Y + TOP_PADDING
    for msg in history:
        tmp_img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
        tmp_draw = ImageDraw.Draw(tmp_img)
        bw, bh, _ = bubble_size(tmp_draw, msg['text'], WIDTH - 100)
        content_bottom = max(content_bottom, msg['y'] + bh)
    
    if typing and typing.get('type') == 'dots':
        content_bottom = max(content_bottom, typing['y'] + 60)
    
    scroll_offset = max(0, content_bottom + 20 - viewport_bottom)
    
    # Draw messages (cull outside viewport; clip name label above header)
    for msg in history:
        y_draw = msg['y'] - scroll_offset
        # measure bubble for culling
        tmp_img2 = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
        tmp_draw2 = ImageDraw.Draw(tmp_img2)
        bw2, bh2, _ = bubble_size(tmp_draw2, msg['text'], WIDTH - 100)
        if y_draw + bh2 < content_top:
            continue
        if y_draw > viewport_bottom:
            continue
        draw_bubble(img, draw, msg['text'], msg['side'], y_draw, name=msg.get('name'), clip_top=content_top)
    
    # Typing indicator
    if typing and typing.get('type') == 'dots':
        bubble_w, bubble_h = 80, 48
        x0 = 16
        y0 = typing['y'] - scroll_offset
        if y0 < content_top:
            y0 = content_top
        draw.rounded_rectangle([x0, y0, x0 + bubble_w, y0 + bubble_h], 20, fill=GREY)
        
        # Animated dots
        for j in range(typing.get('dots', 0)):
            dot_x = x0 + 20 + j * 20
            dot_y = y0 + 24
            draw.ellipse([dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4], fill=(174, 174, 178))
        
        if typing.get('name'):
            draw.text((x0 + 6, y0 - 28), typing['name'], font=SMALL_FONT, fill=TEXT_SUBTLE)
    
    # Input and keyboard
    if keyboard_visible:
        draw_input_bar(img, draw, input_text)
        draw_keyboard(draw, highlight=highlight_key)
    else:
        draw_home_indicator(draw)
    # Finally, draw status/header on top to avoid any overlap
    draw_chat_base(draw, title=title)

    return img

def typing_indicator(name, y_offset=CHAT_TOP_Y + TOP_PADDING + 40, title="Chat", history=None):
    """Typing dots animation."""
    history = history or []
    frames = []
    for i in range(1, 4):
        img = render_chat_frame(
            history,
            typing={"type": "dots", "name": name, "y": y_offset, "dots": i},
            title=title
        )
        frames.append(ImageClip(np.array(img)).set_duration(0.4))
    return concatenate_videoclips(frames)

def typing_keyboard(text, title="Chat", history=None):
    """Keyboard typing animation with better text handling."""
    history = history or []
    frames = []
    typed = ""
    
    for char in text:
        typed += char
        highlight = char if char in KEY_POSITIONS else None
        
        # Handle special characters for highlighting
        if char == ' ':
            highlight = ' '
        elif char.isalpha():
            highlight = char.upper()
        elif char in '😳🙂😊😂🤔💭':  # Common emoji
            highlight = 'emoji'
        
        img = render_chat_frame(history, title=title, input_text=typed, highlight_key=highlight)
        duration = random.uniform(0.04, 0.08) if char.strip() else random.uniform(0.06, 0.12)
        frames.append(ImageClip(np.array(img)).set_duration(duration))
    
    # Hold final frame
    if frames:
        frames[-1] = frames[-1].set_duration(frames[-1].duration + 0.3)
    
    return concatenate_videoclips(frames)

def main():
    global ME_NAME, dialogue
    args = parse_args()

    script_me = script_title = script_type = script_contact = None
    if args.script:
        script_me, script_title, loaded, script_type, script_contact = load_script(args.script)
        dialogue = loaded
    # Resolve ME_NAME priority: CLI > script > default
    if args.me:
        ME_NAME = args.me
    elif script_me:
        ME_NAME = script_me

    # Determine conversation type and primary contact (for direct)
    chat_type = args.type or script_type
    # Infer type if not provided
    if not chat_type:
        participants = list(dict.fromkeys([n for n, _ in dialogue if n != ME_NAME]))
        chat_type = 'direct' if len(participants) <= 1 else 'group'

    contact = args.contact or script_contact
    if chat_type == 'direct':
        # Infer contact if missing: first non-me sender in the script
        if not contact:
            for n, _ in dialogue:
                if n != ME_NAME:
                    contact = n
                    break
        if not contact:
            raise ValueError('For type=direct, could not infer contact (no non-me sender found). Provide --contact or set "contact" in script.')
        group_title = None
    else:
        # Group chat title
        participants = list(dict.fromkeys([n for n, _ in dialogue]))
        group_title = args.title or script_title or compute_group_title(participants)

    clips = []
    # Per-chat state for direct conversations
    chat_states = {}
    history = []
    y_offset = CHAT_TOP_Y + TOP_PADDING + 40

    def open_chat(title, history):
        # Show current chat view (with existing history) to simulate switching
        frame = render_chat_frame(history, title=title)
        clips.append(ImageClip(np.array(frame)).set_duration(0.6))

    if chat_type == 'direct':
        current_peer = contact
        # initialize state for the first peer if not exists
        if current_peer not in chat_states:
            chat_states[current_peer] = {"history": [], "y": CHAT_TOP_Y + TOP_PADDING + 40}
        history = chat_states[current_peer]["history"]
        y_offset = chat_states[current_peer]["y"]
        open_chat(current_peer, history)
        for name, text in dialogue:
            # Determine target peer for this message
            if name == ME_NAME:
                target_peer = current_peer
                side = 'right'
            else:
                target_peer = name
                side = 'left'

            # Switch chats if needed
            if target_peer != current_peer:
                current_peer = target_peer
                if current_peer not in chat_states:
                    chat_states[current_peer] = {"history": [], "y": CHAT_TOP_Y + TOP_PADDING + 40}
                history = chat_states[current_peer]["history"]
                y_offset = chat_states[current_peer]["y"]
                open_chat(current_peer, history)

            # Typing animation
            if side == 'right':
                clips.append(typing_keyboard(text, title=current_peer, history=history))
            else:
                clips.append(typing_indicator(name, y_offset=y_offset, title=current_peer, history=history))

            # Measure, append, render frame
            tmp_img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
            tmp_draw = ImageDraw.Draw(tmp_img)
            bubble_w, bubble_h, _ = bubble_size(tmp_draw, text, WIDTH - 100)

            history.append({
                "name": None,  # 1:1 chat: no left-side name label
                "text": text,
                "side": side,
                "y": y_offset
            })
            frame_img = render_chat_frame(history, title=current_peer)
            clips.append(ImageClip(np.array(frame_img)).set_duration(1.5))
            y_offset += bubble_h + 24
            # persist updated y for this chat
            chat_states[current_peer]["y"] = y_offset
    else:
        # Group chat — single room, show names on left if >2 participants
        show_names = True if len(participants) > 2 else False
        for name, text in dialogue:
            side = 'right' if name == ME_NAME else 'left'
            if side == 'right':
                clips.append(typing_keyboard(text, title=group_title, history=history))
            else:
                clips.append(typing_indicator(name, y_offset=y_offset, title=group_title, history=history))

            tmp_img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
            tmp_draw = ImageDraw.Draw(tmp_img)
            bubble_w, bubble_h, _ = bubble_size(tmp_draw, text, WIDTH - 100)

            history.append({
                "name": (name if (side == 'left' and show_names) else None),
                "text": text,
                "side": side,
                "y": y_offset
            })
            frame_img = render_chat_frame(history, title=group_title)
            clips.append(ImageClip(np.array(frame_img)).set_duration(1.5))
            y_offset += bubble_h + 24

    # Render final video
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(args.output, fps=args.fps)
    print(f"Video generated -> {args.output}")

if __name__ == '__main__':
    main()
