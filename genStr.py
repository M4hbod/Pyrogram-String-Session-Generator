import asyncio

from bot import bot, HU_APP
from pyromod import listen
from asyncio.exceptions import TimeoutError

from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    SessionPasswordNeeded, FloodWait,
    PhoneNumberInvalid, ApiIdInvalid,
    PhoneCodeInvalid, PhoneCodeExpired
)

API_TEXT = """سلام {}.
📌کار من ساختن استرینگ سشن پایروگرامه.

برام `API_ID` مورد نظرت رو بفرست تا شروع کنیم."""
HASH_TEXT = "حالا `API_HASH` رو بفرست.\n\nبرای کنسل کردن دستور /cancel رو بفرست."
PHONE_NUMBER_TEXT = (
    "حالا شماره اکانتی که میخوای استرینگش رو بگیری رو بفرست \n"
    "به این شکل: **+989186665517**\n\n"
    "برای کنسل کردن دستور /cancel رو بفرست."
)

@bot.on_message(filters.private & filters.command("start"))
async def genStr(_, msg: Message):
    chat = msg.chat
    api = await bot.ask(
        chat.id, API_TEXT.format(msg.from_user.mention)
    )
    if await is_cancel(msg, api.text):
        return
    try:
        check_api = int(api.text)
    except Exception:
        await msg.reply("`API_ID` اشتباهه.\n/start رو بفرست تا دوباره شروع کنیم.")
        return
    api_id = api.text
    await api.delete()
    hash = await bot.ask(chat.id, HASH_TEXT)
    if await is_cancel(msg, hash.text):
        return
    if not len(hash.text) >= 30:
        await msg.reply("`API_HASH` اشتباهه.\n/start رو بفرست تتا دوباره شروع کنیم.")
        return
    api_hash = hash.text
    await hash.delete()
    while True:
        number = await bot.ask(chat.id, PHONE_NUMBER_TEXT)
        if not number.text:
            continue
        if await is_cancel(msg, number.text):
            return
        phone = number.text
        await number.delete()
        confirm = await bot.ask(chat.id, f'`شماره شما "{phone}" هستش درسته؟? (ص/غ):` \n\nاگه درسته: `ص`\nاگه غلطه: `غ`')
        if await is_cancel(msg, confirm.text):
            return
        if "ص" in confirm.text:
            break
    try:
        client = Client("my_account", api_id=api_id, api_hash=api_hash)
    except Exception as e:
        await bot.send_message(chat.id ,f"**ارور:** `{str(e)}`\n/start رو بفرست تا دوباره شروع کنیم.")
        return
    try:
        await client.connect()
    except ConnectionError:
        await client.disconnect()
        await client.connect()
    try:
        code = await client.send_code(phone)
        await asyncio.sleep(1)
    except FloodWait as e:
        await msg.reply(f"شما فلود ویت خوردید به مدت {e.x} ثانیه")
        return
    except ApiIdInvalid:
        await msg.reply("API ID و API Hash اشتباهن.\n\n/start رو بفرست تا دوباره شروع کنیم.")
        return
    except PhoneNumberInvalid:
        await msg.reply("شماره شما اشتباهه.\n\n/start رو بفرست تا دوباره شروع کنیم.")
        return
    try:
        otp = await bot.ask(
            chat.id, ("کد ورود برای شما ارسال شد, "
                      "کد را به صورت `1 2 3 4 5` ارسال کنید. __(بین هر رقم یک فاصله بیندازید!)__ \n\n"
                      "اگر برای شما کدی ارسال نشده دستور /restart رو بفرستید و دوباره مراحل رو با دستور /start شروع کنید.\n"
                      "دستور /cancel رو برای لغو عملیات بفرست."), timeout=300)

    except TimeoutError:
        await msg.reply("محدودیت زمانی به 5 دقیقه رسید.\n/start رو بفرست تا دوباره شروع کنیم")
        return
    if await is_cancel(msg, otp.text):
        return
    otp_code = otp.text
    await otp.delete()
    try:
        await client.sign_in(phone, code.phone_code_hash, phone_code=' '.join(str(otp_code)))
    except PhoneCodeInvalid:
        await msg.reply("کد اشتباه است.\n\n/start رو بفرستید تا دوباره شروع کنیم.")
        return
    except PhoneCodeExpired:
        await msg.reply("کد منقضی شده است.\n\n/start رو بفرستید تا دوباره شروع کنیم.")
        return
    except SessionPasswordNeeded:
        try:
            two_step_code = await bot.ask(
                chat.id, 
                "اکانت شما دارای تایید دو مرحله ای میباشد.\nلطفا پسورد خود را وارد کنید.\n\nبرای لغو عملیات /cancel رو بفرستید.",
                timeout=300
            )
        except TimeoutError:
            await msg.reply("`محدودیت زمانی به 5 دقیقه رسید.\n\n/start رو بفرستید تا دوباره شروع کنیم.`")
            return
        if await is_cancel(msg, two_step_code.text):
            return
        new_code = two_step_code.text
        await two_step_code.delete()
        try:
            await client.check_password(new_code)
        except Exception as e:
            await msg.reply(f"**ارور:** `{str(e)}`")
            return
    except Exception as e:
        await bot.send_message(chat.id ,f"**ارور:** `{str(e)}`")
        return
    try:
        session_string = await client.export_session_string()
        await client.send_message("me", f"#PYROGRAM #STRING_SESSION\n\n```{session_string}``` \n\nBy [@PyroSSGenBot](tg://openmessage?user_id=2120893508) \nتوسط @M4hbod")
        await client.disconnect()
        text = "استرینگ سشن تولید شد.\nدکمه زیر رو بزنید."
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="📑سشن استرینگ", url=f"tg://openmessage?user_id={chat.id}")]]
        )
        await bot.send_message(chat.id, text, reply_markup=reply_markup)
    except Exception as e:
        await bot.send_message(chat.id ,f"**ارور:** `{str(e)}`")
        return


@bot.on_message(filters.private & filters.command("restart"))
async def restart(_, msg: Message):
    await msg.reply("ربات ریستارت شد!")
    HU_APP.restart()


@bot.on_message(filters.private & filters.command("help"))
async def restart(_, msg: Message):
    out = f"""
سلام, {msg.from_user.mention}. کار من ساختن استرینگ سشن پایروگرامه \
من `STRING_SESSION` رو برای رباتی که میخوای رو بهت میدم.

به `API_ID`، `API_HASH`، شماره اکانت و کدی که برات میاد نیازه. \
که به تلگرام یا خود گوشیت اس ام اس میشه.
تو باید **کد** رو به شکل `1 2 3 4 5` بفرستی. __(بین هر رقم یک فاصله بزاری!)__

**نکته:** اگه ربات کد رو نفرستاد اول دستور /restart رو بفرست بعد دوباره دستور /start رو بفرست که از اول عملیات رو شروع کنی. 

"""
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('گروه', url='https://t.me/MakhusicSupportGroup'),
                InlineKeyboardButton('ساخته شده توسط', url='https://t.me/M4hbod')
            ],
            [
                InlineKeyboardButton('گیت‌هاب', url='https://github.com/M4hbod/Pyrogram-String-Session-Generator'),
            ]
        ]
    )
    await msg.reply(out, reply_markup=reply_markup)


async def is_cancel(msg: Message, text: str):
    if text.startswith("/cancel"):
        await msg.reply("عملیات کنسل شد.")
        return True
    return False

if __name__ == "__main__":
    bot.run()
