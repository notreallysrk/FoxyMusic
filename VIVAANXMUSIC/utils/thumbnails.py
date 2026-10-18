import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.future import VideosSearch
from config import YOUTUBE_IMG_URL

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
W, H = 1280, 720


def _font(size, bold=False):
    paths = [
        "VIVAANXMUSIC/assets/thumb/font2.ttf" if bold else "VIVAANXMUSIC/assets/thumb/font.ttf",
        "VIVAANXMUSIC/assets/thumb/font.ttf",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _fit(text, font, width):
    text = str(text or "Unknown")
    if font.getlength(text) <= width:
        return text
    while text and font.getlength(text + "…") > width:
        text = text[:-1]
    return text + "…"


def _cover(image, size):
    image = image.convert("RGB")
    sw, sh = image.size
    tw, th = size
    scale = max(tw / max(sw, 1), th / max(sh, 1))
    image = image.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
    left = (image.width - tw) // 2
    top = (image.height - th) // 2
    return image.crop((left, top, left + tw, top + th))


def _rounded_paste(canvas, image, xy, radius, border=(255, 255, 255, 150), border_width=2):
    image = image.convert("RGBA")
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius, fill=255)
    canvas.paste(image, xy, mask)
    if border_width:
        ImageDraw.Draw(canvas).rounded_rectangle((xy[0], xy[1], xy[0] + image.width - 1, xy[1] + image.height - 1), radius, outline=border, width=border_width)


async def _download(session, url, fallback):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            if resp.status == 200:
                raw = await resp.read()
                from io import BytesIO
                return Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        pass
    return fallback.copy().convert("RGB")


