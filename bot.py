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

# ── Configuration ─────────────────────────────────────────────────────────────
API_ID    = int(os.environ.get("API_ID", 0))
API_HASH  = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(i) for i in os.environ.get("ADMIN_IDS", "").split(",") if i]

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Constants
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
LOGO_PATH = "kenshin_logo.png"
FONT_PATH = "OpenSans-Bold.ttf"

# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE PROCESSING ENGINE (WATERMARK & BRANDING)
# ══════════════════════════════════════════════════════════════════════════════

async def create_kenshin_poster(image_url):
    """Downloads image, adds logo watermark and bottom branding bar"""
    if not image_url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=10) as resp:
                if resp.status != 200:
                    return None
                img_data = await resp.read()
        
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        img = ImageOps.fit(img, (1280, 720)) # Standard HD Ratio
        
        # 1. Top-Right Logo (Watermark)
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((160, 160), Image.Resampling.LANCZOS)
            img.paste(logo, (1280 - logo.width - 30, 30), logo)
            
        # 2. Bottom Branding Bar
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        bar_height = 100
        overlay = Image.new('RGBA', (1280, bar_height), (0, 0, 0, 225)) # Semi-transparent black
        img.paste(overlay, (0, 720 - bar_height), overlay)
        
        # Text Rendering
        try:
            font = ImageFont.truetype(FONT_PATH, 58)
        except:
            font = ImageFont.load_default()
            
        brand_text = "KENSHIN ANIME"
        text_w = draw.textlength(brand_text, font=font)
        draw.text(((1280 - text_w) / 2, 720 - 90), brand_text, fill=(255, 255, 255), font=font)
        
        # Save to Memory
        output = BytesIO()
        output.name = "kenshin_poster.jpg"
        img.save(output, "JPEG", quality=95)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Image Gen Error: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  MULTI-SOURCE SCRAPER (9 SOURCES)
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_anime_images(query, mal_id=None):
    """Scrapes 9 high-quality image sources for anime wallpapers"""
    all_urls = []
    clean_query = re.sub(r"[^a-z0-9 ]", "", query.lower()).strip()
    tag = clean_query.replace(" ", "_")
    
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Source 1: Wallhaven (High Res API)
        try:
            async with session.get("https://wallhaven.cc/api/v1/search", params={"q": query, "categories": "010"}) as r:
                data = await r.json()
                all_urls.extend([img["path"] for img in data.get("data", [])])
        except: pass
        
        # Sources 2-8: Anime Boorus (Gelbooru, Safebooru, Danbooru, etc.)
        booru_sites = ["safebooru.org", "gelbooru.com", "konachan.com"]
        for site in booru_sites:
            try:
                url = f"https://{site}/index.php"
                params = {"page": "dapi", "s": "post", "q": "index", "tags": tag, "json": "1", "limit": "25"}
                async with session.get(url, params=params) as r:
                    res = await r.json(content_type=None)
                    posts = res if isinstance(res, list) else res.get("post", [])
                    for p in posts:
                        f_url = p.get("file_url") or p.get("sample_url")
                        if f_url:
                            all_urls.append("https:" + f_url if f_url.startswith("//") else f_url)
            except: pass

        # Source 9: MyAnimeList (Jikan API Official Art)
        if mal_id:
            try:
                async with session.get(f"https://api.jikan.moe/v4/anime/{mal_id}/pictures") as r:
                    data = await r.json()
                    all_urls.extend([pic["jpg"]["large_image_url"] for pic in data.get("data", [])])
            except: pass
            
    # Remove duplicates and return
    return list(dict.fromkeys(all_urls))

# ══════════════════════════════════════════════════════════════════════════════
#  BOT COMMANDS (START, HELP, SETLOGO)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, msg: Message):
    await msg.reply(
        "👋 **Namaste Bahi! Kenshin Bot Ready Hai.**\n\n"
        "Mujhe kisi bhi Anime ka naam bhejo, main uski poori history (Info), "
        "ek mast branded poster, aur dher saari HD images bhej dunga.\n\n"
        "Type `/help` to see what I can do!"
    )

