import sqlite3
import logging
import time
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

load_dotenv()  # load environment variables from .env file

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_SUPPORT_CHAT_ID = os.environ['TELEGRAM_SUPPORT_CHAT_ID']
DB_FILE = os.environ['DB_FILE']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS threads
                       (id INTEGER PRIMARY KEY,
                       user_id INTEGER,
                       status TEXT,
                       date_opened TEXT,
                       date_closed TEXT,
                       closed_by INTEGER)''')
        conn.commit()

def insert_thread(thread_id, user_id, status):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO threads (id, user_id, status, date_opened) VALUES (?, ?, ?, datetime('now'))",
                    (thread_id, user_id, status))
        conn.commit()

def update_thread_status(thread_id, status, closed_by=None):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        if closed_by:
            cur.execute("UPDATE threads SET status = ?, date_closed = datetime('now'), closed_by = ? WHERE id = ?",
                        (status, closed_by, thread_id))
        else:
            cur.execute("UPDATE threads SET status = ? WHERE id = ?", (status, thread_id))
        conn.commit()

def find_thread(user_id, status):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM threads WHERE user_id = ? AND status = ? ORDER BY id DESC", (user_id, status))
        result = cur.fetchone()
    return result if result else None

async def create_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _topic = await context.bot.createForumTopic(TELEGRAM_SUPPORT_CHAT_ID, name=update.effective_user.username)
    _thread_id = int(_topic.message_thread_id)
    _user_id = update.effective_user.id
    insert_thread(_thread_id, _user_id, status="open")
    return _thread_id

async def forward_to_support_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    thread_info = find_thread(update.effective_user.id, status="open")

    if not thread_info:
        _thread_id = await create_thread(update, context)
    else:
        _thread_id = thread_info[0]

    await context.bot.forward_message(chat_id=TELEGRAM_SUPPORT_CHAT_ID, from_chat_id=update.effective_chat.id,
                                      message_id=update.effective_message.message_id, message_thread_id=_thread_id)

async def forward_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _thread_id = str(update.effective_message.message_thread_id)
    if _thread_id != 'None':
        if find_thread(update.effective_user.id, status="open"):
            await context.bot.copy_message(chat_id=update.effective_user.id, from_chat_id=update.effective_chat.id,
                                           message_id=update.effective_message.message_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _thread_id = str(update.effective_message.message_thread_id)
    _closed_by_id = update.effective_user.id
    if _thread_id != 'None':
        if find_thread(update.effective_user.id, status="open"):
            update_thread_status(_thread_id, status="closed", closed_by=_closed_by_id)
            _custom_emoji_id = '5408906741125490282'
            await context.bot.edit_forum_topic(TELEGRAM_SUPPORT_CHAT_ID, message_thread_id=_thread_id,
                                               icon_custom_emoji_id=_custom_emoji_id)
            await context.bot.close_forum_topic(TELEGRAM_SUPPORT_CHAT_ID, message_thread_id=_thread_id)

            if find_thread(update.effective_user.id, status="closed"):
                await context.bot.send_message(chat_id=update.effective_user.id,
                                               text="Your ticket has been closed by a support person. "
                                                    "Press /open to continue if the issue is not resolved. "
                                                    "Write a message to open a new ticket.")

async def open_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not find_thread(update.effective_user.id, status="open"):
        thread_info = find_thread(update.effective_user.id, status="closed")
        if thread_info:
            _thread_id = thread_info[0]
            update_thread_status(_thread_id, status="open")
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

    application.add_handler(start_handler)
    application.add_handler(close_ticket_handler)
    application.add_handler(open_ticket_handler)
    application.add_handler(user_message_handler)
    application.add_handler(chat_message_handler)

    application.run_polling()

# Initialize database
init_db()

if __name__ == '__main__':
    main()