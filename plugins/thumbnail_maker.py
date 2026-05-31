import os
import aiohttp
import asyncio
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops, ImageEnhance
import textwrap
import io

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

TEMPLATE_PATH = os.path.join(ASSETS_DIR, "template.png")
HEX_MASK_PATH = os.path.join(ASSETS_DIR, "hex_mask.png")

def clean_logo(img):
    img = img.convert("RGBA")
    if img.getextrema()[3][0] < 255:
        return img
    
    tiny = img.convert("RGB").resize((32, 32))
    for r, g, b in tiny.getdata():
        if abs(r-g) > 25 or abs(r-b) > 25:
            return img 
            
    white_img = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white_img.putalpha(img.convert("L"))
    return white_img

def enhance_image(img):
    img = img.convert("RGB")
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = ImageEnhance.Contrast(img).enhance(1.2)
    img = ImageEnhance.Color(img).enhance(1.2)
    return img.convert("RGBA")

def apply_small_caps(text):
    if not text: return text
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    smallcaps = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    trans = str.maketrans(normal, smallcaps)
    return text.translate(trans)

def colorize_template_2(template_img, new_hex):
    import numpy as np
    arr = np.array(template_img)
    target_hex = new_hex.lstrip('#')
    new_r, new_g, new_b = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))

    max_c = np.max(arr[:,:,:3], axis=2)
    min_c = np.min(arr[:,:,:3], axis=2)
    saturation = max_c - min_c

    # Very simple color isolation for turquoise & purple on Template 2
    # Adjust this threshold as needed based on actual template colors
    mask = saturation > 30

    arr[:,:,0][mask] = new_r
    arr[:,:,1][mask] = new_g
    arr[:,:,2][mask] = new_b

    return Image.fromarray(arr)

