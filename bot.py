import os
import re
import html
import asyncio
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

# ── Configuration ─────────────────────────────────────────────────────────────
API_ID    = int(os.environ.get("API_ID", 0))
API_HASH  = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(i) for i in os.environ.get("ADMIN_IDS", "").split(",") if i]

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
LOGO_PATH = "kenshin_logo.png"
FONT_PATH = "OpenSans-Bold.ttf"

# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE PROCESSING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

async def create_kenshin_poster(image_url):
    if not image_url: return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=10) as resp:
                if resp.status != 200: return None
                img_data = await resp.read()
        
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        img = ImageOps.fit(img, (1280, 720)) 
        
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((160, 160), Image.Resampling.LANCZOS)
            img.paste(logo, (1280 - logo.width - 30, 30), logo)
            
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        bar_height = 100
        overlay = Image.new('RGBA', (1280, bar_height), (0, 0, 0, 225))
        img.paste(overlay, (0, 720 - bar_height), overlay)
        
        try: font = ImageFont.truetype(FONT_PATH, 58)
        except: font = ImageFont.load_default()
            
        brand_text = "KENSHIN ANIME"
        text_w = draw.textlength(brand_text, font=font)
        draw.text(((1280 - text_w) / 2, 720 - 90), brand_text, fill="white", font=font)
        
        output = BytesIO(); output.name = "kenshin_poster.jpg"
        img.save(output, "JPEG", quality=95); output.seek(0)
        return output
    except: return None

# ══════════════════════════════════════════════════════════════════════════════
#  MULTI-SOURCE SCRAPER
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_anime_images(query, mal_id=None):
    all_urls = []
    tag = re.sub(r"[^a-z0-9 ]", "", query.lower()).strip().replace(" ", "_")
    
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try: # Wallhaven
            async with session.get("https://wallhaven.cc/api/v1/search", params={"q": query, "categories": "010"}) as r:
                all_urls.extend([x["path"] for x in (await r.json()).get("data", [])])
        except: pass
        
        for site in ["safebooru.org", "gelbooru.com"]: # Boorus
            try:
                async with session.get(f"https://{site}/index.php", params={"page":"dapi","s":"post","q":"index","tags":tag,"json":"1","limit":"20"}) as r:
                    res = await r.json(content_type=None)
                    posts = res if isinstance(res, list) else res.get("post", [])
                    all_urls.extend([p["file_url"] for p in posts if "file_url" in p])
            except: pass

        if mal_id: # Jikan
            try:
                async with session.get(f"https://api.jikan.moe/v4/anime/{mal_id}/pictures") as r:
                    all_urls.extend([x["jpg"]["large_image_url"] for x in (await r.json()).get("data", [])])
            except: pass
            
    return list(dict.fromkeys(all_urls))

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, msg: Message):
    await msg.reply("🔥 **Kenshin Bot is ON!**\nSend an Anime/Manga name directly, or use `/char Name` for characters.")

@app.on_message(filters.command("help") & filters.private)
async def help_handler(_, msg: Message):
    await msg.reply(
        "🚀 **Guide:**\n"
        "1️⃣ **Anime/Manga/Manhwa:** Just type the name.\n"
        "2️⃣ **Characters:** `/char Name` (e.g., `/char Gojo Satoru`).\n"
        "3️⃣ **Logo:** Reply to an image with `/setlogo`.\n"
    )

