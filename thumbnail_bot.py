import os
import re
import io
import base64
import asyncio
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",") if id_]

# States for conversation
ANIME_NAME, BG_IMAGE, MAIN_IMAGE, RIGHT1_IMAGE, RIGHT2_IMAGE = range(5)

# Paths
BASE_DIR = Path(__file__).parent
CHANNEL_LOGO_PATH = BASE_DIR / "channel_logo.png"
FONT_REGULAR = BASE_DIR / "OpenSans-Regular.ttf"
FONT_BOLD = BASE_DIR / "OpenSans-Bold.ttf"

# Default Telegram logo (base64 encoded small PNG)
TELEGRAM_LOGO_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwYAAAA
... (truncated for brevity, full base64 would be here) ...
"""
# In a real implementation you would include the full base64 string of a small Telegram logo.
# For now we'll use a placeholder. You can generate your own using an online tool.

# If you prefer to have a file, uncomment below:
# TELEGRAM_LOGO_PATH = BASE_DIR / "telegram_logo.png"

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "🎬 Welcome to Anime Thumbnail Bot!\n"
        "Send me the anime name to begin."
    )
    return ANIME_NAME

async def get_anime_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime_name"] = update.message.text.strip()
    await update.message.reply_text("📷 Now send the background image (any photo).")
    return BG_IMAGE

async def get_bg_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo.")
        return BG_IMAGE
    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)
    path = BASE_DIR / f"bg_{update.effective_user.id}.jpg"
    await file.download_to_drive(path)
    context.user_data["bg_path"] = str(path)
    await update.message.reply_text("🖼️ Send the main character image.")
    return MAIN_IMAGE

async def get_main_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo.")
        return MAIN_IMAGE
    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)
    path = BASE_DIR / f"main_{update.effective_user.id}.jpg"
    await file.download_to_drive(path)
    context.user_data["main_path"] = str(path)
    await update.message.reply_text("🖼️ Send the first right‑side image.")
    return RIGHT1_IMAGE

async def get_right1_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo.")
        return RIGHT1_IMAGE
    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)
    path = BASE_DIR / f"right1_{update.effective_user.id}.jpg"
    await file.download_to_drive(path)
    context.user_data["right1_path"] = str(path)
    await update.message.reply_text("🖼️ Send the second right‑side image.")
    return RIGHT2_IMAGE

async def get_right2_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo.")
        return RIGHT2_IMAGE
    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)
    path = BASE_DIR / f"right2_{update.effective_user.id}.jpg"
    await file.download_to_drive(path)
    context.user_data["right2_path"] = str(path)

    # All images collected, now generate thumbnail
    await update.message.reply_text("✨ Generating thumbnail... Please wait.")

    anime_name = context.user_data["anime_name"]
    anime_info = await fetch_anime_info(anime_name)

    try:
        thumbnail_path = await generate_thumbnail(
            bg_path=context.user_data["bg_path"],
            main_path=context.user_data["main_path"],
            right1_path=context.user_data["right1_path"],
            right2_path=context.user_data["right2_path"],
            anime_info=anime_info,
            channel_logo_path=CHANNEL_LOGO_PATH if CHANNEL_LOGO_PATH.exists() else None
        )
        with open(thumbnail_path, "rb") as f:
            await update.message.reply_photo(photo=f, caption="🎉 Your thumbnail is ready!")
        # Clean up temporary files
        for key in ["bg_path", "main_path", "right1_path", "right2_path"]:
            path = context.user_data.get(key)
            if path and os.path.exists(path):
                os.remove(path)
        os.remove(thumbnail_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    finally:
        context.user_data.clear()
    return ConversationHandler.END

async def set_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to set the channel logo (only admin)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ You are not authorized.")
        return
    if not update.message.photo:
        await update.message.reply_text("Please send an image as the logo.")
        return
    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)
    await file.download_to_drive(CHANNEL_LOGO_PATH)
    await update.message.reply_text("✅ Channel logo updated!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("You are not authorized.")
        return
    context.user_data.clear()
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def fetch_anime_info(anime_name: str):
    """Fetch details from Jikan API."""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=1"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["data"]:
                        anime = data["data"][0]
                        title = anime.get("title", anime_name)
                        synopsis = anime.get("synopsis", "No synopsis available.")
                        genres = ", ".join([g["name"] for g in anime.get("genres", [])]) or "N/A"
                        rating = anime.get("score", "N/A")
                        if rating != "N/A":
                            rating = f"{rating}/10"
                        # Try to extract season from title or aired dates
                        season_str = ""
                        if "season" in anime:
                            season = anime["season"]
                            year = anime.get("year", "")
                            if season and year:
                                season_str = f"{season.capitalize()} {year}"
                        # Fallback: search for "Season X" in title
                        if not season_str:
                            match = re.search(r"(?:Season|S)\s*(\d+)", title, re.I)
                            if match:
                                season_str = f"SEASON-{int(match.group(1)):02d}"
                            else:
                                season_str = "SEASON-??"
                        return {
                            "title": title,
                            "synopsis": synopsis,
                            "genres": genres,
                            "rating": rating,
                            "season": season_str
                        }
        except Exception:
            pass
    # Fallback
    return {
        "title": anime_name,
        "synopsis": "No synopsis available.",
        "genres": "N/A",
        "rating": "N/A",
        "season": "SEASON-??"
    }

async def generate_thumbnail(bg_path, main_path, right1_path, right2_path, anime_info, channel_logo_path=None):
    """Compose the final thumbnail."""
    # Dimensions
    W, H = 1200, 675
    # Load background
    bg = Image.open(bg_path).convert("RGBA").resize((W, H))
    # Semi‑transparent overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 180))
    bg = Image.alpha_composite(bg, overlay)

    # Load main character image
    main = Image.open(main_path).convert("RGBA")
    main_size = (300, 300)
    main.thumbnail(main_size, Image.Resampling.LANCZOS)
    # Create rounded rectangle mask
    mask = Image.new("L", main.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, main.size[0], main.size[1]), radius=30, fill=255)
    main.putalpha(mask)
    bg.paste(main, (40, H//2 - main.size[1]//2), main)

    # Load right images
    right1 = Image.open(right1_path).convert("RGBA")
    right1_size = (250, 250)
    right1.thumbnail(right1_size, Image.Resampling.LANCZOS)
    right2 = Image.open(right2_path).convert("RGBA")
    right2.thumbnail(right1_size, Image.Resampling.LANCZOS)
    # Position: x = 900, y = 80 for first, y = 380 for second
    bg.paste(right1, (W - right1.size[0] - 40, 80), right1)
    bg.paste(right2, (W - right2.size[0] - 40, 380), right2)

    # Channel logo (top right)
    if channel_logo_path and os.path.exists(channel_logo_path):
        logo = Image.open(channel_logo_path).convert("RGBA")
        logo.thumbnail((60, 60), Image.Resampling.LANCZOS)
        bg.paste(logo, (W - logo.size[0] - 20, 20), logo)

    # Draw text
    draw = ImageDraw.Draw(bg)
    try:
        font_bold = ImageFont.truetype(str(FONT_BOLD), 28)
        font_reg = ImageFont.truetype(str(FONT_REGULAR), 20)
        font_small = ImageFont.truetype(str(FONT_REGULAR), 18)
    except:
        font_bold = ImageFont.load_default()
        font_reg = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Anime title
    title = anime_info["title"]
    title_x = 40
    title_y = H - 200
    draw.text((title_x, title_y), title, fill="white", font=font_bold)

    # Line under title
    draw.line((title_x, title_y + 35, title_x + 300, title_y + 35), fill="white", width=2)

    # Genres
    genres = anime_info["genres"]
    genres_y = title_y + 50
    draw.text((title_x, genres_y), genres, fill="white", font=font_reg)

    # Synopsis (wrap)
    synopsis = anime_info["synopsis"]
    max_width = 500
    lines = []
    words = synopsis.split()
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font_small)
        if bbox[2] - bbox[0] <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    synopsis_y = genres_y + 40
    for line in lines[:3]:  # max 3 lines
        draw.text((title_x, synopsis_y), line, fill="white", font=font_small)
        synopsis_y += 28

    # Rating and season (side by side)
    rating = anime_info["rating"]
    season = anime_info["season"]
    rating_text = f"★ {rating}" if rating != "N/A" else "N/A"
    season_text = season
    draw.text((title_x, synopsis_y + 10), rating_text, fill="white", font=font_bold)
    draw.text((title_x + 200, synopsis_y + 10), season_text, fill="white", font=font_bold)

    # Bottom left branding: "KENSHIN ANIME" + Telegram logo
    # For Telegram logo, we could use a base64 image or a file.
    # Here we'll just draw text; if you have the logo, paste it.
    brand_text = "KENSHIN ANIME"
    text_width = draw.textlength(brand_text, font=font_bold)
    draw.text((40, H - 50), brand_text, fill="white", font=font_bold)
    # Placeholder for Telegram logo – if you have it, paste:
    # logo_telegram = Image.open(...).resize((30,30))
    # bg.paste(logo_telegram, (40 + text_width + 5, H - 45), logo_telegram)

    # Convert to RGB and save
    final = bg.convert("RGB")
    output_path = BASE_DIR / f"thumbnail_{datetime.now().timestamp()}.jpg"
    final.save(output_path, "JPEG")
    return str(output_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ANIME_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_anime_name)],
            BG_IMAGE: [MessageHandler(filters.PHOTO, get_bg_image)],
            MAIN_IMAGE: [MessageHandler(filters.PHOTO, get_main_image)],
            RIGHT1_IMAGE: [MessageHandler(filters.PHOTO, get_right1_image)],
            RIGHT2_IMAGE: [MessageHandler(filters.PHOTO, get_right2_image)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("setlogo", set_logo))
    # Optional: help command
    app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text(
        "Commands:\n"
        "/start – begin creating a thumbnail\n"
        "/setlogo – set your channel logo (send an image after the command)\n"
        "/cancel – cancel current operation"
    )))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
