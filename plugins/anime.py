import re
import time
import asyncio
import aiohttp
import urllib.parse
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.enums import ParseMode, ButtonStyle
from pyrogram import StopPropagation
from bot import Bot
from databases.database import db
from plugins.thumbnail_maker import generate_poster
from plugins.utils import apply_small_caps

user_data = {}

FANART_API_KEY = "dde00a3fdd2498bf1f664e686bd951ce"

COLORS = [
    {"name": "ORANGE", "hex": "#FF6B00", "url": "assets/template.png"},
    {"name": "GREEN", "hex": "#28a745", "url": "https://ibb.co/G4GhnCsZ"},
    {"name": "TURQUOISE", "hex": "#40E0D0", "url": "https://ibb.co/1fVPgwqd"},
    {"name": "DARK YELLOW", "hex": "#DAA520", "url": "https://ibb.co/yTznRcZ"},
    {"name": "PINK", "hex": "#FF69B4", "url": "https://ibb.co/b5DVk3LR"},
    {"name": "BLUE", "hex": "#007BFF", "url": "https://ibb.co/pjz3Ts34"},
    {"name": "PALE GREEN", "hex": "#98FB98", "url": "https://ibb.co/C3jnf6sr"},
    {"name": "RED", "hex": "#DC143C", "url": "https://ibb.co/9m1V2CPM"},
    {"name": "TEAL BLUE", "hex": "#20B2AA", "url": "https://ibb.co/LXD0djss"},
    {"name": "DARK PURPLE", "hex": "#483D8B", "url": "https://ibb.co/FLqd5jt4"},
    {"name": "PURPLE", "hex": "#8A2BE2", "url": "https://ibb.co/yc8zYYYt"}
]

async def fetch_extra_images(title_eng, title_rom, mal_id=None):
    extra_images = []
    if mal_id:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.jikan.moe/v4/anime/{mal_id}/pictures") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'data' in data:
                            for pic in data['data']:
                                if 'large_image_url' in pic['jpg']:
                                    extra_images.append(pic['jpg']['large_image_url'])
        except Exception:
            pass

    if FANART_API_KEY:
        search_titles = []
        for t in [title_eng, title_rom]:
            if not t: continue
            search_titles.append(t) 
            if ':' in t:
                search_titles.append(t.split(':')[0].strip()) 
            search_titles.append(t.split()[0].strip()) 
                
        search_titles = list(dict.fromkeys(search_titles))
        try:
            async with aiohttp.ClientSession() as session:
                tv_id = None
                for t in search_titles:
                    encoded_title = urllib.parse.quote(t)
                    url = f"https://webservice.fanart.tv/v3/search/tv?api_key={FANART_API_KEY}&query={encoded_title}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data and isinstance(data, list) and len(data) > 0:
                                tv_id = data[0].get('tvdb_id')
                                if tv_id: break 
                if tv_id:
                    img_url = f"https://webservice.fanart.tv/v3/tv/{tv_id}?api_key={FANART_API_KEY}"
                    async with session.get(img_url) as img_resp:
                        if img_resp.status == 200:
                            img_data = await img_resp.json()
                            for key in ['tvposter', 'showbackground', 'characterart', 'hdclearart']:
                                for item in img_data.get(key, []):
                                    extra_images.append(item['url'])
        except Exception:
            pass
    return extra_images

async def fetch_anime_search(query, source="anilist"):
    if source == "mal":
        url = f"https://api.jikan.moe/v4/anime?q={query}&limit=5"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if 'data' in data:
                    results = []
                    for item in data['data']:
                        results.append({
                            'id': item['mal_id'],
                            'mal_id': item['mal_id'],
                            'title': {
                                'romaji': item['title'],
                                'english': item.get('title_english', item['title'])
                            },
                            'genres': [g['name'] for g in item.get('genres', [])],
                            'description': item.get('synopsis', ''),
                            'coverImage': {'extraLarge': item['images']['jpg']['large_image_url']} if 'images' in item and 'jpg' in item['images'] else {},
                            'bannerImage': None 
                        })
                    return results
        return []

    url = "https://graphql.anilist.co"
    query_graphql = '''
    query ($search: String) {
      Page (page: 1, perPage: 5) {
        media (search: $search, type: ANIME) {
          id
          idMal
          title {
            romaji
            english
          }
          genres
          description(asHtml: false)
          coverImage {
            extraLarge
          }
          bannerImage
        }
      }
    }
    '''
    variables = {"search": query}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={'query': query_graphql, 'variables': variables}) as resp:
            data = await resp.json()
            if 'data' in data and 'Page' in data['data'] and 'media' in data['data']['Page']:
                results = []
                for item in data['data']['Page']['media']:
                    item['mal_id'] = item.get('idMal') 
                    results.append(item)
                return results
    return []

