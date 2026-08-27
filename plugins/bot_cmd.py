# +++ Made By Sanjiii [telegram username: @Urr_Sanjiii] +++
#>>>> Forward mode By @metaui <<<<#


import os
import asyncio
import logging as log
from asyncio import Lock
from bot import Bot
from config import OWNER_ID, SUPPORT_GROUP
import time
from datetime import datetime 
from pyrogram import Client, filters
from helper_func import is_admin, get_readable_time, banUser
from plugins.FORMATS import HELP_TEXT, BAN_TXT, CMD_TXT, USER_CMD_TXT, FSUB_CMD_TXT
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from databases.database import db
# ⬇️ Is niche wali line ko dhyan se dekho, yahan comma ke baad CallbackQuery add kiya hai ⬇️
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

REPLY_ERROR = """ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴀs ᴀ ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴛᴇʟᴇɢʀᴀᴍ ᴍᴇssᴀɢᴇ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ sᴘᴀᴄᴇs."""
# Define a global variable to store the cancel state
is_canceled = False
cancel_lock = Lock()

#Settings for banned users..
@Bot.on_message(banUser & filters.private & filters.command(['start', 'help']))
async def handle_banuser(client, message):
    return await message.reply(text=BAN_TXT,)#💩)

#--------------------------------------------------------------[[ADMIN COMMANDS]]---------------------------------------------------------------------------#
# Handler for the /cancel command
@Bot.on_message(filters.command('cancel') & filters.private & is_admin)
async def cancel_broadcast(client: Bot, message: Message):
    global is_canceled
    async with cancel_lock:
        is_canceled = True

