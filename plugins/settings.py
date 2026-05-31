from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from bot import Bot
from plugins.utils import apply_small_caps
import asyncio

# Updated Main Settings Text with Small Caps and Quotes
MAIN_SETTINGS_TEXT = f"""{apply_small_caps("i'm an auto post maker & thumb maker bot, built with love.")}

{apply_small_caps("❝ ​❝ I’ll teach you about the world... and how limited your vision really is. ❞")}
— {apply_small_caps("➳≛⃝ Gojo ×͜×")}

✖️ {apply_small_caps("choose the category for which you wanna get help.")} {apply_small_caps("ask your doubts at support chat.")}

≡ {apply_small_caps("click below buttons to change or set its caption, buttons and template:")}"""

# FIX: Removed double header, removed extra spaces, added Quotes to Title, and added Audio.
def get_anime_settings_text(current_template="Template 1 (Orange)", current_branding="FOR MORE VISIT @ANIME_VERSE", current_buttons="🔸 JOIN NOW TO WATCH ▾ - {link}"):
    return f"""• <b>ᴛᴇᴍᴘʟᴀᴛᴇ:</b> {current_template}
• <b>ʙʀᴀɴᴅɪɴɢ:</b> {current_branding}
• <b>ʙᴜᴛᴛᴏɴs:</b>
<pre>{current_buttons}</pre>
• <b>ᴄᴀᴘᴛɪᴏɴ:</b>
<pre><code class="language-html">HTML
&lt;blockquote&gt;&lt;b&gt;{{title}}&lt;/b&gt;&lt;/blockquote&gt;
» Type: &lt;code&gt;{{type}}&lt;/code&gt;
» Rating: &lt;code&gt;{{rating}}&lt;/code&gt;
» Status: &lt;code&gt;{{status}}&lt;/code&gt;
» Episodes: &lt;code&gt;{{episodes}}&lt;/code&gt;
» Audio: &lt;code&gt;{{audio}}&lt;/code&gt;
» Genre: {{genres}}
&lt;blockquote expandable&gt;➤ Synopsis: {{plot}}&lt;/blockquote&gt;</code></pre>
<blockquote><b>⧗ sᴇᴛ ᴛʜᴇ ғᴏʟʟᴏᴡɪɴɢ ᴏᴘᴛɪᴏɴs: ❞</b></blockquote>"""


CAPTION_TEXT = """CURRENT CAPTION FORMAT:

<blockquote><b>{title}</b></blockquote>
» Type: <code>{type}</code>
» Rating: <code>{rating}</code>
» Status: <code>{status}</code>
» Episodes: <code>{episodes}</code>
» Audio: <code>{audio}</code>
» Genre: {genres}
<blockquote expandable>➤ Synopsis: {plot}</blockquote>

SEND THE NEW CAPTION FORMAT.
Available placeholders: {title}, {year}, {season}, {episodes}, {audio}, {genres}, {rating}, {status}, {plot}, {synopsis}."""

def get_anime_buttons_text(current_buttons=""):
    if not current_buttons:
        current_buttons = "Join - {link} && Group - https://t.me/posterprobot\nFor More - https://t.me/posterprobot"
    return f"""<blockquote><b>⧗ Sᴇᴛ Bᴜᴛᴛᴏɴs ғᴏʀ ANIME</b>
Cᴜʀʀᴇɴᴛ Bᴜᴛᴛᴏɴs:

<code>{current_buttons}</code>

Sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ʙᴜᴛᴛᴏɴ ᴄᴏɴғɪɢ.
Fᴏʀᴍᴀᴛ:

<code>Button Text - {{link}}</code>

Mᴜʟᴛɪᴘʟᴇ Bᴜᴛᴛᴏɴs:

<code>Join - {{link}} && Group - https://t.me/posterprobot</code>

Cᴏʟᴏʀᴇᴅ Bᴜᴛᴛᴏɴs:

<code>#g Gʀᴇᴇɴ - {{link}}</code>
<code>#r Rᴇᴅ - {{link}}</code>
<code>#p Pʀɪᴍᴀʀʏ - {{link}}</code></blockquote>"""

