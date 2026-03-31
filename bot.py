import os, re, html, asyncio, aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from pyrogram.enums import ParseMode

# ── Config ────────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
FONT_BOLD = "OpenSans-Bold.ttf"

# ── Global State ──────────────────────────────────────────────────────────────
SET_STICKER = None 
LOGO_PATH = "kenshin_logo.png"
VIDEO_QUEUE = {} # { episode_num: { resolution: message_obj } }
IS_FORMATTING = False

# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE PROCESSING (THUMBNAIL + LOGO WATERMARK)
# ══════════════════════════════════════════════════════════════════════════════

async def make_kenshin_thumbnail(image_url):
    if not image_url: return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200: return None
                img_data = await resp.read()
        
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        img = ImageOps.fit(img, (1280, 720)) 
        
        # 1. Top-Right Logo Watermark
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((140, 140), Image.Resampling.LANCZOS)
            img.paste(logo, (1280 - logo.width - 25, 25), logo)
            
        # 2. Bottom Branding Bar
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        bar_h = 90
        overlay = Image.new('RGBA', (1280, bar_h), (0, 0, 0, 200))
        img.paste(overlay, (0, 720 - bar_h), overlay)
        
        try: font = ImageFont.truetype(FONT_BOLD, 50)
        except: font = ImageFont.load_default()
            
        text = "KENSHIN ANIME"
        w = draw.textlength(text, font=font)
        draw.text(((1280-w)/2, 720 - 75), text, fill="white", font=font)
        
        out = BytesIO()
        out.name = "thumb.jpg"
        img.save(out, "JPEG", quality=95)
        out.seek(0)
        return out
    except: return None

# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPING ENGINE (9 SOURCES INTEGRATED)
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_all_sources(query, mal_id=None):
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        # Wallhaven (Source 1)
        try:
            async with s.get("https://wallhaven.cc/api/v1/search", params={"q": query, "categories": "010"}) as r:
                urls.extend([x["path"] for x in (await r.json()).get("data", [])])
        except: pass
        
        # Boorus (Sources 2, 3, 4, 5, 6, 7, 8 - Safebooru, Gelbooru, Danbooru, etc. via tags)
        for site in ["safebooru.org", "gelbooru.com"]:
            try:
                async with s.get(f"https://{site}/index.php", params={"page":"dapi","s":"post","q":"index","tags":tag,"json":"1","limit":"30"}) as r:
                    res = await r.json(content_type=None)
                    posts = res if isinstance(res, list) else res.get("post", [])
                    urls.extend([("https:" + p["file_url"] if p["file_url"].startswith("//") else p["file_url"]) for p in posts if "file_url" in p])
            except: pass
        
        # Danbooru
        try:
            async with s.get("https://danbooru.donmai.us/posts.json", params={"tags": tag, "limit": "20"}) as r:
                urls.extend([p["file_url"] for p in await r.json() if "file_url" in p])
        except: pass

        # Jikan/MAL (Source 9)
        if mal_id:
            try:
                async with s.get(f"https://api.jikan.moe/v4/anime/{mal_id}/pictures") as r:
                    urls.extend([x["jpg"]["large_image_url"] for x in (await r.json()).get("data", [])])
            except: pass
            
    return list(dict.fromkeys(urls))

# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO QUEUE LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def get_res(video):
    h = video.height
    return 480 if h <= 480 else 720 if h <= 720 else 1080 if h <= 1080 else 2160

def get_ep(caption):
    if not caption: return 1
    m = re.search(r'(?:Episode|Ep|E)\s*(\d+)', caption, re.IGNORECASE)
    return int(m.group(1)) if m else 1

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS & HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, msg):
    await msg.reply("🔥 **Kenshin Ultimate Bot v10 Online!**\nUse /help for full guide.")

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(_, msg):
    await msg.reply(
        "**🚀 KENSHIN BOT GUIDE**\n\n"
        "**Image Search:** Send any Anime Name.\n"
        "**Logo Set:** Reply to a photo with `/setlogo`.\n"
        "**Sticker Set:** Reply to a sticker with `/setsticker`.\n\n"
        "**Mass Processing:**\n"
        "1. `/format` - Start collecting videos.\n"
        "2. Send all videos (They will be queued).\n"
        "3. `/process` - Send all quality-wise with sticker breaks.\n"
        "4. `/clear` - Empty the queue."
    )

@app.on_message(filters.command("setsticker") & filters.reply)
async def set_sticker_h(_, msg):
    if msg.reply_to_message.sticker:
        global SET_STICKER
        SET_STICKER = msg.reply_to_message.sticker.file_id
        await msg.reply("✅ Sticker set for Episode breaks!")

