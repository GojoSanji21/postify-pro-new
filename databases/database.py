


import time
import pymongo, os
import motor
from config import DB_URL, DB_NAME
from bot import Bot
from config import LOGGER
from datetime import datetime, timedelta
import motor.motor_asyncio  # Import the correct module

dbclient = pymongo.MongoClient(DB_URL)
database = dbclient[DB_NAME]




default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }



class Rohit:

    def __init__(self, DB_URL, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URL)
        self.database = self.dbclient[DB_NAME]

        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.user_data = self.database['users']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        self.shortener_data = self.database['shortener']
        self.settings_data = self.database['settings']

        self.auto_delete_data = self.database['auto_delete']
        self.hide_caption_data = self.database['hide_caption']
        self.protect_content_data = self.database['protect_content']
        self.channel_button_data = self.database['channel_button']

        self.settings_data = self.database['settings']
        self.del_timer_data = self.database['del_timer']
        self.channel_button_link_data = self.database['channelButton_link']

        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.store_reqLink_data = self.database['store_reqLink']

    # Shortener Token
    async def set_shortener_url(self, url):
        try:
        # Check if an active shortener exists
            existing = await self.shortener_data.find_one({"active": True})
            if existing:
            # Update the URL of the existing active shortener
                await self.shortener_data.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"shortener_url": url, "updated_at": datetime.utcnow()}}
                )
            else:
            # Insert a new active shortener with the given URL
                await self.shortener_data.insert_one({
                    "shortener_url": url,
                    "api_key": None,
                    "active": True,
                    "created_at": datetime.utcnow()
                })
            return True
        except Exception as e:
            LOGGER(__name__).error(f"Error setting shortener URL: {e}")
            return False

    async def set_shortener_api(self, api):
        try:
        # Check if an active shortener exists
            existing = await self.shortener_data.find_one({"active": True})
            if existing:
            # Update the API key of the existing active shortener
                await self.shortener_data.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"api_key": api, "updated_at": datetime.utcnow()}}
                )
            else:
            # Insert a new active shortener with the given API key
                await self.shortener_data.insert_one({
                    "shortener_url": None,
                    "api_key": api,
                    "active": True,
                    "created_at": datetime.utcnow()
                })
            return True
        except Exception as e:
            LOGGER(__name__).error(f"Error setting shortener API key: {e}")
            return False

    async def get_shortener_url(self):
        try:
        # Retrieve the shortener URL of the active shortener
            shortener = await self.shortener_data.find_one({"active": True}, {"_id": 0, "shortener_url": 1})
            return shortener.get("shortener_url") if shortener else None
        except Exception as e:
            LOGGER(__name__).error(f"Error fetching shortener URL: {e}")
            return None

    async def get_shortener_api(self):
        try:
        # Retrieve the API key of the active shortener
            shortener = await self.shortener_data.find_one({"active": True}, {"_id": 0, "api_key": 1})
            return shortener.get("api_key") if shortener else None
        except Exception as e:
            LOGGER(__name__).error(f"Error fetching shortener API key: {e}")
            return None


    async def deactivate_shortener(self):
        try:
            # Deactivate all active shorteners
            await self.shortener_data.update_many({"active": True}, {"$set": {"active": False}})
            return True
        except Exception as e:
            LOGGER(__name__).error(f"Error deactivating shorteners: {e}")
            return False

    async def set_verified_time(self, verified_time: int):
        try:
            # Update the verified time in the database
            result = await self.settings_data.update_one(
                {"_id": "verified_time"},  # Assuming there's an entry with this ID for settings
                {"$set": {"verified_time": verified_time}},
                upsert=True  # Create the document if it doesn't exist
            )
            return result.modified_count > 0  # Return True if the update was successful
        except Exception as e:
            LOGGER(__name__).error(f"Error updating verified time: {e}")
            return False

    async def get_verified_time(self):
        try:
            # Retrieve the verified time from the database
            settings = await self.settings_data.find_one({"_id": "verified_time"})
            return settings.get("verified_time", None) if settings else None
        except Exception as e:
            LOGGER(__name__).error(f"Error fetching verified time: {e}")
            return None

    async def set_tut_video(self, video_url: str):
        try:
            # Update the tutorial video URL in the database
            result = await self.settings_data.update_one(
                {"_id": "tutorial_video"},  # Assuming there's an entry with this ID for settings
                {"$set": {"tutorial_video_url": video_url}},
                upsert=True  # Create the document if it doesn't exist
            )
            return result.modified_count > 0  # Return True if the update was successful
        except Exception as e:
            LOGGER(__name__).error(f"Error updating tutorial video URL: {e}")
            return False

    async def get_tut_video(self):
        try:
            # Retrieve the tutorial video URL from the database
            settings = await self.settings_data.find_one({"_id": "tutorial_video"})
            return settings.get("tutorial_video_url", None) if settings else None
        except Exception as e:
            LOGGER(__name__).error(f"Error fetching tutorial video URL: {e}")
            return None

    # USER MANAGEMENT
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})
        return

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in user_docs]
        return user_ids

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        return

    # Update shortener settings for a user
    async def update_shortener(self, user_id: int, site: str, api_key: str):
        """
        Update the shortener site and API key for a user.
        """
        await self.shortener_data.update_one(
            {'_id': user_id},
            {'$set': {'site': site, 'api': api_key}},
            upsert=True  # Create a new document if one doesn't exist
        )

    # Enable or disable shortener functionality for a user
    async def toggle_shortener(self, user_id: int, enable: bool):
        """
        Enable or disable the shortener functionality for a user.
        """
        await self.shortener_data.update_one(
            {'_id': user_id},
            {'$set': {'enabled': enable}},
            upsert=True  # Create a new document if one doesn't exist
        )

    # Fetch the shortener settings for a user
    async def fetch_shortener(self, user_id: int):
        """
        Fetch the shortener settings for a user.
        Returns a dictionary or None if no settings are found.
        """
        user = await self.shortener_data.find_one({'_id': user_id})
        if user:
            return {
                'site': user.get('site'),
                'api': user.get('api'),
                'enabled': user.get('enabled', False)
            }
        return None


    # CHANNEL BUTTON SETTINGS
    async def set_channel_button_link(self, button_name: str, button_link: str):
        await self.channel_button_link_data.delete_many({})  # Remove all existing documents
        await self.channel_button_link_data.insert_one({'button_name': button_name, 'button_link': button_link}) # Insert the new document

    async def get_channel_button_link(self):
        data = await self.channel_button_link_data.find_one({})
        if data:
            return data.get('button_name'), data.get('button_link')
        return ' Channel', 'https://t.me/Javpostr'


    # DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int):
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})

    async def get_del_timer(self):
        data = await self.del_timer_data.find_one({})
        if data:
            return data.get('value', 600)
        return 600

    # SET BOOLEAN VALUES FOR DIFFERENT SETTINGS

    async def set_auto_delete(self, value: bool):
        existing = await self.auto_delete_data.find_one({})
        if existing:
            await self.auto_delete_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.auto_delete_data.insert_one({'value': value})

    async def set_hide_caption(self, value: bool):
        existing = await self.hide_caption_data.find_one({})
        if existing:
            await self.hide_caption_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.hide_caption_data.insert_one({'value': value})

    async def set_protect_content(self, value: bool):
        existing = await self.protect_content_data.find_one({})
        if existing:
            await self.protect_content_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.protect_content_data.insert_one({'value': value})

    async def set_channel_button(self, value: bool):
        existing = await self.channel_button_data.find_one({})
        if existing:
            await self.channel_button_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.channel_button_data.insert_one({'value': value})

    async def set_request_forcesub(self, value: bool):
        existing = await self.rqst_fsub_data.find_one({})
        if existing:
            await self.rqst_fsub_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.rqst_fsub_data.insert_one({'value': value})


    # GET BOOLEAN VALUES FOR DIFFERENT SETTINGS

    async def get_auto_delete(self):
        data = await self.auto_delete_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_hide_caption(self):
        data = await self.hide_caption_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_protect_content(self):
        data = await self.protect_content_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_channel_button(self):
        data = await self.channel_button_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    async def get_request_forcesub(self):
        data = await self.rqst_fsub_data.find_one({})
        if data:
            return data.get('value', False)
        return False

    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int):
        found = await self.channel_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.channel_data.insert_one({'_id': channel_id})
            return

    async def del_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.channel_data.delete_one({'_id': channel_id})
            return

    async def get_all_channels(self):
        channel_docs = await self.channel_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    # ADMIN USER MANAGEMENT
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
            return

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
            return

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    # BAN USER MANAGEMENT
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})
            return

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            return

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    # REQUEST FORCE-SUB MANAGEMENT

    # Initialize a channel with an empty user_ids array (acting as a set)
    async def add_reqChannel(self, channel_id: int):
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id},
            {'$setOnInsert': {'user_ids': []}},  # Start with an empty array to represent the set
            upsert=True  # Insert the document if it doesn't exist
        )

    # Set the request_forcesub mode for a specific channel
    async def set_request_forcesub_channel(self, channel_id: int, fsub_mode: bool):
        await self.rqst_fsub_Channel_data.update_one(
        {'_id': channel_id},
        {'$set': {'fsub_mode': fsub_mode}},
        upsert=True
    )

    # Method 1: Add user to the channel set
    async def reqSent_user(self, channel_id: int, user_id: int):
        # Add the user to the set of users for a specific channel
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id},
            {'$addToSet': {'user_ids': user_id}},
            upsert=True
        )

    # Method 2: Remove a user from the channel set
    async def del_reqSent_user(self, channel_id: int, user_id: int):
        # Remove the user from the set of users for the channel
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id},
            {'$pull': {'user_ids': user_id}}
        )

    # Clear the user set (user_ids array) for a specific channel
    async def clear_reqSent_user(self, channel_id: int):
        if await self.reqChannel_exist(channel_id):
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': channel_id},
                {'$set': {'user_ids': []}}  # Reset user_ids to an empty array
            )

    # Method 3: Check if a user exists in the channel set
    async def reqSent_user_exist(self, channel_id: int, user_id: int):
        # Check if the user exists in the set of the channel's users
        found = await self.rqst_fsub_Channel_data.find_one(
            {'_id': channel_id, 'user_ids': user_id}
        )
        return bool(found)

    # Method 4: Remove a channel and its set of users
    async def del_reqChannel(self, channel_id: int):
        # Delete the entire channel's user set
        await self.rqst_fsub_Channel_data.delete_one({'_id': channel_id})

    # Method 5: Check if a channel exists
    async def reqChannel_exist(self, channel_id: int):
        # Check if the channel exists
        found = await self.rqst_fsub_Channel_data.find_one({'_id': channel_id})
        return bool(found)

    # Method 6: Get all users from a channel's set
    async def get_reqSent_user(self, channel_id: int):
        # Retrieve the list of users for a specific channel
        data = await self.rqst_fsub_Channel_data.find_one({'_id': channel_id})
        if data:
            return data.get('user_ids', [])
        return []

    # Method 7: Get all available channel IDs
    async def get_reqChannel(self):
        # Retrieve all channel IDs
        channel_docs = await self.rqst_fsub_Channel_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids


    # Get all available channel IDs in store_reqLink_data
    async def get_reqLink_channels(self):
        # Retrieve all documents from store_reqLink_data
        channel_docs = await self.store_reqLink_data.find().to_list(length=None)
        # Extract the channel IDs from the documents
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    # Get the stored link for a specific channel
    async def get_stored_reqLink(self, channel_id: int):
        # Retrieve the stored link for a specific channel_id from store_reqLink_data
        data = await self.store_reqLink_data.find_one({'_id': channel_id})
        if data:
            return data.get('link')
        return None

    # Set (or update) the stored link for a specific channel
    async def store_reqLink(self, channel_id: int, link: str):
        # Insert or update the link for the channel_id in store_reqLink_data
        await self.store_reqLink_data.update_one(
            {'_id': channel_id},
            {'$set': {'link': link}},
            upsert=True
        )

    # Delete the stored link and the channel from store_reqLink_data
    async def del_stored_reqLink(self, channel_id: int):
        # Delete the document with the channel_id in store_reqLink_data
        await self.store_reqLink_data.delete_one({'_id': channel_id})

    # ========== FSUB BUTTON LINKS MANAGEMENT (/byt /ryt /lyt) ==========
    async def add_fsub_button_link(self, link: str):
        """Add a link for /byt command (ForceSub button links)"""
        fsub_links = self.database['fsub_button_links']
        await fsub_links.insert_one({'link': link, 'created_at': datetime.utcnow()})
        return True

    async def get_all_fsub_button_links(self):
        """Get all links added via /byt command"""
        fsub_links = self.database['fsub_button_links']
        links_data = await fsub_links.find().to_list(length=None)
        return [link.get('link') for link in links_data]

    async def delete_all_fsub_button_links(self):
        """Delete all links added via /byt command"""
        fsub_links = self.database['fsub_button_links']
        result = await fsub_links.delete_many({})
        return result.deleted_count > 0

    async def get_fsub_button_links_count(self):
        """Get count of links added via /byt command"""
        fsub_links = self.database['fsub_button_links']
        count = await fsub_links.count_documents({})
        return count

    # ========== PREMIUM USER MANAGEMENT ==========
    async def set_premium_user(self, user_id: int, days: int):
        """Add or update a user to premium status"""
        premium_data = self.database['premium_users']
        expiry_date = datetime.utcnow() + timedelta(days=days)
        await premium_data.update_one(
            {'_id': user_id},
            {'$set': {'expiry_date': expiry_date, 'added_on': datetime.utcnow()}},
            upsert=True
        )
        return True

    async def is_premium_user(self, user_id: int):
        """Check if user is premium"""
        premium_data = self.database['premium_users']
        user = await premium_data.find_one({'_id': user_id})
        if not user:
            return False

        expiry_date = user.get('expiry_date')
        if expiry_date and expiry_date > datetime.utcnow():
            return True
        else:
            # Remove expired premium user
            if expiry_date and expiry_date <= datetime.utcnow():
                await premium_data.delete_one({'_id': user_id})
            return False

    async def remove_premium_user(self, user_id: int):
        """Remove premium status from user"""
        premium_data = self.database['premium_users']
        result = await premium_data.delete_one({'_id': user_id})
        return result.deleted_count > 0

    async def get_premium_user_info(self, user_id: int):
        """Get premium user info"""
        premium_data = self.database['premium_users']
        user = await premium_data.find_one({'_id': user_id})
        if user:
            return {
                'user_id': user_id,
                'expiry_date': user.get('expiry_date'),
                'added_on': user.get('added_on')
            }
        return None

    async def get_all_premium_users(self):
        """Get all active premium users"""
        premium_data = self.database['premium_users']
        users = await premium_data.find().to_list(length=None)
        active_users = []
        for user in users:
            expiry_date = user.get('expiry_date')
            if expiry_date and expiry_date > datetime.utcnow():
                active_users.append(user['_id'])
            else:
                await premium_data.delete_one({'_id': user['_id']})
        return active_users



    async def get_anime_brand_text(self, user_id: int):
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('anime_brand_text', None) if user else None

    async def set_anime_brand_text(self, user_id: int, text: str):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'anime_brand_text': text}}, upsert=True)

    async def get_anime_brand_logo(self, user_id: int):
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('anime_brand_logo', None) if user else None

    async def set_anime_brand_logo(self, user_id: int, logo_path: str):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'anime_brand_logo': logo_path}}, upsert=True)

    async def del_anime_branding(self, user_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$unset': {'anime_brand_text': '', 'anime_brand_logo': ''}})

    async def get_anime_button_config(self, user_id: int):
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('anime_button_config', None) if user else None

    async def set_anime_button_config(self, user_id: int, config: str):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'anime_button_config': config}}, upsert=True)

    async def add_user_channel(self, user_id: int, channel_id: int, channel_title: str):
        channel_info = {'id': channel_id, 'title': channel_title}
        await self.user_data.update_one(
            {'_id': user_id},
            {'$addToSet': {'user_channels': channel_info}},
            upsert=True
        )

    async def get_user_channels(self, user_id: int):
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('user_channels', []) if user else []

    async def get_anime_template(self, user_id: int):
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('anime_template', 1) if user else 1

    async def set_anime_template(self, user_id: int, template_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'anime_template': template_id}}, upsert=True)

db = Rohit(DB_URL, DB_NAME)