@Bot.on_message(filters.command("anime") & filters.private)
async def anime_cmd(client: Bot, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Please provide an anime name to search. Example: `/anime Naruto`")

    query = " ".join(message.command[1:])
    user_id = message.from_user.id

    user_data[user_id] = {
        'query': query,
        'results': [],
        'selected_anime': None,
        'crop_state': 0,
        'color_state': 0,
        'images': [],
        'current_image_idx': 0,
        'audio': None,
        'custom_image': None,
        'photo_msg_id': None,
        'timestamp': time.time()
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("Anilist"), callback_data="search_anilist"),
         InlineKeyboardButton(apply_small_caps("MyAnimeList"), callback_data="search_mal")],
        [InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")]
    ])

    await message.reply_text(f"SELECT SOURCE FOR: {query}", reply_markup=keyboard)


@Bot.on_callback_query(filters.regex("^search_anilist$"), group=-1)
async def handle_anilist_search(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("Session expired.", show_alert=True)
        raise StopPropagation

    query = user_data[user_id]['query']
    await callback_query.answer("Fetching from AniList...")
    await callback_query.message.edit_text("Searching...")

    try:
        results = await fetch_anime_search(query, "anilist")
        user_data[user_id]['results'] = results
        if not results:
            await callback_query.message.edit_text("No results found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")]]))
            raise StopPropagation

        buttons = [[InlineKeyboardButton(anime['title']['english'] or anime['title']['romaji'], callback_data=f"sel_ani_{i}")] for i, anime in enumerate(results)]
        buttons.append([InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")])

        await callback_query.message.edit_text(f"SEARCH RESULTS (ANILIST):", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")]]))
    raise StopPropagation


@Bot.on_callback_query(filters.regex("^search_mal$"), group=-1)
async def handle_mal_search(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("Session expired.", show_alert=True)
        raise StopPropagation

    query = user_data[user_id]['query']
    await callback_query.answer("Fetching from MAL...")
    await callback_query.message.edit_text("Searching...")

    try:
        results = await fetch_anime_search(query, "mal")
        user_data[user_id]['results'] = results
        if not results:
            await callback_query.message.edit_text("No results found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")]]))
            raise StopPropagation

        buttons = [[InlineKeyboardButton(anime['title']['english'] or anime['title']['romaji'], callback_data=f"sel_mal_{i}")] for i, anime in enumerate(results)]
        buttons.append([InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")])

        await callback_query.message.edit_text(f"SEARCH RESULTS (MAL):", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")]]))
    raise StopPropagation


@Bot.on_callback_query(filters.regex("^close_anime_menu$"), group=-1)
async def close_anime_menu(client: Bot, callback_query: CallbackQuery):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    if user_id in user_data:
        try:
            if user_data[user_id].get('photo_msg_id'):
                await client.delete_messages(chat_id=user_id, message_ids=user_data[user_id]['photo_msg_id'])
        except: pass
        del user_data[user_id]
    await callback_query.message.delete()
    raise StopPropagation


def get_initial_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("Custom Img"), callback_data="anime_thumb_custom"),
         InlineKeyboardButton(apply_small_caps("Skip"), callback_data="anime_audio_menu")],
        [InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")]
    ])


