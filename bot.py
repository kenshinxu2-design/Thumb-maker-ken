import os
import io
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- ENVIRONMENT CONFIG ---
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i) for i in ADMIN_STR.split(",") if i.strip()]

FONT_BOLD = "OpenSans-Bold.ttf"
FONT_REGULAR = "OpenSans-Regular.ttf"
LOGO_PATH = "branding_logo.png"

# Conversation States
GET_NAME, GET_BG, GET_CHAR, GET_ICON1, GET_ICON2, GET_SEASON = range(6)
SETTING_LOGO = 10

# Helper: Fetch Anime Data
def get_anime_info(name):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={name}&limit=1"
        res = requests.get(url).json()
        data = res['data'][0]
        return {
            "title": data['title'].upper(),
            "genres": " | ".join([g['name'].upper() for g in data['genres']]),
            "synopsis": data['synopsis'][:280] + "...",
            "rating": f"⭐ {data['score']}/10"
        }
    except Exception:
        return None

# --- CORE IMAGE ENGINE ---
def create_thumbnail(data):
    base_w, base_h = 1280, 720
    
    # 1. Background + Black Transparent Overlay
    bg = Image.open(io.BytesIO(data['bg'])).convert("RGBA")
    bg = ImageOps.fit(bg, (base_w, base_h))
    overlay = Image.new('RGBA', (base_w, base_h), (0, 0, 0, 175))
    combined = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(combined)
    
    # Fonts
    f_title = ImageFont.truetype(FONT_BOLD, 55)
    f_genre = ImageFont.truetype(FONT_BOLD, 30)
    f_body = ImageFont.truetype(FONT_REGULAR, 22)
    f_brand = ImageFont.truetype(FONT_BOLD, 45)

    # 2. LEFT SIDE: Main Character in Shape/Frame
    char_img = Image.open(io.BytesIO(data['char'])).convert("RGBA")
    char_w, char_h = 420, 520
    char_img = ImageOps.fit(char_img, (char_w, char_h))
    # Frame for Character
    draw.rectangle([45, 45, 475, 575], outline="white", width=6)
    combined.paste(char_img, (50, 50), char_img)
    
    # Branding below character (Left Bottom)
    draw.text((60, 600), "KENSHIN ANIME", font=f_brand, fill="white")

    # 3. RIGHT SIDE: Branding Logo (Top Right)
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((150, 150))
        combined.paste(logo, (1100, 30), logo)

    # 4. RIGHT SIDE: Icon 1 & Icon 2 (Stacked)
    icon_size = (200, 120)
    def paste_right_icon(img_bytes, y_pos):
        ic = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        ic = ImageOps.fit(ic, icon_size)
        draw.rectangle([950, y_pos-5, 1155, y_pos+125], outline="white", width=3)
        combined.paste(ic, (955, y_pos), ic)

    paste_right_icon(data['icon1'], 180) # Icon 1
    paste_right_icon(data['icon2'], 320) # Icon 2

    # 5. RIGHT SIDE TEXT AREA (Under Icons)
    info = data['info']
    text_x = 550
    draw.text((text_x, 80), info['title'], font=f_title, fill="white")
    draw.line([text_x, 150, 1100, 150], fill="white", width=4) # Separator Line
    
    draw.text((text_x, 170), info['genres'], font=f_genre, fill="#FFD700") # Genre in Gold/Yellow
    
    # Wrapped Synopsis
    lines = textwrap.wrap(info['synopsis'], width=50)
    y_syn = 230
    for line in lines:
        draw.text((text_x, y_syn), line, font=f_body, fill="#E0E0E0")
        y_syn += 30

    # Rating & Season (Side by Side at bottom right)
    draw.text((text_x, 580), info['rating'], font=f_genre, fill="white")
    draw.text((text_x + 300, 580), f"SEASON: {data['season']}", font=f_genre, fill="white")

    # Save and Return
    out = io.BytesIO()
    combined.convert("RGB").save(out, format="JPEG", quality=95)
    out.seek(0)
    return out

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    await update.message.reply_text("Bahi, Anime ka name batao:")
    return GET_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_anime_info(update.message.text)
    if not info:
        await update.message.reply_text("Data nahi mila, firse try karo.")
        return GET_NAME
    context.user_data['info'] = info
    await update.message.reply_text(f"Mila: {info['title']}\nAb Background image bhejo:")
    return GET_BG

async def handle_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f = await update.message.photo[-1].get_file()
    context.user_data['bg'] = await f.download_as_bytearray()
    await update.message.reply_text("Ab Main Character image (Left side frame ke liye) bhejo:")
    return GET_CHAR

async def handle_char(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f = await update.message.photo[-1].get_file()
    context.user_data['char'] = await f.download_as_bytearray()
    await update.message.reply_text("Ab Right side ki 1st Choti Image (Icon 1) bhejo:")
    return GET_ICON1

async def handle_icon1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f = await update.message.photo[-1].get_file()
    context.user_data['icon1'] = await f.download_as_bytearray()
    await update.message.reply_text("Ab Right side ki 2nd Choti Image (Icon 2) bhejo:")
    return GET_ICON2

async def handle_icon2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f = await update.message.photo[-1].get_file()
    context.user_data['icon2'] = await f.download_as_bytearray()
    await update.message.reply_text("Ab Season info likho (e.g. 01):")
    return GET_SEASON

async def handle_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['season'] = update.message.text
    await update.message.reply_text("Thumbnail ready ho raha hai...")
    try:
        img = create_thumbnail(context.user_data)
        await update.message.reply_photo(img, caption="Ye lo bahi, depto waisa hi!")
    except Exception as e:
        await update.message.reply_text(f"Kuch gadbad ho gayi: {e}")
    return ConversationHandler.END

async def set_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    await update.message.reply_text("Apna Channel Logo bhejo (Top Right ke liye):")
    return SETTING_LOGO

async def save_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f = await update.message.photo[-1].get_file()
    await f.download_to_drive(LOGO_PATH)
    await update.message.reply_text("Logo set ho gaya!")
    return ConversationHandler.END

def main():
    if not API_TOKEN:
        print("Error: BOT_TOKEN variable missing!")
        return

    app = Application.builder().token(API_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("setlogo", set_logo)],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            GET_BG: [MessageHandler(filters.PHOTO, handle_bg)],
            GET_CHAR: [MessageHandler(filters.PHOTO, handle_char)],
            GET_ICON1: [MessageHandler(filters.PHOTO, handle_icon1)],
            GET_ICON2: [MessageHandler(filters.PHOTO, handle_icon2)],
            GET_SEASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_season)],
            SETTING_LOGO: [MessageHandler(filters.PHOTO, save_logo)],
        },
        fallbacks=[],
    )
    
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
