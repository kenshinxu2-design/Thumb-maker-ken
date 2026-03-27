import os
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pyrogram import Client, filters
from pyrogram.types import Message
import requests
from io import BytesIO

# Bot credentials
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

app = Client("thumbnail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User states for multi-step process
user_states = {}

class ThumbnailState:
    def __init__(self):
        self.anime_name = None
        self.background = None
        self.right_thumbnail = None
        self.left_thumbnail = None


def download_font():
    """Download Poppins Bold font if not exists"""
    font_path = "/tmp/Poppins-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path


def get_dominant_color(image):
    """Get dominant color from image for theme matching"""
    img = image.copy()
    img = img.resize((150, 150))
    pixels = img.getdata()
    
    # Get most common color
    colors = {}
    for pixel in pixels:
        if isinstance(pixel, int):
            continue
        rgb = pixel[:3] if len(pixel) >= 3 else pixel
        colors[rgb] = colors.get(rgb, 0) + 1
    
    if colors:
        dominant = max(colors.items(), key=lambda x: x[1])[0]
        return dominant
    return (33, 150, 243)  # Default blue


def create_phone_mockup(image, size=(280, 560)):
    """Create phone mockup effect with rounded corners"""
    img = image.copy()
    img = img.resize(size, Image.Resampling.LANCZOS)
    
    # Create rounded rectangle mask
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=30, fill=255)
    
    # Apply mask
    output = Image.new('RGBA', size, (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    
    # Add phone frame
    frame = Image.new('RGBA', (size[0] + 20, size[1] + 20), (0, 0, 0, 0))
    frame_draw = ImageDraw.Draw(frame)
    frame_draw.rounded_rectangle([(0, 0), (size[0] + 20, size[1] + 20)], 
                                  radius=35, outline=(40, 40, 40), width=8)
    
    # Composite
    result = Image.new('RGBA', (size[0] + 20, size[1] + 20), (0, 0, 0, 0))
    result.paste(frame, (0, 0), frame)
    result.paste(output, (10, 10), output)
    
    return result


def create_frosted_button(text, size, color):
    """Create frosted glass button effect"""
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Semi-transparent background with color tint
    bg_color = (*color, 120)
    draw.rounded_rectangle([(0, 0), size], radius=15, fill=bg_color)
    
    # Border glow
    draw.rounded_rectangle([(0, 0), size], radius=15, 
                          outline=(*color, 200), width=2)
    
    # Text
    try:
        font_path = download_font()
        font = ImageFont.truetype(font_path, 28)
    except:
        font = ImageFont.load_default()
    
    # Center text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Text with shadow
    draw.text((x+2, y+2), text, fill=(0, 0, 0, 150), font=font)
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    return img


def create_thumbnail(anime_name, bg_image, right_img, left_img):
    """Main thumbnail creation function"""
    
    # Canvas size
    width, height = 1280, 720
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    
    # 1. Background - blurred
    background = bg_image.copy()
    background = background.resize((width, height), Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=15))
    
    # Darken background
    enhancer = ImageEnhance.Brightness(background)
    background = enhancer.enhance(0.4)
    
    canvas.paste(background, (0, 0))
    
    # Get theme color from right thumbnail
    theme_color = get_dominant_color(right_img)
    
    # 2. Right thumbnail with dark overlay
    right_thumbnail = right_img.copy()
    right_thumbnail = right_thumbnail.resize((580, 650), Image.Resampling.LANCZOS)
    
    # Create dark overlay
    overlay = Image.new('RGBA', right_thumbnail.size, (0, 0, 0, 140))
    right_thumbnail = Image.alpha_composite(
        right_thumbnail.convert('RGBA'), 
        overlay
    )
    
    # Position right thumbnail
    right_x = width - 600
    right_y = 35
    canvas.paste(right_thumbnail, (right_x, right_y), right_thumbnail)
    
    # 3. Left character in phone mockup
    phone_mockup = create_phone_mockup(left_img)
    phone_x = 40
    phone_y = (height - phone_mockup.height) // 2
    canvas.paste(phone_mockup, (phone_x, phone_y), phone_mockup)
    
    # 4. Title section
    draw = ImageDraw.Draw(canvas)
    
    try:
        font_path = download_font()
        title_font = ImageFont.truetype(font_path, 72)
        subtitle_font = ImageFont.truetype(font_path, 42)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Anime name (top)
    title_upper = anime_name.upper()
    
    # Create text with stroke
    title_x = 370
    title_y = 100
    
    # Stroke effect
    for adj in range(-3, 4):
        for adj2 in range(-3, 4):
            draw.text((title_x+adj, title_y+adj2), title_upper, 
                     fill=(0, 0, 0, 180), font=title_font)
    
    # Main text with theme color gradient simulation
    draw.text((title_x, title_y), title_upper, 
             fill=(255, 255, 255, 255), font=title_font)
    
    # "KENSHIN ANIME" branding
    branding_y = title_y + 90
    draw.text((title_x+2, branding_y+2), "KENSHIN ANIME", 
             fill=(0, 0, 0, 200), font=subtitle_font)
    draw.text((title_x, branding_y), "KENSHIN ANIME", 
             fill=theme_color, font=subtitle_font)
    
    # 5. Bottom buttons
    button_y = height - 100
    
    # Watch Now button
    watch_btn = create_frosted_button("WATCH NOW", (280, 70), theme_color)
    canvas.paste(watch_btn, (370, button_y), watch_btn)
    
    # Kenshin Anime button
    kenshin_btn = create_frosted_button("KENSHIN ANIME", (280, 70), theme_color)
    canvas.paste(kenshin_btn, (670, button_y), kenshin_btn)
    
    # 6. Add accent lines/decoration
    draw.line([(360, title_y - 20), (width - 50, title_y - 20)], 
             fill=(*theme_color, 200), width=3)
    
    return canvas.convert('RGB')


@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Unauthorized! This bot is admin-only.")
        return
    
    await message.reply(
        "🎨 **Kenshin Anime Thumbnail Generator**\n\n"
        "Use /create <anime_name> to start creating a thumbnail!\n\n"
        "Example: `/create Fullmetal Alchemist`"
    )


@app.on_message(filters.command("create") & filters.private)
async def create_command(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Unauthorized!")
        return
    
    # Extract anime name
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Usage: /create <anime_name>")
        return
    
    anime_name = parts[1].strip()
    
    # Initialize state
    user_states[message.from_user.id] = ThumbnailState()
    user_states[message.from_user.id].anime_name = anime_name
    
    await message.reply(
        f"✅ Creating thumbnail for: **{anime_name}**\n\n"
        f"📤 Now send the **background image** (anime scene that will be blurred)"
    )


@app.on_message(filters.photo & filters.private)
async def handle_images(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    user_id = message.from_user.id
    if user_id not in user_states:
        await message.reply("❌ Use /create <anime_name> first!")
        return
    
    state = user_states[user_id]
    
    # Download image
    file_path = await message.download()
    img = Image.open(file_path).convert('RGB')
    os.remove(file_path)
    
    # Process based on current state
    if state.background is None:
        state.background = img
        await message.reply(
            "✅ Background received!\n\n"
            "📤 Now send the **right thumbnail** (main anime poster)"
        )
    
    elif state.right_thumbnail is None:
        state.right_thumbnail = img
        await message.reply(
            "✅ Right thumbnail received!\n\n"
            "📤 Now send the **left thumbnail** (main character image for phone mockup)"
        )
    
    elif state.left_thumbnail is None:
        state.left_thumbnail = img
        
        # All images received, create thumbnail
        status_msg = await message.reply("⏳ Creating thumbnail... Please wait!")
        
        try:
            result = create_thumbnail(
                state.anime_name,
                state.background,
                state.right_thumbnail,
                state.left_thumbnail
            )
            
            # Save to buffer
            output = BytesIO()
            result.save(output, format='JPEG', quality=95)
            output.seek(0)
            
            await message.reply_photo(
                photo=output,
                caption=f"✨ **{state.anime_name}** Thumbnail Ready!\n\n"
                        f"Made with ❤️ by Kenshin Anime"
            )
            
            await status_msg.delete()
            
            # Clean up state
            del user_states[user_id]
            
        except Exception as e:
            await status_msg.edit(f"❌ Error creating thumbnail: {str(e)}")
            del user_states[user_id]


@app.on_message(filters.command("cancel") & filters.private)
async def cancel(client, message: Message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
        await message.reply("❌ Thumbnail creation cancelled!")
    else:
        await message.reply("No active thumbnail creation process.")


if __name__ == "__main__":
    print("🚀 Kenshin Anime Thumbnail Bot Starting...")
    app.run()