@app.on_message(filters.command("setlogo") & filters.reply & filters.private)
async def setlogo_handler(_, msg: Message):
    if msg.reply_to_message.photo:
        await msg.reply_to_message.download(file_name=LOGO_PATH)
        await msg.reply("✅ **Logo Updated!**")
    else:
        await msg.reply("❌ Photo par reply karke command do!")

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTER SEARCH ENGINE (NEW FEATURE)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command(["char", "character"]) & filters.private)
async def char_search(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    
    query = msg.text.split(" ", 1)[1] if len(msg.text.split(" ")) > 1 else ""
    if not query: return await msg.reply("❌ Character ka naam toh likh bahi!")

    status = await msg.reply(f"🔍 **Searching Character: {query}...**")
    
    char_query = """
    query ($search: String) {
      Character(search: $search) {
        name { full native }
        image { large }
        description
        gender
        age
      }
    }
    """
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graphql.anilist.co", json={"query": char_query, "variables": {"search": query}}) as r:
            res = await r.json()
            character = res.get("data", {}).get("Character")

    if not character: return await status.edit("❌ **Character nahi mila bahi!**")

    name = character.get("name", {}).get("full", "Unknown")
    native = character.get("name", {}).get("native", "")
    age = character.get("age") or "Unknown"
    gender = character.get("gender") or "Unknown"
    desc = html.escape(re.sub(r"<[^>]+>", "", character.get("description") or "No description available."))
    img = character.get("image", {}).get("large")

    caption = (
        f"<b><blockquote>​「 {name.upper()} {f'({native})' if native else ''} 」</blockquote>\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"👤 Gender: {gender}\n"
        f"🎂 Age: {age}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"<blockquote expandable>​📜 ABOUT: ​{desc}</blockquote>\n\n"
        f"<blockquote>POWERED BY:- [@KENSHIN_ANIME]</blockquote></b>"
    )

    await status.delete()
    if img: await msg.reply_photo(img, caption=caption, parse_mode=ParseMode.HTML)
    else: await msg.reply(caption, parse_mode=ParseMode.HTML)

# ══════════════════════════════════════════════════════════════════════════════
#  ANIME / MANGA / MANHWA SEARCH ENGINE
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_anilist_media(query, media_type):
    ani_query = """
    query ($search: String, $type: MediaType) {
      Media(search: $search, type: $type) {
        idMal title { english romaji } format genres description averageScore 
        season seasonYear studios(isMain: true) { nodes { name } }
        bannerImage coverImage { extraLarge }
      }
    }
    """
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graphql.anilist.co", json={"query": ani_query, "variables": {"search": query, "type": media_type}}) as r:
            res = await r.json()
            return res.get("data", {}).get("Media")

@app.on_message(filters.text & filters.private)
async def anime_manga_engine(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    query = msg.text.strip()
    if query.startswith("/"): return 

    status = await msg.reply(f"🔍 **Dhoondh raha hoon: {query}...**")

    # Pehle ANIME search karega, agar nahi mila toh MANGA (Manhwa/Manga) search karega
    media = await fetch_anilist_media(query, "ANIME")
    if not media:
        media = await fetch_anilist_media(query, "MANGA")
    
    if not media:
        return await status.edit("❌ **Maaf karna bahi, ye Anime ya Manga nahi mila!**")

    await status.edit("📡 **Info mil gayi! Ab images aur poster ban raha hai...**")

    eng_title = media["title"].get("english") or media["title"].get("romaji") or query
    score = f"{(media.get('averageScore') or 0) / 10:.1f}/10"
    m_format = media.get("format", "ANIME").replace("_", " ") # Example: TV, MANGA, ONE_SHOT
    season_info = f"{(media.get('season') or '').title()} {media.get('seasonYear') or ''}".strip() or "N/A"
    studio_name = media.get("studios", {}).get("nodes", [{}])[0].get("name", "N/A") if media.get("studios", {}).get("nodes") else "N/A"
    genres_list = ", ".join(media.get("genres", [])[:5])
    clean_desc = html.escape(re.sub(r"<[^>]+>", "", media.get("description") or "No description available."))

    main_img_url = media.get("bannerImage") or media.get("coverImage", {}).get("extraLarge")
    processed_thumb = await create_kenshin_poster(main_img_url)
    
    gallery = await scrape_anime_images(query, media.get("idMal"))

    caption = (
        f"<b><blockquote>​「 {eng_title.upper()} 」</blockquote>\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"🌸 Type: {m_format}\n"
        f"🍥 Season: {season_info}\n"
        f"🍡 Score: {score}\n"
        f"🍵 Studio/Author: {studio_name}\n"
        f"🎐 Genres: {genres_list}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"<blockquote expandable>​📜 SYNOPSIS: ​{clean_desc}</blockquote>\n\n"
        f"<blockquote>POWERED BY:- [@KENSHIN_ANIME]</blockquote></b>"
    )

    await status.delete()

    # Send Main Poster
    if processed_thumb:
        await msg.reply_photo(processed_thumb, caption=caption, parse_mode=ParseMode.HTML)
    elif main_img_url:
        await msg.reply_photo(main_img_url, caption=caption, parse_mode=ParseMode.HTML)

    # ANTI-FLOOD BATCH SENDER FOR IMAGES (Solution to images stopping)
    if gallery:
        for i in range(0, min(len(gallery), 20), 10): # Max 20 images bhejege taaki ban na ho
            batch = [InputMediaPhoto(url) for url in gallery[i:i+10]]
            try:
                await msg.reply_media_group(batch)
                await asyncio.sleep(3) # Telegram ko rest dene ke liye 3 sec delay
            except FloodWait as e:
                # Agar Telegram bolta hai ruk jao, toh bot utne seconds wait karega
                print(f"Sleeping for {e.value} seconds due to FloodWait")
                await asyncio.sleep(e.value + 1)
                await msg.reply_media_group(batch)
            except Exception as e:
                print(f"Batch Error: {e}")

if __name__ == "__main__":
    app.run()