BRANDING_TEXT = """≡ Username: @ANIME_FURY
≡ Logo: branding.png

◉ CONFIGURE BRANDING OPTIONS BELOW: ❞"""

FONT_TEXT = """≡ Current Style: Small Caps
≡ Applied To: Title, Genres, Synopsis, Type, Category, Rating, Status, Episodes, Chapters, Pages, Year, Audio, Language

◉ CONFIGURE FONT OPTIONS BELOW: ❞"""

# FIX: New Main Settings Image
TEMPLATE_PIC = "https://ibb.co/p691TdFL"
# FIX: New Template 1 Preview Image
TEMPLATE_1_PIC = "https://ibb.co/1G9m6Ldz"

WAIT_MSG = "<blockquote><b>> › > ᴡᴀɪᴛ ᴀ sᴇᴄᴏɴᴅ...</b></blockquote>"

def get_header(title, user_id=None, user_name=None):
    sc_title = apply_small_caps(title)
    res = f"<blockquote><b>⚙️ {sc_title}</b></blockquote>\n"
    if user_id and user_name:
        res += f"<blockquote><b>👤 ᴜsᴇʀ:</b> <a href=\"tg://user?id={user_id}\">{user_name}</a></blockquote>\n"
    return res

font_toggles = {}

@Bot.on_message(filters.command('settings') & filters.private)
async def settings_command(client: Client, message: Message):
    user = message.from_user
    header = get_header("General Settings", user.id, user.first_name)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("Anime"), callback_data="set_anime"), InlineKeyboardButton(apply_small_caps("Manga"), callback_data="set_manga")],
        [InlineKeyboardButton(apply_small_caps("TvShows"), callback_data="set_tvshows"), InlineKeyboardButton(apply_small_caps("Movies"), callback_data="set_movies")],
        [InlineKeyboardButton(apply_small_caps("Post Setting"), callback_data="post_settings")],
        [InlineKeyboardButton(apply_small_caps("Auto Forward"), callback_data="auto_forward"), InlineKeyboardButton(apply_small_caps("Post Search"), callback_data="post_search")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="close")]
    ])
    await message.reply_photo(photo=TEMPLATE_PIC, caption=header + MAIN_SETTINGS_TEXT, reply_markup=keyboard)

@Bot.on_callback_query(filters.regex('^settings_main$'))
async def settings_main_cb(client: Client, query: CallbackQuery):
    user = query.from_user
    await query.edit_message_caption(caption=WAIT_MSG)
    header = get_header("General Settings", user.id, user.first_name)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("Anime"), callback_data="set_anime"), InlineKeyboardButton(apply_small_caps("Manga"), callback_data="set_manga")],
        [InlineKeyboardButton(apply_small_caps("TvShows"), callback_data="set_tvshows"), InlineKeyboardButton(apply_small_caps("Movies"), callback_data="set_movies")],
        [InlineKeyboardButton(apply_small_caps("Post Setting"), callback_data="post_settings")],
        [InlineKeyboardButton(apply_small_caps("Auto Forward"), callback_data="auto_forward"), InlineKeyboardButton(apply_small_caps("Post Search"), callback_data="post_search")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="close")]
    ])
    try:
        await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_PIC, caption=header + MAIN_SETTINGS_TEXT), reply_markup=keyboard)
    except:
        pass

