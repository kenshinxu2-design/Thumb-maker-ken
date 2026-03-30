import os
import io
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- CONFIGURATION ---
API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_IDS = [12345678]  # Apni ID yahan daalein
FONT_BOLD = "OpenSans-Bold.ttf"
FONT_REGULAR = "OpenSans-Regular.ttf"
LOGO_PATH = "branding_logo.png"

# Conversation States
GET_NAME, GET_BG, GET_CHAR, GET_ICON1, GET_ICON2, GET_SEASON = range(6)
SETTING_LOGO = 10

# API Function
def get_anime_info(name):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={name}&limit=1"
        res = requests.get(url).json()
        data = res['data'][0]
        return {
            "title": data['title'].upper(),
            "genres": " | ".join([g['name'].upper() for g in data['genres']]),
            "synopsis": data['synopsis'][:300] + "...",
            "rating": f"{data['score']}/10"
        }
    except:
        return None

# Image Processing Logic
def create_thumbnail(data):
    base_w, base_h = 1280, 720
    
    # 1. Background
    bg = Image.open(io.BytesIO(data['bg'])).convert("RGBA")
    bg = ImageOps.fit(bg, (base_w, base_h))
    
    # 2. Black Transparent Overlay
    overlay = Image.new('RGBA', (base_w, base_h), (0, 0, 0, 160))
    combined = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(combined)
    
    # Fonts
    font_title = ImageFont.truetype(FONT_BOLD, 70)
    font_genre = ImageFont.truetype(FONT_BOLD, 40)
    font_body = ImageFont.truetype(FONT_REGULAR, 25)
    font_brand = ImageFont.truetype(FONT_BOLD, 55)

    # 3. Main Character Image (Right Side)
    char_img = Image.open(io.BytesIO(data['char'])).convert("RGBA")
    char_w, char_h = 360, 560
    char_img = ImageOps.fit(char_img, (char_w, char_h))
    # Draw White Frame
    draw.rectangle([875, 45, 1255, 625], outline="white", width=8)
    combined.paste(char_img, (885, 55), char_img)

    # 4. Top-Left Logo (From /setlogo)
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo = ImageOps.fit(logo, (120, 120))
        combined.paste(logo, (20, 20), logo)

    # 5. Left Icons (Middle Section)
    def paste_icon(img_bytes, pos):
        icon = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        icon = ImageOps.fit(icon, (110, 110))
        combined.paste(icon, pos, icon)

    paste_icon(data['icon1'], (20, 350))
    paste_icon(data['icon2'], (20, 480))

    # 6. Bottom Branding Text
    draw.text((430, 630), "KENSHIN ANIME", font=font_brand, fill="white")

    # 7. Text Info
    info = data['info']
    draw.text((150, 100), info['title'], font=font_title, fill="white")
    draw.line([150, 185, 750, 185], fill="white", width=5)
    draw.text((150, 210), info['genres'], font=font_genre, fill="white")
    
    lines = textwrap.wrap(info['synopsis'], width=60)
    y_text = 280
    for line in lines:
        draw.text((150, y_text), line, font=font_body, fill="white")
        y_text += 35

    draw.text((150, 580), f"⭐ {info['rating']}", font=font_genre, fill="white")
    draw.text((450, 580), f"SEASON-{data['season']}", font=font_genre, fill="white")

    out = io.BytesIO()
    combined.convert("RGB").save(out, format="JPEG", quality=95)
    out.seek(0)
    return out

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    await update.message.reply_text("Bahi, Anime ka naam bhejo:")
    return GET_NAME

async def set_logo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    await update.message.reply_text("Apna branding logo (Photo) bhejo:")
    return SETTING_LOGO

async def save_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    await photo.download_to_drive(LOGO_PATH)
    await update.message.reply_text("Logo save ho gaya bahi! Ab ye har thumbnail par aayega.")
    return ConversationHandler.END

# ... (Include handle_name, handle_bg, handle_char, handle_icon1, handle_icon2 from previous code here) ...
# (Small change in handle_season to call create_thumbnail)

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    info = get_anime_info(name)
    if not info:
        await update.message.reply_text("Nahi mila bahi, sahi naam likho.")
        return GET_NAME
    context.user_data['info'] = info
    await update.message.reply_text(f"Mila: {info['title']}\nAb Background image bhejo:")
    return GET_BG

async def handle_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    context.user_data['bg'] = await photo.download_as_bytearray()
    await update.message.reply_text("Ab Character image bhejo (Right side):")
    return GET_CHAR

async def handle_char(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    context.user_data['char'] = await photo.download_as_bytearray()
    await update.message.reply_text("Ab Left side ki Icon 1 bhejo:")
    return GET_ICON1

async def handle_icon1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    context.user_data['icon1'] = await photo.download_as_bytearray()
    await update.message.reply_text("Ab Left side ki Icon 2 bhejo:")
    return GET_ICON2

async def handle_icon2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    context.user_data['icon2'] = await photo.download_as_bytearray()
    await update.message.reply_text("Ab Season info (e.g. 03):")
    return GET_SEASON

async def handle_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['season'] = update.message.text
    await update.message.reply_text("Thumbnail ban raha hai...")
    img = create_thumbnail(context.user_data)
    await update.message.reply_photo(img, caption="Ye lo bahi!")
    return ConversationHandler.END

def main():
    app = Application.builder().token(API_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("setlogo", set_logo_start)],
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
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
