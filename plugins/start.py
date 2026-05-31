# +++ ᴜɪ ʙʏ ᴀʜᴍᴇᴅ [telegram username: @ᴜʀʀ_sᴀɴᴊɪɪɪ] +++

import asyncio
import base64
import logging
import os
import random
import sys
import re
import string 
import string as rohit
import time
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction, ButtonStyle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from plugins.autoDelete import auto_del_notification, delete_message
from bot import Bot
from config import *
from helper_func import *
from databases.database import *
from plugins.FORMATS import *
from databases.database import db
from config import *
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid
from datetime import datetime, timedelta
from pytz import timezone

# +++ ᴜɪ ʙʏ ᴀʜᴍᴇᴅ [telegram username: @ᴜʀʀ_sᴀɴᴊɪɪɪ] +++

# Track (user_id, link_param) pairs who already saw /byt forcesub for a specific link
byt_fsub_seen = set()

# Dictionary to track which users are in "add channel state"
add_channel_state = {}

@Bot.on_callback_query(filters.regex('^add_channel_req$'), group=-1)
async def add_channel_req_cb(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    add_channel_state[user_id] = True

    msg_text = """<blockquote><b>➕ Add Channel</b>

To add a channel, you have two options:

<b>1. Automatic Detection:</b>
• Add the bot to your channel as an administrator
• The bot will automatically detect and add the channel

<b>2. Manual Addition:</b>
• Use the command: <code>/addchannel [Channel ID/Username if public]</code>
• Or reply to a forwarded message from the channel with <code>/addchannel</code>

Note: You must be an administrator in the channel for the bot to work.</blockquote>"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="cancel_add_channel")]
    ])

    if query.message.photo:
        await query.message.delete()
        await client.send_message(chat_id=user_id, text=msg_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(text=msg_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@Bot.on_callback_query(filters.regex('^cancel_add_channel$'), group=-1)
async def cancel_add_channel_cb(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in add_channel_state:
        del add_channel_state[user_id]
    await query.message.delete()
    await query.answer("Add channel process canceled.")

from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus

@Bot.on_message(filters.command('addchannel') & filters.private)
async def add_channel_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in add_channel_state:
        return

    chat_id = None
    if message.reply_to_message and getattr(message.reply_to_message, "forward_origin", None):
        origin = message.reply_to_message.forward_origin
        if hasattr(origin, "chat") and origin.chat:
            chat_id = origin.chat.id
        elif hasattr(origin, "sender_chat") and origin.sender_chat:
            chat_id = origin.sender_chat.id
    elif message.reply_to_message and message.reply_to_message.forward_from_chat:
        chat_id = message.reply_to_message.forward_from_chat.id
    elif len(message.command) > 1:
        target = message.command[1]
        try:
            chat_id = int(target)
        except ValueError:
            chat_id = target

    if not chat_id:
        await message.reply_text("Please provide a valid channel ID/username or reply to a forwarded message from the channel.")
        return

    try:
        chat = await client.get_chat(chat_id)
        member = await client.get_chat_member(chat.id, user_id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            await message.reply_text("You must be an administrator in the channel.")
            return

        bot_member = await client.get_chat_member(chat.id, client.me.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            await message.reply_text("The bot must be an administrator in the channel.")
            return

        await db.add_user_channel(user_id, chat.id, chat.title)
        del add_channel_state[user_id]
        await message.reply_text(f"Successfully added channel: {chat.title}")
    except Exception as e:
        await message.reply_text(f"Failed to add channel: {e}")

@Bot.on_chat_member_updated()
async def chat_member_updated_handler(client: Client, update: ChatMemberUpdated):
    # Only process updates regarding the bot itself being promoted to admin
    if update.new_chat_member and update.new_chat_member.user.id == client.me.id:
        if update.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            user_id = update.from_user.id
            chat = update.chat
            try:
                await db.add_user_channel(user_id, chat.id, chat.title)
                # clear state if present, but process regardless
                if user_id in add_channel_state:
                    del add_channel_state[user_id]
                msg_text = """<blockquote>🍂 ʏᴏᴜ ʜᴀᴠᴇ ᴀᴅᴅᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ..
ɴᴏᴡ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴛʜᴇ ғᴜɴᴄᴛɪᴏɴs ᴏғ ᴛʜᴇ ʙᴏᴛ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ‼️</blockquote>"""
                await client.send_message(user_id, msg_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                try: await client.send_message(user_id, f"Error adding channel: {e}")
                except: pass

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id

    # Default initialization
    AUTO_DEL = False
    DEL_TIMER = 0
    HIDE_CAPTION = False
    CHNL_BTN = None
    PROTECT_MODE = False
    last_message = None
    messages = []

    ADMINS = await db.get_all_admins()

    logging.info(f"Received /start command from user ID: {id}")

    # Check and add user to the database if not present
    if not await db.present_user(id):
        try:
            await db.add_user(id)
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            return

    text = message.text        
    if len(text)>7:
        await message.delete()

        # If /byt buttons are added, show byt forcesub ONCE per link
        # Track by (user_id, link_param) so same link = no repeat, new link = show again
        try:
            link_param = text.split(" ", 1)[1] if len(text.split(" ", 1)) > 1 else None
        except:
            link_param = None

        try:
            byt_links = await db.get_all_fsub_button_links()
            if byt_links and link_param:
                user_link_key = (id, link_param)
                if user_link_key not in byt_fsub_seen:
                    byt_fsub_seen.add(user_link_key)
                    byt_buttons = []
                    for link in byt_links:
                        byt_buttons.append([InlineKeyboardButton(text='»  ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ  «', url=link)])
                    try:
                        byt_buttons.append([InlineKeyboardButton(text='‼️ ɴᴏᴡ ᴄʟɪᴄᴋ ʜᴇʀᴇ ‼️', url=f"https://t.me/{client.username}?start={message.command[1]}")])
                    except IndexError:
                        pass
                    await client.send_photo(
                        chat_id=id,
                        photo=FORCE_PIC if FORCE_PIC else random.choice(PICS),
                        caption=FORCE_MSG.format(
                            first=message.from_user.first_name,
                            last=message.from_user.last_name,
                            username=None if not message.from_user.username else '@' + message.from_user.username,
                            mention=message.from_user.mention,
                            id=message.from_user.id
                        ),
                        reply_markup=InlineKeyboardMarkup(byt_buttons)
                    )
                    return  # Stop here - user must click 'now click here' again to get files
                # If already seen for this link, just continue to deliver files
        except Exception as e:
            logging.info(f"Error sending /byt force-sub message: {e}")

        try: base64_string = text.split(" ", 1)[1]
        except: return

        string = await decode(base64_string)
        if not string:  # Check if decode failed
            return
        argument = string.split("-")

        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except:
                return

            if start <= end:
                ids = range(start,end+1)
            else:
                ids = []
                i = start
                while True:
                    ids.append(i)
                    i -= 1
                    if i < end:
                        break

        elif len(argument) == 2:
            try: ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except: return

        last_message = None
        await message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)

        try: messages = await get_messages(client, ids)
        except: return await message.reply("<b><i>sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ..!</i></b>")

        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(db.get_auto_delete(), db.get_del_timer(), db.get_hide_caption(), db.get_channel_button(), db.get_protect_content())
        if CHNL_BTN: button_name, button_link = await db.get_channel_button_link()

        for idx, msg in enumerate(messages):
            if bool(CUSTOM_CAPTION) & bool(msg.document):
                caption = CUSTOM_CAPTION.format(previouscaption = "" if not msg.caption else msg.caption.html, filename = msg.document.file_name)

            elif HIDE_CAPTION and (msg.document or msg.audio):
                caption = ""

            else:
                caption = "" if not msg.caption else msg.caption.html

            if CHNL_BTN:
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text=button_name, url=button_link)]]) if msg.document or msg.photo or msg.video or msg.audio else None
            else:
                reply_markup = msg.reply_markup

            try:
                copied_msg = await msg.copy(chat_id=id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_MODE)
                await asyncio.sleep(0.1)

                if AUTO_DEL:
                    asyncio.create_task(delete_message(copied_msg, DEL_TIMER))
                    if idx == len(messages) - 1: last_message = copied_msg

            except FloodWait as e:
                await asyncio.sleep(e.x)
                copied_msg = await msg.copy(chat_id=id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_MODE)
                await asyncio.sleep(0.1)

                if AUTO_DEL:
                    asyncio.create_task(delete_message(copied_msg, DEL_TIMER))
                    if idx == len(messages) - 1: last_message = copied_msg

        if AUTO_DEL and last_message:
                asyncio.create_task(auto_del_notification(client.username, last_message, DEL_TIMER, message.command[1]))

    else:
        reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴄʟɪᴄᴋ ғᴏʀ ᴍᴏʀᴇ •", callback_data='about', style=ButtonStyle.PRIMARY)],
                    [InlineKeyboardButton("• sᴇᴛᴛɪɴɢs", callback_data='setting', style=ButtonStyle.DANGER),
                     InlineKeyboardButton('ᴘᴏsᴛᴇʀ', callback_data='settings_main', style=ButtonStyle.DANGER)],
                    [InlineKeyboardButton("➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data='add_channel_req', style=ButtonStyle.SUCCESS)],
                ])
        await message.reply_photo(
            photo = random.choice(PICS),
            caption = START_MSG.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
            reply_markup = reply_markup,
		has_spoiler = True
        )
        try: await message.delete()
        except: pass

   
##===================================================================================================================##

#TRIGGRED START MESSAGE FOR HANDLE FORCE SUB MESSAGE AND FORCE SUB CHANNEL IF A USER NOT JOINED A CHANNEL

##===================================================================================================================##   


# Create a global dictionary to store chat data
chat_data_cache = {}

@Bot.on_message(filters.command('start') & filters.private & ~banUser)
async def not_joined(client: Client, message: Message):
    temp = await message.reply(f"<b>??</b>")

    user_id = message.from_user.id

    REQFSUB = await db.get_request_forcesub()
    buttons = []
    count = 0

    try:
        for total, chat_id in enumerate(await db.get_all_channels(), start=1):
            await message.reply_chat_action(ChatAction.PLAYING)

            # Show the join button of non-subscribed Channels.....
            if not await is_userJoin(client, user_id, chat_id):
                try:
                    # Check if chat data is in cache
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]  # Get data from cache
                    else:
                        data = await client.get_chat(chat_id)  # Fetch from API
                        chat_data_cache[chat_id] = data  # Store in cache

                    cname = data.title

                    # Handle private channels and links
                    if REQFSUB and not data.username: 
                        link = await db.get_stored_reqLink(chat_id)
                        await db.add_reqChannel(chat_id)

                        if not link:
                            link = (await client.create_chat_invite_link(chat_id=chat_id, creates_join_request=True)).invite_link
                            await db.store_reqLink(chat_id, link)
                    else:
                        link = data.invite_link

                    # Add button for the chat
                    buttons.append([InlineKeyboardButton(text='»  ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ  «', url=link)])
                    count += 1
                    await temp.edit(f"<b>{'! ' * count}</b>")

                except Exception as e:
                    print(f"Can't Export Channel Name and Link..., Please Check If the Bot is admin in the FORCE SUB CHANNELS:\nProvided Force sub Channel:- {chat_id}")
                    return await temp.edit(f"<b>! ᴇʀʀᴏʀ, ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @urr_sanjiii</b>\n<blockquote expandable><b>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>")

        # If user has joined all channels, delete temp and return (success - they're verified)
        if count == 0:
            await temp.delete()
            return 

        # Add /byt links (always show if they exist, regardless of REQFSUB)
        try:
            byt_links = await db.get_all_fsub_button_links()
            if byt_links:
                for link in byt_links:
                    buttons.append([InlineKeyboardButton(text='»  ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ  «', url=link)])
        except Exception as e:
            logging.info(f"No /byt links to add: {e}")

        # Add "now click here" button last
        try:
            buttons.append([InlineKeyboardButton(text='‼️ ɴᴏᴡ ᴄʟɪᴄᴋ ʜᴇʀᴇ ‼️', url=f"https://t.me/{client.username}?start={message.command[1]}")])
        except IndexError:
            pass

        await message.reply_photo(
            photo=random.choice(PICS),
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        print(f"Error: {e}")  # Print the error message for debugging
        # Optionally, send an error message to the user or handle further actions here
        await temp.edit(f"<b><i>! ᴇʀʀᴏʀ, ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @urr_sanjiii</i></b>\n<blockquote expandable><b>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>")


# +++ Customised By Rohit [telegram username: @rohit_1888] +++

#=====================================================================================##
#......... RESTART COMMAND FOR RESTARTING BOT .......#
#=====================================================================================##

@Bot.on_message(filters.command('restart') & filters.private & filters.user(OWNER_ID))
async def restart_bot(client: Client, message: Message):
    print("Restarting bot...")
    msg = await message.reply(text=f"<b><i>» {client.name} ɢᴏɪɴɢ ᴛᴏ ʀᴇsᴛᴀʀᴛ...\n\n» ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ 5 sᴇᴄᴏɴᴅs...!!!</i></b>")
    try:
        await asyncio.sleep(5)  # Wait for 5 seconds before restarting
        await msg.delete()
        args = [sys.executable, "main.py"]  # Adjust this if your start file is named differently
        os.execl(sys.executable, *args)
    except Exception as e:
        print(f"Error occured while Restarting the bot: {e}")
        return await msg.edit_text(f"<b>! ᴇʀʀᴏʀ, ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @urr_sanjiii</b>\n<blockquote expandable><b>ʀᴇᴀsᴏɴ:</b> {e}</blockquote>")
    # Optionally, you can add cleanup tasks here
    #subprocess.Popen([sys.executable, "main.py"])  # Adjust this if your start file is named differently
    #sys.exit()
