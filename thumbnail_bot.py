import os
import requests
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

app = Client("kenshin_final", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
session_state = {}

# Fonts (Ensure these are in your /fonts folder)
FONT_TITLE = "fonts/font.ttf"
FONT_BOLD = "fonts/DejaVuSansCondensed-Bold.ttf"

def get_font(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def fetch_anime_data(query):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
        res = requests.get(url).json()
        if res['data']:
            anime = res['data'][0]
            return {
                "name": anime['title_english'] or anime['title'],
                "rating": anime.get('score', '9.8'),
                "genres": ", ".join([g['name'] for g in anime['genres'][:3]]),
                "synopsis": anime.get('synopsis', 'No synopsis available.').replace("[Written by MAL Rewrite]", ""),
            }
    except: return None

# ==========================================
# =         GOD-LEVEL UI GENERATOR         =
# ==========================================
def create_kenshin_ui(data, output_path):
    W, H = 1280, 720
    # Base Layer
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    
    # 1. Background with Blur
    bg = Image.open(data['bg']).convert("RGBA").resize((W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(4))
    canvas.paste(bg, (0, 0))
    
    # Darken Background
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 100))
    canvas.paste(overlay, (0, 0), overlay)
    
    # 2. THE TRANSPARENT PANEL
    # Inner dark panel
    panel_shape = [60, 60, 1220, 660]
    panel_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(panel_img)
    p_draw.rounded_rectangle(panel_shape, radius=30, fill=(0, 0, 0, 190)) # High Transparency
    canvas.alpha_composite(panel_img)
    
    draw = ImageDraw.Draw(canvas)
    # 3. NEON BORDER (Cyan/Blue Glow)
    draw.rounded_rectangle(panel_shape, radius=30, outline="#00FFFF", width=4)

    # 4. CHARACTER IMAGE (Left side, rounded)
    char_img = Image.open(data['char']).convert("RGBA").resize((380, 540))
    mask = Image.new("L", char_img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 380, 540], radius=25, fill=255)
    canvas.paste(char_img, (100, 90), mask)

    # 5. TEXT CONTENT
    # Branding Header
    draw.text((520, 95), "A KENSHIN ANIME SELECTION", font=get_font(FONT_BOLD, 22), fill="#FFD700")

    # Title (GOLD STYLE)
    title_text = data['name'].upper()
    draw.text((520, 130), title_text, font=get_font(FONT_TITLE, 90), fill="white")

    # Rating & Genres
    draw.text((520, 250), f"★ {data['rating']}", font=get_font(FONT_BOLD, 45), fill="#FFD700")
    draw.text((650, 265), f"Genres: {data['genres']}", font=get_font(FONT_BOLD, 24), fill="white")

    # Synopsis (Wrapped)
    lines = textwrap.wrap(data['synopsis'], width=60)
    y_start = 330
    for line in lines[:6]:
        draw.text((520, y_start), line, font=get_font(FONT_BOLD, 20), fill="#DDDDDD")
        y_start += 28

    # 6. BUTTONS
    # Watch Now (White)
    draw.rounded_rectangle([520, 530, 780, 600], radius=35, fill="white")
    draw.text((560, 542), "▶ WATCH NOW", font=get_font(FONT_BOLD, 24), fill="black")

    # More Info (Dark Grey)
    draw.rounded_rectangle([810, 530, 1020, 600], radius=35, fill="#333333")
    draw.text((845, 542), "MORE INFO", font=get_font(FONT_BOLD, 22), fill="white")

    # Final Branding Watermark (Bottom Right)
    draw.text((1120, 615), "Kenshin", font=get_font(FONT_TITLE, 20), fill="#FFD700")

    canvas.save(output_path)
    return output_path

# ==========================================
# =           BOT LOGIC HANDLERS           =
# ==========================================

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(c, m):
    if str(m.from_user.id) != ADMIN_ID: return
    await m.reply("🔥 **KENSHIN GOD-LEVEL MAKER V3**\n\nBas Anime ka naam likho:")

@app.on_message(filters.text & filters.private)
async def handle_text(c, m):
    uid = m.from_user.id
    if str(uid) != ADMIN_ID: return
    
    msg = await m.reply("Fetching Info... 🔍")
    info = fetch_anime_data(m.text)
    if not info: return await msg.edit("Nahi mila! Sahi naam likho.")
    
    session_state[uid] = info
    session_state[uid]['temp'] = []
    await msg.edit(f"✅ Found: **{info['name']}**\n\nAb **Background Image** bhejo:")

@app.on_message(filters.photo & filters.private)
async def handle_images(c, m):
    uid = m.from_user.id
    if uid not in session_state: return
    
    path = await m.download()
    state = session_state[uid]
    state['temp'].append(path)

    if 'bg' not in state:
        state['bg'] = path
        await m.reply("Background Set! Ab **Character Image** bhejo:")
    else:
        state['char'] = path
        process_msg = await m.reply("🚀 God-Level Design render ho raha hai...")
        
        output = f"kenshin_pro_{uid}.png"
        create_kenshin_ui(state, output)
        
        await m.reply_photo(output, caption=f"**{state['name']}**\nPremium Thumbnail ready for Kenshin! ⚡")
        
        # Cleanup
        for f in state['temp']: os.remove(f)
        if os.path.exists(output): os.remove(output)
        del session_state[uid]

app.run()
