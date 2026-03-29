import os, re, html, asyncio
import aiohttp
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InputMediaPhoto

# ── Config ────────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))

app = Client("kenshin_info_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

HEADERS = {"User-Agent": "KenshinAnimeBot/2.0"}

# ── AniList fetch ─────────────────────────────────────────────────────────────
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

# ── Jikan (MAL) fetch ─────────────────────────────────────────────────────────
async def fetch_jikan_pictures(mal_id: int) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            # Anime pictures
            async with s.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/pictures",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    for item in (d.get("data") or []):
                        if item.get("jpg", {}).get("large_image_url"):
                            urls.append(item["jpg"]["large_image_url"])
            await asyncio.sleep(0.4)
            # Character pictures
            async with s.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/characters",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    for char in (d.get("data") or [])[:12]:
                        img = (char.get("character") or {}).get("images", {}).get("jpg", {}).get("image_url")
                        if img:
                            urls.append(img)
    except Exception as e:
        print(f"[Jikan] {e}")
    return urls

# ── Kitsu fetch ───────────────────────────────────────────────────────────────
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
                for size in ("original", "large", "medium"):
                    if img.get(size):
                        urls.append(img[size])
                        break
    except Exception as e:
        print(f"[Kitsu] {e}")
    return urls

# ── Clean synopsis ────────────────────────────────────────────────────────────
def clean_desc(text: str, limit: int = 900) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text).strip()
    text = re.sub(r"\(Source:[^)]+\)", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text

# ── Stars string ─────────────────────────────────────────────────────────────
def stars(rating: float) -> str:
    filled = round(rating / 2)
    filled = max(0, min(5, filled))
    return "⭐" * filled + "☆" * (5 - filled)

# ── Format info message ───────────────────────────────────────────────────────
def format_info(media: dict) -> str:
    title  = (media["title"].get("english") or media["title"].get("romaji") or "Unknown")
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

# ── Validate image URL ────────────────────────────────────────────────────────
async def is_valid_image(session: aiohttp.ClientSession, url: str) -> bool:
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=6), allow_redirects=True) as r:
            ct = r.headers.get("content-type", "")
            return r.status == 200 and "image" in ct
    except:
        return False

# ── Main handler ──────────────────────────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.reply(
        "**🎌 Kenshin Anime Info Bot**\n\n"
        "Bas anime ka naam bhejo — main:\n"
        "• Genres, Rating, Synopsis dunga\n"
        "• Jitni ho sake utni images bhejunga\n\n"
        "_Example:_ `Solo Leveling` ya `Naruto`"
    )

@app.on_message(filters.text & filters.private & ~filters.command(["start"]))
async def on_anime_name(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    name = msg.text.strip()
    wait = await msg.reply(f"🔍 **{name}** search ho raha hai...")

    # Fetch AniList data
    media = await fetch_anilist(name)
    if not media:
        await wait.edit(
            "❌ Anime nahi mila AniList pe!\n"
            "Spelling check kar ya English title try kar."
        )
        return

    mal_id = media.get("idMal")

    await wait.edit("📸 Images collect ho rahi hain...")

    # Collect all images from all sources
    image_urls = []

    # 1. AniList cover + banner
    cover = media.get("coverImage") or {}
    for key in ("extraLarge", "large"):
        if cover.get(key):
            image_urls.append(cover[key])
            break
    if media.get("bannerImage"):
        image_urls.append(media["bannerImage"])

    # 2. Jikan/MAL pictures + characters
    if mal_id:
        jikan_imgs = await fetch_jikan_pictures(mal_id)
        image_urls.extend(jikan_imgs)

    # 3. Kitsu poster + cover
    kitsu_imgs = await fetch_kitsu_images(name)
    image_urls.extend(kitsu_imgs)

    # Deduplicate
    seen = set()
    unique_urls = []
    for u in image_urls:
        if u and u not in seen:
            seen.add(u)
            unique_urls.append(u)

    # Validate (check up to 35 URLs)
    await wait.edit(f"🖼️ {len(unique_urls)} images validate ho rahi hain...")
    valid_urls = []
    check_urls = unique_urls[:35]
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        results = await asyncio.gather(
            *[is_valid_image(session, u) for u in check_urls],
            return_exceptions=True
        )
        for url, ok in zip(check_urls, results):
            if ok is True:
                valid_urls.append(url)

    await wait.delete()

    # Send info card with first image
    info_text = format_info(media)
    if valid_urls:
        try:
            await msg.reply_photo(valid_urls[0], caption=info_text)
        except Exception:
            await msg.reply(info_text)

        # Remaining images in batches of 10
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

    await msg.reply(f"✅ Done! **{len(valid_urls)}** images bheji `{name}` ke liye.")


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Kenshin Anime Info Bot start ho raha hai...")
    app.run()
