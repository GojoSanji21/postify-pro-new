import random
import requests
import logging
import asyncio
import aiohttp 
from pyrogram import enums
from bot import Bot
from pyrogram import __version__
from plugins.FORMATS import *
from config import *
from pyrogram.enums import ParseMode, ChatAction
from plugins.autoDelete import convert_time
from databases.database import db
from datetime import timedelta
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, ReplyKeyboardMarkup, ReplyKeyboardRemove


message_content = '''👋 Hey {first}\n
<blockquote><b>ᴘʀᴇᴍɪᴜᴍ ᴍᴇᴍʙᴇʀsʜɪᴘ ʙᴇɴᴇғɪᴛs:</b>
✨ ɴᴏ ᴀᴅs/ᴛᴏᴋᴇɴ ɴᴇᴇᴅᴇᴅ
✨ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss
✨ ᴘʀɪᴏʀɪᴛʏ sᴜᴘᴘᴏʀᴛ
✨ ᴇxᴄʟᴜsɪᴠᴇ ғᴇᴀᴛᴜʀᴇs
</blockquote>

<b>💰 ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʟᴀɴs:</b>

<blockquote>
🔹 <b>7 DAYS</b> - ₹39
🔹 <b>30 DAYS</b> - ₹99
🔹 <b>90 DAYS</b> - ₹299
🔹 <b>365 DAYS (1 YEAR)</b> - ₹999
</blockquote>
'''


