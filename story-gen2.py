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

# Video settings
WIDTH, HEIGHT = 720, 1280
# Layout constants (iPhone 15 Pro dimensions and spacing)
STATUS_BAR_H = 59  # iPhone 15 Pro status bar height
HEADER_H = 96      # Proper header height for navigation
CHAT_TOP_Y = STATUS_BAR_H + HEADER_H
TOP_PADDING = 12
BOTTOM_SAFE = 34   # iPhone 15 home indicator area
INPUT_BAR_H = 44   
KEYBOARD_H = 291   

# iPhone 15 Dark Mode colors (exact iOS 17 values)
CHAT_BG = (0, 0, 0)            # True black for OLED
BLUE = (0, 122, 255)           # iOS system blue
GREY = (48, 48, 50)            # Message bubble grey (darker)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TEXT_DARK = (255, 255, 255)
TEXT_SUBTLE = (142, 142, 147)  # iOS secondary label
NAV_BG = (28, 28, 30)          # Navigation bar background
SEPARATOR = (38, 38, 40)       # Subtle separators
KEYBOARD_BG = (0, 0, 0)        
KEY_FILL = (84, 84, 88)        # Key background
KEY_HL = (99, 99, 102)         # Key highlight
INPUT_BG = (58, 58, 60)        # Input field background

# Typography - iPhone 15 system fonts
try:
    # Try SF Pro Display equivalent
    FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
    SMALL_FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    TIME_FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
    HEADER_FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 38)
except Exception:
    try:
        # Fallback to Ubuntu fonts but larger for iPhone feel
        FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 36)
        SMALL_FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 30)
        TIME_FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 34)
        HEADER_FONT = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf", 40)
    except Exception:
        FONT = ImageFont.load_default()
        SMALL_FONT = ImageFont.load_default()
        TIME_FONT = ImageFont.load_default()
        HEADER_FONT = ImageFont.load_default()

# Random battery level (generated once per run)
BATTERY_LEVEL = random.randint(15, 100)
NETWORK_TYPE = "5G"  # Static network type for realism

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
    """iPhone 15 Pro status bar with pixel-perfect iOS accuracy."""
    def current_time_str():
        now = datetime.datetime.now()
        try:
            return now.strftime("%-I:%M")
        except Exception:
            return now.strftime("%I:%M").lstrip("0")
    time_str = current_time_str()

    # Time on left
    draw.text((24, 16), time_str, font=TIME_FONT, fill=WHITE)

    # Dynamic Island (more accurate)
    island_width = 108
    island_height = 34
    island_x = (WIDTH - island_width) // 2
    island_y = 12
    draw.rounded_rectangle([island_x, island_y, island_x + island_width, island_y + island_height],
                           island_height // 2, fill=(18, 18, 18))

    # --- Status icons on the same baseline ---
    baseline_y = 22  # Common baseline for all status elements

    # Battery (right-aligned)
    right_margin = 18
    battery_width = 26
    battery_height = 13
    battery_x = WIDTH - right_margin - battery_width
    battery_y = baseline_y - battery_height//2  # Center on baseline
    
    # Battery outline
    draw.rounded_rectangle([battery_x, battery_y, battery_x + battery_width, battery_y + battery_height],
                           3, fill=None, outline=WHITE, width=1)
    draw.rectangle([battery_x + battery_width, battery_y + 4, 
                  battery_x + battery_width + 2, battery_y + battery_height - 4], fill=WHITE)
    
    # Battery fill
    fill_width = int((battery_width - 4) * (BATTERY_LEVEL / 100))
    fill_color = (52, 199, 89) if BATTERY_LEVEL > 20 else (255, 59, 48)
    if fill_width > 0:
        draw.rounded_rectangle([battery_x + 2, battery_y + 2, 
                              battery_x + 2 + fill_width, battery_y + battery_height - 2],
                               2, fill=fill_color)

    # 5G text - aligned on same baseline
    network_type = "5G"
    netw_w = draw.textlength(network_type, font=SMALL_FONT)
    # Calculate vertical position to align with baseline
    bbox = SMALL_FONT.getbbox(network_type)
    network_height = bbox[3] - bbox[1]
    network_x = battery_x - 10 - netw_w
    network_y = baseline_y - network_height + 6  # Adjust to match baseline
    draw.text((network_x, network_y), network_type, font=SMALL_FONT, fill=WHITE)

    # Signal bars - aligned with 5G text
    bars_right = network_x - 8
    bar_width = 3
    bar_gap = 4
    bar_max_height = 14  # Maximum height of signal bars
    
    for i in range(4):  # iPhone 15 has 4 signal bars
        bar_height = 6 + i * 3 if i < 3 else 14  # Last bar is tallest
        bar_x = bars_right - (4 - i) * (bar_width + bar_gap)
        # Align bottoms of bars with baseline
        bar_y = baseline_y - bar_height + 7  # Adjustment to align with baseline
        fill_color = WHITE if i < 3 else (152, 152, 157)  # Last bar dimmed
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=fill_color)
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + 2], 1, fill=fill_color)

