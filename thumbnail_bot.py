import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- Configuration ---
API_ID = os.environ.get("API_ID") 
API_HASH = os.environ.get("API_HASH") 
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = os.environ.get("ADMIN_ID") # Your numeric user ID

app = Client("thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store what step the admin is currently on
# Steps: 0=Idle, 1=Waiting for BG, 2=Waiting for Left, 3=Waiting for Right
admin_sessions = {}

# --- Image Generation Logic ---
def create_thumbnail(name, bg_path, left_path, right_path, output_path):
    # Canvas Settings
    WIDTH, HEIGHT = 1280, 720
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. Background (Blurred and darkened slightly)
    bg = Image.open(bg_path).convert("RGBA").resize((WIDTH, HEIGHT))
    bg = bg.filter(ImageFilter.GaussianBlur(3))
    bg_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 100)) # Dark tint
    canvas.paste(bg, (0, 0))
    canvas.paste(bg_overlay, (0, 0), bg_overlay)

    # 2. Right Anime Thumbnail (with rounded corners)
    right_img = Image.open(right_path).convert("RGBA").resize((750, 420))
    right_mask = Image.new("L", right_img.size, 0)
    ImageDraw.Draw(right_mask).rounded_rectangle((0, 0, right_img.size[0], right_img.size[1]), 20, fill=255)
    canvas.paste(right_img, (480, 160), right_mask)

    # 3. Left Character Image (with rounded corners)
    left_img = Image.open(left_path).convert("RGBA").resize((400, 660))
    left_mask = Image.new("L", left_img.size, 0)
    ImageDraw.Draw(left_mask).rounded_rectangle((0, 0, left_img.size[0], left_img.size[1]), 30, fill=255)
    canvas.paste(left_img, (40, 30), left_mask)

    # 4. Load Fonts (Using the ones you uploaded)
    try:
        title_font = ImageFont.truetype("fonts/font.ttf", 65)
        subtitle_font = ImageFont.truetype("fonts/DejaVuSansCondensed-Bold.ttf", 35)
        button_font = ImageFont.truetype("fonts/DejaVuSansCondensed-Bold.ttf", 25)
    except OSError:
        print("Fonts not found! Make sure they are in the 'fonts' folder. Using defaults.")
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        button_font = ImageFont.load_default()

    # 5. Add Texts
    # Main Anime Title
    draw.text((480, 30), name.upper(), font=title_font, fill="white")
    # Subtitle (KENSHIN ANIME)
    draw.text((480, 100), "KENSHIN ANIME", font=subtitle_font, fill="#FFD700") # Yellow/Gold

    # 6. Buttons
    btn_y = 620
    buttons = [("WATCH NOW", 480), ("KENSHIN ANIME", 820)]
    
    for text, x_pos in buttons:
        # Button Background
        draw.rounded_rectangle((x_pos, btn_y, x_pos + 300, btn_y + 70), radius=15, fill="#1A1A1A", outline="#333333", width=2)
        # Button Text (Centered)
        text_bbox = draw.textbbox((0, 0), text, font=button_font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_x = x_pos + (300 - text_w) / 2
        text_y = btn_y + (70 - text_h) / 2 - 5
        draw.text((text_x, text_y), text, font=button_font, fill="white")

    # Save final image
    canvas.save(output_path, "PNG")
    return output_path

# --- Bot Handlers ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return await message.reply("Bro, this is a private admin bot.")
    
    await message.reply("🔥 **Thumbnail Maker Ready!** 🔥\n\nSend me the **Anime Name** to start.")

@app.on_message(filters.text & filters.private & ~filters.command("start"))
async def get_name(client, message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    admin_sessions[ADMIN_ID] = {
        "step": 1,
        "name": message.text,
        "files": []
    }
    await message.reply(f"Anime set to: **{message.text}**\n\nNow send me the **Background Image**.")

@app.on_message(filters.photo & filters.private)
async def handle_photos(client, message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return

    session = admin_sessions.get(ADMIN_ID)
    if not session:
        return await message.reply("Send me the Anime Name first bro!")

    step = session["step"]
    msg = await message.reply("Downloading image...")
    file_path = await message.download()
    session["files"].append(file_path)

    if step == 1:
        session["step"] = 2
        await msg.edit("✅ Background saved!\n\nNow send the **Left Character Image**.")
    elif step == 2:
        session["step"] = 3
        await msg.edit("✅ Left Character saved!\n\nNow send the **Right Thumbnail Image**.")
    elif step == 3:
        await msg.edit("✅ All images received! Generating your thumbnail, wait a few seconds...")
        
        # Generate the thumbnail
        out_file = "final_thumbnail.png"
        try:
            create_thumbnail(
                name=session["name"],
                bg_path=session["files"][0],
                left_path=session["files"][1],
                right_path=session["files"][2],
                output_path=out_file
            )
            
            # Send it back
            await message.reply_photo(photo=out_file, caption=f"Thumbnail ready for **{session['name']}**! 🚀")
        except Exception as e:
            await msg.edit(f"❌ Error making thumbnail: {e}")
        finally:
            # Clean up local files so your server doesn't get full
            for f in session["files"]:
                if os.path.exists(f): os.remove(f)
            if os.path.exists(out_file): os.remove(out_file)
            admin_sessions.pop(ADMIN_ID, None) # Reset session

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