@Bot.on_callback_query(filters.regex('^set_anime$'))
async def anime_settings_cb(client: Client, query: CallbackQuery):
    user = query.from_user
    await query.edit_message_caption(caption=WAIT_MSG)
    header = get_header("Anime Settings")

    try:
        from databases.database import db
        current_brand_text = await db.get_anime_brand_text(user.id) or "FOR MORE VISIT @ANIME_VERSE"
    except:
        current_brand_text = "FOR MORE VISIT @ANIME_VERSE"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("Caption"), callback_data="set_anime_caption"), InlineKeyboardButton(apply_small_caps("Buttons"), callback_data="set_anime_buttons")],
        [InlineKeyboardButton(apply_small_caps("Template"), callback_data="set_anime_template"), InlineKeyboardButton(apply_small_caps("Branding"), callback_data="set_anime_branding")],
        [InlineKeyboardButton(apply_small_caps("Font Style"), callback_data="set_anime_font")],
        [InlineKeyboardButton(apply_small_caps("Ongoing Anime"), callback_data="set_anime_ongoing")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="settings_main")]
    ])
    try:
        await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_PIC, caption=header + get_anime_settings_text(current_branding=current_brand_text)), reply_markup=keyboard)
    except:
        pass

@Bot.on_callback_query(filters.regex('^set_anime_caption$'))
async def anime_caption_cb(client: Client, query: CallbackQuery):
    await query.edit_message_caption(caption=WAIT_MSG)
    header = get_header("Caption Settings")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("Set Text"), callback_data="set_anime_caption_text")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="set_anime")]
    ])
    await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_PIC, caption=header + CAPTION_TEXT), reply_markup=keyboard)

@Bot.on_callback_query(filters.regex('^set_anime_caption_text$'))
async def anime_caption_text_cb(client: Client, query: CallbackQuery):
    await query.answer("Please send the custom caption format now.")
    try:
        response = await client.ask(query.from_user.id, "Send the new caption format (HTML allowed):", timeout=60)
        await response.reply_text("Caption successfully set.")
        await anime_caption_cb(client, query)
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "Timeout occurred.")

@Bot.on_callback_query(filters.regex('^set_anime_buttons$'))
async def anime_buttons_cb(client: Client, query: CallbackQuery):
    await query.edit_message_caption(caption=WAIT_MSG)
    header = get_header("Buttons Settings")
    try:
        from databases.database import db
        current_buttons = await db.get_anime_button_config(query.from_user.id)
    except:
        current_buttons = None

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗦𝗘𝗧", callback_data="set_anime_buttons_text"), InlineKeyboardButton("𝗕𝗔𝗖𝗞", callback_data="set_anime")],
        [InlineKeyboardButton("𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="close")]
    ])
    await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_PIC, caption=header + get_anime_buttons_text(current_buttons)), reply_markup=keyboard)

@Bot.on_callback_query(filters.regex('^set_anime_buttons_text$'))
async def anime_buttons_text_cb(client: Client, query: CallbackQuery):
    await query.answer("Please send the new button config now.")
    try:
        response = await client.ask(query.from_user.id, "Send the new button config format:", timeout=60)
        try:
            from databases.database import db
            await db.set_anime_button_config(query.from_user.id, response.text)
        except: pass
        await response.reply_text("✅ ʙᴜᴛᴛᴏɴs ᴄᴏɴғɪɢ sᴀᴠᴇᴅ ғᴏʀ ᴀɴɪᴍᴇ.")
        await anime_buttons_cb(client, query)
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "Timeout occurred.")

@Bot.on_callback_query(filters.regex('^set_anime_template$'))
async def anime_template_cb(client: Client, query: CallbackQuery):
    await query.edit_message_caption(caption=WAIT_MSG)
    header = get_header("Template Settings")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("✅ Template 1 (Main)"), callback_data="set_anime_template_1")],
        [InlineKeyboardButton(apply_small_caps("Poster 2"), callback_data="set_anime_template_2"), InlineKeyboardButton(apply_small_caps("Poster 3"), callback_data="set_anime_template_3")],
        [InlineKeyboardButton(apply_small_caps("Poster 4"), callback_data="set_anime_template_4"), InlineKeyboardButton(apply_small_caps("Poster 5"), callback_data="set_anime_template_5")],
        [InlineKeyboardButton(apply_small_caps("Poster 6"), callback_data="set_anime_template_6"), InlineKeyboardButton(apply_small_caps("Poster 7"), callback_data="set_anime_template_7")],
        [InlineKeyboardButton(apply_small_caps("Poster 8"), callback_data="set_anime_template_8"), InlineKeyboardButton(apply_small_caps("Poster 9"), callback_data="set_anime_template_9")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="set_anime")]
    ])
    text = apply_small_caps("◉ Select Template For Anime") + "\n\n- " + apply_small_caps("Current: Template 1 (Main)")
    try:
        await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_PIC, caption=header + text), reply_markup=keyboard)
    except:
        pass

