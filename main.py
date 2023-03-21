import json
import logging
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TELEGRAM_TOKEN = "our_bot_token"
TELEGRAM_SUPPORT_CHAT_ID = "your_chat_id"
JSON_FILE = "bip-1im-support-group.json"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def json_open_to_read():
    filepath = JSON_FILE
    with open(filepath, "r") as read_file:
        data = json.load(read_file)
    return data


def json_open_to_write(data):
    filepath = JSON_FILE
    with open(filepath, "w") as write_file:
        json.dump(data, write_file)


def json_append_thread(thread_id, user_id):
    data = json_open_to_read()
    _status = "open"
    _date_opened = time.strftime("%Y-%m-%d %H:%M:%S")
    data[thread_id] = {"user_id": user_id, "status": _status, "date_opened": _date_opened}
    json_open_to_write(data)


def json_close_thread(thread_id, closed_by_id):
    data = json_open_to_read()
    _status = "closed"
    _date_closed = time.strftime("%Y-%m-%d %H:%M:%S")
    data[thread_id]["status"] = _status
    data[thread_id]["date_closed"] = _date_closed
    data[thread_id]["closed_by"] = closed_by_id
    json_open_to_write(data)


def json_open_thread(thread_id):
    data = json_open_to_read()
    _status = "open"
    data[thread_id]["status"] = _status
    data[thread_id]["date_closed"] = ''
    data[thread_id]["closed_by"] = ''
    json_open_to_write(data)


def find_open_thread(user_id):
    status = "open"
    data = json_open_to_read()
    if data:
        _threads = {k: v for k, v in data.items() if v["status"] == status and v["user_id"] == user_id}
        if _threads:
            if len(_threads) > 1:
                logging.info("There are more than one open threads. I took the last one.")
            _thread_id = list(_threads.keys())
            _thread_id = _thread_id[len(_threads) - 1]
            return _thread_id
        else:
            return None
    else:
        return None


def find_closed_thread(user_id):
    status = "closed"
    data = json_open_to_read()
    if data:
        _threads = {k: v for k, v in data.items() if v["status"] == status and v["user_id"] == user_id}
        if _threads:
            _thread_id = list(_threads.keys())
            _thread_id = _thread_id[len(_threads) - 1]
            return _thread_id
        else:
            return None
    else:
        return None


async def create_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _data = json_open_to_read()
    _topic = await context.bot.createForumTopic(TELEGRAM_SUPPORT_CHAT_ID, name=update.effective_user.username)
    _thread_id = int(_topic.message_thread_id)
    _user_id = update.effective_user.id
    json_append_thread(_thread_id, _user_id)
    return _thread_id


async def forward_to_support_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _thread_id = find_open_thread(update.effective_user.id)
    if not _thread_id:
        _thread_id = await create_thread(update, context)

    await context.bot.forward_message(chat_id=TELEGRAM_SUPPORT_CHAT_ID, from_chat_id=update.effective_chat.id,
                                      message_id=update.effective_message.message_id, message_thread_id=_thread_id)


async def forward_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _thread_id = str(update.effective_message.message_thread_id)
    if _thread_id != 'None':
        _data = json_open_to_read()
        _user_id = int(_data[_thread_id]["user_id"])
        await context.bot.copy_message(chat_id=_user_id, from_chat_id=update.effective_chat.id,
                                       message_id=update.effective_message.message_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _thread_id = str(update.effective_message.message_thread_id)
    _closed_by_id = update.effective_user.id
    if _thread_id != 'None':
        _data = json_open_to_read()
        _is_open = _data[_thread_id]["status"] == "open"
        if _is_open:
            json_close_thread(_thread_id, _closed_by_id)
            _custom_emoji_id = '5408906741125490282'
            await context.bot.edit_forum_topic(TELEGRAM_SUPPORT_CHAT_ID, message_thread_id=_thread_id,
                                               icon_custom_emoji_id=_custom_emoji_id)
            await context.bot.close_forum_topic(TELEGRAM_SUPPORT_CHAT_ID, message_thread_id=_thread_id)

            _user_id = int(_data[_thread_id]["user_id"])
            await context.bot.send_message(chat_id=_user_id,
                                           text="Your ticket has been closed by a support person. "
                                                "Press /open to continue if the issue is not resolved. "
                                                "Write a message to open a new ticket.")


async def open_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _thread_id = find_open_thread(update.effective_user.id)
    if not _thread_id:
        _thread_id = find_closed_thread(update.effective_user.id)
        if _thread_id:
            json_open_thread(_thread_id)
            await context.bot.reopen_forum_topic(TELEGRAM_SUPPORT_CHAT_ID, message_thread_id=_thread_id)
            await context.bot.send_message(chat_id=update.effective_user.id, text="Your ticket has been reopened. "
                                                                                  "Write a message to continue.")
            _custom_emoji_id = ''
            await context.bot.edit_forum_topic(TELEGRAM_SUPPORT_CHAT_ID, message_thread_id=_thread_id,
                                               icon_custom_emoji_id=_custom_emoji_id)
        else:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="You don't have any tickets to open. "
                                                "Write a message to open a new ticket.")
    else:
        await context.bot.send_message(chat_id=update.effective_user.id, text="You already have an open ticket. "
                                                                              "Write a message to continue.")


def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    start_handler = CommandHandler('start', start)
    close_ticket_handler = CommandHandler('close', close_ticket, filters.Chat(int(TELEGRAM_SUPPORT_CHAT_ID)))
    open_ticket_handler = CommandHandler('open', open_ticket, filters.ChatType.PRIVATE)
    user_message_handler = MessageHandler(filters.ChatType.PRIVATE, forward_to_support_chat)
    chat_message_handler = MessageHandler(filters.Chat(int(TELEGRAM_SUPPORT_CHAT_ID)) & ~filters.StatusUpdate.ALL,
                                          forward_to_user)
    # chat_message_handler = MessageHandler(filters.ChatType.SUPERGROUP, forward_to_user)

    application.add_handler(start_handler)
    application.add_handler(close_ticket_handler)
    application.add_handler(open_ticket_handler)
    application.add_handler(user_message_handler)
    application.add_handler(chat_message_handler)

    application.run_polling()
    # application.run_webhook()


if __name__ == '__main__':
    main()