@Bot.on_callback_query(filters.regex(r"^sel_(ani|mal)_(\d+)"), group=-1)
async def handle_anime_select(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("Session expired.", show_alert=True)
        raise StopPropagation

    await callback_query.message.edit_text("⏳ Fetching High-Res Posters & Fanart...")

    idx = int(callback_query.matches[0].group(2))
    selected_anime = user_data[user_id]['results'][idx]
    user_data[user_id]['selected_anime'] = selected_anime

    title_eng = selected_anime['title'].get('english', '')
    title_rom = selected_anime['title'].get('romaji', '')
    
    images = []
    if selected_anime.get('bannerImage'): images.append(selected_anime['bannerImage'])
    if selected_anime.get('coverImage', {}).get('extraLarge'): images.append(selected_anime['coverImage']['extraLarge'])
    
    extra = await fetch_extra_images(title_eng, title_rom, mal_id=selected_anime.get('mal_id'))
    images.extend(extra)
    
    images = list(dict.fromkeys(images))
    user_data[user_id]['images'] = images

    img_url = images[0] if images else "https://via.placeholder.com/1920x1080"
    msg_text = apply_small_caps("Poster selection ready. Send custom image or skip to proceed.")

    try:
        await callback_query.message.delete()
        await client.send_photo(chat_id=callback_query.message.chat.id, photo=img_url, caption=msg_text, reply_markup=get_initial_keyboard())
    except Exception as e:
        await client.send_message(chat_id=callback_query.message.chat.id, text=f"{msg_text} \n\n (Preview failed: {e})", reply_markup=get_initial_keyboard())
    raise StopPropagation


@Bot.on_callback_query(filters.regex("^anime_thumb_custom$"), group=-1)
async def handle_anime_thumb_custom(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("Session expired.", show_alert=True)
        raise StopPropagation

    await callback_query.answer("Please send the custom photo now.")
    try:
        response = await client.ask(user_id, "Send the custom image for the poster now:", filters=filters.photo, timeout=60)
        photo_path = await response.download()
        user_data[user_id]['custom_image'] = photo_path
        await anime_audio_menu(client, callback_query)
    except asyncio.TimeoutError:
        await client.send_message(user_id, "Timeout occurred. Custom upload canceled.")
    raise StopPropagation


@Bot.on_callback_query(filters.regex("^anime_audio_menu$"), group=-1)
async def anime_audio_menu(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Hindi", callback_data="anime_audio_Hindi"), InlineKeyboardButton("English", callback_data="anime_audio_English")],
        [InlineKeyboardButton("Dual Audio", callback_data="anime_audio_Dual Audio"), InlineKeyboardButton("Multi Audio", callback_data="anime_audio_Multi Audio")],
        [InlineKeyboardButton("Jap & Eng", callback_data="anime_audio_Jap & Eng"), InlineKeyboardButton("Custom Text", callback_data="anime_audio_custom")],
        [InlineKeyboardButton(apply_small_caps("Cancel"), callback_data="close_anime_menu")]
    ])
    msg_text = "Select Audio Language or send custom text:"

    if callback_query.message.photo:
        await callback_query.message.delete()
        await client.send_message(user_id, msg_text, reply_markup=keyboard)
    else:
        await callback_query.message.edit_text(msg_text, reply_markup=keyboard)
    raise StopPropagation


@Bot.on_callback_query(filters.regex("^anime_audio_custom$"), group=-1)
async def handle_anime_audio_custom(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("Session expired.", show_alert=True)
        raise StopPropagation

    await callback_query.answer("Please send the custom audio text now.")
    try:
        response = await client.ask(user_id, "Send the custom audio text:", timeout=60)
        user_data[user_id]['audio'] = response.text
        callback_query.data = f"anime_audio_{response.text}"
        await handle_anime_generate(client, callback_query)
    except asyncio.TimeoutError:
        await client.send_message(user_id, "Timeout occurred.")
    raise StopPropagation


async def build_final_poster(client, callback_query, user_id):
    anime = user_data[user_id]['selected_anime']
    title = anime['title']['english'] or anime['title']['romaji']
    
    genres = "  ".join(anime.get('genres', [])[:3])
    
    synopsis = anime.get('description', '')
    if synopsis:
        synopsis = synopsis.replace('<br>', '').replace('<i>', '').replace('</i>', '').replace('<b>', '').replace('</b>', '')
    if synopsis and len(synopsis) > 300:
        synopsis = synopsis[:297] + "..."

    images = user_data[user_id]['images']
    img_idx = user_data[user_id]['current_image_idx']
    image_url = images[img_idx] if images else "https://via.placeholder.com/1920x1080"
    custom_image_path = user_data[user_id].get('custom_image')
    crop_state = user_data[user_id]['crop_state']
    color_state = user_data[user_id]['color_state']
    audio = user_data[user_id].get('audio', 'N/A')

    color_info = COLORS[color_state]

    try:
        from plugins.settings import font_toggles
        small_caps = font_toggles.get(user_id, {}).get("style_smallcaps", True)
    except: small_caps = False

    try:
        from databases.database import db
        if hasattr(db, 'get_anime_brand_text'):
            custom_text = await db.get_anime_brand_text(user_id)
            custom_logo = await db.get_anime_brand_logo(user_id)
        else:
            custom_text = await db.get_text(user_id)
            custom_logo = await db.get_logo(user_id)
    except Exception:
        custom_text = None
        custom_logo = None

    if callback_query and callback_query.from_user:
        fallback_name = f"@{callback_query.from_user.username}" if callback_query.from_user.username else callback_query.from_user.first_name
    else:
        try:
            usr = await client.get_users(user_id)
            fallback_name = f"@{usr.username}" if usr.username else usr.first_name
        except Exception:
            fallback_name = "PosterProBot"

    final_username = custom_text if custom_text else fallback_name

    poster_buf = await generate_poster(
        anime_img_url=image_url if not custom_image_path else None,
        custom_image_path=custom_image_path,
        title=title,
        genres=genres,
        synopsis=synopsis,
        username=final_username,
        logo_url=custom_logo,    
        crop_state=crop_state,
        small_caps=False,
        template_url=color_info['url'], 
        color_hex=color_info['hex']
    )

    try:
        caption_template = await db.get_caption(user_id)
    except: caption_template = None

    if not caption_template:
        caption_template = "<blockquote><b>{title}</b></blockquote>\n» Type: <code>{type}</code>\n» Rating: <code>{rating}</code>\n» Status: <code>{status}</code>\n» Episodes: <code>{episodes}</code>\n» Audio: <code>{audio}</code>\n» Genre: {genres}\n<blockquote expandable>➤ Synopsis: {plot}</blockquote>"

    anime_type = str(anime.get('format', anime.get('type', 'TV')))
    rating = str(anime.get('averageScore', anime.get('score', 'N/A')))
    status = str(anime.get('status', 'FINISHED'))
    episodes = str(anime.get('episodes', 'N/A'))

    v_title = apply_small_caps(title) if small_caps else title
    v_type = apply_small_caps(anime_type) if small_caps else anime_type
    v_rating = apply_small_caps(rating) if small_caps else rating
    v_status = apply_small_caps(status) if small_caps else status
    v_episodes = apply_small_caps(episodes) if small_caps else episodes
    v_genres = apply_small_caps(genres) if small_caps else genres
    v_plot = apply_small_caps(synopsis) if small_caps else synopsis
    v_audio = apply_small_caps(audio) if small_caps else audio

    try:
        caption = caption_template.format(title=v_title, type=v_type, rating=v_rating, status=v_status, episodes=v_episodes, genres=v_genres, plot=v_plot, synopsis=v_plot, audio=v_audio, year="N/A", season="N/A")
    except Exception:
        caption = f"<blockquote><b>{v_title}</b></blockquote>\n» Audio: <code>{v_audio}</code>\n» Genres: {v_genres}"

    return poster_buf, caption

def get_final_keyboard(color_state):
    color_name = COLORS[color_state]['name']
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗠𝗢𝗩𝗘", callback_data="anime_final_move"),
         InlineKeyboardButton("𝗡𝗘𝗫𝗧 𝗜𝗠𝗔𝗚𝗘", callback_data="anime_final_next")],
        [InlineKeyboardButton(f"🎨 {color_name}", callback_data="anime_final_color")],
        [InlineKeyboardButton("𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="close_anime_menu"),
         InlineKeyboardButton("𝗗𝗢𝗡𝗘", callback_data="final_done")]
    ])