async def get_thumb(videoid, user_id=None):
    # Bump cache version so older single-panel thumbnails are regenerated.
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v5.png")
    if os.path.exists(cache_path):
        return cache_path

    try:
        response = await VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1).next()
        results = response.get("result", [])
        if not results:
            raise ValueError("No YouTube result")
        current = results[0]
        title = current.get("title", "Unknown Song")
        channel = current.get("channel", {}).get("name", "YouTube Music")
        thumbnail_url = current.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
        duration = current.get("duration") or "Live"
        views = current.get("viewCount", {}).get("short", "Views unavailable")
    except Exception:
        title, channel, thumbnail_url, duration, views = "Unknown Song", "YouTube Music", YOUTUBE_IMG_URL, "Live", "Views unavailable"

    async with aiohttp.ClientSession() as session:
        main_image = await _download(session, thumbnail_url, Image.new("RGB", (16, 9), (80, 45, 25)))
        # Find nearby songs for the layered carousel; gracefully fall back if search fails.
        related = []
        try:
            search = await VideosSearch(f"{title} {channel}", limit=7).next()
            for item in search.get("result", []):
                vid = item.get("id")
                if vid and vid != videoid:
                    related.append({
                        "title": item.get("title", "Related song"),
                        "channel": item.get("channel", {}).get("name", "YouTube Music"),
                        "url": item.get("thumbnails", [{}])[0].get("url", thumbnail_url),
                    })
                if len(related) == 4:
                    break
        except Exception:
            pass
        related_images = []
        for item in related:
            related_images.append(await _download(session, item["url"], main_image))

    # Warm blurred background based on the current song artwork.
    bg = _cover(main_image, (W, H)).filter(ImageFilter.GaussianBlur(30))
    bg = ImageEnhance.Brightness(bg).enhance(0.48).convert("RGBA")
    warm = Image.new("RGBA", (W, H), (150, 72, 14, 95))
    bg = Image.alpha_composite(bg, warm)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.rectangle((0, 0, W, H), fill=(15, 12, 14, 40))
    bg = Image.alpha_composite(bg, shade)
    draw = ImageDraw.Draw(bg)

    # Five layered song cards, with the currently playing song emphasized in the middle.
    slots = [
        (78, 210, 220, 310, 0),
        (245, 178, 270, 350, 1),
        (815, 178, 270, 350, 1),
        (982, 210, 220, 310, 0),
    ]
    # Render back cards first so the central card naturally sits on top.
    for idx, (x, y, cw, ch, _) in enumerate(slots):
        im = related_images[idx] if idx < len(related_images) else main_image
        card = Image.new("RGBA", (cw, ch), (25, 25, 29, 205))
        art_h = int(ch * 0.68)
        art = _cover(im, (cw - 10, art_h))
        _rounded_paste(card, art, (5, 5), 16, border=(255, 255, 255, 100), border_width=1)
        cd = ImageDraw.Draw(card)
        small = _font(17, True)
        sub = _font(13)
        label = related[idx]["title"] if idx < len(related) else "More music"
        artist = related[idx]["channel"] if idx < len(related) else channel
        cd.text((12, art_h + 13), _fit(label, small, cw - 24), font=small, fill=(255, 255, 255, 245))
        cd.text((12, art_h + 40), _fit(artist, sub, cw - 24), font=sub, fill=(218, 218, 228, 230))
        _rounded_paste(bg, card, (x, y), 22, border=(255, 255, 255, 135), border_width=2)

    # Main featured card.
    cx, cy, cw, ch = 438, 112, 404, 438
    card = Image.new("RGBA", (cw, ch), (30, 27, 30, 220))
    art = _cover(main_image, (cw - 18, 294))
    _rounded_paste(card, art, (9, 9), 24, border=(255, 255, 255, 170), border_width=1)
    cd = ImageDraw.Draw(card)
    title_font, artist_font, meta_font = _font(29, True), _font(22), _font(16)
    cd.text((24, 317), _fit(title, title_font, cw - 48), font=title_font, fill=(255, 255, 255, 255))
    cd.text((24, 356), _fit(channel, artist_font, cw - 48), font=artist_font, fill=(220, 220, 232, 255))
    cd.text((25, 402), f"▶   {_fit(views, meta_font, 170)}   •   {duration}", font=meta_font, fill=(240, 240, 245, 255))
    _rounded_paste(bg, card, (cx, cy), 30, border=(255, 255, 255, 190), border_width=2)

    # Bottom translucent playback bar.
    bar = (54, 574, 1226, 686)
    draw.rounded_rectangle(bar, radius=55, fill=(20, 18, 23, 165), outline=(255, 255, 255, 145), width=2)
    icon_font = _font(38, True)
    draw.text((105, 602), "◀◀", font=_font(29, True), fill="white")
    draw.text((225, 596), "Ⅱ", font=_font(43, True), fill="white")
    draw.text((327, 602), "▶▶", font=_font(29, True), fill="white")

    # Current-track mini player.
    mini = (425, 586, 865, 674)
    draw.rounded_rectangle(mini, radius=23, fill=(8, 8, 12, 205))
    mini_art = _cover(main_image, (66, 66))
    _rounded_paste(bg, mini_art, (437, 597), 10, border=(255, 255, 255, 100), border_width=1)
    draw = ImageDraw.Draw(bg)
    draw.text((516, 595), _fit(title, _font(19, True), 330), font=_font(19, True), fill="white")
    draw.text((516, 621), _fit(channel, _font(15), 330), font=_font(15), fill=(215, 215, 225, 255))
    draw.rounded_rectangle((516, 652, 839, 658), radius=3, fill=(110, 115, 135, 255))
    draw.rounded_rectangle((516, 652, 650, 658), radius=3, fill=(255, 55, 95, 255))
    draw.text((898, 607), "◖))", font=_font(28, True), fill="white")
    draw.text((1000, 607), "☷", font=_font(31, True), fill="white")
    draw.text((1095, 607), "☏", font=_font(29, True), fill="white")

    # Subtle bot branding footer.
    brand_font = _font(15, True)
    brand = "Q U E E N M U S I C B O T"
    bw = draw.textbbox((0, 0), brand, font=brand_font)[2]
    draw.text(((W - bw) / 2, 698), brand, font=brand_font, fill=(255, 255, 255, 210))

    bg.convert("RGB").save(cache_path, quality=94)
    return cache_path