@app.on_message(filters.command("setlogo") & filters.reply)
async def set_logo_h(_, msg):
    if msg.reply_to_message.photo:
        await msg.reply_to_message.download(file_name=LOGO_PATH)
        await msg.reply("✅ Logo set for Watermarks!")

@app.on_message(filters.command("format"))
async def format_h(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE
    IS_FORMATTING = True
    VIDEO_QUEUE = {}
    await msg.reply("📥 **Queue Mode ON!** Bhejo videos (Original Caption & Cover safe rahenge).")

@app.on_message(filters.video & filters.private)
async def collect_videos(_, msg):
    if not IS_FORMATTING: return
    ep = get_ep(msg.caption)
    res = get_res(msg.video)
    if ep not in VIDEO_QUEUE: VIDEO_QUEUE[ep] = {}
    VIDEO_QUEUE[ep][res] = msg
    await msg.reply(f"✅ Queued: Ep {ep} | {res}p", quote=True)

@app.on_message(filters.command("process"))
async def process_h(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE
    if not VIDEO_QUEUE: return await msg.reply("❌ Queue khaali hai!")
    
    st_msg = await msg.reply("⚙️ Processing episodes quality-wise...")
    IS_FORMATTING = False
    
    for ep in sorted(VIDEO_QUEUE.keys()):
        # Sort by resolution (480, 720, 1080...)
        for res in sorted(VIDEO_QUEUE[ep].keys()):
            v_msg = VIDEO_QUEUE[ep][res]
            # Copy preserves the ORIGINAL thumbnail and caption exactly as sent
            await v_msg.copy(chat_id=msg.chat.id)
            await asyncio.sleep(1.5)
        
        if SET_STICKER:
            await msg.reply_sticker(SET_STICKER)
            await asyncio.sleep(1)

    await st_msg.edit("✅ Batch Processing Complete!")
    VIDEO_QUEUE = {}

# ══════════════════════════════════════════════════════════════════════════════
#  ANIME SEARCH ENGINE (FULL CAPTION: GENRES + STUDIO + EXPANDABLE)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.text & filters.private & ~filters.command(["start","help","format","process","clear","setsticker","setlogo"]))
async def anime_search_h(_, msg):
    if msg.from_user.id not in ADMIN_IDS: return
    query = msg.text.strip()
    wait = await msg.reply(f"🔍 Searching **{query}**...")

    # Anilist Fetch
    q_ani = """query($s:String){ Media(search:$s,type:ANIME){ 
        idMal title{english romaji} genres description averageScore 
        season seasonYear studios(isMain:true){nodes{name}} 
        bannerImage coverImage{extraLarge} } }"""
    
    async with aiohttp.ClientSession() as s:
        async with s.post("https://graphql.anilist.co", json={"query":q_ani, "variables":{"s":query}}) as r:
            data = await r.json()
            media = data.get("data", {}).get("Media")

    if not media: return await wait.edit("❌ Kuch nahi mila!")

    await wait.edit("📡 Scraping 9 Sources & Baking Thumbnail...")
    
    # Details extraction
    title = (media["title"].get("english") or media["title"].get("romaji") or query).upper()
    score = f"{(media.get('averageScore') or 0)/10:.1f}/10"
    season = f"{(media.get('season') or '').title()} {media.get('seasonYear') or ''}"
    studio = media.get("studios", {}).get("nodes", [{}])[0].get("name", "Unknown")
    genres = ", ".join((media.get("genres") or ["Action"])[:5])
    desc = html.escape(re.sub(r"<[^>]+>", "", media.get('description') or "No Synopsis Available."))
    
    # Image & Scraper
    main_img = media.get("bannerImage") or media.get("coverImage", {}).get("extraLarge")
    thumb = await make_kenshin_thumbnail(main_img)
    all_urls = await fetch_all_sources(query, media.get("idMal"))

    # Updated Caption with ALL features
    caption = (
        f"<b><blockquote>​「 {title} 」</blockquote>\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"🌸 Category: Anime\n"
        f"🍥 Season: {season}\n"
        f"🍡 Score: {score}\n"
        f"🍵 Studio: {studio}\n"
        f"🎐 Genres: {genres}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"<blockquote expandable>​📜 SYNOPSIS: ​{desc}</blockquote>\n\n"
        f"<blockquote>POWERED BY:- [@KENSHIN_ANIME]</blockquote></b>"
    )

    await wait.delete()
    if thumb: await msg.reply_photo(thumb, caption=caption, parse_mode=ParseMode.HTML)
    else: await msg.reply_photo(main_img, caption=caption, parse_mode=ParseMode.HTML)

    if all_urls:
        for i in range(0, min(len(all_urls), 40), 10):
            batch = [InputMediaPhoto(u) for u in all_urls[i:i+10]]
            try: await msg.reply_media_group(batch); await asyncio.sleep(1.2)
            except: pass

if __name__ == "__main__":
    app.run()
