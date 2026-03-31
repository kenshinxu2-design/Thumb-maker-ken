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
MAX_IMAGES = 1000

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
FONT_BOLD = "OpenSans-Bold.ttf"

# ══════════════════════════════════════════════════════════════════════════════
#  ABBREVIATIONS + ROLE KEYWORDS
# ══════════════════════════════════════════════════════════════════════════════
ABBR = {
    "jjk": "Jujutsu Kaisen", "aot": "Attack on Titan", "mha": "My Hero Academia",
    "hxh": "Hunter x Hunter", "fmab": "Fullmetal Alchemist Brotherhood",
    "op": "One Piece", "sl": "Solo Leveling", "dbs": "Dragon Ball Super",
    "kny": "Demon Slayer", "ds": "Demon Slayer", "rezero": "Re:Zero",
    "sao": "Sword Art Online", "cote": "Classroom of the Elite",
    "mp100": "Mob Psycho 100", "opm": "One Punch Man",
    "tg": "Tokyo Ghoul", "bsd": "Bungo Stray Dogs", "bc": "Black Clover",
    "csm": "Chainsaw Man", "jojo": "JoJo's Bizarre Adventure",
    "tensura": "That Time I Got Reincarnated as a Slime",
    "onk": "Oshi no Ko", "blue lock": "Blue Lock", "dr": "Dandadan",
}

ROLE_KEYWORDS = {
    "main character": "main", "mc": "main",
    "villain": "villain", "antagonist": "villain",
    "female lead": "female_lead", "waifu": "female_lead",
}

def parse_query(raw: str):
    q = raw.strip().lower()
    for kw in sorted(ROLE_KEYWORDS.keys(), key=len, reverse=True):
        if kw in q:
            q = q.replace(kw, "").strip(" ,.-")
            break
    anime_resolved = None
    for abbr in sorted(ABBR.keys(), key=len, reverse=True):
        if q == abbr or q.startswith(abbr + " ") or q.endswith(" " + abbr):
            anime_resolved = ABBR[abbr]
            break
    return anime_resolved or raw.strip()

def get_safe_name(char_obj: dict, query: str = "Unknown") -> str:
    raw = char_obj.get("name")
    if not raw: return query
    if isinstance(raw, dict): return raw.get("full") or raw.get("first") or query
    return str(raw)

# ══════════════════════════════════════════════════════════════════════════════
#  THUMBNAIL MAKER LOGIC
# ══════════════════════════════════════════════════════════════════════════════
async def make_kenshin_thumbnail(image_url):
    """Downloads image and adds Kenshin Branding at bottom"""
    if not image_url: return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200: return None
                img_data = await resp.read()
        
        img = Image.open(BytesIO(img_data)).convert("RGB")
        img = ImageOps.fit(img, (1280, 720)) 
        
        draw = ImageDraw.Draw(img)
        bar_height = 80
        overlay = Image.new('RGBA', (1280, bar_height), (0, 0, 0, 180))
        img.paste(overlay, (0, 720 - bar_height), overlay)
        
        try: font = ImageFont.truetype(FONT_BOLD, 45)
        except: font = ImageFont.load_default()
            
        text = "KENSHIN ANIME"
        w = draw.textlength(text, font=font)
        draw.text(((1280-w)/2, 720 - 65), text, fill="white", font=font)
        
        output = BytesIO()
        output.name = "thumb.jpg"
        img.save(output, "JPEG", quality=95)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Error making thumb: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE SOURCES (9 Sources)
# ══════════════════════════════════════════════════════════════════════════════
async def safe_fetch(coro) -> list:
    try:
        res = await coro
        return res if isinstance(res, list) else []
    except: return []

async def src_wallhaven(query: str, pages: int = 5) -> list:
    urls = []
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for page in range(1, pages + 1):
            try:
                async with s.get("https://wallhaven.cc/api/v1/search", params={"q": query, "categories": "010", "purity": "100", "sorting": "relevance", "page": str(page)}, timeout=8) as r:
                    d = await r.json()
                    batch = [p["path"] for p in (d.get("data") or []) if p.get("path")]
                    if not batch: break
                    urls.extend(batch)
            except: break
    return urls

async def src_safebooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        try:
            async with s.get("https://safebooru.org/index.php", params={"page": "dapi", "s": "post", "q": "index", "tags": tag, "json": "1", "limit": "100"}, timeout=8) as r:
                posts = await r.json(content_type=None)
                for p in (posts or []):
                    img = p.get("sample_url") or p.get("file_url")
                    if img: urls.append("https:" + img if img.startswith("//") else img)
        except: pass
    return urls