@app.on_message(filters.command("help") & filters.private)
async def help_handler(_, msg: Message):
    help_text = (
        "🚀 **Kenshin Bot Master Guide:**\n\n"
        "1️⃣ **Anime Info:** Bas anime ka naam likho (e.g., `Naruto`).\n"
        "2️⃣ **Set Logo:** Kisi photo par reply karo aur likho `/setlogo`.\n"
        "3️⃣ **Watermark:** Main har main photo par logo aur branding bar lagata hoon.\n"
        "4️⃣ **Images:** Har search par main top 9 sources se images dhoondhta hoon.\n\n"
        "Power by: @Kenshin_Anime"
    )
    await msg.reply(help_text)

@app.on_message(filters.command("setlogo") & filters.reply & filters.private)
async def setlogo_handler(_, msg: Message):
    if msg.reply_to_message.photo:
        await msg.reply_to_message.download(file_name=LOGO_PATH)
        await msg.reply("✅ **Mubarak ho!** Logo update ho gaya hai. Ab posters pe yehi dikhega.")
    else:
        await msg.reply("❌ Bahi, kisi **Photo** par reply karke command do!")

# ══════════════════════════════════════════════════════════════════════════════
#  CORE SEARCH ENGINE (ANILIST + SCRAPERS)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.text & filters.private)
async def anime_search_engine(_, msg: Message):
    # Security: Only Admins can use
    if msg.from_user.id not in ADMIN_IDS:
        return
    
    query = msg.text.strip()
    if query.startswith("/"): return # Ignore commands

    status = await msg.reply(f"🔍 **Dhoondh raha hoon: {query}...**")

    # Anilist GraphQL Query (Fetching Studio, Genres, Score, etc.)
    ani_query = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        idMal
        title { english romaji }
        genres
        description
        averageScore
        season
        seasonYear
        studios(isMain: true) { nodes { name } }
        bannerImage
        coverImage { extraLarge }
      }
    }
    """
    
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graphql.anilist.co", json={"query": ani_query, "variables": {"search": query}}) as r:
            res = await r.json()
            media = res.get("data", {}).get("Media")

    if not media:
        return await status.edit("❌ **Maaf karna bahi, ye anime nahi mila!**")

    await status.edit("📡 **Info mil gayi! Ab images aur poster taiyaar kar raha hoon...**")

    # Data Formatting
    eng_title = media["title"].get("english") or media["title"].get("romaji")
    score = f"{(media.get('averageScore') or 0) / 10:.1f}/10"
    season_info = f"{(media.get('season') or 'Unknown').title()} {media.get('seasonYear') or ''}"
    studio_name = media.get("studios", {}).get("nodes", [{}])[0].get("name", "N/A")
    genres_list = ", ".join(media.get("genres", [])[:5])
    clean_desc = html.escape(re.sub(r"<[^>]+>", "", media.get("description", "No description available.")))

    # Process Branding Photo
    main_img_url = media.get("bannerImage") or media.get("coverImage", {}).get("extraLarge")
    processed_thumb = await create_kenshin_poster(main_img_url)
    
    # Scrape HD Images from 9 sources
    gallery = await scrape_anime_images(query, media.get("idMal"))

    # Caption with Expandable Blockquote
    caption = (
        f"<b><blockquote>​「 {eng_title.upper()} 」</blockquote>\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"🌸 Category: Anime\n"
        f"🍥 Season: {season_info}\n"
        f"🍡 Score: {score}\n"
        f"🍵 Studio: {studio_name}\n"
        f"🎐 Genres: {genres_list}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"<blockquote expandable>​📜 SYNOPSIS: ​{clean_desc}</blockquote>\n\n"
        f"<blockquote>POWERED BY:- [@KENSHIN_ANIME]</blockquote></b>"
    )

    await status.delete()

    # 1. Send Main Poster with Details
    try:
        if processed_thumb:
            await msg.reply_photo(processed_thumb, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await msg.reply_photo(main_img_url, caption=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply(f"❌ Error sending poster: {e}")

    # 2. Send Image Gallery in Batches
    if gallery:
        for i in range(0, min(len(gallery), 30), 10): # Max 3 batches of 10
            batch = [InputMediaPhoto(url) for url in gallery[i:i+10]]
            try:
                await msg.reply_media_group(batch)
                await asyncio.sleep(1.5) # Flood wait protection
            except:
                continue

if __name__ == "__main__":
    app.run()