def draw_header(draw, title="Messages"):
    """iPhone 15 Messages app header with realistic design."""
    y0 = STATUS_BAR_H
    
    # Header background
    draw.rectangle([0, y0, WIDTH, y0 + HEADER_H], fill=NAV_BG)
    
    # Back button
    back_x = 16
    back_y = y0 + HEADER_H/2
    draw.line([(back_x + 10, back_y - 9), (back_x + 2, back_y)], fill=BLUE, width=2)
    draw.line([(back_x + 2, back_y), (back_x + 10, back_y + 9)], fill=BLUE, width=2)
    
    # Avatar with perfectly centered initials
    avatar_size = 40
    avatar_x = (WIDTH - avatar_size) // 2
    avatar_y = y0 + 14
    avatar_color = (72, 72, 74)
    
    # Draw avatar circle
    draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size], fill=avatar_color)
    
    # Extract first letters of words in title, max 2 letters
    initials = "".join(word[0] for word in title.split()[:2] if word).upper()
    if not initials:
        initials = "?"
    
    # Precisely position the text in the center of the circle
    initials_width = draw.textlength(initials, font=FONT)
    
    # Use proper text bbox calculation for vertical centering
    bbox = FONT.getbbox(initials)
    initials_height = bbox[3] - bbox[1] if bbox else 0
    text_ascent = bbox[1] if bbox else 0
    
    # Center horizontally and vertically (accounting for font metrics)
    initials_x = avatar_x + (avatar_size - initials_width) // 2
    # The -2 adjustment fine-tunes vertical alignment based on how SF Pro renders
    initials_y = avatar_y + (avatar_size - initials_height) // 2 - text_ascent - 2
    
    draw.text((initials_x, initials_y), initials, font=FONT, fill=WHITE)
    
    # Contact name below avatar
    title_width = draw.textlength(title, font=SMALL_FONT)
    title_x = (WIDTH - title_width) // 2
    draw.text((title_x, avatar_y + avatar_size + 8), title, font=SMALL_FONT, fill=WHITE)
    
    # Call and Video icons (right side) - accurate iOS style
    video_x = WIDTH - 52
    video_y = y0 + HEADER_H/2 - 16
    draw.rounded_rectangle([video_x, video_y, video_x + 28, video_y + 32], 8, fill=BLUE)
    draw.ellipse([video_x + 10, video_y + 8, video_x + 18, video_y + 16], fill=NAV_BG)
    draw.ellipse([video_x + 20, video_y + 8, video_x + 22, video_y + 10], fill=(52, 199, 89))
    phone_x = WIDTH - 104
    phone_y = y0 + HEADER_H/2 - 16
    draw.ellipse([phone_x, phone_y, phone_x + 32, phone_y + 32], fill=BLUE)
    ph_x, ph_y = phone_x + 16, phone_y + 16
    draw.rounded_rectangle([ph_x - 5, ph_y - 10, ph_x + 5, ph_y - 6], 2, fill=NAV_BG)
    draw.line([ph_x, ph_y - 6, ph_x, ph_y + 4], fill=NAV_BG, width=3)
    draw.rounded_rectangle([ph_x - 5, ph_y + 4, ph_x + 5, ph_y + 8], 2, fill=NAV_BG)
    draw.line([0, y0 + HEADER_H - 1, WIDTH, y0 + HEADER_H - 1], fill=SEPARATOR, width=1)

def compute_group_title(participants):
    others = [p for p in participants if p != ME_NAME]
    if not others:
        return ME_NAME
    title = ", ".join(others[:3])
    if len(others) > 3:
        title += f" +{len(others)-3}"
    return title