async def src_gelbooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        try:
            async with s.get("https://gelbooru.com/index.php", params={"page": "dapi", "s": "post", "q": "index", "tags": f"{tag} rating:general", "json": "1", "limit": "100"}, timeout=8) as r:
                d = await r.json(content_type=None)
                for p in (d.get("post") or []):
                    img = p.get("sample_url") or p.get("file_url")
                    if img: urls.append("https:" + img if img.startswith("//") else img)
        except: pass
    return urls

async def src_danbooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for page in range(1, 3):
            try:
                async with s.get("https://danbooru.donmai.us/posts.json", params={"tags": f"{tag} rating:g", "limit": "100", "page": str(page)}, timeout=8) as r:
                    for p in await r.json():
                        img = p.get("large_file_url") or p.get("file_url")
                        if img: urls.append(img)
            except: break
    return urls

async def src_jikan(mal_id: int) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(f"https://api.jikan.moe/v4/anime/{mal_id}/pictures", timeout=8) as r:
                d = await r.json()
                for item in (d.get("data") or []):
                    lg = item.get("jpg", {}).get("large_image_url")
                    if lg: urls.append(lg)
    except: pass
    return urls

# ══════════════════════════════════════════════════════════════════════════════
#  APIs & VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
ANILIST_Q = """query($s:String){ Media(search:$s,type:ANIME){ idMal title{english romaji} genres description averageScore season seasonYear studios(isMain:true){nodes{name}} coverImage{extraLarge} bannerImage } }"""

async def fetch_anilist(name: str):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://graphql.anilist.co", json={"query": ANILIST_Q, "variables": {"s": name}}, timeout=8) as r:
                return (await r.json()).get("data", {}).get("Media")
    except: return None

async def search_character(name: str):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get("https://api.jikan.moe/v4/characters", params={"q": name, "limit": "1"}, timeout=8) as r:
                d = await r.json()
                results = d.get("data") or []
                if not results: return None
                char_id = results[0].get("mal_id")
                if char_id:
                    async with s.get(f"https://api.jikan.moe/v4/characters/{char_id}", timeout=8) as r2:
                        return (await r2.json()).get("data")
                return results[0]
    except: return None

async def validate_urls(all_urls: list) -> list:
    valid = []
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for i in range(0, min(len(all_urls), MAX_IMAGES), 50):
            batch = all_urls[i:i+50]
            async def check(u):
                try:
                    async with session.head(u, timeout=5, allow_redirects=True) as r:
                        return u if r.status == 200 else None
                except: return None
            res = await asyncio.gather(*[check(u) for u in batch])
            valid.extend([u for u in res if u])
    return valid

# ══════════════════════════════════════════════════════════════════════════════
#  FORMATTING (NEW HTML)
# ══════════════════════════════════════════════════════════════════════════════
def clean_desc(text: str, limit: int = 400) -> str:
    if not text: return "No details available."
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).strip()
    return text[:limit].rsplit(" ", 1)[0] + "..." if len(text) > limit else text

def format_anime_info(media: dict) -> str:
    title = media["title"].get("english") or media["title"].get("romaji") or "Unknown"
    genres = ", ".join((media.get("genres") or ["Unknown"])[:4])
    rating = f"{(media.get('averageScore') or 0) / 10:.1f}"
    season = f"{(media.get('season') or 'Unknown').title()} {media.get('seasonYear') or ''}".strip()
    studio = media.get("studios", {}).get("nodes", [{}])[0].get("name", "Unknown")
    
    return (
        f"<b><blockquote>​「 {title} 」</blockquote>\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"🌸 Category: Anime\n"
        f"🍥 Season: {season}\n"
        f"🍡 Score: {rating}/10\n"
        f"🍵 Studio: {studio}\n"
        f"🎐 Tags: {genres}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"<blockquote>​📜 SYNOPSIS: ​{clean_desc(media.get('description'))}</blockquote>\n\n"
        f"<blockquote>POWERED BY:- [@KENSHIN_ANIME]</blockquote></b>"
    )

def format_char_info(char: dict) -> str:
    fullname = get_safe_name(char)
    fav = char.get("favorites") or 0
    return (
        f"<b><blockquote>​「 {fullname} 」</blockquote>\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"🌸 Category: Character\n"
        f"❤️ Favorites: {fav:,}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"<blockquote>​📜 ABOUT: ​{clean_desc(char.get('about'))}</blockquote>\n\n"
        f"<blockquote>POWERED BY:- [@KENSHIN_ANIME]</blockquote></b>"
    )

# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════════════════════════════════════
@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    await msg.reply("🚀 **Kenshin Bot v6 (HD Edition) Online!**\nSend anime or character name.")

@app.on_message(filters.text & filters.private & ~filters.command(["start"]))
async def on_search(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    query = parse_query(msg.text)
    wait = await msg.reply(f"🔍 Searching **{query}**...")

    media, char = await asyncio.gather(fetch_anilist(query), search_character(query))
    
    is_char = False
    if char and not media:
        is_char = True
    elif char and media:
        char_full = get_safe_name(char, "").lower()
        anime_name = (media.get("title", {}).get("english") or media.get("title", {}).get("romaji") or "").lower()
        if sum(1 for w in query.lower().split() if w in char_full) > sum(1 for w in query.lower().split() if w in anime_name):
            is_char = True

    if is_char:
        await _send_character(msg, wait, char, query)
    elif media:
        await _send_anime(msg, wait, media, query)
    else:
        await wait.edit("❌ Kuch nahi mila! Sahi naam likho.")

async def _send_anime(msg: Message, wait: Message, media: dict, query: str):
    title = media["title"].get("english") or media["title"].get("romaji") or query
    await wait.edit(f"🎌 **{title}** mila! Generating Thumbnail & Fetching Images...")
    
    # 1. Prepare Primary Image & Thumbnail
    primary_url = media.get("bannerImage") or media.get("coverImage", {}).get("extraLarge")
    thumb = await make_kenshin_thumbnail(primary_url)
    
    # 2. Fetch all other images
    wh, sb, gb, db = await asyncio.gather(
        safe_fetch(src_wallhaven(title)), safe_fetch(src_safebooru(title)),
        safe_fetch(src_gelbooru(title)), safe_fetch(src_danbooru(title))
    )
    jk = await safe_fetch(src_jikan(media.get("idMal"))) if media.get("idMal") else []
    
    all_urls = list(dict.fromkeys(wh + sb + gb + db + jk))
    valid = await validate_urls(all_urls)
    await wait.delete()
    
    caption_text = format_anime_info(media)
    
    # Send First Message (Thumbnail + HTML Caption)
    try:
        if thumb: await msg.reply_photo(thumb, caption=caption_text, parse_mode=ParseMode.HTML)
        elif primary_url: await msg.reply_photo(primary_url, caption=caption_text, parse_mode=ParseMode.HTML)
        else: await msg.reply(caption_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(e)
        await msg.reply(caption_text, parse_mode=ParseMode.HTML)
        
    # Send rest of the images in batches of 10
    if valid:
        for i in range(0, len(valid), 10):
            batch = [InputMediaPhoto(u) for u in valid[i:i+10]]
            try: await msg.reply_media_group(batch); await asyncio.sleep(1.5)
            except: pass

async def _send_character(msg: Message, wait: Message, char: dict, query: str):
    name = get_safe_name(char, query)
    await wait.edit(f"👤 **{name}** mila! Generating Thumbnail & Fetching Images...")
    
    primary_url = (char.get("images") or {}).get("jpg", {}).get("image_url")
    thumb = await make_kenshin_thumbnail(primary_url)
    
    wh, sb, gb, db = await asyncio.gather(
        safe_fetch(src_wallhaven(name, pages=3)), safe_fetch(src_safebooru(name)),
        safe_fetch(src_gelbooru(name)), safe_fetch(src_danbooru(name))
    )
    
    all_urls = list(dict.fromkeys(wh + sb + gb + db))
    valid = await validate_urls(all_urls)
    await wait.delete()
    
    caption_text = format_char_info(char)
    
    try:
        if thumb: await msg.reply_photo(thumb, caption=caption_text, parse_mode=ParseMode.HTML)
        elif primary_url: await msg.reply_photo(primary_url, caption=caption_text, parse_mode=ParseMode.HTML)
        else: await msg.reply(caption_text, parse_mode=ParseMode.HTML)
    except:
        await msg.reply(caption_text, parse_mode=ParseMode.HTML)
            
    if valid:
        for i in range(0, len(valid), 10):
            batch = [InputMediaPhoto(u) for u in valid[i:i+10]]
            try: await msg.reply_media_group(batch); await asyncio.sleep(1.5)
            except: pass

if __name__ == "__main__":
    app.run()
