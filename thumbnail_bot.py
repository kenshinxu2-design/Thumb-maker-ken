import os, re, html, asyncio, urllib.parse
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto

# ── Config ────────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))

app = Client("kenshin_info_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}

# ── AniList ───────────────────────────────────────────────────────────────────
ANILIST_Q = """
query($s:String){
  Media(search:$s, type:ANIME){
    idMal
    title{ english romaji }
    genres
    description(asHtml:false)
    averageScore
    episodes
    status
    season
    seasonYear
    studios(isMain:true){ nodes{ name } }
    coverImage{ extraLarge large }
    bannerImage
    trailer{ site id }
  }
}
"""

async def fetch_anilist(name: str) -> dict | None:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.post(
                "https://graphql.anilist.co",
                json={"query": ANILIST_Q, "variables": {"s": name}},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status != 200:
                    return None
                d = await r.json()
        return (d.get("data") or {}).get("Media")
    except Exception as e:
        print(f"[AniList] {e}")
        return None

# ── Wallhaven (best HD wallpapers, free) ──────────────────────────────────────
async def fetch_wallhaven(query: str) -> list:
    urls = []
    queries = [query, f"{query} season 2"]
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for q in queries:
            try:
                async with s.get(
                    "https://wallhaven.cc/api/v1/search",
                    params={
                        "q": q,
                        "categories": "010",   # anime only
                        "purity": "100",        # SFW only
                        "sorting": "relevance",
                        "order": "desc",
                        "page": "1",
                    },
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status == 200:
                        d = await r.json()
                        for pin in (d.get("data") or []):
                            path = pin.get("path")
                            if path:
                                urls.append(path)
                        print(f"[Wallhaven] '{q}' → {len(d.get('data') or [])} results")
                    else:
                        print(f"[Wallhaven] {r.status} for '{q}'")
            except Exception as e:
                print(f"[Wallhaven] {e}")
    return urls

# ── Safebooru (anime art/fan art, free) ───────────────────────────────────────
async def fetch_safebooru(query: str) -> list:
    urls = []
    # Convert query to booru tags format
    tag = query.lower().strip().replace(" ", "_")
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                "https://safebooru.org/index.php",
                params={
                    "page": "dapi",
                    "s": "post",
                    "q": "index",
                    "tags": tag,
                    "json": "1",
                    "limit": "30",
                },
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status == 200:
                    posts = await r.json(content_type=None)
                    if isinstance(posts, list):
                        for p in posts:
                            img = p.get("sample_url") or p.get("file_url")
                            if img:
                                if img.startswith("//"):
                                    img = "https:" + img
                                urls.append(img)
                        print(f"[Safebooru] '{tag}' → {len(urls)} results")
                    else:
                        print(f"[Safebooru] Unexpected response type")
                else:
                    print(f"[Safebooru] {r.status}")
    except Exception as e:
        print(f"[Safebooru] {e}")
    return urls

# ── Jikan/MAL ─────────────────────────────────────────────────────────────────
async def fetch_jikan_pictures(mal_id: int) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/pictures",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    for item in (d.get("data") or []):
                        lg = item.get("jpg", {}).get("large_image_url")
                        if lg:
                            urls.append(lg)
    except Exception as e:
        print(f"[Jikan] {e}")
    return urls

# ── Kitsu ─────────────────────────────────────────────────────────────────────
async def fetch_kitsu_images(name: str) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                "https://kitsu.io/api/edge/anime",
                params={"filter[text]": name, "page[limit]": "3"},
                headers={"Accept": "application/vnd.api+json"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200:
                    return []
                d = await r.json()
        for item in (d.get("data") or []):
            attrs = item.get("attributes", {})
            for key in ("coverImage", "posterImage"):
                img = attrs.get(key) or {}
                for size in ("original", "large"):
                    if img.get(size):
                        urls.append(img[size])
                        break
    except Exception as e:
        print(f"[Kitsu] {e}")
    return urls

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_desc(text: str, limit: int = 900) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text).strip()
    text = re.sub(r"\(Source:[^)]+\)", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text

def stars(rating: float) -> str:
    filled = max(0, min(5, round(rating / 2)))
    return "⭐" * filled + "☆" * (5 - filled)

def format_info(media: dict) -> str:
    title  = media["title"].get("english") or media["title"].get("romaji") or "Unknown"
    genres = " | ".join(media.get("genres") or [])
    score  = media.get("averageScore") or 0
    rating = round(score / 10, 1)
    eps    = media.get("episodes") or "?"
    status = (media.get("status") or "").replace("_", " ").title()
    season = f"{(media.get('season') or '').title()} {media.get('seasonYear') or ''}".strip()
    nodes  = (media.get("studios") or {}).get("nodes") or []
    studio = nodes[0]["name"] if nodes else "Unknown"
    desc   = clean_desc(media.get("description") or "")
    trailer = ""
    tr = media.get("trailer") or {}
    if tr.get("site") == "youtube" and tr.get("id"):
        trailer = f"\n🎬 **Trailer:** https://youtu.be/{tr['id']}"
    return (
        f"🎌 **{title}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎭 **Genres:** `{genres}`\n"
        f"⭐ **Rating:** {stars(rating)} `{rating}/10`\n"
        f"📺 **Episodes:** `{eps}`\n"
        f"📡 **Status:** `{status}`\n"
        f"🗓️ **Season:** `{season}`\n"
        f"🏢 **Studio:** `{studio}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **Synopsis:**\n{desc}"
        f"{trailer}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 **KenshinAnime** | @kenshin\\_anime"
    )

async def is_valid_image(session: aiohttp.ClientSession, url: str) -> bool:
    try:
        async with session.head(
            url, timeout=aiohttp.ClientTimeout(total=7),
            allow_redirects=True, headers=HEADERS
        ) as r:
            ct = r.headers.get("content-type", "")
            return r.status == 200 and ("image" in ct or url.endswith((".jpg", ".jpeg", ".png", ".webp")))
    except:
        return False

# ── Bot Handlers ──────────────────────────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.reply(
        "**🎌 Kenshin Anime Info Bot v4**\n\n"
        "Bas anime ka naam bhejo:\n"
        "• Full info (genres, rating, synopsis)\n"
        "• HD wallpapers from Wallhaven\n"
        "• Fan art from Safebooru\n"
        "• Official art from MAL + Kitsu\n\n"
        "_Example:_ `Solo Leveling` ya `Trigun Stampede`"
    )

@app.on_message(filters.text & filters.private & ~filters.command(["start"]))
async def on_anime_name(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    name = msg.text.strip()
    wait = await msg.reply(f"🔍 Searching **{name}**...")

    # Run AniList + Wallhaven + Safebooru + Kitsu in parallel
    media_task     = asyncio.create_task(fetch_anilist(name))
    wallhaven_task = asyncio.create_task(fetch_wallhaven(name))
    safebooru_task = asyncio.create_task(fetch_safebooru(name))
    kitsu_task     = asyncio.create_task(fetch_kitsu_images(name))

    media, wallhaven_imgs, safebooru_imgs, kitsu_imgs = await asyncio.gather(
        media_task, wallhaven_task, safebooru_task, kitsu_task
    )

    if not media:
        await wait.edit("❌ Anime nahi mila!\nSpelling check kar ya English title try kar.")
        return

    mal_id = media.get("idMal")
    await wait.edit("📸 MAL images fetch ho rahi hain...")
    jikan_imgs = await fetch_jikan_pictures(mal_id) if mal_id else []

    # Collect: Wallhaven first (best quality), then fan art, then official
    image_urls = []

    # AniList cover + banner
    cover = media.get("coverImage") or {}
    for key in ("extraLarge", "large"):
        if cover.get(key):
            image_urls.append(cover[key])
            break
    if media.get("bannerImage"):
        image_urls.append(media["bannerImage"])

    image_urls.extend(wallhaven_imgs)   # HD wallpapers
    image_urls.extend(safebooru_imgs)   # Fan art
    image_urls.extend(jikan_imgs)       # Official MAL
    image_urls.extend(kitsu_imgs)       # Kitsu posters

    # Deduplicate
    seen, unique = set(), []
    for u in image_urls:
        if u and u not in seen:
            seen.add(u)
            unique.append(u)

    total_found = len(unique)
    await wait.edit(f"🖼️ {total_found} images mili! Validate ho rahi hain...")

    # Validate up to 60 URLs in parallel
    valid_urls = []
    check = unique[:60]
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        results = await asyncio.gather(
            *[is_valid_image(session, u) for u in check],
            return_exceptions=True
        )
        for url, ok in zip(check, results):
            if ok is True:
                valid_urls.append(url)

    await wait.delete()

    info_text = format_info(media)

    if valid_urls:
        try:
            await msg.reply_photo(valid_urls[0], caption=info_text)
        except Exception:
            await msg.reply(info_text)

        remaining = valid_urls[1:]
        for i in range(0, len(remaining), 10):
            batch = remaining[i:i+10]
            if not batch:
                break
            try:
                await msg.reply_media_group([InputMediaPhoto(u) for u in batch])
                await asyncio.sleep(1.2)
            except Exception as e:
                print(f"[MediaGroup] {e}")
                for u in batch:
                    try:
                        await msg.reply_photo(u)
                        await asyncio.sleep(0.5)
                    except:
                        pass
    else:
        await msg.reply(info_text)
        await msg.reply("⚠️ Koi valid image nahi mili. Dusra naam try kar.")
        return

    src_info = (
        f"📊 **Sources:**\n"
        f"🖼️ Wallhaven: `{len(wallhaven_imgs)}`\n"
        f"🎨 Safebooru: `{len(safebooru_imgs)}`\n"
        f"📺 MAL: `{len(jikan_imgs)}`\n"
        f"✅ **Total sent: {len(valid_urls)} images**"
    )
    await msg.reply(src_info)

# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Kenshin Anime Info Bot v4 start ho raha hai...")
    app.run()