_EMOJI_REGEX = re.compile(r"[\U0001F000-\U0001FAFF\U00002700-\U000027BF\U0001F900-\U0001F9FF]")

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
    padding = 18  # iPhone 15 bubble padding
    lines = wrap_text(draw, text, max_width)
    text_width = max(draw.textlength(l, font=FONT) for l in lines) if lines else 0
    text_height = max(1, len(lines)) * 44  # iPhone line height
    return (text_width + padding * 2, text_height + padding * 2, lines)

def draw_bubble(img, draw, text, side, y_offset, name=None, max_width=None, clip_top=None):
    padding = 18
    max_width = max_width or (WIDTH - 120)  # More realistic max width
    bubble_w, bubble_h, lines = bubble_size(draw, text, max_width)
    
    if side == "left":
        x0 = 20  # More spacing from edge
        color = GREY
        txt_color = TEXT_DARK
    else:
        x0 = WIDTH - bubble_w - 20
        color = BLUE
        txt_color = WHITE
    
    y0 = y_offset

    # Name label for group chats (smaller, more subtle)
    if name and side == "left":
        name_y = y0 - 26
        if clip_top is None or name_y >= clip_top:
            draw.text((x0 + 8, name_y), name, font=SMALL_FONT, fill=TEXT_SUBTLE)

    # iPhone 15 bubble style with proper radius
    radius = 22  # iPhone bubble radius
    draw.rounded_rectangle([x0, y0, x0 + bubble_w, y0 + bubble_h], radius, fill=color)
    
    # Tail (more subtle and iPhone-like)
    if side == "left":
        tail_points = [(x0 + 16, y0 + bubble_h - 8), (x0 - 6, y0 + bubble_h + 4), (x0 + 16, y0 + bubble_h - 20)]
        draw.polygon(tail_points, fill=color)
    else:
        x1 = x0 + bubble_w
        tail_points = [(x1 - 16, y0 + bubble_h - 8), (x1 + 6, y0 + bubble_h + 4), (x1 - 16, y0 + bubble_h - 20)]
        draw.polygon(tail_points, fill=color)

    # Text with proper line spacing
    y_text = y0 + padding
    for l in lines:
        draw.text((x0 + padding, y_text), l, font=FONT, fill=txt_color)
        y_text += 44

    return bubble_w, bubble_h

def draw_chat_base(draw, title="Chat"):
    draw_status_bar(draw)
    draw_header(draw, title=title)