@Bot.on_callback_query(filters.regex(r"^anime_audio_(.*)"), group=-1)
async def handle_anime_generate(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("Session expired.", show_alert=True)
        raise StopPropagation

    if callback_query.data != "anime_audio_custom":
        audio = callback_query.matches[0].group(1) if hasattr(callback_query, 'matches') and callback_query.matches else callback_query.data.replace("anime_audio_", "")
        user_data[user_id]['audio'] = audio
    else:
        audio = user_data[user_id]['audio']

    await callback_query.message.edit_text("⏳ FETCHING METADATA...")
    await asyncio.sleep(1)
    await callback_query.message.edit_text("⏳ APPLYING ENHANCEMENTS AND GENERATING POSTER...")

    try:
        poster_buf, caption = await build_final_poster(client, callback_query, user_id)
        try:
            await callback_query.message.delete()
        except: pass
        
        photo_msg = await client.send_photo(
            chat_id=user_id,
            photo=poster_buf,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        
        user_data[user_id]['photo_msg_id'] = photo_msg.id
        
        await client.send_message(
            chat_id=user_id,
            text=f"⚙️ **{apply_small_caps('POSTER CONTROLS:')}**\nUse buttons below to modify your poster:",
            reply_markup=get_final_keyboard(user_data[user_id]['color_state'])
        )

    except Exception as e:
        await client.send_message(chat_id=user_id, text=f"Generation failed: {e}")

    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_final_move$"), group=-1)
async def handle_anime_final_move(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        return await callback_query.answer("Session expired.", show_alert=True)

    user_data[user_id]['crop_state'] = (user_data[user_id]['crop_state'] + 1) % 3
    states = ["Center Focus", "Top Focus (Face)", "Bottom Focus"]
    await callback_query.answer(f"Position: {states[user_data[user_id]['crop_state']]}", show_alert=False)

    try:
        poster_buf, caption = await build_final_poster(client, callback_query, user_id)
        await client.edit_message_media(
            chat_id=user_id,
            message_id=user_data[user_id]['photo_msg_id'],
            media=InputMediaPhoto(poster_buf, caption=caption, parse_mode=ParseMode.HTML)
        )
    except Exception:
        pass
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_final_next$"), group=-1)
async def handle_anime_final_next(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        return await callback_query.answer("Session expired.", show_alert=True)

    user_data[user_id]['current_image_idx'] = (user_data[user_id]['current_image_idx'] + 1) % max(1, len(user_data[user_id]['images']))
    await callback_query.answer("Loading next image...", show_alert=False)

    try:
        poster_buf, caption = await build_final_poster(client, callback_query, user_id)
        await client.edit_message_media(
            chat_id=user_id,
            message_id=user_data[user_id]['photo_msg_id'],
            media=InputMediaPhoto(poster_buf, caption=caption, parse_mode=ParseMode.HTML)
        )
    except Exception:
        pass
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_final_color$"), group=-1)
async def handle_anime_final_color(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        return await callback_query.answer("Session expired.", show_alert=True)

    user_data[user_id]['color_state'] = (user_data[user_id]['color_state'] + 1) % len(COLORS)
    color_name = COLORS[user_data[user_id]['color_state']]['name']
    
    await callback_query.answer(f"Applying {color_name} template...", show_alert=False)

    try:
        poster_buf, caption = await build_final_poster(client, callback_query, user_id)
        
        await client.edit_message_media(
            chat_id=user_id,
            message_id=user_data[user_id]['photo_msg_id'],
            media=InputMediaPhoto(poster_buf, caption=caption, parse_mode=ParseMode.HTML)
        )
        
        await callback_query.edit_message_reply_markup(
            reply_markup=get_final_keyboard(user_data[user_id]['color_state'])
        )
    except Exception:
        pass
    raise StopPropagation

def get_channel_pagination_keyboard(channels, page=0):
    PER_PAGE = 10
    total_pages = (len(channels) + PER_PAGE - 1) // PER_PAGE
    start_idx = page * PER_PAGE
    end_idx = min(start_idx + PER_PAGE, len(channels))

    keyboard_buttons = []
    current_row = []
    for i in range(start_idx, end_idx):
        channel = channels[i]
        current_row.append(InlineKeyboardButton(channel['title'], callback_data=f"anime_pub_ch_{channel['id']}"))
        if len(current_row) == 2:
            keyboard_buttons.append(current_row)
            current_row = []
    if current_row:
        keyboard_buttons.append(current_row)

    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️", callback_data=f"anime_pub_page_{page-1}"))
    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton("➡️", callback_data=f"anime_pub_page_{page+1}"))

    if pagination_row:
        keyboard_buttons.append(pagination_row)

    keyboard_buttons.append([InlineKeyboardButton("𝗠𝗘𝗡𝗨", callback_data="close_anime_menu"), InlineKeyboardButton("𝗕𝗔𝗖𝗞", callback_data="close_anime_menu")])
    return InlineKeyboardMarkup(keyboard_buttons)

async def process_publish_workflow(client: Bot, callback_query: CallbackQuery, user_id: int, page=0, edit_message=False):
    channels = await db.get_user_channels(user_id)
    if not channels:
        msg = "You haven't added any channels. Use ➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ to add one first."
        if edit_message:
            await callback_query.message.edit_text(msg)
        else:
            await client.send_message(user_id, msg)
        return

    channels.sort(key=lambda x: str(x.get('title', '')).lower())

    keyboard = get_channel_pagination_keyboard(channels, page)
    msg_text = "Select a channel to publish to:"

    if edit_message:
        await callback_query.message.edit_text(msg_text, reply_markup=keyboard)
    else:
        await client.send_message(user_id, msg_text, reply_markup=keyboard)

@Bot.on_callback_query(filters.regex(r"^anime_pub_page_(\d+)$"), group=-1)
async def handle_anime_pub_page(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        return await callback_query.answer("Session expired.", show_alert=True)
    page = int(callback_query.matches[0].group(1))
    await process_publish_workflow(client, callback_query, user_id, page=page, edit_message=True)
    raise StopPropagation

def parse_anime_buttons(config_str: str, target_link: str) -> InlineKeyboardMarkup:
    if not config_str:
        return None
    rows = []
    lines = config_str.strip().split('\n')
    for line in lines:
        if not line.strip():
            continue
        buttons_in_row = line.split('&&')
        row = []
        for btn_str in buttons_in_row:
            parts = btn_str.split('-', 1)
            if len(parts) == 2:
                btn_text = parts[0].strip()
                style = ButtonStyle.DEFAULT

                if btn_text.startswith('#p '):
                    style = ButtonStyle.PRIMARY
                    btn_text = btn_text[3:]
                elif btn_text.startswith('#g '):
                    style = ButtonStyle.SUCCESS
                    btn_text = btn_text[3:]
                elif btn_text.startswith('#r '):
                    style = ButtonStyle.DANGER
                    btn_text = btn_text[3:]
                elif btn_text.startswith('#'):
                    btn_text = btn_text.split(' ', 1)[1] if ' ' in btn_text else btn_text

                btn_url = parts[1].strip().replace('{link}', target_link)
                row.append(InlineKeyboardButton(btn_text, url=btn_url, style=style))
        if row:
            rows.append(row)
    return InlineKeyboardMarkup(rows) if rows else None

async def send_anime_post(client: Bot, user_id: int, chat_id: int, pin: bool = False):
    if user_id not in user_data or not user_data[user_id].get('photo_msg_id'):
        return None

    try:
        poster_buf, caption = await build_final_poster(client, None, user_id)
        post_link = user_data[user_id].get('post_link', '')

        button_config = await db.get_anime_button_config(user_id)
        if not button_config:
            button_config = "Join - {link} && Group - https://t.me/posterprobot\nFor More - https://t.me/posterprobot"

        reply_markup = parse_anime_buttons(button_config, post_link)

        msg = await client.send_photo(
            chat_id=chat_id,
            photo=poster_buf,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        if pin:
            try:
                await msg.pin()
            except Exception:
                pass
        return msg
    except Exception as e:
        import logging
        logging.error(f"Error sending anime post: {e}")
        return None

@Bot.on_callback_query(filters.regex("^anime_pub_cancel_confirm$"), group=-1)
async def handle_anime_pub_cancel_confirm(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        return await callback_query.answer("Session expired.", show_alert=True)
    await process_publish_workflow(client, callback_query, user_id, page=0, edit_message=True)
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_pub_confirm$"), group=-1)
async def handle_anime_pub_confirm(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data or 'publish_chat_id' not in user_data[user_id]:
        return await callback_query.answer("Session expired.", show_alert=True)

    msg_text = """<blockquote>ᴛʜʀᴏᴜɢʜ ᴛʜɪs ᴍᴇɴᴜ ʏᴏᴜ ᴄᴀɴ sᴀᴠᴇ ᴛʜᴇ ᴘᴏsᴛ ᴛᴏ sᴇɴᴅ ɪᴛ ʟᴀᴛᴇʀ ᴏʀ ᴄʜᴏᴏsᴇ ᴀᴅᴅɪᴛɪᴏɴᴀʟ sᴇᴛᴛɪɴɢs ʙᴇғᴏʀᴇ sᴇɴᴅɪɴɢ ɪᴛ ɪɴ ᴏɴᴇ ᴏʀ ᴍᴏʀᴇ ᴄʜᴀɴɴᴇʟs.

• Press "Schedule sending" to schedule the post to be sent at a future date
• Press "Schedule deletion" to schedule the post to be deleted at a future date
• Press "Pin post" to pin the post at the top of the channel.</blockquote>"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗦𝗘𝗡𝗗 𝗣𝗢𝗦𝗧", callback_data="anime_pub_send"), InlineKeyboardButton("𝗦𝗖𝗛𝗘𝗗𝗨𝗟𝗘", callback_data="anime_pub_schedule")],
        [InlineKeyboardButton("𝗦𝗘𝗡𝗗 𝗣𝗢𝗦𝗧 𝗧𝗢 𝗠𝗢𝗥𝗘 𝗖𝗛𝗔𝗡𝗡𝗘𝗟𝗦", callback_data="anime_pub_more")],
        [InlineKeyboardButton("𝗣𝗜𝗡 𝗣𝗢𝗦𝗧", callback_data="anime_pub_pin"), InlineKeyboardButton("𝗕𝗔𝗖𝗞", callback_data="anime_pub_back")],
        [InlineKeyboardButton("𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="close_anime_menu")]
    ])

    await callback_query.message.edit_text(msg_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    raise StopPropagation

@Bot.on_callback_query(filters.regex(r"^anime_pub_ch_(-\d+|\d+)$"), group=-1)
async def handle_anime_pub_ch(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        return await callback_query.answer("Session expired.", show_alert=True)

    chat_id = int(callback_query.matches[0].group(1))
    user_data[user_id]['publish_chat_id'] = chat_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirm Sending", callback_data="anime_pub_confirm"), InlineKeyboardButton("No", callback_data="anime_pub_cancel_confirm")],
        [InlineKeyboardButton("Back", callback_data="anime_pub_cancel_confirm")]
    ])

    await callback_query.message.edit_text("Do you want to post in this specific channel?", reply_markup=keyboard)
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_pub_back$"), group=-1)
async def handle_anime_pub_back(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        return await callback_query.answer("Session expired.", show_alert=True)
    await process_publish_workflow(client, callback_query, user_id)
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_pub_send$"), group=-1)
async def handle_anime_pub_send(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data or 'publish_chat_id' not in user_data[user_id]:
        return await callback_query.answer("Session expired.", show_alert=True)

    chat_id = user_data[user_id]['publish_chat_id']
    await callback_query.message.edit_text("Sending post...")
    msg = await send_anime_post(client, user_id, chat_id)
    if msg:
        await callback_query.message.edit_text("Post sent successfully.")
    else:
        await callback_query.message.edit_text("Failed to send post.")
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_pub_pin$"), group=-1)
async def handle_anime_pub_pin(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data or 'publish_chat_id' not in user_data[user_id]:
        return await callback_query.answer("Session expired.", show_alert=True)

    chat_id = user_data[user_id]['publish_chat_id']
    await callback_query.message.edit_text("Sending and pinning post...")
    msg = await send_anime_post(client, user_id, chat_id, pin=True)
    if msg:
        await callback_query.message.edit_text("Post sent and pinned successfully.")
    else:
        await callback_query.message.edit_text("Failed to send/pin post.")
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^anime_pub_more$"), group=-1)
async def handle_anime_pub_more(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data or 'publish_chat_id' not in user_data[user_id]:
        return await callback_query.answer("Session expired.", show_alert=True)

    chat_id = user_data[user_id]['publish_chat_id']
    await callback_query.message.edit_text("Sending post to current channel...")
    msg = await send_anime_post(client, user_id, chat_id)
    if msg:
        await callback_query.answer("Post sent. Select next channel.", show_alert=False)
        await process_publish_workflow(client, callback_query, user_id)
    else:
        await callback_query.message.edit_text("Failed to send post.")
    raise StopPropagation

from datetime import datetime

@Bot.on_callback_query(filters.regex("^anime_pub_schedule$"), group=-1)
async def handle_anime_pub_schedule(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_data or 'publish_chat_id' not in user_data[user_id]:
        return await callback_query.answer("Session expired.", show_alert=True)

    chat_id = user_data[user_id]['publish_chat_id']

    msg_text = """<blockquote>Sending schedule
Write the date in which the post will be sent using this format:
dd/mm/yy hh:mm

Examples:
<code>1/4/2022 22:30</code>
<code>in 10 days 5 hours 2 minutes</code>
<code>tomorrow at 12:00</code></blockquote>"""

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="close_anime_menu")]])

    try:
        response = await client.ask(user_id, msg_text, reply_markup=keyboard, parse_mode=ParseMode.HTML, timeout=120)

        # Simple parsing for dd/mm/yy hh:mm
        try:
            # We'll just support the exact dd/mm/yy hh:mm for now since full NLP parsing is complex
            dt_str = response.text.strip()
            # If length is 14 like 01/04/22 22:30 or 15 for 01/04/2022 22:30
            try:
                if len(dt_str.split('/')[2].split(' ')[0]) == 2:
                    dt_obj = datetime.strptime(dt_str, "%d/%m/%y %H:%M")
                else:
                    dt_obj = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
            except ValueError:
                # Basic relative handling (very simplified)
                from datetime import timedelta
                dt_obj = datetime.now()
                if "in" in dt_str.lower() and "minute" in dt_str.lower():
                    import re
                    mins = re.search(r'in (\d+) minute', dt_str.lower())
                    if mins: dt_obj += timedelta(minutes=int(mins.group(1)))
                else:
                    await client.send_message(user_id, "Could not parse date format. Please use dd/mm/yy hh:mm (e.g. 15/05/24 14:30)")
                    return

            client.scheduler.add_job(
                send_anime_post,
                'date',
                run_date=dt_obj,
                args=[client, user_id, chat_id]
            )
            await client.send_message(user_id, f"Post scheduled successfully for {dt_obj.strftime('%d/%m/%Y %H:%M')}.")
        except Exception as e:
            await client.send_message(user_id, f"Error parsing date or scheduling: {e}")

    except asyncio.TimeoutError:
        await client.send_message(user_id, "Scheduling canceled due to timeout.")
    raise StopPropagation

@Bot.on_callback_query(filters.regex("^final_done$"), group=-1)
async def handle_final_done(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.answer("Poster Done! Fetching channels...")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="close_anime_menu")]
    ])
    try:
        response = await client.ask(user_id, "<blockquote>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴍᴇ ᴛʜᴇ ʟɪɴᴋ ғᴏʀ ᴛʜᴇ ᴘᴏsᴛ/ᴅᴏᴡɴʟᴏᴀᴅ ʙᴜᴛᴛᴏɴ</blockquote>", reply_markup=keyboard, parse_mode=ParseMode.HTML, timeout=120)
        user_data[user_id]['post_link'] = response.text
        await process_publish_workflow(client, callback_query, user_id)
    except asyncio.TimeoutError:
        await client.send_message(user_id, "Publish process canceled due to timeout.")
    raise StopPropagation
