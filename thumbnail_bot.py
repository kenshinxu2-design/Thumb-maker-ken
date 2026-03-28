# ── Kenshin Anime Thumbnail Bot ─────────────────────────────────────────────
# Layout (exactly like your thumbnail):
#   TOP-LEFT    : Channel logo (circular, 112x112)
#   LEFT-CENTER : Title | Line | Genres | Synopsis | Stars+Rating
#   RIGHT       : Character in octagonal neon-glow frame
#   BOTTOM-RIGHT: "KENSHIN ANIME" in Satisfy script font
# ─────────────────────────────────────────────────────────────────────────────

import os, io, re, html, asyncio, math
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
from pyrogram import Client, filters, idle
from pyrogram.types import Message
import aiohttp, requests

# ── Config ───────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── Font Setup ────────────────────────────────────────────────────────────────
os.makedirs("fonts", exist_ok=True)

FONT_URLS = {
    # Bebas Neue  → bold condensed caps  (title / genres / rating)
    "bebas": [
        "https://cdn.jsdelivr.net/fontsource/fonts/bebas-neue@latest/latin-400-normal.ttf",
        "https://github.com/google/fonts/raw/refs/heads/main/ofl/bebasneuepro/BebasNeuePro-Regular.ttf",
    ],
    # Oswald Bold → synopsis body text
    "oswald": [
        "https://cdn.jsdelivr.net/fontsource/fonts/oswald@latest/latin-700-normal.ttf",
        "https://github.com/google/fonts/raw/refs/heads/main/ofl/oswald/static/Oswald-Bold.ttf",
    ],
    # Satisfy     → "KENSHIN ANIME" script at bottom
    "satisfy": [
        "https://cdn.jsdelivr.net/fontsource/fonts/satisfy@latest/latin-400-normal.ttf",
        "https://github.com/google/fonts/raw/refs/heads/main/ofl/satisfy/Satisfy-Regular.ttf",
    ],
}

def ensure_fonts():
    os.makedirs("fonts", exist_ok=True)
    for name, urls in FONT_URLS.items():
        path = f"fonts/{name}.ttf"
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print(f"[Font] {name} already exists ✓")
            continue
        downloaded = False
        for url in urls:
            try:
                print(f"[Font] Downloading {name} from {url[:60]}...")
                r = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                if len(r.content) < 1000:
                    print(f"[Font] {name} response too small, skipping...")
                    continue
                with open(path, "wb") as f:
                    f.write(r.content)
                print(f"[Font] {name} ✓ ({len(r.content)//1024}KB)")
                downloaded = True
                break
            except Exception as e:
                print(f"[Font] {url[:60]}... failed: {e}")
        if not downloaded:
            print(f"[Font] ⚠️  {name} download failed — will use fallback font")

def fnt(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = f"fonts/{name}.ttf"
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return ImageFont.truetype(path, size)
    # Fallback: system fonts so bot never crashes
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ttf-bitstream-vera/Vera.ttf",
    ]
    for fb in fallbacks:
        if os.path.exists(fb):
            print(f"[Font] Using system fallback: {fb}")
            return ImageFont.truetype(fb, size)
    return ImageFont.load_default()

# ── State Machine ─────────────────────────────────────────────────────────────
states: dict = {}   # uid → { step, data }

# ── AniList Fetch (anime + manga fallback) ───────────────────────────────────
async def fetch_anime(name: str) -> dict | None:
    for media_type in ("ANIME", "MANGA"):
        q = (
            "query($s:String){Media(search:$s,type:" + media_type + "){"
            "title{english romaji}genres description(asHtml:false)averageScore}}"
        )
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                    "https://graphql.anilist.co",
                    json={"query": q, "variables": {"s": name}},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    if r.status != 200:
                        continue
                    d = await r.json()
            media = (d.get("data") or {}).get("Media")
            if not media:
                continue
            title  = (media["title"].get("english") or media["title"].get("romaji") or name).upper()
            genres = [g.upper() for g in (media.get("genres") or [])[:3]]
            desc   = re.sub(r"<[^>]+>", "", media.get("description") or "").strip()
            desc   = html.unescape(desc).upper()
            score  = media.get("averageScore") or 0
            return {"title": title, "genres": genres, "desc": desc, "rating": round(score / 10, 1)}
        except Exception as e:
            print(f"[AniList] {media_type} error: {e}")
    return None

# ── Thumbnail Generator ───────────────────────────────────────────────────────
W, H = 1280, 720

# Character frame position & size (right side)
CX, CY, CW, CH = 810, 25, 448, 660

def make_octa_mask(w: int, h: int) -> Image.Image:
    cut = int(min(w, h) * 0.13)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(
        [(cut,0),(w-cut,0),(w,cut),(w,h-cut),(w-cut,h),(cut,h),(0,h-cut),(0,cut)],
        fill=255,
    )
    return m

def draw_star_poly(draw, cx, cy, r_out, r_in, fill, n=5):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi * i / n - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.polygon(pts, fill=fill)