# FIX: Jab Template 1 dabayenge toh Template 1 Preview Pic Dikhayega!
@Bot.on_callback_query(filters.regex('^set_anime_template_1$'))
async def anime_template_1_cb(client: Client, query: CallbackQuery):
    await query.answer("Previewing Template 1...", show_alert=False)
    header = get_header("Template Settings")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("✅ Template 1 (Main)"), callback_data="set_anime_template_1")],
        [InlineKeyboardButton(apply_small_caps("Poster 2"), callback_data="set_anime_template_2"), InlineKeyboardButton(apply_small_caps("Poster 3"), callback_data="set_anime_template_3")],
        [InlineKeyboardButton(apply_small_caps("Poster 4"), callback_data="set_anime_template_4"), InlineKeyboardButton(apply_small_caps("Poster 5"), callback_data="set_anime_template_5")],
        [InlineKeyboardButton(apply_small_caps("Poster 6"), callback_data="set_anime_template_6"), InlineKeyboardButton(apply_small_caps("Poster 7"), callback_data="set_anime_template_7")],
        [InlineKeyboardButton(apply_small_caps("Poster 8"), callback_data="set_anime_template_8"), InlineKeyboardButton(apply_small_caps("Poster 9"), callback_data="set_anime_template_9")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="set_anime")]
    ])
    text = apply_small_caps("◉ Select Template For Anime") + "\n\n- " + apply_small_caps("Current: Template 1 (Main)")
    try:
        await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_1_PIC, caption=header + text), reply_markup=keyboard)
    except:
        pass


@Bot.on_callback_query(filters.regex('^set_anime_branding$'))
async def anime_branding_cb(client: Client, query: CallbackQuery):
    await query.edit_message_caption(caption=WAIT_MSG)
    header = get_header("Branding Settings")

    try:
        from databases.database import db
        user_id = query.from_user.id
        current_brand_text = await db.get_anime_brand_text(user_id) or "@ANIME_FURY"
        current_brand_logo = await db.get_anime_brand_logo(user_id) or "branding.png"
    except:
        current_brand_text = "@ANIME_FURY"
        current_brand_logo = "branding.png"

    dynamic_branding_text = f"≡ Username: {current_brand_text}\n≡ Logo: {current_brand_logo}\n\n◉ CONFIGURE BRANDING OPTIONS BELOW: ❞"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(apply_small_caps("Set Text"), callback_data="set_anime_brand_text"), InlineKeyboardButton(apply_small_caps("Set Logo"), callback_data="set_anime_brand_logo")],
        [InlineKeyboardButton(apply_small_caps("Use Default"), callback_data="set_anime_brand_default")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="set_anime")]
    ])
    await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_PIC, caption=header + dynamic_branding_text), reply_markup=keyboard)

@Bot.on_callback_query(filters.regex('^set_anime_brand_text$'))
async def anime_brand_text_cb(client: Client, query: CallbackQuery):
    await query.answer("Please send the custom text now.")
    try:
        response = await client.ask(query.from_user.id, "Send the custom text for branding now:", timeout=60)
        try:
            from databases.database import db
            await db.set_anime_brand_text(query.from_user.id, response.text)
        except: pass
        await response.reply_text(f"Text set to: {response.text}")
        await anime_branding_cb(client, query)
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "Timeout occurred.")