@Bot.on_message(filters.command('broadcast') & filters.private & is_admin)
async def send_text(client: Bot, message: Message):
    global is_canceled
    async with cancel_lock:
        is_canceled = False
    mode = False
    broad_mode = ''
    store = message.text.split()[1:]
    
    if store and len(store) == 1 and store[0] == 'silent':
        mode = True
        broad_mode = 'SILENT '

    if message.reply_to_message:
        query = await db.full_userbase()
        broadcast_msg = message.reply_to_message
        total = len(query)
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0

        pls_wait = await message.reply("<i>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴍᴇssᴀɢᴇ... ᴛʜɪs ᴡɪʟʟ ᴛᴀᴋᴇ sᴏᴍᴇ ᴛɪᴍᴇ.</i>")
        bar_length = 20
        final_progress_bar = "●" * bar_length
        complete_msg = f"🤖 {broad_mode}ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ✅"
        progress_bar = ''
        last_update_percentage = 0
        percent_complete = 0
        update_interval = 0.05  # Update progress bar every 5%

        for i, chat_id in enumerate(query, start=1):
            async with cancel_lock:
                if is_canceled:
                    final_progress_bar = progress_bar
                    complete_msg = f"🤖 {broad_mode}ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴀɴᴄᴇʟᴇᴅ ❌"
                    break
            try:
                await broadcast_msg.copy(chat_id, disable_notification=mode)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id, disable_notification=mode)
                successful += 1
            except UserIsBlocked:
                await db.del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await db.del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1

            # Calculate percentage complete
            percent_complete = i / total

            # Update progress bar
            if percent_complete - last_update_percentage >= update_interval or last_update_percentage == 0:
                num_blocks = int(percent_complete * bar_length)
                progress_bar = "●" * num_blocks + "○" * (bar_length - num_blocks)
    
                # Send periodic status updates
                status_update = f"""<b>🤖 {broad_mode}ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴ ᴘʀᴏɢʀᴇss...

<blockquote>⏳:</b> [{progress_bar}] <code>{percent_complete:.0%}</code></blockquote>

<b>🚻 ᴛᴏᴛᴀʟ ᴜsᴇʀs: <code>{total}</code>
✅ sᴜᴄᴄᴇssғᴜʟ: <code>{successful}</code>
🚫 ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: <code>{blocked}</code>
⚠️ ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: <code>{deleted}</code>
❌ ᴜɴsᴜᴄᴄᴇssғᴜʟ: <code>{unsuccessful}</code></b>

➪ ᴛᴏ sᴛᴏᴘ ᴛʜᴇ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ: <b>/cancel</b>"""
                await pls_wait.edit(status_update)
                last_update_percentage = percent_complete

        # Final status update
        final_status = f"""<b>{complete_msg}

<blockquote>ᴅᴏɴᴇ:</b> [{final_progress_bar}] {percent_complete:.0%}</blockquote>

<b>🚻 ᴛᴏᴛᴀʟ ᴜsᴇʀs: <code>{total}</code>
✅ sᴜᴄᴄᴇssғᴜʟ: <code>{successful}</code>
🚫 ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: <code>{blocked}</code>
⚠️ ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: <code>{deleted}</code>
❌ ᴜɴsᴜᴄᴄᴇssғᴜʟ: <code>{unsuccessful}</code></b>"""
        return await pls_wait.edit(final_status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()


########=============================================================######
              ### >>>>>>>>  Forward Mode Start <<<<<<< ###
########=============================================================########


@Bot.on_message(filters.command('fcast') & filters.private & is_admin)
async def send_text_fcast(client: Bot, message: Message):
    global is_canceled
    async with cancel_lock:
        is_canceled = False
    mode = False
    broad_mode = ''
    store = message.text.split()[1:]
    
    if store and len(store) == 1 and store[0] == 'silent':
        mode = True
        broad_mode = 'SILENT '

    if message.reply_to_message:
        query = await db.full_userbase()
        broadcast_msg = message.reply_to_message
        total = len(query)
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0

        pls_wait = await message.reply("<i>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴍᴇssᴀɢᴇ... ᴛʜɪs ᴡɪʟʟ ᴛᴀᴋᴇ sᴏᴍᴇ ᴛɪᴍᴇ.</i>")
        bar_length = 20
        final_progress_bar = "●" * bar_length
        complete_msg = f"🤖 {broad_mode}ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ✅"
        progress_bar = ''
        last_update_percentage = 0
        percent_complete = 0
        update_interval = 0.05  # Update progress bar every 5%

        for i, chat_id in enumerate(query, start=1):
            async with cancel_lock:
                if is_canceled:
                    final_progress_bar = progress_bar
                    complete_msg = f"🤖 {broad_mode}ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴀɴᴄᴇʟᴇᴅ ❌"
                    break
            try:
                # ✅ Forwarding the message instead of copying
                await client.forward_messages(chat_id, from_chat_id=message.chat.id, message_ids=broadcast_msg.id, disable_notification=mode)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await client.forward_messages(chat_id, from_chat_id=message.chat.id, message_ids=broadcast_msg.id, disable_notification=mode)
                successful += 1
            except UserIsBlocked:
                await db.del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await db.del_user(chat_id)
                deleted += 1
            except Exception as e:
                print(f"Error forwarding to {chat_id}: {e}")  # Debugging ke liye
                unsuccessful += 1

            # Calculate percentage complete
            percent_complete = i / total

            # Update progress bar
            if percent_complete - last_update_percentage >= update_interval or last_update_percentage == 0:
                num_blocks = int(percent_complete * bar_length)
                progress_bar = "●" * num_blocks + "○" * (bar_length - num_blocks)
    
                # Send periodic status updates
                status_update = f"""<b>🤖 {broad_mode}ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴ ᴘʀᴏɢʀᴇss...

<blockquote>⏳:</b> [{progress_bar}] <code>{percent_complete:.0%}</code></blockquote>

<b>🚻 ᴛᴏᴛᴀʟ ᴜsᴇʀs: <code>{total}</code>
✅ sᴜᴄᴄᴇssғᴜʟ: <code>{successful}</code>
🚫 ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: <code>{blocked}</code>
⚠️ ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: <code>{deleted}</code>
❌ ᴜɴsᴜᴄᴄᴇssғᴜʟ: <code>{unsuccessful}</code></b>

➪ ᴛᴏ sᴛᴏᴘ ᴛʜᴇ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ: <b>/cancel</b>"""
                await pls_wait.edit(status_update)
                last_update_percentage = percent_complete

        # Final status update
        final_status = f"""<b>{complete_msg}

<blockquote>ᴅᴏɴᴇ:</b> [{final_progress_bar}] {percent_complete:.0%}</blockquote>

<b>🚻 ᴛᴏᴛᴀʟ ᴜsᴇʀs: <code>{total}</code>
✅ sᴜᴄᴄᴇssғᴜʟ: <code>{successful}</code>
🚫 ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: <code>{blocked}</code>
⚠️ ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: <code>{deleted}</code>
❌ ᴜɴsᴜᴄᴄᴇssғᴜʟ: <code>{unsuccessful}</code></b>"""
        return await pls_wait.edit(final_status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
        

########=============================================================########
               ### >>>>>>>>  Forward Mode END <<<<<<< ###
########=============================================================########


########=============================================================########
              ### >>>>>>>>  Pin Broadcast Mode <<<<<<< ###
########=============================================================########

@Bot.on_message(filters.command('bcast') & filters.private & is_admin)
async def pin_broadcast(client: Bot, message: Message):
    global is_canceled
    async with cancel_lock:
        is_canceled = False
    mode = False
    broad_mode = ''
    store = message.text.split()[1:]
    
    if store and len(store) == 1 and store[0] == 'silent':
        mode = True
        broad_mode = 'SILENT '

    if message.reply_to_message:
        query = await db.full_userbase()
        broadcast_msg = message.reply_to_message
        total = len(query)
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        pinned = 0

        pls_wait = await message.reply("<i>📌 ᴘɪɴɴɪɴɢ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜsᴇʀs... ᴛʜɪs ᴡɪʟʟ ᴛᴀᴋᴇ sᴏᴍᴇ ᴛɪᴍᴇ.</i>")
        bar_length = 20
        final_progress_bar = "●" * bar_length
        complete_msg = f"🤖 {broad_mode}ᴘɪɴ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ✅"
        progress_bar = ''
        last_update_percentage = 0
        percent_complete = 0
        update_interval = 0.05

        for i, chat_id in enumerate(query, start=1):
            async with cancel_lock:
                if is_canceled:
                    final_progress_bar = progress_bar
                    complete_msg = f"🤖 {broad_mode}ᴘɪɴ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴀɴᴄᴇʟᴇᴅ ❌"
                    break
            try:
                # Copy message first
                copied_msg = await broadcast_msg.copy(chat_id, disable_notification=mode)
                # Then pin it
                await client.pin_chat_message(chat_id, copied_msg.id)
                successful += 1
                pinned += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                try:
                    copied_msg = await broadcast_msg.copy(chat_id, disable_notification=mode)
                    await client.pin_chat_message(chat_id, copied_msg.id)
                    successful += 1
                    pinned += 1
                except:
                    unsuccessful += 1
            except UserIsBlocked:
                await db.del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await db.del_user(chat_id)
                deleted += 1
            except Exception as e:
                print(f"Error pinning to {chat_id}: {e}")
                unsuccessful += 1

            percent_complete = i / total

            if percent_complete - last_update_percentage >= update_interval or last_update_percentage == 0:
                num_blocks = int(percent_complete * bar_length)
                progress_bar = "●" * num_blocks + "○" * (bar_length - num_blocks)
    
                status_update = f"""<b>🤖 {broad_mode}ᴘɪɴ ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴ ᴘʀᴏɢʀᴇss...

<blockquote>⏳:</b> [{progress_bar}] <code>{percent_complete:.0%}</code></blockquote>

<b>🚻 ᴛᴏᴛᴀʟ ᴜsᴇʀs: <code>{total}</code>
✅ sᴜᴄᴄᴇssғᴜʟ: <code>{successful}</code>
📌 ᴘɪɴɴᴇᴅ: <code>{pinned}</code>
🚫 ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: <code>{blocked}</code>
⚠️ ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: <code>{deleted}</code>
❌ ᴜɴsᴜᴄᴄᴇssғᴜʟ: <code>{unsuccessful}</code></b>

➪ ᴛᴏ sᴛᴏᴘ ᴛʜᴇ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ: <b>/cancel</b>"""
                await pls_wait.edit(status_update)
                last_update_percentage = percent_complete

        final_status = f"""<b>{complete_msg}

<blockquote>ᴅᴏɴᴇ:</b> [{final_progress_bar}] {percent_complete:.0%}</blockquote>

<b>🚻 ᴛᴏᴛᴀʟ ᴜsᴇʀs: <code>{total}</code>
✅ sᴜᴄᴄᴇssғᴜʟ: <code>{successful}</code>
📌 ᴘɪɴɴᴇᴅ: <code>{pinned}</code>
🚫 ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: <code>{blocked}</code>
⚠️ ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: <code>{deleted}</code>
❌ ᴜɴsᴜᴄᴄᴇssғᴜʟ: <code>{unsuccessful}</code></b>"""
        return await pls_wait.edit(final_status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()

########=============================================================########
               ### >>>>>>>>  Pin Broadcast END <<<<<<< ###
########=============================================================########




@Bot.on_message(filters.command('status') & filters.private & is_admin)
async def info(client: Bot, message: Message):   
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("•  ᴄʟᴏsᴇ  •", callback_data = "close")]])
    
    start_time = time.time()
    temp_msg = await message.reply("<b><i>ᴘʀᴏᴄᴇssɪɴɢ....</i></b>", quote=True)  # Temporary message
    end_time = time.time()
    
    # Calculate ping time in milliseconds
    ping_time = (end_time - start_time) * 1000
    
    users = await db.full_userbase()
    now = datetime.now()
    delta = now - client.uptime
    bottime = get_readable_time(delta.seconds)
    
    await temp_msg.edit(f"🚻 : <b>{len(users)} ᴜsᴇʀs\n\n🤖 ᴜᴘᴛɪᴍᴇ » {bottime}\n\n📡 ᴘɪɴɢ » {ping_time:.2f} ms</b>", reply_markup = reply_markup,)