async def generate_poster(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, crop_state=0, small_caps=False, template_url=None, color_hex="#FF6B00", template_version=1):

    if custom_image_path:
        anime_img = Image.open(custom_image_path).convert('RGBA')
    elif anime_img_url:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(anime_img_url) as resp:
                    anime_img_data = await resp.read()
                    anime_img = Image.open(io.BytesIO(anime_img_data)).convert('RGBA')
            except Exception:
                anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))
    else:
        anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))

    base_template = None
    if template_url and template_url.startswith("http"):
        try:
            async with aiohttp.ClientSession() as session:
                if "ibb.co" in template_url and not template_url.endswith(('.png', '.jpg', '.jpeg')):
                    async with session.get(template_url) as html_resp:
                        if html_resp.status == 200:
                            html = await html_resp.text()
                            match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                            if match:
                                template_url = match.group(1)
                
                async with session.get(template_url) as resp:
                    if resp.status == 200:
                        template_data = await resp.read()
                        base_template = Image.open(io.BytesIO(template_data)).convert('RGBA')
        except Exception:
            pass
            
    if not base_template:
        base_template = Image.open(TEMPLATE_PATH).convert('RGBA')

    if template_version == 2 and color_hex:
        base_template = colorize_template_2(base_template, color_hex).convert('RGBA')

    # If Poster 2 AND no custom image is sent (i.e. skipped fanart)
    # Then DO NOT punch out the mask. The fanart should sit cleanly below without hexagonal cutout.
    if template_version == 2 and not custom_image_path:
        anime_artwork = ImageOps.fit(anime_img, base_template.size, method=Image.Resampling.LANCZOS)
        anime_artwork = enhance_image(anime_artwork)
        final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        final_img.paste(anime_artwork, (0, 0))
        final_img.paste(base_template, (0, 0), base_template)
    else:
        try:
            fetched_mask = Image.open(HEX_MASK_PATH).convert('L')
        except:
            fetched_mask = Image.new('L', base_template.size, 0)

        fetched_mask = fetched_mask.resize(base_template.size, Image.Resampling.LANCZOS)

        strict_mask = fetched_mask.point(lambda p: 255 if p > 128 else 0)
        expanded_mask = strict_mask.filter(ImageFilter.MaxFilter(7))
        inverse_mask = ImageOps.invert(expanded_mask)

        r, g, b, a = base_template.split()
        punched_alpha = ImageChops.darker(a, inverse_mask)
        base_template.putalpha(punched_alpha)

        # 16:9 Blurred Background Layer
        blurred_bg = ImageOps.fit(anime_img, base_template.size, method=Image.Resampling.LANCZOS)
        blurred_bg = blurred_bg.filter(ImageFilter.GaussianBlur(35))
        blurred_bg = ImageEnhance.Brightness(blurred_bg).enhance(0.5)
        anime_artwork = blurred_bg.convert('RGBA')

        bbox = strict_mask.getbbox()
        if not bbox:
            bbox = (0, 0, 1920, 1080)

        mask_h = bbox[3] - bbox[1]
        mask_w = bbox[2] - bbox[0]

        # Universal Zoom Fit Setup (No blurred sides)
        if crop_state == 1:
            v_center = 0.0 # Top Focus
        elif crop_state == 2:
            v_center = 1.0 # Bottom Focus
        else:
            v_center = 0.5 # Center Focus (Default)

        fitted = ImageOps.fit(anime_img, (mask_w, mask_h), method=Image.Resampling.LANCZOS, centering=(0.5, v_center))
        anime_artwork.paste(fitted, (bbox[0], bbox[1]))

        anime_artwork = enhance_image(anime_artwork)

        final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        final_img.paste(anime_artwork, (0, 0))
        final_img.paste(base_template, (0, 0), base_template)

    draw = ImageDraw.Draw(final_img)

    logo_img = None
    if logo_url:
        try:
            if logo_url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200:
                            logo_data = await resp.read()
                            logo_img = Image.open(io.BytesIO(logo_data)).convert('RGBA')
            elif os.path.exists(logo_url):
                logo_img = Image.open(logo_url).convert('RGBA')
        except Exception:
            pass

    genres_caps = genres.upper() if genres else ""

    if small_caps:
        genres_caps = apply_small_caps(genres_caps)
        synopsis = apply_small_caps(synopsis)
        username = apply_small_caps(username)

    # ==========================================
    # BULLETPROOF FONT LOADER (Direct from your local files)
    # ==========================================
    try:
        if template_version == 2:
            font_main_white = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 85)
            font_colored_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 65)
        else:
            font_main_white = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 85)
            font_colored_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 65)
    except:
        font_main_white = font_colored_title = ImageFont.load_default()

    try:
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 35)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 30)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 40)
    except:
        try:
            # Agar Medium upload nahi kiya, toh Bold ko chhota karke use kar lega (Lekin microscopic nahi hoga)
            font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 35)
            font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 30)
            font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 40)
        except:
            font_genres = font_synopsis = font_brand = ImageFont.load_default()

    # ==========================================
    # TITLE SHORTENER & S2 REPLACER
    # ==========================================
    title = title.upper()
    title = re.sub(r'(?i)\bSEASON\s+(\d+)', r'S\1', title) # Works for "Season 2", "SEASON 2", etc.
    
    wrapped_title = textwrap.fill(title, width=17) 
    title_lines = wrapped_title.split('\n')
    
    # 2-Line Limit Rule!
    if len(title_lines) > 2:
        title_lines = title_lines[:2]
        if len(title_lines[1]) > 14:
            title_lines[1] = title_lines[1][:14] + "..."
        else:
            title_lines[1] = title_lines[1] + "..."

    x_offset = 80
    y_dynamic_offset = 280

    try:
        font_colored_title_enlarged = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 75)
    except:
        font_colored_title_enlarged = font_colored_title

    for i, line in enumerate(title_lines):
        if i == 0:
            fill_color = "grey" if template_version == 2 else "white"
            draw.text((x_offset, y_dynamic_offset), line, font=font_main_white, fill=fill_color)
            y_dynamic_offset += 100 
        else:
            draw.text((x_offset, y_dynamic_offset), line, font=font_colored_title_enlarged, fill=color_hex)
            y_dynamic_offset += 85

    y_dynamic_offset += 30 if template_version == 2 else 20
    draw.text((x_offset, y_dynamic_offset), genres_caps, font=font_genres, fill=color_hex)

    synopsis_dynamic_max_chars = 220 - ((len(title_lines) - 1) * 60) 
    if len(synopsis) > synopsis_dynamic_max_chars:
        synopsis = synopsis[:synopsis_dynamic_max_chars].rsplit(' ', 1)[0] + "...read more"
    wrapped_synopsis = textwrap.fill(synopsis, width=45)

    y_dynamic_offset += 70 if template_version == 2 else 60
    draw.text((x_offset, y_dynamic_offset), wrapped_synopsis, font=font_synopsis, fill="#D3D3D3")

    brand_x = 80
    brand_y = 60
    
    if logo_img:
        try:
            logo_img = clean_logo(logo_img)
            logo_img = logo_img.resize((80, 80), Image.Resampling.LANCZOS).convert('RGBA')
            final_img.paste(logo_img, (brand_x, brand_y), logo_img)
            brand_x += 100 
        except Exception:
            pass 

    brand_color = color_hex if template_version == 2 else "white"
    draw.text((brand_x, brand_y + 15), username, font=font_brand, fill=brand_color)

    buf = io.BytesIO()
    final_img.save(buf, format='PNG')
    buf.seek(0)
    return buf