@Bot.on_callback_query(filters.regex('^set_anime_brand_logo$'))
async def anime_brand_logo_cb(client: Client, query: CallbackQuery):
    await query.answer("Please send the custom logo photo now.")
    try:
        response = await client.ask(query.from_user.id, "Send the custom logo photo for branding now:", filters=filters.photo, timeout=60)
        photo_path = await response.download()
        try:
            from databases.database import db
            await db.set_anime_brand_logo(query.from_user.id, photo_path)
        except: pass
        await response.reply_text("Logo successfully set.")
        await anime_branding_cb(client, query)
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "Timeout occurred.")

@Bot.on_callback_query(filters.regex('^set_anime_brand_default$'))
async def anime_brand_default_cb(client: Client, query: CallbackQuery):
    try:
        from databases.database import db
        await db.del_anime_branding(query.from_user.id)
    except: pass
    await query.answer("Reverted to default branding.", show_alert=True)
    await anime_branding_cb(client, query)

@Bot.on_callback_query(filters.regex('^set_anime_font'))
async def anime_font_cb(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if user_id not in font_toggles:
        font_toggles[user_id] = {
            "style_normal": False,
            "style_smallcaps": True,
            "title": False,
            "genres": True,
            "type": True,
            "rating": True,
            "status": True,
            "episodes": True,
            "synopsis": True,
            "audio": True,
            "year": True
        }

    t = font_toggles[user_id]

    if data.startswith("set_anime_font_toggle_"):
        key = data.replace("set_anime_font_toggle_", "")
        if key in t:
            if key == "style_normal":
                t["style_normal"] = True
                t["style_smallcaps"] = False
            elif key == "style_smallcaps":
                t["style_normal"] = False
                t["style_smallcaps"] = True
            else:
                t[key] = not t[key]

    await query.edit_message_caption(caption=WAIT_MSG)
    header = get_header("Font Settings")

    def btn_label(state, name):
        return apply_small_caps(f"{'✅' if state else '❌'} {name}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_label(t['style_normal'], "Normal"), callback_data="set_anime_font_toggle_style_normal"),
         InlineKeyboardButton(btn_label(t['style_smallcaps'], "Small Caps"), callback_data="set_anime_font_toggle_style_smallcaps")],
        [InlineKeyboardButton(btn_label(t['title'], "Title"), callback_data="set_anime_font_toggle_title"),
         InlineKeyboardButton(btn_label(t['genres'], "Genres"), callback_data="set_anime_font_toggle_genres")],
        [InlineKeyboardButton(btn_label(t['type'], "Type"), callback_data="set_anime_font_toggle_type"),
         InlineKeyboardButton(btn_label(t['rating'], "Rating"), callback_data="set_anime_font_toggle_rating")],
        [InlineKeyboardButton(btn_label(t['status'], "Status"), callback_data="set_anime_font_toggle_status"),
         InlineKeyboardButton(btn_label(t['episodes'], "Episodes"), callback_data="set_anime_font_toggle_episodes")],
        [InlineKeyboardButton(btn_label(t['synopsis'], "Synopsis"), callback_data="set_anime_font_toggle_synopsis"),
         InlineKeyboardButton(btn_label(t['audio'], "Audio"), callback_data="set_anime_font_toggle_audio")],
        [InlineKeyboardButton(btn_label(t['year'], "Year"), callback_data="set_anime_font_toggle_year"),
         InlineKeyboardButton(apply_small_caps("Set All"), callback_data="set_anime_font_toggle_all")],
        [InlineKeyboardButton(apply_small_caps("Back"), callback_data="set_anime")]
    ])

    try:
        await query.edit_message_media(media=InputMediaPhoto(TEMPLATE_PIC, caption=header + FONT_TEXT), reply_markup=keyboard)
    except:
        pass
