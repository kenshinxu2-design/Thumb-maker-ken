import os
import requests
import asyncio
import textwrap
from time import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# --- Config ---
API_ID = os.environ.get("API_ID") 
API_HASH = os.environ.get("API_HASH") 
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = os.environ.get("ADMIN_ID")

app = Client("kenshin_auto", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
session_state = {}

# Fonts (Make sure these exist in fonts/ folder)
FONT_TITLE = "fonts/font.ttf"
FONT_UI = "fonts/DejaVuSansCondensed-Bold.ttf"

# --- API Helper: Fetch Anime Info ---
def fetch_anime_data(query):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
        res = requests.get(url).json()
        if res['data']:
            anime = res['data'][0]
            return {
                "name": anime['title_english'] or anime['title'],
                "rating": anime.get('score', 'N/A'),
                "genres": ", ".join([g['name'] for g in anime['genres'][:3]]),
                "synopsis": anime.get('synopsis', 'No synopsis available.').replace("[Written by MAL Rewrite]", ""),
            }
    except Exception as e:
        print(f"API Error: {e}")
    return None

def get_font(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

# ==========================================
# =           STYLE 2: UI LAYOUT           =
# ==========================================
def create_style_2_ui(data, output_path):
    W, H = 1280, 720
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    
    # 1. Background
    bg = Image.open(data['bg']).convert("RGBA").resize((W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(2))
    canvas.paste(bg, (0, 0))
    
    # Dark Overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    canvas.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(canvas)

    # 2. UI Elements
    draw.text((50, 30), "KENSHIN ANIME", font=get_font(FONT_UI, 28), fill="#FFD700")
    draw.rounded_rectangle([900, 25, 1230, 65], radius=20, fill="#333333")
    draw.text((920, 33), "🔍 Search Anime...", font=get_font(FONT_UI, 18), fill="#AAAAAA")

    # Panel
    draw.rounded_rectangle([50, 100, 1230, 670], radius=25, fill=(0, 0, 0, 180), outline="#444444", width=2)

    # Char Image
    char_img = Image.open(data['char']).convert("RGBA").resize((350, 520))
    mask = Image.new("L", char_img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 350, 520], radius=20, fill=255)
    canvas.paste(char_img, (80, 130), mask)

    # Info Text
    draw.text((460, 140), data['name'].upper()[:20], font=get_font(FONT_TITLE, 70), fill="white")
    draw.text((460, 230), f"⭐ {data['rating']}  |  {data['genres']}", font=get_font(FONT_UI, 24), fill="#FFD700")

    # Wrapped Synopsis
    lines = textwrap.wrap(data['synopsis'], width=65)
    y_text = 280
    for line in lines[:7]:
        draw.text((460, y_text), line, font=get_font(FONT_UI, 19), fill="#CCCCCC")
        y_text += 28

    # Buttons
    btn_y = 580
    for text, x, color, t_col in [("▶ Watch Now", 460, "#FFD700", "black"), ("ℹ More Info", 660, "#333333", "white"), ("❤ Favorite", 840, "#333333", "white")]:
        draw.rounded_rectangle([x, btn_y, x+180, btn_y+50], radius=10, fill=color)
        draw.text((x+25, btn_y+15), text, font=get_font(FONT_UI, 16), fill=t_col)

    canvas.save(output_path)
    return output_path

# ==========================================
# =           BOT HANDLERS                 =
# ==========================================

@app.on_message(filters.command("start") & filters.private)
async def start(c, m):
    if str(m.from_user.id) != ADMIN_ID: return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Style 1 (Original)", callback_data="s1"),
        InlineKeyboardButton("Style 2 (Kenshin UI)", callback_data="s2")
    ]])
    await m.reply("Bhai, Style select kar. Info main khud nikal lunga! 😎", reply_markup=kb)

@app.on_callback_query()
async def cb(c, q):
    uid = q.from_user.id
    style = 1 if q.data == "s1" else 2
    session_state[uid] = {"style": style, "step": "name", "temp": []}
    await q.message.edit(f"Style {style} Set! Ab bas **Anime ka Naam** likho:")

@app.on_message(filters.text & filters.private)
async def handle_name(c, m):
    uid = m.from_user.id
    if uid not in session_state or session_state[uid]['step'] != "name": return
    
    msg = await m.reply("Searching info on Google/MAL... 🔍")
    info = fetch_anime_data(m.text)
    
    if not info:
        return await msg.edit("Bhai is anime ki info nahi mili. Naam sahi likho!")
    
    session_state[uid].update(info)
    session_state[uid]['step'] = "bg"
    await msg.edit(f"✅ Found: **{info['name']}**\n⭐ Rating: {info['rating']}\n\nAb **Background Image** bhejo:")

@app.on_message(filters.photo & filters.private)
async def handle_images(c, m):
    uid = m.from_user.id
    if uid not in session_state: return
    
    state = session_state[uid]
    path = await m.download()
    state['temp'].append(path)

    if state['step'] == "bg":
        state.update({"bg": path, "step": "char"})
        await m.reply("Background Done! Ab **Character Image** bhejo:")
    elif state['step'] == "char":
        state["char"] = path
        p = await m.reply("🚀 God-Level Creation in progress...")
        
        out = f"kenshin_{uid}.png"
        # Style logic here (Style 1 placeholder or Style 2)
        create_style_2_ui(state, out)
        
        await m.reply_photo(out, caption=f"**{state['name']}**\nDone by Kenshin Bot ⚡")
        
        for f in state['temp']: 
            if os.path.exists(f): os.remove(f)
        if os.path.exists(out): os.remove(out)
        del session_state[uid]

app.run()