logging.basicConfig(
    level=logging.INFO,  # Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def fileSettings(getfunc, setfunc=None, delfunc=False):
    btn_mode, txt_mode, pic_mode = '❌', off_txt, off_pic
    del_btn_mode = 'ᴇɴᴀʙʟᴇ ✅'
    try:
        if not setfunc:
            if await getfunc():
                txt_mode = on_txt
                btn_mode = '✅'
                del_btn_mode = 'ᴅɪsᴀʙʟᴇ ❌'

            return txt_mode, (del_btn_mode if delfunc else btn_mode)

        else:
            if await getfunc():
                await setfunc(False)
            else:
                await setfunc(True)
                pic_mode, txt_mode = on_pic, on_txt
                btn_mode = '✅'
                del_btn_mode = 'ᴅɪsᴀʙʟᴇ ❌'

            return pic_mode, txt_mode, (del_btn_mode if delfunc else btn_mode)

    except Exception as e:
        print(
            f"Error occured at [fileSettings(getfunc, setfunc=None, delfunc=False)] : {e}")


# Function to fetch anime data asynchronously
async def fetch_anime_data(api_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            response.raise_for_status()
            return await response.json()

# Function to get top anime asynchronously
async def get_top_anime():
    url = "https://api.jikan.moe/v4/top/anime"
    data = await fetch_anime_data(url)
    return data.get("data", [])

# Function to get weekly anime asynchronously
async def get_weekly_anime():
    url = "https://api.jikan.moe/v4/seasons/now"
    data = await fetch_anime_data(url)
    return data.get("data", [])

# Function to search for anime asynchronously
async def search_anime(query):
    url = f"https://api.jikan.moe/v4/anime?q={query}&page=1"
    data = await fetch_anime_data(url)
    return data.get("data", [])

# Cool font style for the anime title
def style_anime_title(title):
    return f"{title}".replace("A", "ᴀ").replace("B", "ʙ").replace("C", "ᴄ").replace("D", "ᴅ").replace("E", "ᴇ").replace("F", "ғ").replace("G", "ɢ").replace("H", "ʜ").replace("I", "ɪ").replace("J", "ᴊ").replace("K", "ᴋ").replace("L", "ʟ").replace("M", "ᴍ").replace("N", "ɴ").replace("O", "ᴏ").replace("P", "ᴘ").replace("Q", "ǫ").replace("R", "ʀ").replace("S", "s").replace("T", "ᴛ").replace("U", "ᴜ").replace("V", "ᴠ").replace("W", "ᴡ").replace("X", "x").replace("Y", "ʏ").replace("Z", "ᴢ")

# Get an emoji based on the anime title
def get_anime_emoji(title):
    emojis = ["✨", "🌟", "💫", "🔥", "💥", "🌸", "🎉", "🎇", "🎆", "⚡"]
    return emojis[hash(title) % len(emojis)]
# Provide or Make Button by takiing required modes and data

def buttonStatus(pc_data: str, hc_data: str, cb_data: str) -> list:
    button = [
        [
            InlineKeyboardButton(
                f'• ᴘᴄ: {pc_data}', callback_data='pc'),
            InlineKeyboardButton(
                f'• ʜᴄ: {hc_data}', callback_data='hc')
        ],
        [
            InlineKeyboardButton(
                f'• ᴄʙ: {cb_data}', callback_data='cb'),
            InlineKeyboardButton(f'sʙ •', callback_data='setcb')
        ],
        [
            InlineKeyboardButton('• ʀᴇғʀᴇsʜ', callback_data='files_cmd'),
            InlineKeyboardButton('ᴄʟᴏsᴇ •', callback_data='close')
        ],
    ]
    return button

# Verify user, if he/she is admin or owner before processing the query...


async def authoUser(query, id, owner_only=False):
    if not owner_only:
        if not any([id == OWNER_ID, await db.admin_exist(id)]):
            await query.answer("❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪs ʙᴏᴛ ʙᴀʙᴇʏʏʏ...!!!", show_alert=True)
            return False
        return True
    else:
        if id != OWNER_ID:
            await query.answer("❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴛʜᴇ ᴏᴡɴᴇʀ ᴏғ ᴛʜɪs ʙᴏᴛ ʙᴀʙᴇʏʏʏ...!!!", show_alert=True)
            return False
        return True


@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data
    if data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except BaseException:
            pass

    elif data == "about":
        user = await client.get_users(OWNER_ID)
        user_link = f"https://t.me/{user.username}" if user.username else f"tg://openmessage?user_id={OWNER_ID}" 
        ownername = f"<a href={user_link}>{user.first_name}</a>" if user.first_name else f"<a href={user_link}>no name !</a>"
        await query.edit_message_media(
            InputMediaPhoto("https://graph.org/file/0c1deac4eae31f7919a9e-255eee8322a7fbecf1.jpg", 
                            ABOUT_TXT.format(
                                botname = client.name,
                                ownername = ownername, 
                            )
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='start'), InlineKeyboardButton('sᴛᴀᴛs •', callback_data='setting')]
            ]),
        )
                
    elif query.data == "plan":
        btn = [[InlineKeyboardButton("👨‍💼 ᴏᴡɴᴇʀ", url="https://t.me/DoraShin_hlo"),
                 InlineKeyboardButton("📧 ᴀᴅᴍɪɴ", url="https://t.me/DoraShin_hlo")],
            [
            InlineKeyboardButton(' ᴄʟᴏꜱᴇ ', callback_data='close')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.reply_photo(
            photo=("https://graph.org/file/0c1deac4eae31f7919a9e-255eee8322a7fbecf1.jpg"),
            caption=message_content.format(
                first = query.from_user.mention, 
                second = query.from_user.mention
        ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        
    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
            

    elif data == "setting":
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), "<b>» ᴘʟᴇᴀsᴇ wᴀɪᴛ ᴀ sᴇᴄᴏɴᴅ ʙᴀʙᴇʏʏ !!</b>"))
        try:
            total_fsub = len(await db.get_all_channels())
            total_admin = len(await db.get_all_admins())
            total_ban = len(await db.get_ban_users())
            autodel_mode = 'ᴇɴᴀʙʟᴇᴅ' if await db.get_auto_delete() else 'ᴅɪsᴀʙʟᴇᴅ'
            protect_content = 'ᴇɴᴀʙʟᴇᴅ' if await db.get_protect_content() else 'ᴅɪsᴀʙʟᴇᴅ'
            hide_caption = 'ᴇɴᴀʙʟᴇᴅ' if await db.get_hide_caption() else 'ᴅɪsᴀʙʟᴇᴅ'
            chnl_butn = 'ᴇɴᴀʙʟᴇᴅ' if await db.get_channel_button() else 'ᴅɪsᴀʙʟᴇᴅ'
            reqfsub = 'ᴇɴᴀʙʟᴇᴅ' if await db.get_request_forcesub() else 'ᴅɪsᴀʙʟᴇᴅ'

            await query.edit_message_media(
                InputMediaPhoto(random.choice(PICS),
                                SETTING_TXT.format(
                                    total_fsub=total_fsub,
                                    total_admin=total_admin,
                                    total_ban=total_ban,
                                    autodel_mode=autodel_mode,
                                    protect_content=protect_content,
                                    hide_caption=hide_caption,
                                    chnl_butn=chnl_butn,
                                    reqfsub=reqfsub
                )
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='start'), InlineKeyboardButton(
                        'ᴄʟᴏsᴇ •', callback_data='close')]
                ]),
            )
        except Exception as e:
            print(f"! Error Occurred on callback data = 'setting' : {e}")

    elif data == "start":
        await query.edit_message_media(
            InputMediaPhoto(random.choice(PICS),
                            START_MSG.format(
                                first=query.from_user.first_name,
                                last=query.from_user.last_name,
                                username=None if not query.from_user.username else '@' + query.from_user.username,
                                mention=query.from_user.mention,
                                id=query.from_user.id
            )
            ),
            reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴄʟɪᴄᴋ ғᴏʀ ᴍᴏʀᴇ •", callback_data='about')],
                    [InlineKeyboardButton("• sᴇᴛᴛɪɴɢs", callback_data='setting'),
                     InlineKeyboardButton('ᴘᴏsᴛᴇʀ', callback_data='settings_main')],
                    [InlineKeyboardButton("➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data='add_channel_req')],
                ]),
        )

    elif data == "files_cmd":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                protect_content, pcd = await fileSettings(db.get_protect_content)
                hide_caption, hcd = await fileSettings(db.get_hide_caption)
                channel_button, cbd = await fileSettings(db.get_channel_button)
                name, link = await db.get_channel_button_link()

                await query.edit_message_media(
                    InputMediaPhoto(files_cmd_pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd)),
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'files_cmd' : {e}")

    elif data == "pc":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                pic, protect_content, pcd = await fileSettings(db.get_protect_content, db.set_protect_content)
                hide_caption, hcd = await fileSettings(db.get_hide_caption)
                channel_button, cbd = await fileSettings(db.get_channel_button)
                name, link = await db.get_channel_button_link()

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd))
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'pc' : {e}")

    elif data == "hc":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                protect_content, pcd = await fileSettings(db.get_protect_content)
                pic, hide_caption, hcd = await fileSettings(db.get_hide_caption, db.set_hide_caption)
                channel_button, cbd = await fileSettings(db.get_channel_button)
                name, link = await db.get_channel_button_link()

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd))
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'hc' : {e}")

    elif data == "cb":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                protect_content, pcd = await fileSettings(db.get_protect_content)
                hide_caption, hcd = await fileSettings(db.get_hide_caption)
                pic, channel_button, cbd = await fileSettings(db.get_channel_button, db.set_channel_button)
                name, link = await db.get_channel_button_link()

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd))
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'cb' : {e}")

    elif data == "setcb":
        id = query.from_user.id
        if await authoUser(query, id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                button_name, button_link = await db.get_channel_button_link()

                button_preview = [[InlineKeyboardButton(
                    text=button_name, url=button_link)]]
                set_msg = await client.ask(chat_id=id, text=f'<b>ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴ, ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛs ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.\nғᴏʀ ᴇxᴀᴍᴘʟᴇ:\n<blockquote><code>»  ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ  « - https://t.me/Mugiwaras_Network</code></blockquote>\n\n<i>» ʙᴇʟᴏᴡ ɪs ʙᴜᴛᴛᴏɴ ᴘʀᴇᴠɪᴇᴡ ⬇️</i></b>', timeout=60, reply_markup=InlineKeyboardMarkup(button_preview), disable_web_page_preview=True)
                button = set_msg.text.split(' - ')

                if len(button) != 2:
                    markup = [[InlineKeyboardButton(
                        f'» sᴇᴛ ᴄʜᴀɴɴᴇʟ ʙᴜᴛᴛᴏɴ «', callback_data='setcb')]]
                    return await set_msg.reply("<b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛs.\n\nғᴏʀ ᴇxᴀᴍᴘʟᴇ:\n<blockquote><code>»  ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ  « - https://t.me/Mugiwaras_Network</code></blockquote>\n\nᴛʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..</b>", reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)

                button_name = button[0].strip()
                button_link = button[1].strip()
                button_preview = [[InlineKeyboardButton(
                    text=button_name, url=button_link)]]

                await set_msg.reply("<b>ʙᴜᴛᴛᴏɴ ᴀᴅᴅᴇᴅ sᴜᴄcᴇssғᴜʟʟʏ ✅\n\n<blockquote>» sᴇᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴀs ᴘʀᴇᴠɪᴇᴡ ⬇️</blockquote></b>", reply_markup=InlineKeyboardMarkup(button_preview))
                await db.set_channel_button_link(button_name, button_link)
                return
            except Exception as e:
                try:
                    await set_msg.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ..\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>")
                    print(f"! Error Occurred on callback data = 'setcb' : {e}")
                except BaseException:
                    await client.send_message(id, text=f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ..\n\n<blockquote>ʀᴇᴀsᴏɴ: 1 minute Time out ..</b></blockquote>", disable_notification=True)
                    print(
                        f"! Error Occurred on callback data = 'setcb' -> Rᴇᴀsᴏɴ: 1 minute Time out ..")

    elif data == 'autodel_cmd':
        if await authoUser(query, query.from_user.id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                timer = convert_time(await db.get_del_timer())
                autodel_mode, mode = await fileSettings(db.get_auto_delete, delfunc=True)

                await query.edit_message_media(
                    InputMediaPhoto(autodel_cmd_pic,
                                    AUTODEL_CMD_TXT.format(
                                        autodel_mode=autodel_mode,
                                        timer=timer
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(mode, callback_data='chng_autodel'), InlineKeyboardButton(
                            'sᴇᴛ ᴛɪᴍᴇʀ', callback_data='set_timer')],
                        [InlineKeyboardButton('ʀᴇғʀᴇsʜ', callback_data='autodel_cmd'), InlineKeyboardButton(
                            'ᴄʟᴏsᴇ', callback_data='close')]
                    ])
                )
            except Exception as e:
                print(
                    f"! Error Occurred on callback data = 'autodel_cmd' : {e}")

    elif data == 'chng_autodel':
        if await authoUser(query, query.from_user.id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                timer = convert_time(await db.get_del_timer())
                pic, autodel_mode, mode = await fileSettings(db.get_auto_delete, db.set_auto_delete, delfunc=True)

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    AUTODEL_CMD_TXT.format(
                                        autodel_mode=autodel_mode,
                                        timer=timer
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(mode, callback_data='chng_autodel'), InlineKeyboardButton(
                            'sᴇᴛ ᴛɪᴍᴇʀ', callback_data='set_timer')],
                        [InlineKeyboardButton('ʀᴇғʀᴇsʜ', callback_data='autodel_cmd'), InlineKeyboardButton(
                            'ᴄʟᴏsᴇ', callback_data='close')]
                    ])
                )
            except Exception as e:
                print(
                    f"! Error Occurred on callback data = 'chng_autodel' : {e}")

    elif data == 'set_timer':
        id = query.from_user.id
        if await authoUser(query, id, owner_only=True):
            try:

                timer = convert_time(await db.get_del_timer())
                set_msg = await client.ask(chat_id=id, text=f'<b><blockquote>» ᴄᴜʀʀᴇɴᴛ ᴛɪᴍᴇʀ: {timer}</blockquote>\n\n» ᴛᴏ ᴄʜᴀɴɢᴇ ᴛɪᴍᴇʀ, ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ɪɴ sᴇᴄᴏɴᴅs ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.\n\n<blockquote>ғᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>300</code>, <code>600</code>, <code>900</code></b></blockquote>', timeout=60)
                del_timer = set_msg.text.split()

                if len(del_timer) == 1 and del_timer[0].isdigit():
                    DEL_TIMER = int(del_timer[0])
                    await db.set_del_timer(DEL_TIMER)
                    timer = convert_time(DEL_TIMER)
                    await set_msg.reply(f"<b>ᴛɪᴍᴇʀ ᴀᴅᴅᴇᴅ sᴜᴄcᴇssғᴜʟʟʏ ✅\n\n<blockquote>» ᴄᴜʀʀᴇɴᴛ ᴛɪᴍᴇʀ: {timer}</blockquote></b>")
                else:
                    markup = [[InlineKeyboardButton(
                        '» sᴇᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ «', callback_data='set_timer')]]
                    return await set_msg.reply("<b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ɪɴ sᴇᴄᴏɴᴅs.\n\n<blockquote>ғᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>300</code>, <code>600</code>, <code>900</code></blockquote>\n\n» ᴛʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ.</b>", reply_markup=InlineKeyboardMarkup(markup))

            except Exception as e:
                try:
                    await set_msg.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ..\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>")
                    print(
                        f"! Error Occurred on callback data = 'set_timer' : {e}")
                except BaseException:
                    await client.send_message(id, text=f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ..\n\n<blockquote>» ʀᴇᴀsᴏɴ: 1 ᴍɪɴᴜᴛᴇ ᴛɪᴍᴇ ᴏᴜᴛ...!!!</b></blockquote>", disable_notification=True)
                    print(
                        f"! Error Occurred on callback data = 'set_timer' -> Rᴇᴀsᴏɴ: 1 minute Time out ..")

    elif data == 'chng_req':
        if await authoUser(query, query.from_user.id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            try:
                on = off = ""
                if await db.get_request_forcesub():
                    await db.set_request_forcesub(False)
                    off = "🔴"
                    texting = off_txt
                else:
                    await db.set_request_forcesub(True)
                    on = "🟢"
                    texting = on_txt

                button = [
                    [InlineKeyboardButton(f"{on} ᴏɴ", "chng_req"), InlineKeyboardButton(
                        f"{off} ᴏғғ", "chng_req")],
                    [InlineKeyboardButton(
                        "•  ᴍᴏʀᴇ sᴇᴛᴛɪɴɢs  •", "more_settings")]
                ]
                # 🎉)
                await query.message.edit_text(text=RFSUB_CMD_TXT.format(req_mode=texting), reply_markup=InlineKeyboardMarkup(button))

            except Exception as e:
                print(f"! Error Occurred on callback data = 'chng_req' : {e}")

    elif data == 'more_settings':
        if await authoUser(query, query.from_user.id, owner_only=True):
            # await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")
            try:
                await query.message.edit_text("<b>» ᴘʟᴇᴀsᴇ wᴀɪᴛ ᴀ sᴇᴄᴏɴᴅ ʙᴀʙᴇʏʏ !!</b>")
                LISTS = "ᴇᴍᴘᴛʏ ʀᴇǫᴜᴇsᴛ ғᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ ʟɪsᴛ !?"

                REQFSUB_CHNLS = await db.get_reqChannel()
                if REQFSUB_CHNLS:
                    LISTS = ""
                    channel_name = "ᴜɴᴀʙʟᴇ ʟᴏᴀᴅ ɴᴀᴍᴇs..."
                    for CHNL in REQFSUB_CHNLS:
                        await query.message.reply_chat_action(ChatAction.TYPING)
                        try:
                            name = (await client.get_chat(CHNL)).title
                        except BaseException:
                            name = None
                        channel_name = name if name else channel_name

                        user = await db.get_reqSent_user(CHNL)
                        channel_users = len(user) if user else 0

                        link = await db.get_stored_reqLink(CHNL)
                        if link:
                            channel_name = f"<a href={link}>{channel_name}</a>"

                        LISTS += f"NAME: {channel_name}\n(ID: <code>{CHNL}</code>)\nUSERS: {channel_users}\n\n"

                buttons = [
                    [InlineKeyboardButton("• ᴄʟᴇᴀʀ ᴜsᴇʀs", "clear_users"), InlineKeyboardButton(
                        "cʟᴇᴀʀ cʜᴀɴɴᴇʟs •", "clear_chnls")],
                    [InlineKeyboardButton(
                        "•  ʀᴇғʀᴇsʜ sᴛᴀᴛᴜs  •", "more_settings")],
                    [InlineKeyboardButton("• ʙᴀᴄᴋ", "req_fsub"), InlineKeyboardButton(
                        "ᴄʟᴏsᴇ •", "close")]
                ]
                await query.message.reply_chat_action(ChatAction.CANCEL)
                await query.message.edit_text(text=RFSUB_MS_TXT.format(reqfsub_list=LISTS.strip()), reply_markup=InlineKeyboardMarkup(buttons))

            except Exception as e:
                print(
                    f"! Error Occurred on callback data = 'more_settings' : {e}")

    elif data == 'clear_users':
        # if await authoUser(query, query.from_user.id, owner_only=True) :
        # await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")
        try:
            REQFSUB_CHNLS = await db.get_reqChannel()
            if not REQFSUB_CHNLS:
                return await query.answer("ᴇᴍᴘᴛʏ ʀᴇǫᴜᴇsᴛ ғᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ !?", show_alert=True)

            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ...!!!")

            REQFSUB_CHNLS = list(map(str, REQFSUB_CHNLS))
            buttons = [REQFSUB_CHNLS[i:i + 2]
                       for i in range(0, len(REQFSUB_CHNLS), 2)]
            buttons.insert(0, ['CANCEL'])
            buttons.append(['DELETE ALL CHANNELS USER'])

            user_reply = await client.ask(query.from_user.id, text=CLEAR_USERS_TXT, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))

            if user_reply.text == 'CANCEL':
                return await user_reply.reply("<b>🆑 ᴄᴀɴᴄᴇʟʟᴇᴅ...!!!</b>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text in REQFSUB_CHNLS:
                try:
                    await db.clear_reqSent_user(int(user_reply.text))
                    return await user_reply.reply(f"<b><blockquote>✅ ᴜsᴇʀ ᴅᴀᴛᴀ sᴜᴄᴄᴇssғᴜʟʟʏ ᴄʟᴇᴀʀᴇᴅ ғʀᴏᴍ ᴄʜᴀɴɴᴇʟ ɪᴅ: <code>{user_reply.text}</code></blockquote></b>", reply_markup=ReplyKeyboardRemove())
                except Exception as e:
                    return await user_reply.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ...\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text == 'DELETE ALL CHANNELS USER':
                try:
                    for CHNL in REQFSUB_CHNLS:
                        await db.clear_reqSent_user(int(CHNL))
                    return await user_reply.reply(f"<b><blockquote>✅ ᴜsᴇʀ ᴅᴀᴛᴀ sᴜᴄᴄᴇssғᴜʟʟʏ ᴄʟᴇᴀʀᴇᴅ ғʀᴏᴍ ᴀʟʟ ᴄʜᴀɴɴᴇʟ ɪᴅs</blockquote></b>", reply_markup=ReplyKeyboardRemove())
                except Exception as e:
                    return await user_reply.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ...\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            else:
                return await user_reply.reply(f"<b><blockquote>INVALID SELECTIONS</blockquote></b>", reply_markup=ReplyKeyboardRemove())

        except Exception as e:
            print(f"! Error Occurred on callback data = 'clear_users' : {e}")

    elif data == 'clear_chnls':
        # if await authoUser(query, query.from_user.id, owner_only=True)

        try:
            REQFSUB_CHNLS = await db.get_reqChannel()
            if not REQFSUB_CHNLS:
                return await query.answer("ᴇᴍᴘᴛʏ ʀᴇǫᴜᴇsᴛ ғᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ !?", show_alert=True)

            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            REQFSUB_CHNLS = list(map(str, REQFSUB_CHNLS))
            buttons = [REQFSUB_CHNLS[i:i + 2]
                       for i in range(0, len(REQFSUB_CHNLS), 2)]
            buttons.insert(0, ['CANCEL'])
            buttons.append(['DELETE ALL CHANNEL IDS'])

            user_reply = await client.ask(query.from_user.id, text=CLEAR_CHNLS_TXT, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))

            if user_reply.text == 'CANCEL':
                return await user_reply.reply("<b>🆑 ᴄᴀɴᴄᴇʟʟᴇᴅ...!!!</b>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text in REQFSUB_CHNLS:
                try:
                    chnl_id = int(user_reply.text)

                    await db.del_reqChannel(chnl_id)

                    try:
                        await client.revoke_chat_invite_link(chnl_id, await db.get_stored_reqLink(chnl_id))
                    except BaseException:
                        pass

                    await db.del_stored_reqLink(chnl_id)

                    return await user_reply.reply(f"<b><blockquote><code>{user_reply.text}</code> ᴄʜᴀɴɴᴇʟ ɪᴅ ᴀʟᴏɴɢ ᴡɪᴛʜ ɪᴛs ᴅᴀᴛᴀ sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ✅</blockquote></b>", reply_markup=ReplyKeyboardRemove())
                except Exception as e:
                    return await user_reply.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ...\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text == 'DELETE ALL CHANNEL IDS':
                try:
                    for CHNL in REQFSUB_CHNLS:
                        chnl = int(CHNL)

                        await db.del_reqChannel(chnl)

                        try:
                            await client.revoke_chat_invite_link(chnl, await db.get_stored_reqLink(chnl))
                        except BaseException:
                            pass

                        await db.del_stored_reqLink(chnl)

                    return await user_reply.reply(f"<b><blockquote>ᴀʟʟ ᴄʜᴀɴɴᴇʟ ɪᴅs ᴀʟᴏɴɢ ᴡɪᴛʜ ɪᴛs ᴅᴀᴛᴀ sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ✅</blockquote></b>", reply_markup=ReplyKeyboardRemove())

                except Exception as e:
                    return await user_reply.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ...\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            else:
                return await user_reply.reply(f"<b><blockquote>INVALID SELECTIONS</blockquote></b>", reply_markup=ReplyKeyboardRemove())

        except Exception as e:
            print(f"! Error Occurred on callback data = 'more_settings' : {e}")

    elif data == 'clear_links':
        # if await authoUser(query, query.from_user.id, owner_only=True) :
        # await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

        try:
            REQFSUB_CHNLS = await db.get_reqLink_channels()
            if not REQFSUB_CHNLS:
                return await query.answer("ɴᴏ sᴛᴏʀᴇᴅ ʀᴇǫᴜᴇsᴛ ʟɪɴᴋ ᴀᴠᴀɪʟᴀʙʟᴇ !?", show_alert=True)

            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....!!!")

            REQFSUB_CHNLS = list(map(str, REQFSUB_CHNLS))
            buttons = [REQFSUB_CHNLS[i:i + 2]
                       for i in range(0, len(REQFSUB_CHNLS), 2)]
            buttons.insert(0, ['CANCEL'])
            buttons.append(['DELETE ALL REQUEST LINKS'])

            user_reply = await client.ask(query.from_user.id, text=CLEAR_LINKS_TXT, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))

            if user_reply.text == 'CANCEL':
                return await user_reply.reply("<b>🆑 ᴄᴀɴᴄᴇʟʟᴇᴅ...</b>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text in REQFSUB_CHNLS:
                channel_id = int(user_reply.text)
                try:
                    try:
                        await client.revoke_chat_invite_link(channel_id, await db.get_stored_reqLink(channel_id))
                    except BaseException:
                        text = """<b>❌ ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴠᴏᴋᴇ ʟɪɴᴋ !
<blockquote expandable>ɪᴅ: <code>{}</code></b>

» ᴇɪᴛʜᴇʀ ᴛʜᴇ ʙᴏᴛ ɪs ɴᴏᴛ ɪɴ ᴀʙᴏᴠᴇ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘʀᴏᴘᴇʀ ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs</blockquote>"""
                        return await user_reply.reply(text=text.format(channel_id), reply_markup=ReplyKeyboardRemove())

                    await db.del_stored_reqLink(channel_id)
                    return await user_reply.reply(f"<b><blockquote><code>{channel_id}</code> ᴄʜᴀɴɴᴇʟs ʟɪɴᴋ sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ✅</blockquote></b>", reply_markup=ReplyKeyboardRemove())

                except Exception as e:
                    return await user_reply.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ...\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text == 'DELETE ALL REQUEST LINKS':
                try:
                    result = ""
                    for CHNL in REQFSUB_CHNLS:
                        channel_id = int(CHNL)
                        try:
                            await client.revoke_chat_invite_link(channel_id, await db.get_stored_reqLink(channel_id))
                        except BaseException:
                            result += f"<blockquote expandable><b><code>{channel_id}</code> ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴠᴏᴋᴇ ❌</b>\n\n» ᴇɪᴛʜᴇʀ ᴛʜᴇ ʙᴏᴛ ɪs ɴᴏᴛ ɪɴ ᴀʙᴏᴠᴇ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘʀᴏᴘᴇʀ ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs.</blockquote>\n"
                            continue
                        await db.del_stored_reqLink(channel_id)
                        result += f"<blockquote><b><code>{channel_id}</code> IDs ʟɪɴᴋ ᴅᴇʟᴇᴛᴇᴅ ✅</b></blockquote>\n"

                    return await user_reply.reply(f"<b>⁉️ ᴏᴘᴇʀᴀᴛɪᴏɴ ʀᴇsᴜʟᴛ:</b>\n{result.strip()}", reply_markup=ReplyKeyboardRemove())

                except Exception as e:
                    return await user_reply.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ...\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            else:
                return await user_reply.reply(f"<b><blockquote>INVALID SELECTIONS</blockquote></b>", reply_markup=ReplyKeyboardRemove())

        except Exception as e:
            print(f"! Error Occurred on callback data = 'more_settings' : {e}")

    elif data == 'req_fsub':
        # if await authoUser(query, query.from_user.id, owner_only=True) :
        await query.answer("Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ...!!!")

        try:
            on = off = ""
            if await db.get_request_forcesub():
                on = "🟢"
                texting = on_txt
            else:
                off = "🔴"
                texting = off_txt

            button = [
                [InlineKeyboardButton(f"{on} ᴏɴ", "chng_req"), InlineKeyboardButton(
                    f"{off} ᴏғғ", "chng_req")],
                [InlineKeyboardButton("• ᴍᴏʀᴇ sᴇᴛᴛɪɴɢs •", "more_settings")]
            ]
            # 🎉)
            await query.message.edit_text(text=RFSUB_CMD_TXT.format(req_mode=texting), reply_markup=InlineKeyboardMarkup(button))

        except Exception as e:
            print(f"! Error Occurred on callback data = 'chng_req' : {e}")


    # Handle shortener settings
    elif data == "shortener_settings":
        if await authoUser(query, query.from_user.id, owner_only=True):
            try:
                await query.answer("» ғᴇᴛᴄʜɪɴɢ sʜᴏʀᴛɴᴇʀ ᴅᴇᴛᴀɪʟs...!!!")

            # Fetch shortener details
                shortener_url = await db.get_shortener_url()
                shortener_api = await db.get_shortener_api()
                verified_time = await db.get_verified_time()
                tut_video = await db.get_tut_video()

            # Prepare the details for display
                shortener_url_display = shortener_url or "Not set"
                shortener_api_display = shortener_api or "Not set"
                status = "Active" if shortener_url and shortener_api else "Inactive"
                verified_time_display = (
                    f"{verified_time} seconds" if verified_time else "Not set"
                )
                tut_video_display = (
                    f"[Tutorial Video]({tut_video})" if tut_video else "Not set"
                )

            # Response message
                response_text = (
                    f"<b>𝐒𝐇𝐎𝐑𝐓𝐍𝐄𝐑 𝐃𝐄𝐓𝐀𝐈𝐋𝐒</b>\n\n"
                    f"» sʜᴏʀᴛɴᴇʀ sɪᴛᴇ: {shortener_url_display}\n"
                    f"» sʜᴏʀᴛɴᴇʀ ᴀᴘɪ ᴛᴏᴋᴇɴ: {shortener_api_display}\n\n"
                    f"» sʜᴏʀᴛɴᴇʀ sᴛᴀᴛᴜs: {status}\n\n"
                    f"» sʜᴏʀᴛɴᴇʀ ᴠᴇʀɪғɪᴇᴅ ᴛɪᴍᴇ: {verified_time_display}\n"
                    f"» sʜᴏʀᴛɴᴇʀ ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ: {tut_video_display}"
                )

            # Update the message with the fetched details
                await query.message.edit_text(
                    text=response_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('•  ʙᴀᴄᴋ  •', callback_data='set_shortener')]
                    ]),
                    disable_web_page_preview=True  # Disable preview for tutorial video link
                )

            except Exception as e:
                logging.error(f"Error fetching shortener settings: {e}")
                await query.message.reply(
                    "🤧 An error occurred while fetching shortener settings. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('•  ʙᴀᴄᴋ  •', callback_data='set_shortener')]
                    ])
                )


    elif data == "chng_shortener":  # Toggle shortener status
        user_id = query.from_user.id
        shortener_details = await db.get_shortener()

    # Toggle the shortener status in the database
        if shortener_details:
        # Disable shortener
            await db.set_shortener("", "")
            await query.answer("sʜᴏʀᴛɴᴇʀ ᴅɪsᴀʙʟᴇᴅ ❌", show_alert=True)
        else:
        # Enable shortener, prompt for URL and API Key
            await query.answer("» sʜᴏʀᴛɴᴇʀ ᴇɴᴀʙʟᴇᴅ ✅. ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ sʜᴏʀᴛɴᴇʀ ᴜʀʟ ᴀɴᴅ ᴀᴘɪ ᴋᴇʏ.", show_alert=True)
            await query.message.reply("» sᴇɴᴅ ᴛʜᴇ 𝐒𝐇𝐎𝐑𝐓𝐍𝐄𝐑 𝐔𝐑𝐋 ᴀɴᴅ 𝐀𝐏𝐈 𝐊𝐄𝐘 ɪɴ ᴛʜᴇ ғᴏʀᴍᴀᴛ:\n`<shortener_url> <api_key>`")




    elif data == 'set_shortener_details':
        if await authoUser(query, query.from_user.id, owner_only=True):
            try:
            # Step 1: Prompt for the shortener URL with a timeout of 1 minute
                await query.answer("» ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ sʜᴏʀᴛɴᴇʀ ᴜʀʟ ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ...")
                set_msg_url = await query.message.reply(
                    "» ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ sʜᴏʀᴛɴᴇʀ sɪᴛᴇ ᴜʀʟ (e.g., inshorturl.com) ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ..",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('•  ʙᴀᴄᴋ  •', callback_data='set_shortener')]])
                )
                site_msg = await client.ask(
                    chat_id=query.from_user.id,
                    text="» ᴇɴᴛᴇʀ sʜᴏʀᴛɴᴇʀ sɪᴛᴇ ᴜʀʟ:",
                    timeout=60
                )

                shortener_url = site_msg.text.strip()


            # Confirm the shortener site URL
                await site_msg.reply(f"» sʜᴏʀᴛɴᴇʀ sɪᴛᴇ ᴜʀʟ sᴇᴛ ᴛᴏ: {shortener_url}\n\n» ɴᴏᴡ ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ ᴀᴘɪ ᴋᴇʏ.")

            # Step 3: Prompt for API key
                set_msg_api = await query.message.reply(
                    "» ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴀᴘɪ ᴋᴇʏ ғᴏʀ ᴛʜᴇ sʜᴏʀᴛɴᴇʀ ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('•  ʙᴀᴄᴋ  •', callback_data='set_shortener')]])
                )

                api_msg = await client.ask(
                    chat_id=query.from_user.id,
                    text="» ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴀᴘɪ ᴋᴇʏ ғᴏʀ sʜᴏʀᴛɴᴇʀ:",
                    timeout=60
                )

                api_key = api_msg.text.strip()

            # Step 4: Save the shortener details in the database
                await db.set_shortener_url(shortener_url)
                await db.set_shortener_api(api_key)

            # Confirmation message
                await api_msg.reply(
                    "✅ Shortener details have been successfully set!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('ᴅɪsᴀʙʟᴇ sʜᴏʀᴛɴᴇʀ ❌', callback_data='disable_shortener')],
                        [InlineKeyboardButton('•  ʙᴀᴄᴋ  •', callback_data='set_shortener')]
                    ])
                )
            except asyncio.TimeoutError:
                await query.message.reply(
                    "» 𝐀𝐋𝐄𝐑𝐓: Timeout\n\n» ʏᴏᴜ ᴅɪᴅ ɴᴏᴛ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴅᴇᴛᴀɪʟs ɪɴ ɢɪᴠᴇɴ ᴛɪᴍᴇ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('•  ʙᴀᴄᴋ  •', callback_data='set_shortener')]])
                )
            except Exception as e:
                logging.error(f"Error setting shortener details: {e}")  # This now works correctly
                await query.message.reply(
                    f"⚠️ Error occurred: {e}",
    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('•  ʙᴀᴄᴋ  •', callback_data='set_shortener')]])
    )

    elif data == "set_shortener":
        if await authoUser(query, query.from_user.id, owner_only=True):
            try:
            # Simulate the command being run again by accessing the message where the button was pressed
                message = query.message  # Access the message where the button was pressed

            # Fetch the shortener URL and API from the database
                shortener_url = await db.get_shortener_url()
                shortener_api = await db.get_shortener_api()

            # Check if both shortener URL and API are available
                if shortener_url and shortener_api:
            # If both URL and API key are available, the shortener is considered "Enabled ✅"
                    shortener_status = "ᴇɴᴀʙʟᴇᴅ ✅"
                    mode_button = InlineKeyboardButton('ᴅɪsᴀʙʟᴇ sʜᴏʀᴛɴᴇʀ ❌', callback_data='disable_shortener')
                else:
            # If either URL or API key is missing, the shortener is "Disabled ❌"
                    shortener_status = "ᴅɪsᴀʙʟᴇᴅ ❌"
                    mode_button = InlineKeyboardButton('ᴇɴᴀʙʟᴇ sʜᴏʀᴛɴᴇʀ ✅', callback_data='set_shortener_details')


            # Refresh the settings and update the message with new content
                await message.reply_photo(
                    photo=START_PIC,
                    caption=SET_SHORTENER_CMD_TXT.format(
                        shortener_status=shortener_status),
                    reply_markup=InlineKeyboardMarkup([
                        [mode_button],
                        [InlineKeyboardButton('Settings ⚙️', callback_data='shortener_settings'),
                     InlineKeyboardButton('🔄 Refresh', callback_data='set_shortener')],
                        [InlineKeyboardButton('Set Verified Time ⏱', callback_data='set_verify_time'),
                     InlineKeyboardButton('Set Tutorial Video 🎥', callback_data='set_tut_video')],
                        [InlineKeyboardButton('Close ✖️', callback_data='close')]
                    ])
                )
            except Exception as e:
            # If an error occurs, display an error message with a contact option
                await query.message.edit_text(
                    f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ..\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote><b>ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ: @urr_sanjiii</b>",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("•  ᴄʟᴏsᴇ  •", callback_data="close")]]
                    )
                )


    elif data == "set_tut_video":
        id = query.from_user.id

        if await authoUser(query, id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ...!!!")

            try:
            # Fetch the current tutorial video URL from the database
                current_video_url = await db.get_tut_video()

            # Prompt the user to input the new tutorial video URL
                set_msg = await client.ask(
                    chat_id=id,
                    text=f'<b><blockquote>» ᴄᴜʀʀᴇɴᴛ ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ URL: {current_video_url if current_video_url else "ɴᴏᴛ sᴇᴛ"}</blockquote>\n\n» ᴛᴏ ᴄʜᴀɴɢᴇ, ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴠɪᴅᴇᴏ URL.\n\n<blockquote>ғᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>https://t.me/anime_raven/829</code></b></blockquote>',
                    timeout=60
                )

            # Validate the user input for a valid URL
                video_url = set_msg.text.strip()

                if video_url.startswith("http") and "://" in video_url:
                # Save the new tutorial video URL to the database
                    await db.set_tut_video(video_url)

                # Confirm the update to the user
                    await set_msg.reply(f"<b>» ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ URL sᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ ✅\n\n<blockquote>» ᴄᴜʀʀᴇɴᴛ ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ URL: {video_url}</blockquote></b>")
                else:
                # If the URL is invalid, prompt the user to try again
                    markup = [[InlineKeyboardButton(
                        'sᴇᴛ ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ ᴜʀʟ', callback_data='set_tut_video')]]
                    return await set_msg.reply(
                        "<b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ʟɪɴᴋ ᴛᴏ ᴀ ᴠᴀʟɪᴅ ᴠɪᴅᴇᴏ.\n\n<blockquote>ғᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>https://t.me/Mugiwaras_Network</code></blockquote>\n\n» ᴛʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..!!</b>", reply_markup=InlineKeyboardMarkup(markup))

            except Exception as e:
                try:
                # Handle any exceptions that occur during the process
                    await set_msg.reply(f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ..\n\n<blockquote>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>")
                    print(f"! Error Occurred on callback data = 'set_tut_video' : {e}")
                except BaseException:
                # If an error occurs while sending the error message, send a timeout message
                    await client.send_message(id, text=f"<b>! ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ..\n\n<blockquote>ʀᴇᴀsᴏɴ: 1 minute Time out...!!!</b></blockquote>", disable_notification=True)
                    print(f"! Error Occurred on callback data = 'set_tut_video' -> Reason: 1 minute Time out ..")


    elif data.startswith("detail_"):
        mal_id = data.split("_")[1]
        url = f"https://api.jikan.moe/v4/anime/{mal_id}"
        anime_data = await fetch_anime_data(url)

        if anime_data and "data" in anime_data:
            anime = anime_data["data"]
            details = (
                f"» ᴛɪᴛʟᴇ: {style_anime_title(anime.get('title'))}\n"
                f"» ᴛʏᴘᴇ: {anime.get('type', 'N/A')}\n"
                f"» ᴇᴘɪsᴏᴅᴇs: {anime.get('episodes', 'Unknown')}\n"
                f"» sᴄᴏʀᴇ: {anime.get('score', 'N/A')}\n"
                f"» sʏɴᴏᴘsɪs: {anime.get('synopsis', 'No synopsis available.')}\n"
                f"[MyAnimeList]({anime.get('url', '#')})"
            )

            await query.message.edit_text(
                details,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("• ᴄʟɪᴄᴋ ᴛᴏ ᴄʟᴏsᴇ ᴛʜɪs ᴘᴀɴᴇʟ •", callback_data='close')]]
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.answer("Failed to fetch anime details..!!", show_alert=True)
