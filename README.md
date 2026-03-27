# 🎨 Kenshin Anime Thumbnail Generator Bot

Professional anime thumbnail creator for Telegram with phone mockup design and frosted glass buttons.

## ✨ Features

- **3-Image Composite**: Background (blurred) + Right Thumbnail + Left Character
- **Phone Mockup**: Rounded corners with frame for character image
- **Theme Matching**: Auto-detects dominant color from anime poster
- **Frosted Glass Buttons**: "WATCH NOW" and "KENSHIN ANIME" buttons
- **Professional Typography**: Poppins Bold font with text effects
- **Admin-Only Access**: Restricted to authorized users
- **Fast Processing**: 2-3 seconds thumbnail generation

## 🚀 Setup Instructions

### 1. Get Your Telegram Credentials

1. Go to https://my.telegram.org
2. Login with your phone number
3. Click "API Development Tools"
4. Create a new application
5. Copy `API_ID` and `API_HASH`

### 2. Create Your Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Follow the prompts
4. Copy your `BOT_TOKEN`

### 3. Get Your User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID for `ADMIN_IDS`

### 4. Deploy to Railway

1. Go to [Railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect this repository
4. Add environment variables:
   - `API_ID`: Your API ID
   - `API_HASH`: Your API Hash
   - `BOT_TOKEN`: Your Bot Token
   - `ADMIN_IDS`: Your User ID (comma-separated for multiple admins)
5. Deploy!

## 📖 How to Use

1. **Start the bot**: `/start`
2. **Create thumbnail**: `/create Fullmetal Alchemist`
3. **Send images** in order:
   - First: Background image (will be blurred)
   - Second: Right thumbnail (main anime poster)
   - Third: Left thumbnail (character for phone mockup)
4. **Receive**: Professional thumbnail in 2-3 seconds!

### Example Workflow

```
You: /create Solo Leveling
Bot: ✅ Creating thumbnail for: Solo Leveling
     📤 Now send the background image

[You send background image]
Bot: ✅ Background received!
     📤 Now send the right thumbnail

[You send anime poster]
Bot: ✅ Right thumbnail received!
     📤 Now send the left thumbnail

[You send character image]
Bot: ⏳ Creating thumbnail... Please wait!
Bot: [Sends finished thumbnail]
     ✨ Solo Leveling Thumbnail Ready!
```

## 🛠️ Technical Details

### Image Processing
- **Canvas**: 1280x720px
- **Background**: Gaussian blur (radius 15) + 40% brightness
- **Right Thumbnail**: 580x650px with dark overlay
- **Phone Mockup**: 280x560px with rounded corners
- **Buttons**: 280x70px frosted glass effect

### Design Elements
- Dynamic color theming from anime poster
- Text stroke effects for readability
- Semi-transparent overlays
- Professional font rendering (Poppins Bold)

### Dependencies
- `pyrogram`: Telegram bot framework
- `TgCrypto`: Fast encryption
- `Pillow`: Image processing
- `requests`: Font downloading

## 📝 Commands

- `/start` - Welcome message
- `/create <anime_name>` - Start thumbnail creation
- `/cancel` - Cancel current process

## 🔒 Security

- Admin-only access via `ADMIN_IDS`
- Unauthorized users are blocked
- Session files auto-generated

## 🐛 Troubleshooting

### Bot not responding?
- Check Railway logs
- Verify all environment variables are set
- Ensure Bot Token is correct

### Images not processing?
- Make sure images are sent as photos (not files)
- Use high-quality images for best results
- Send images one at a time in order

### Font issues?
- Font auto-downloads from Google Fonts
- Falls back to default if download fails

## 📦 Project Structure

```
.
├── thumbnail_bot.py      # Main bot code
├── requirements.txt      # Python dependencies
├── Procfile             # Railway deployment config
├── .env.example         # Environment variables template
└── README.md            # This file
```

## 💡 Tips for Best Results

1. **Background**: Use colorful anime scenes
2. **Right Thumbnail**: Official anime poster works best
3. **Left Character**: Clear character image with good contrast
4. **Image Quality**: Use high-resolution images (1080p+)

## 🎯 Made For

**Kenshin Anime Network**
- Telegram: @kenshin_anime
- Professional anime thumbnails at scale

## 📄 License

Free to use and modify for Kenshin Anime Network.

---

Made with ❤️ for anime lovers worldwide! 🌟
