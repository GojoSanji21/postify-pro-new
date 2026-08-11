# +++ Made By Sanjiii [telegram username: @Urr_Sanjiii] +++

import asyncio
import os
import logging
from logging.handlers import RotatingFileHandler


#Bot token @Botfather, --⚠️ REQUIRED--
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8867922237:AAHfZiIP_xLrxvK7d2WKph9f7U_QBoCzx5s")
#Your API ID from my.telegram.org --⚠️ REQUIRED--
APP_ID = int(os.environ.get("APP_ID", ""))

#Your API Hash from my.telegram.org, --⚠️ REQUIRED--
API_HASH = os.environ.get("API_HASH", "")

#OWNER ID --⚠️ REQUIRED--
OWNER_ID = int(os.environ.get("OWNER_ID", "1683225887"))

#SUPPORT_GROUP: This is used for normal users for getting help if they don't understand how to use the bot --⚠ OPTIONAL--
SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "-1002361458256")

#Port
PORT = os.environ.get("PORT", "8040")

#Database --⚠️ REQUIRED--
DB_URL = os.environ.get("DB_URL", "")
DB_NAME = os.environ.get("DATABASE_NAME", "postifyprobot")

START_PIC = os.environ.get("START_PIC", "https://graph.org/file/903f5b233999f02fa6015-76938468f549dac193.jpg")
FORCE_PIC = os.environ.get("FORCE_PIC", "https://graph.org/file/d14344c65c52acc05cb1e-8e5ac58617613aafa2.jpg")

                        
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

#Collection of pics for Bot // #Optional but atleast one pic link should be replaced if you don't want predefined links
PICS = (os.environ.get("PICS", "https://graph.org/file/b4ea9f0e449f1c0c219e4-1dc7e5131b7e569753.jpg")).split() #Required
#set your Custom Caption here, Keep None for Disable Custom Caption
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", None)

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