def draw_home_indicator(draw):
    """iPhone 15 home indicator with realistic blur and shadow."""
    cx = WIDTH // 2
    y = HEIGHT - 18
    indicator_width = 134
    indicator_height = 5

    # Subtle blurred/gradient background at bottom
    for i in range(24):
        alpha = int(255 * (1 - i / 24) * 0.10)
        color = (28, 28, 30, alpha)
        draw.rectangle([0, HEIGHT - 24 + i, WIDTH, HEIGHT - 24 + i + 1], fill=color)

    # Home indicator pill with subtle drop shadow
    shadow_color = (50, 50, 55)
    draw.rounded_rectangle([cx - indicator_width//2, y - indicator_height//2 + 1,
                            cx + indicator_width//2, y + indicator_height//2 + 1],
                           indicator_height//2 + 1, fill=shadow_color)
    draw.rounded_rectangle([cx - indicator_width//2, y - indicator_height//2,
                            cx + indicator_width//2, y + indicator_height//2],
                           indicator_height//2, fill=(200, 200, 205))

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
    """iPhone 15 style input bar with proper styling."""
    layout = compute_input_layout(draw, text or "")
    bar_y = layout["bar_y"]
    bar_h = layout["bar_h"]
    field_width = layout["field_width"]
    lines = layout["text_lines"]

    # Background strip
    draw.rectangle([0, bar_y - 12, WIDTH, bar_y + bar_h + 12], fill=KEYBOARD_BG)

    # Input field with iPhone 15 styling
    margin = 16
    field_radius = 25  # More rounded like iOS
    
    draw.rounded_rectangle([margin, bar_y, margin + field_width, bar_y + bar_h],
                          field_radius, fill=INPUT_BG)

    # Plus icon (more iOS-like)
    icon_x = margin + 16
    icon_y = bar_y + (bar_h - 28) // 2
    icon_size = 28
    
    # Plus icon circle
    draw.ellipse([icon_x, icon_y, icon_x + icon_size, icon_y + icon_size], 
                outline=(142, 142, 147), width=2)
    
    # Plus symbol
    plus_center_x = icon_x + icon_size // 2
    plus_center_y = icon_y + icon_size // 2
    draw.line([plus_center_x - 6, plus_center_y, plus_center_x + 6, plus_center_y], 
             fill=(142, 142, 147), width=2)
    draw.line([plus_center_x, plus_center_y - 6, plus_center_x, plus_center_y + 6], 
             fill=(142, 142, 147), width=2)

    # Send button (iPhone 15 style)
    send_size = 36
    send_x = WIDTH - margin - send_size - 8
    send_y = bar_y + (bar_h - send_size) // 2
    
    # Send button circle
    draw.ellipse([send_x, send_y, send_x + send_size, send_y + send_size], fill=BLUE)

    # Up arrow (more refined)
    arrow_center_x = send_x + send_size // 2
    arrow_center_y = send_y + send_size // 2
    arrow_points = [
        (arrow_center_x, arrow_center_y - 8),
        (arrow_center_x - 6, arrow_center_y - 2),
        (arrow_center_x - 2, arrow_center_y - 2),
        (arrow_center_x - 2, arrow_center_y + 8),
        (arrow_center_x + 2, arrow_center_y + 8),
        (arrow_center_x + 2, arrow_center_y - 2),
        (arrow_center_x + 6, arrow_center_y - 2)
    ]
    draw.polygon(arrow_points, fill=WHITE)

    # Text with proper positioning
    if lines:
        text_x = margin + 56  # Account for plus icon
        text_y = bar_y + (bar_h - len(lines) * 36) // 2 + 6
        for l in lines:
            draw.text((text_x, text_y), l, font=FONT, fill=WHITE)
            text_y += 36

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
    positions[' '] = (98, space_y, WIDTH - 172, space_y + key_height)
    positions['return'] = (WIDTH - 164, space_y, WIDTH - 16, space_y + key_height)
    
    return positions, kb_top

KEY_POSITIONS, KB_TOP = _compute_key_positions()

def draw_keyboard(draw, highlight=None):
    """iPhone 15 style keyboard with proper key styling."""
    # Keyboard background
    draw.rectangle([0, KB_TOP, WIDTH, HEIGHT], fill=KEYBOARD_BG)
    
    # Draw all keys with iPhone 15 styling
    for key_name, (x0, y0, x1, y1) in KEY_POSITIONS.items():
        if key_name.islower():
            continue
            
        # Key styling
        fill_color = KEY_FILL
        if highlight and (key_name == highlight or key_name.lower() == highlight.lower()):
            fill_color = KEY_HL
            
        # Key background with proper radius
        key_radius = 10  # iPhone key radius
        draw.rounded_rectangle([x0, y0, x1, y1], key_radius, fill=fill_color)
        
        # Subtle key shadow (bottom edge)
        shadow_color = (20, 20, 22)
        draw.rounded_rectangle([x0, y1 - 2, x1, y1], key_radius, fill=shadow_color)
        draw.rounded_rectangle([x0, y0, x1, y1 - 2], key_radius, fill=fill_color)
        
        # Key labels with proper positioning
        label_x = (x0 + x1) // 2
        label_y = (y0 + y1) // 2 - 16
        
        if key_name == 'shift':
            # Shift arrow (more iOS-like)
            arrow_points = [
                (label_x, label_y + 6),
                (label_x - 8, label_y + 14),
                (label_x - 4, label_y + 14),
                (label_x - 4, label_y + 22),
                (label_x + 4, label_y + 22),
                (label_x + 4, label_y + 14),
                (label_x + 8, label_y + 14)
            ]
            draw.polygon(arrow_points, fill=WHITE)
        elif key_name == 'delete':
            # Delete icon (backspace - more refined)
            delete_points = [
                (label_x - 10, label_y + 14),
                (label_x - 6, label_y + 10),
                (label_x + 8, label_y + 10),
                (label_x + 8, label_y + 18),
                (label_x - 6, label_y + 18)
            ]
            draw.polygon(delete_points, fill=WHITE)
            # X mark in delete key
            draw.line([label_x - 2, label_y + 12, label_x + 4, label_y + 16], fill=KEYBOARD_BG, width=2)
            draw.line([label_x + 4, label_y + 12, label_x - 2, label_y + 16], fill=KEYBOARD_BG, width=2)
        elif key_name == '123':
            text_width = draw.textlength("123", font=SMALL_FONT)
            draw.text((label_x - text_width // 2, label_y + 2), "123", font=SMALL_FONT, fill=WHITE)
        elif key_name == 'return':
            text_width = draw.textlength("return", font=SMALL_FONT)
            draw.text((label_x - text_width // 2, label_y + 2), "return", font=SMALL_FONT, fill=WHITE)
        elif key_name == ' ':
            # Space bar gets "space" label
            space_width = draw.textlength("space", font=SMALL_FONT)
            draw.text((label_x - space_width // 2, label_y + 2), "space", 
                     font=SMALL_FONT, fill=(160, 160, 165))
        else:
            # Regular letter keys
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
    
    # Simplified content height calculation - no redundant image creation
    content_bottom = CHAT_TOP_Y + TOP_PADDING
    for msg in history:
        content_bottom = max(content_bottom, msg['y'] + msg.get('height', 60))
    
    if typing and typing.get('type') == 'dots':
        content_bottom = max(content_bottom, typing['y'] + 60)
    
    scroll_offset = max(0, content_bottom + 20 - viewport_bottom)
    
    # Draw messages (simplified culling)
    for msg in history:
        y_draw = msg['y'] - scroll_offset
        if y_draw > viewport_bottom + 100:  # Simple cull check
            continue
        if y_draw < content_top - 100:
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
    
    draw_chat_base(draw, title=title)
    return img

def typing_indicator(name, y_offset=CHAT_TOP_Y + TOP_PADDING + 40, title="Chat", history=None):
    """Slightly slower typing dots animation."""
    history = history or []
    frames = []
    # Keep 2 frames but slightly longer duration
    for i in range(1, 3):
        img = render_chat_frame(
            history,
            typing={"type": "dots", "name": name, "y": y_offset, "dots": i},
            title=title
        )
        frames.append(ImageClip(np.array(img)).set_duration(0.5))  # Slower: 0.3 -> 0.5
    return concatenate_videoclips(frames)

def typing_keyboard(text, title="Chat", history=None):
    """Slightly slower keyboard typing animation for more realism."""
    history = history or []
    frames = []
    typed = ""
    
    # Skip every other character but with slightly longer durations
    for i, char in enumerate(text):
        typed += char
        if i % 2 == 0:  # Only animate every other character
            highlight = None
            if char == ' ':
                highlight = ' '
            elif char.isalpha():
                highlight = char.upper()
            
            img = render_chat_frame(history, title=title, input_text=typed, highlight_key=highlight)
            frames.append(ImageClip(np.array(img)).set_duration(0.08))  # Slightly slower: 0.05 -> 0.08
    
    # Final frame with complete text (longer pause)
    img = render_chat_frame(history, title=title, input_text=text)
    frames.append(ImageClip(np.array(img)).set_duration(0.4))  # Longer pause: 0.2 -> 0.4
    
    return concatenate_videoclips(frames)

def main():
    global ME_NAME, dialogue
    args = parse_args()

    print("Loading script and initializing...")
    script_me = script_title = script_type = script_contact = None
    if args.script:
        print(f"Loading script from: {args.script}")
        script_me, script_title, loaded, script_type, script_contact = load_script(args.script)
        dialogue = loaded
        print(f"Loaded {len(dialogue)} messages")
    
    # Resolve ME_NAME priority: CLI > script > default
    if args.me:
        ME_NAME = args.me
    elif script_me:
        ME_NAME = script_me
    print(f"Your name (blue bubbles): {ME_NAME}")

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
        print(f"Chat type: Direct conversation with {contact}")
    else:
        # Group chat title
        participants = list(dict.fromkeys([n for n, _ in dialogue]))
        group_title = args.title or script_title or compute_group_title(participants)
        print(f"Chat type: Group conversation - {group_title}")
        print(f"Participants: {', '.join(participants)}")

    clips = []
    # Per-chat state for direct conversations
    chat_states = {}
    history = []
    y_offset = CHAT_TOP_Y + TOP_PADDING + 40

    def open_chat(title, history):
        # Show current chat view (with existing history) to simulate switching
        frame = render_chat_frame(history, title=title)
        clips.append(ImageClip(np.array(frame)).set_duration(0.3))  # Shorter duration

    # Pre-calculate bubble sizes to avoid redundant calculations
    print("Pre-calculating bubble sizes...")
    bubble_cache = {}
    
    if chat_type == 'direct':
        current_peer = contact
        # initialize state for the first peer if not exists
        if current_peer not in chat_states:
            chat_states[current_peer] = {"history": [], "y": CHAT_TOP_Y + TOP_PADDING + 40}
        history = chat_states[current_peer]["history"]
        y_offset = chat_states[current_peer]["y"]
        print(f"Opening chat with {current_peer}")
        open_chat(current_peer, history)
        
        for i, (name, text) in enumerate(dialogue, 1):
            print(f"Processing message {i}/{len(dialogue)}: {name[:10]}...")
            
            # Determine target peer for this message
            if name == ME_NAME:
                target_peer = current_peer
                side = 'right'
            else:
                target_peer = name
                side = 'left'

            # Switch chats if needed
            if target_peer != current_peer:
                print(f"Switching to chat with {target_peer}")
                current_peer = target_peer
                if current_peer not in chat_states:
                    chat_states[current_peer] = {"history": [], "y": CHAT_TOP_Y + TOP_PADDING + 40}
                history = chat_states[current_peer]["history"]
                y_offset = chat_states[current_peer]["y"]
                open_chat(current_peer, history)

            # Typing animation
            if side == 'right':
                print(f"  Rendering keyboard typing animation...")
                clips.append(typing_keyboard(text, title=current_peer, history=history))
            else:
                print(f"  Rendering typing dots animation...")
                clips.append(typing_indicator(name, y_offset=y_offset, title=current_peer, history=history))

            # Calculate bubble size once
            if text not in bubble_cache:
                tmp_img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
                tmp_draw = ImageDraw.Draw(tmp_img)
                bubble_w, bubble_h, _ = bubble_size(tmp_draw, text, WIDTH - 100)
                bubble_cache[text] = (bubble_w, bubble_h)
            else:
                bubble_w, bubble_h = bubble_cache[text]

            history.append({
                "name": None,  # 1:1 chat: no left-side name label
                "text": text,
                "side": side,
                "y": y_offset,
                "height": bubble_h  # Cache height for performance
            })
            print(f"  Rendering message frame...")
            frame_img = render_chat_frame(history, title=current_peer)
            clips.append(ImageClip(np.array(frame_img)).set_duration(0.8))  # Shorter duration
            y_offset += bubble_h + 24
            # persist updated y for this chat
            chat_states[current_peer]["y"] = y_offset
    else:
        # Group chat — single room, show names on left if >2 participants
        show_names = True if len(participants) > 2 else False
        print(f"Starting group chat rendering (show names: {show_names})")
        
        for i, (name, text) in enumerate(dialogue, 1):
            print(f"Processing message {i}/{len(dialogue)}: {name[:10]}...")
            
            side = 'right' if name == ME_NAME else 'left'
            if side == 'right':
                print(f"  Rendering keyboard typing animation...")
                clips.append(typing_keyboard(text, title=group_title, history=history))
            else:
                print(f"  Rendering typing dots animation...")
                clips.append(typing_indicator(name, y_offset=y_offset, title=group_title, history=history))

            # Calculate bubble size once
            if text not in bubble_cache:
                tmp_img = Image.new("RGB", (WIDTH, HEIGHT), CHAT_BG)
                tmp_draw = ImageDraw.Draw(tmp_img)
                bubble_w, bubble_h, _ = bubble_size(tmp_draw, text, WIDTH - 100)
                bubble_cache[text] = (bubble_w, bubble_h)
            else:
                bubble_w, bubble_h = bubble_cache[text]

            history.append({
                "name": (name if (side == 'left' and show_names) else None),
                "text": text,
                "side": side,
                "y": y_offset,
                "height": bubble_h  # Cache height for performance
            })
            print(f"  Rendering message frame...")
            frame_img = render_chat_frame(history, title=group_title)
            clips.append(ImageClip(np.array(frame_img)).set_duration(0.8))  # Shorter duration
            y_offset += bubble_h + 24

    # Render final video with lower quality for speed
    print(f"\nCombining {len(clips)} video clips...")
    final = concatenate_videoclips(clips, method="compose")
    
    print(f"Encoding video to {args.output}...")
    print("This may take a moment depending on video length...")
    final.write_videofile(args.output, fps=args.fps, 
                         codec='libx264', 
                         preset='ultrafast',  # Fastest encoding
                         ffmpeg_params=['-crf', '28'])  # Lower quality for speed
    print(f"✅ Video generated successfully -> {args.output}")

if __name__ == '__main__':
    main()