def txt_w(draw, text: str, font) -> int:
    return draw.textbbox((0, 0), text, font=font)[2]

def auto_title_font(draw, title: str, max_w: int):
    for size in range(95, 44, -5):
        f = fnt("bebas", size)
        if txt_w(draw, title, f) <= max_w:
            return f
    return fnt("bebas", 45)

def wordwrap(draw, text: str, font, max_w: int, max_lines: int = 7):
    words, lines, cur = text.split(), [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if txt_w(draw, test, font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines[:max_lines]

def make_thumbnail(bg_b: bytes, char_b: bytes, anime: dict, logo_b: bytes | None) -> io.BytesIO:
    # ── Background ────────────────────────────────────────────────────────────
    canvas = Image.open(io.BytesIO(bg_b)).convert("RGBA")
    canvas = ImageOps.fit(canvas, (W, H), Image.LANCZOS)
    # Darken it so text pops
    canvas = ImageEnhance.Brightness(canvas.convert("RGB")).enhance(0.55).convert("RGBA")
    # Blue-dark overlay (matches your thumbnail's dark blue tone)
    canvas = Image.alpha_composite(canvas, Image.new("RGBA", (W, H), (0, 5, 22, 158)))

    # ── Character (octagonal, right side) ────────────────────────────────────
    char = ImageOps.fit(Image.open(io.BytesIO(char_b)).convert("RGBA"), (CW, CH), Image.LANCZOS)
    char_out = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    char_out.paste(char, mask=make_octa_mask(CW, CH))

    # Neon-blue glow border (multiple passes, thickest → thinnest)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    cut  = int(min(CW, CH) * 0.13)
    bp   = [
        (CX+cut, CY),      (CX+CW-cut, CY),
        (CX+CW,  CY+cut),  (CX+CW,    CY+CH-cut),
        (CX+CW-cut, CY+CH),(CX+cut,   CY+CH),
        (CX,  CY+CH-cut),  (CX,       CY+cut),
    ]
    for bw, ba in [(16,15),(11,40),(7,90),(4,175),(2,255)]:
        gd.line(bp + [bp[0]], fill=(0, 185, 255, ba), width=bw)
    canvas = Image.alpha_composite(canvas, glow)
    canvas.paste(char_out, (CX, CY), char_out)

    # ── Text layer ────────────────────────────────────────────────────────────
    draw  = ImageDraw.Draw(canvas)
    TX    = 130                  # left text start x
    MAX_W = CX - TX - 20        # ≈ 660px

    # Title (auto-sized to fit)
    tf = auto_title_font(draw, anime["title"], MAX_W)
    ty = 52
    draw.text((TX+2, ty+2), anime["title"], font=tf, fill=(0, 0, 0, 120))   # shadow
    draw.text((TX,   ty),   anime["title"], font=tf, fill=(255, 255, 255))
    ty += tf.size + 14

    # ── Separator line ────────────────────────────────────────────────────────
    draw.rectangle([TX, ty, TX + MAX_W, ty + 3], fill=(255, 255, 255, 210))
    ty += 16

    # ── Genres ────────────────────────────────────────────────────────────────
    gf = fnt("bebas", 42)
    draw.text((TX, ty), "  |  ".join(anime["genres"]), font=gf, fill=(255, 255, 255, 235))
    ty += 57

    # ── Synopsis (word-wrapped, ALL CAPS, Oswald Bold) ────────────────────────
    bf    = fnt("oswald", 26)
    lines = wordwrap(draw, anime["desc"], bf, MAX_W, max_lines=7)
    for line in lines:
        draw.text((TX, ty), line, font=bf, fill=(225, 225, 225, 215))
        ty += 34

    # ── Stars + Rating ────────────────────────────────────────────────────────
    ry  = max(ty + 18, 548)
    sr  = 16   # star radius
    gap = sr * 2 + 10
    for i in range(5):
        filled = i < int(round(anime["rating"] / 2))
        draw_star_poly(
            draw,
            TX + i * gap + sr, ry + sr,
            sr, sr * 0.42,
            (255, 220, 50) if filled else (130, 130, 130),
        )
    rf = fnt("bebas", 46)
    draw.text((TX + 5 * gap + 14, ry - 2), f"{anime['rating']}/10", font=rf, fill=(255, 255, 255))

    # ── Bottom "KENSHIN ANIME" (Satisfy script) ───────────────────────────────
    pf = fnt("satisfy", 76)
    draw.text((702+3, 626+3), "KENSHIN ANIME", font=pf, fill=(0, 60, 200, 110))   # shadow
    draw.text((702,   626),   "KENSHIN ANIME", font=pf, fill=(255, 255, 255, 242))

    # ── Logo (top-left, circular) ─────────────────────────────────────────────
    if logo_b:
        logo = Image.open(io.BytesIO(logo_b)).convert("RGBA").resize((112, 112), Image.LANCZOS)
        lm   = Image.new("L", (112, 112), 0)
        ImageDraw.Draw(lm).ellipse((0, 0, 112, 112), fill=255)
        lc   = Image.new("RGBA", (112, 112), (0, 0, 0, 0))
        lc.paste(logo, mask=lm)
        canvas.paste(lc, (15, 15), lc)

    # ── Output ────────────────────────────────────────────────────────────────
    out = io.BytesIO()
    canvas.convert("RGB").save(out, "PNG")
    out.seek(0)
    return out

# ── Bot Handlers ──────────────────────────────────────────────────────────────

@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.reply(
        "**🎌 Kenshin Anime Thumbnail Bot**\n\n"
        "`/thumbnail` — Thumbnail banao\n"
        "`/setlogo`   — Channel logo set karo\n"
        "`/cancel`    — Session cancel karo\n\n"
        "⚠️ Pehli baar `/setlogo` se apna logo set kar lo."
    )


@app.on_message(filters.command("cancel") & filters.private)
async def cmd_cancel(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    states.pop(msg.from_user.id, None)
    await msg.reply("❌ Session cancel ho gaya!")


@app.on_message(filters.command("setlogo") & filters.private)
async def cmd_setlogo(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    states[msg.from_user.id] = {"step": "logo"}
    await msg.reply("📸 Channel logo image bhejo:")


@app.on_message(filters.command("thumbnail") & filters.private)
async def cmd_thumbnail(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    states[msg.from_user.id] = {"step": "anime_name", "data": {}}
    await msg.reply("🎌 **Anime ya Manhwa ka naam bhejo:**")


@app.on_message((filters.photo | filters.text) & filters.private)
async def on_input(_, msg: Message):
    uid = msg.from_user.id
    if uid not in ADMIN_IDS:
        return
    st = states.get(uid)
    if not st:
        return
    # ignore other slash commands in the handler
    if msg.text and msg.text.startswith("/"):
        return

    step = st["step"]

    # ── LOGO ──────────────────────────────────────────────────────────────────
    if step == "logo":
        if not msg.photo:
            await msg.reply("⚠️ Photo bhejo bhai!")
            return
        buf = await msg.download(in_memory=True)
        buf.seek(0)
        open("logo.png", "wb").write(buf.read())
        states.pop(uid)
        await msg.reply("✅ Logo save ho gaya!")

    # ── ANIME NAME ────────────────────────────────────────────────────────────
    elif step == "anime_name":
        if msg.photo:
            await msg.reply("⚠️ Pehle anime ka naam **text** mein bhejo.")
            return
        name = msg.text.strip()
        wait = await msg.reply(f"⏳ **{name}** search ho raha hai AniList pe...")
        anime = await fetch_anime(name)
        if not anime:
            await wait.edit(
                "❌ AniList pe nahi mila!\n"
                "• English naam try karo\n"
                "• Spelling check karo\n"
                "`/thumbnail` se dobara try karo."
            )
            states.pop(uid)
            return
        st["data"]["anime"] = anime
        st["step"] = "bg_image"
        await wait.edit(
            f"✅ **{anime['title']}** mila!\n"
            f"🎭 Genres: `{'  |  '.join(anime['genres'])}`\n"
            f"⭐ Rating: `{anime['rating']}/10`\n\n"
            "Ab **background image** bhejo 🖼️\n"
            "_Anime ka koi bhi dungeon/scene wali image_"
        )

    # ── BG IMAGE ──────────────────────────────────────────────────────────────
    elif step == "bg_image":
        if not msg.photo:
            await msg.reply("⚠️ Background image (photo) bhejo!")
            return
        buf = await msg.download(in_memory=True)
        buf.seek(0)
        st["data"]["bg"] = buf.read()
        st["step"] = "char_image"
        await msg.reply("✅ Background liya!\nAb **character image** bhejo 🧍\n_Main character ki full-body ya half-body image_")

    # ── CHARACTER IMAGE ────────────────────────────────────────────────────────
    elif step == "char_image":
        if not msg.photo:
            await msg.reply("⚠️ Character image (photo) bhejo!")
            return
        buf = await msg.download(in_memory=True)
        buf.seek(0)
        st["data"]["char"] = buf.read()

        proc = await msg.reply("⚙️ Thumbnail ban raha hai, thoda wait karo...")
        try:
            logo_b = None
            if os.path.exists("logo.png"):
                with open("logo.png", "rb") as f:
                    logo_b = f.read()
            else:
                await proc.edit("⚙️ Thumbnail ban raha hai...\n_(Logo set nahi hai, `/setlogo` se baad mein set karo)_")

            thumb = make_thumbnail(
                st["data"]["bg"],
                st["data"]["char"],
                st["data"]["anime"],
                logo_b,
            )
            await proc.delete()
            await msg.reply_photo(
                thumb,
                caption=f"🎌 **{st['data']['anime']['title']}** — Thumbnail Ready! ✅",
            )
            states.pop(uid)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await proc.edit(f"❌ Error aaya bhai:\n`{e}`")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ensure_fonts()
    print("🚀 Kenshin Anime Thumbnail Bot chalu ho raha hai...")
    app.run()