@Bot.on_message(filters.command('cmd') & filters.private & is_admin)
async def bcmd(bot: Bot, message: Message):        
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("•  ᴄʟᴏsᴇ  •", callback_data = "close")]])
    await message.reply(text=CMD_TXT, reply_markup = reply_markup, quote= True)
    
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------#    

#--------------------------------------------------------------[[NORMAL USER ACCESSIBLE COMMANDS]]----------------------------------------------------------------------#

@Bot.on_message(filters.command('forcesub') & filters.private & ~banUser)
async def fsub_commands(client: Client, message: Message):
    button = [[InlineKeyboardButton("•  ᴄʟᴏsᴇ  •", callback_data="close")]]
    await message.reply(text=FSUB_CMD_TXT, reply_markup=InlineKeyboardMarkup(button), quote=True)


@Bot.on_message(filters.command('users') & filters.private & ~banUser)
async def user_setting_commands(client: Client, message: Message):
    button = [[InlineKeyboardButton("•  ᴄʟᴏsᴇ  •", callback_data="close")]]
    await message.reply(text=USER_CMD_TXT, reply_markup=InlineKeyboardMarkup(button), quote=True)

    
HELP = "https://graph.org//file/10f310dd6a7cb56ad7c0b.jpg"
@Bot.on_message(filters.command('help') & filters.private & ~banUser)
async def help(client: Client, message: Message):
    buttons = [
        [
            InlineKeyboardButton("🔥 ᴏᴡɴᴇʀ", url="https://t.me/DoraShin_hlo"), 
            InlineKeyboardButton("👨‍💻 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/urr_sanjiii")
        ]
    ]
    if SUPPORT_GROUP:
        buttons.insert(0, [InlineKeyboardButton("•  sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ ɢʀᴏᴜᴘ  •", url="https://t.me/Mugiwaras_Network")])

    try:
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo = HELP,
            caption = HELP_TEXT.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
            reply_markup = reply_markup,
            message_effect_id = 5046509860389126442 #🎉
        )
    except Exception as e:
        return await message.reply(f"<b><i>! ᴇʀʀᴏʀ, ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @urr_sanjiii</i></b>\n<blockquote expandable><b>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>")


