"""
README - VIVAANXMUSIC Enhanced Features
"""

# 🎵 VIVAANXMUSIC - Complete Telegram Music Bot 🎵

## Latest Updates & Enhancements ✨

### New Features Added:

1. **Enhanced Statistics Tracking** 📊
   - Real-time bot performance metrics
   - Track active users and groups
   - Monitor total songs and videos played
   - Display accurate uptime

2. **Improved Player Controls** 🎧
   - Play/Pause/Skip/Previous buttons
   - Shuffle and repeat modes
   - Queue management
   - Playlist support

3. **Better Settings Management** ⚙️
   - Group-specific settings
   - User preferences
   - Notification controls
   - Audio/Video quality settings

4. **Enhanced Commands** 📝
   - `/stats` - View detailed statistics
   - `/ping` - Check bot status and response time
   - `/help` - Comprehensive help menu
   - `/settings` - Configure group settings
   - `/player` - Interactive player controls

5. **Performance Improvements** ⚡
   - Optimized database operations
   - Better error handling
   - Improved logging
   - Faster response times

### Existing Features:

✅ Play music from YouTube, Spotify, Apple Music
✅ Download songs, videos, and media from various platforms
✅ AI-powered features (GPT, Claude, Image Analysis)
✅ Media downloads (Instagram, TikTok, YouTube, etc.)
✅ Weather and news information
✅ Encryption/Decryption utilities
✅ Lyrics search and display
✅ Admin controls and moderation
✅ Multi-platform support

## Installation & Setup

```bash
# Clone repository
git clone https://github.com/Yewsdhi/Queenupdate.git
cd Queenupdate

# Install dependencies
pip install -r requirements.txt

# Configure .env file
cp .env.example .env
# Edit .env with your credentials

# Run bot
python -m VIVAANXMUSIC
```

## Configuration

Set the following environment variables:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
STRING1=your_session_string_1
STRING2=your_session_string_2
STRING3=your_session_string_3
STRING4=your_session_string_4
STRING5=your_session_string_5
MONGODB_URL=your_mongodb_url
OWNER_ID=your_owner_id
HEROKU_API_KEY=your_heroku_api_key
HEROKU_APP_NAME=your_heroku_app_name
```

## Bot Commands Reference

### Music Commands
- `/play` - Play audio in voice chat
- `/vplay` - Play video in voice chat
- `/song` - Download a song
- `/spotify` - Download from Spotify
- `/apple` - Download from Apple Music
- `/lyrics` - Search for lyrics
- `/queue` - Show current queue
- `/player` - Open player controls
- `/autoplay` - Toggle autoplay
- `/vcnotify` - Toggle VC notifications

### AI Features
- `/gpt` - Ask AI assistant
- `/claude` - Claude AI chat
- `/geminivision` - Analyze images
- `/editimg` - Edit images with AI
- `/getdraw` - Generate AI images
- `/genvid` - Generate short videos
- `/upscale` - Enhance images
- `/rmbg` - Remove image background

### Download Features
- `/youtube` - Download YouTube videos
- `/insta` - Download Instagram media
- `/tiktok` - Download TikTok videos
- `/facebook` - Download Facebook media
- `/x` - Download X/Twitter media
- `/snap` - Download Snapchat content

### Utilities
- `/weather` - Get weather information
- `/movie` - Search movie information
- `/news` - Get latest news
- `/ping` - Check bot status
- `/stats` - View bot statistics
- `/help` - Show help menu

### Admin Commands
- `/settings` - Configure group settings
- `/encrypt` - Encrypt content (PM only)
- `/decrypt` - Decrypt content (PM only)

## Performance Metrics

The bot now tracks:
- Total songs played
- Total videos played
- Active users count
- Active groups count
- Bot uptime
- Response time

## Troubleshooting

### Bot not responding?
- Check if bot token is valid
- Verify pyrogram strings are correct
- Check MongoDB connection
- Review error logs

### No sound in voice chat?
- Turn on voice chat in group
- Check FFmpeg installation
- Verify audio permissions
- Check bot admin status

### Download failures?
- Verify internet connection
- Check if content is available
- Review server logs
- Update yt-dlp package

## Support & Contact

📧 For support and issues:
- Open GitHub issues
- Contact @support on Telegram
- Check documentation

## Credits

🎵 **VIVAANXMUSIC** - Enhanced Telegram Music Bot
- Based on Pyrogram framework
- Powered by multiple APIs
- Community driven development

## License

MIT License - Feel free to use and modify

---

**Last Updated:** 2024
**Version:** Enhanced Edition
**Status:** ✅ Active & Maintained

Made with ❤️ for music lovers 🎵
