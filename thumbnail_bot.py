import os
import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# --- Config ---
API_ID = os.environ.get("API_ID") 
API_HASH = os.environ.get("API_HASH") 
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = os.environ.get("ADMIN_ID")

app = Client("kenshin_pro", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
session_state = {}

# Fonts
FONT_TITLE = "fonts/font.ttf"
FONT_UI = "fonts/DejaVuSansCondensed-Bold.ttf"

def get_font(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

# ==========================================
# =           STYLE 2: UI LAYOUT           =
# ==========================================
def create_style_2_ui(data, output_path):
    W, H = 1280, 720
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    
    # 1. Full Background
    bg = Image.open(data['bg']).convert("RGBA").resize((W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(2)) # Slight blur
    canvas.paste(bg, (0, 0))
    
    # Dark Overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 120))
    canvas.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(canvas)

    # 2. Top Navigation (Search Bar & Branding)
    draw.text((50, 30), "KENSHIN ANIME", font=get_font(FONT_UI, 28), fill="#FFD700")
    # Search Bar Shape
    draw.rounded_rectangle([900, 25, 1230, 65], radius=20, fill="#333333")
    draw.text((920, 33), "🔍 Search Anime...", font=get_font(FONT_UI, 18), fill="#AAAAAA")

    # 3. MAIN RECTANGLE PANEL
    panel_box = [50, 100, 1230, 670]
    draw.rounded_rectangle(panel_box, radius=25, fill=(0, 0, 0, 180), outline="#444444", width=2)

    # 4. Character Image (Inside Panel)
    char_img = Image.open(data['char']).convert("RGBA").resize((350, 520))
    # Round corners for character image
    mask = Image.new("L", char_img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 350, 520], radius=20, fill=255)
    canvas.paste(char_img, (80, 130), mask)

    # 5. Information Text
    title_f = get_font(FONT_TITLE, 70)
    info_f = get_font(FONT_UI, 24)
    desc_f = get_font(FONT_UI, 20)

    # Title
    draw.text((460, 140), data['name'].upper(), font=title_f, fill="white")
    
    # Rating & Genres
    draw.text((460, 230), f"⭐ {data['rating']}  |  {data['genres']}", font=info_f, fill="#FFD700")

    # Synopsis (Wrapped Text)
    import textwrap
    lines = textwrap.wrap(data['synopsis'], width=60)
    y_text = 280
    for line in lines[:6]: # Limit to 6 lines
        draw.text((460, y_text), line, font=desc_f, fill="#CCCCCC")
        y_text += 30

    # 6. BUTTONS (Watch Now, More, Favorite)
    btn_y = 570
    buttons = [
        ("▶ Watch Now", 460, "#FFD700", "black"),
        ("ℹ More Info", 660, "#333333", "white"),
        ("❤ Favorite", 840, "#333333", "white")
    ]

    for text, x, color, txt_color in buttons:
        draw.rounded_rectangle([x, btn_y, x+180, btn_y+55], radius=12, fill=color)
        draw.text((x+25, btn_y+15), text, font=get_font(FONT_UI, 18), fill=txt_color)

    canvas.save(output_path)
    return output_path

# ==========================================
# =           BOT HANDLERS                 =
# ==========================================

@app.on_message(filters.command("start") & filters.private)
async def start(c, m):
    if str(m.from_user.id) != ADMIN_ID: return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Style 1 (Fixed Original)", callback_data="s1")],
        [InlineKeyboardButton("Style 2 (Kenshin UI)", callback_data="s2")]
    ])
    await m.reply("Bhai, kaun sa style banau?", reply_markup=kb)

@app.on_callback_query()
async def cb(c, q):
    uid = q.from_user.id
    if q.data == "s2":
        session_state[uid] = {"style": 2, "step": "name", "temp": []}
        await q.message.edit("**Style 2 Select kiya.**\n\nAb Anime ka **Naam** likho:")

@app.on_message(filters.text & filters.private)
async def text_in(c, m):
    uid = m.from_user.id
    if uid not in session_state: return
    
    state = session_state[uid]
    step = state['step']

    if step == "name":
        state.update({"name": m.text, "step": "rating"})
        await m.reply("Rating likho (e.g. 9.5):")
    elif step == "rating":
        state.update({"rating": m.text, "step": "genres"})
        await m.reply("Genres likho (e.g. Action, Adventure):")
    elif step == "genres":
        state.update({"genres": m.text, "step": "synopsis"})
        await m.reply("Chhoti Synopsis (kahani) likho:")
    elif step == "synopsis":
        state.update({"synopsis": m.text, "step": "bg"})
        await m.reply("Ab **Background Image** bhejo:")

@app.on_message(filters.photo & filters.private)
async def photo_in(c, m):
    uid = m.from_user.id
    if uid not in session_state: return
    
    state = session_state[uid]
    path = await m.download()
    state['temp'].append(path)

    if state['step'] == "bg":
        state.update({"bg": path, "step": "char"})
        await m.reply("Background mil gaya! Ab **Character Image** bhejo (Rectangle ke andar ke liye):")
    elif state['step'] == "char":
        state["char"] = path
        msg = await m.reply("🚀 God-Level UI Ban raha hai...")
        
        out = f"final_{uid}.png"
        create_style_2_ui(state, out)
        
        await m.reply_photo(out, caption=f"**{state['name']}** - Kenshin Special UI")
        
        # Cleanup
        for f in state['temp']: os.remove(f)
        if os.path.exists(out): os.remove(out)
        del session_state[uid]

app.run()