#--------------------------------------------------------------[[FSUB BUTTON LINKS MANAGEMENT]]-----------------------------------------------------------------#

@Bot.on_message(filters.command('byt') & filters.private & is_admin)
async def add_fsub_button_link(client: Bot, message: Message):
    """Add a link for ForceSub button - /byt <link>"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        return await message.reply("<b>ᴜsᴀɢᴇ: /byt <link>\n\n📌 ᴇxᴀᴍᴘʟᴇ: /byt https://t.me/channel_name</b>")
    
    link = args[1].strip()
    
    # Basic URL validation
    if not link.startswith(('http://', 'https://', 't.me/', '@')):
        return await message.reply("<b>❌ ɪɴᴠᴀʟɪᴅ ʟɪɴᴋ! ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ URL ᴏʀ Tᴇʟᴇɢʀᴀᴍ ʟɪɴᴋ</b>")
    
    try:
        await db.add_fsub_button_link(link)
        count = await db.get_fsub_button_links_count()
        await message.reply(f"<b>✅ ʟɪɴᴋ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n📊 ᴛᴏᴛᴀʟ /ʙʏᴛ ʟɪɴᴋs: {count}</b>")
    except Exception as e:
        log.error(f"Error adding fsub button link: {e}")
        await message.reply(f"<b>❌ ᴇʀʀᴏʀ: {str(e)}</b>")


@Bot.on_message(filters.command('ryt') & filters.private & is_admin)
async def remove_all_fsub_button_links(client: Bot, message: Message):
    """Remove all links added via /byt command"""
    count = await db.get_fsub_button_links_count()
    
    if count == 0:
        return await message.reply("<b>❌ ɴᴏ ʟɪɴᴋs ᴛᴏ ʀᴇᴍᴏᴠᴇ!</b>")
    
    try:
        await db.delete_all_fsub_button_links()
        await message.reply(f"<b>✅ ᴀʟʟ {count} /ʙʏᴛ ʟɪɴᴋs ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>")
    except Exception as e:
        log.error(f"Error removing fsub button links: {e}")
        await message.reply(f"<b>❌ ᴇʀʀᴏʀ: {str(e)}</b>")


@Bot.on_message(filters.command('lyt') & filters.private & is_admin)
async def list_fsub_button_links(client: Bot, message: Message):
    """List all links added via /byt command"""
    try:
        links = await db.get_all_fsub_button_links()
        
        if not links:
            return await message.reply("<b>❌ ɴᴏ ʟɪɴᴋs ᴀᴅᴅᴇᴅ ʏᴇᴛ!</b>")
        
        text = "<b>📋 /ʙʏᴛ ʟɪɴᴋs ʟɪsᴛ:\n\n</b>"
        for idx, link in enumerate(links, 1):
            text += f"<b>{idx}. </b><code>{link}</code>\n"
        
        text += f"\n<b>📊 ᴛᴏᴛᴀʟ: {len(links)} ʟɪɴᴋs</b>"
        await message.reply(text)
    except Exception as e:
        log.error(f"Error listing fsub button links: {e}")
        await message.reply(f"<b>❌ ᴇʀʀᴏʀ: {str(e)}</b>")
#--------------------------------------------------------------[[PREMIUM COMMANDS]]---------------------------------------------------------------------------#

@Bot.on_message(filters.command('premium') & filters.private & is_admin)
async def add_premium_user(client: Bot, message: Message):
    """Add a user to premium status"""
    try:
        text = message.text.split()

        if len(text) < 3:
            return await message.reply(
                "<b>📌 ᴜsᴀɢᴇ:</b>\n"
                "<code>/premium &lt;userID&gt; &lt;days&gt;</code>\n\n"
                "<b>ᴇxᴀᴍᴘʟᴇ:</b>\n"
                "<code>/premium 123456789 30</code>"
            )

        try:
            user_id = int(text[1])
            days = int(text[2])
        except ValueError:
            return await message.reply("<b>❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ ᴏʀ ᴅᴀʏs!</b>")

        if days <= 0:
            return await message.reply("<b>❌ ᴅᴀʏs ᴍᴜsᴛ ʙᴇ ɢʀᴇᴀᴛᴇʀ ᴛʜᴀɴ 0!</b>")

        await db.set_premium_user(user_id, days)

        text_response = (
            f"<b>✅ ᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n</b>"
            f"<b>👤 ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>\n"
            f"<b>📅 ᴅᴜʀᴀᴛɪᴏɴ:</b> <code>{days} ᴅᴀʏs</code>\n"
            f"<b>🎁 ᴘᴇʀᴋ:</b> <i>ɴᴏ ᴛᴏᴋᴇɴ ᴀᴅs ʀᴇqᴜɪʀᴇᴅ</i>"
        )

        await message.reply(text_response)

    except Exception as e:
        log.error(f"Error adding premium user: {e}")
        await message.reply(f"<b>❌ ᴇʀʀᴏʀ: {str(e)}</b>")

@Bot.on_message(filters.command('remove') & filters.private & is_admin)
async def remove_premium_user(client: Bot, message: Message):
    """Remove premium status from user"""
    try:
        text = message.text.split()
        
        if len(text) < 2:
            return await message.reply(
                "<b>📌 ᴜsᴀɢᴇ:</b>\n"
                "<code>/remove &lt;userID&gt;</code>\n\n"
                "<b>ᴇxᴀᴍᴘʟᴇ:</b>\n"
                "<code>/remove 123456789</code>"
            )
        
        try:
            user_id = int(text[1])
        except ValueError:
            return await message.reply("<b>❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ!</b>")
        
        is_premium = await db.is_premium_user(user_id)
        
        if not is_premium:
            return await message.reply(
                f"<b>❌ ᴜsᴇʀ <code>{user_id}</code> ɪs ɴᴏᴛ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ!</b>"
            )
        
        await db.remove_premium_user(user_id)
        
        text_response = (
            f"<b>✅ ᴘʀᴇᴍɪᴜᴍ ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n</b>"
            f"<b>👤 ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>\n"
            f"<b>📌 sᴛᴀᴛᴜs:</b> <i>ʀᴇɢᴜʟᴀʀ ᴜsᴇʀ</i>"
        )
        
        await message.reply(text_response)
        
    except Exception as e:
        log.error(f"Error removing premium user: {e}")
        await message.reply(f"<b>❌ ᴇʀʀᴏʀ: {str(e)}</b>")




from plugins.anime import process_publish_workflow, user_data
from plugins.utils import apply_small_caps
from pyrogram.enums import ParseMode
from pyrogram import StopPropagation
import asyncio

@Bot.on_message(filters.command('create') & filters.private)
async def create_command(client: Bot, message: Message):
    user_id = message.from_user.id
    image_url = "https://graph.org/file/4579616111776d30d008f-5ac8b112f9fdd86cd5.jpg"
    welcome_msg = apply_small_caps("welcome to the post creator. please click the button below to begin.")
    caption = f"<blockquote><b>{welcome_msg}</b></blockquote>"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Create Post", callback_data="start_create_post")]
    ])

    await message.reply_photo(photo=image_url, caption=caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@Bot.on_callback_query(filters.regex('^start_create_post$'), group=-1)
async def start_create_post_cb(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.answer("Starting post creation...")

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="close")]])
    try:
        from databases.database import db
        button_config = await db.get_anime_button_config(user_id)
        if not button_config: button_config = "Join - {link} && Group - https://t.me/posterprobot\nFor More - https://t.me/posterprobot"

        # Display the pre-saved auto-buttons or format
        # Ask user for target link
        response = await client.ask(user_id, f"<blockquote>Cᴜʀʀᴇɴᴛ Bᴜᴛᴛᴏɴs:\n\n<code>{button_config}</code>\n\nᴘʟᴇᴀsᴇ sᴇɴᴅ ᴍᴇ ᴛʜᴇ ʟɪɴᴋ ғᴏʀ ᴛʜᴇ ᴘᴏsᴛ/ᴅᴏᴡɴʟᴏᴀᴅ ʙᴜᴛᴛᴏɴ</blockquote>", reply_markup=keyboard, parse_mode=ParseMode.HTML, timeout=120)

        if user_id not in user_data:
            user_data[user_id] = {}

        user_data[user_id]['post_link'] = response.text
        user_data[user_id]['is_create_mode'] = True
        user_data[user_id]['create_image_url'] = "https://graph.org/file/4579616111776d30d008f-5ac8b112f9fdd86cd5.jpg"
        welcome_msg = apply_small_caps("welcome to the post creator. please click the button below to begin.")
        user_data[user_id]['create_caption'] = f"<blockquote><b>{welcome_msg}</b></blockquote>"

        await process_publish_workflow(client, callback_query, user_id)

    except asyncio.TimeoutError:
        await client.send_message(user_id, "Publish process canceled due to timeout.")
    raise StopPropagation
