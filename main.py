import logging

logger = logging.getLogger(__name__)

API_TOKEN = '6008733112:AAFgT0QyG4-R_lvOV3yNC_pkXd6heg0gpow'

# Replace YOUR_API_TOKEN with the API token provided by BotFather
bot = telegram.Bot(token='YOUR_API_TOKEN')

# Replace YOUR_GROUP_ID with the ID of the Telegram group where you want to create the topic
group_id = '-1001896478530'


# Define a function to handle the /addtopic command
def handle_add_topic_command(update, context):
    text = update.message.text.split(maxsplit=1)
    if len(text) == 2:
        topic_name = text[1]
        try:
            # Create a new topic in the group
            topic_id = bot.create_forum_topic(group_id, title=topic_name)
            update.message.reply_text(f'Topic "{topic_name}" created.')
        except BadRequest as e:
            update.message.reply_text(f'Error creating topic: {e.message}')
    else:
        update.message.reply_text('Usage: /addtopic <topic name>')


def main() -> None:
    updater = Updater(API_TOKEN)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Echo any message that is not a command
    dispatcher.add_handler(MessageHandler(~Filters.command, handle_add_topic_command))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
