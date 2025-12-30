import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Беремо з environment variables
ADMIN_ID = int(os.getenv('ADMIN_ID', '5553120504'))
BOT_TOKEN = os.getenv('BOT_TOKEN', '8421620746:AAErfrKNdODpr4jgaMB5-FZ6xDAJItrBKR8')
TEAM_LINK = os.getenv('TEAM_LINK', 'https://t.me/+h4CjQYaOkIhmZjFi')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+47T4lfz3KutlNDQy')

MENU, NAME, EXPERIENCE, TEAM_TYPE, TRAFFIC_VOLUME, CONFIRM = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Подать заявку']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я чат-бот команды NEVADA TRAFFIC по арбитражу трафика. Если ты хочешь "
        "присоединиться к нашей команде, оставь заявку.",
        reply_markup=reply_markup
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "Подать заявку":
        await update.message.reply_text(
            "Спасибо за твой интерес к нашей команде.\n"
            "Укажи свое имя.",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME
    
    return MENU

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    
    keyboard = [['Нет'], ['Да']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text("Есть опыт?", reply_markup=reply_markup)
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['experience'] = update.message.text
    
    keyboard = [['Соло'], ['Команда']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text("Ты соло траффер или команда?", reply_markup=reply_markup)
    return TEAM_TYPE

async def get_team_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['team_type'] = update.message.text
    
    await update.message.reply_text(
        "Сколько ты примерно переливаешь трафика в день.\n"
        "Введи примерное число.",
        reply_markup=ReplyKeyboardRemove()
    )
    return TRAFFIC_VOLUME

async def get_traffic_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if not text.isdigit():
        await update.message.reply_text("Пожалуйста, введи число.\nНапример: 500 или 0")
        return TRAFFIC_VOLUME
    
    context.user_data['traffic_volume'] = text
    
    keyboard = [['ПОДАТЬ ЗАЯВКУ']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("Нажми кнопку для отправки заявки:", reply_markup=reply_markup)
    return CONFIRM

async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "ПОДАТЬ ЗАЯВКУ":
        user_id = update.effective_user.id
        username = update.effective_user.username if update.effective_user.username else 'нет'
        
        application_data = (
            f"📝 <b>НОВАЯ ЗАЯВКА | NEVADA TRAFFIC</b>\n"
            f"{'='*40}\n\n"
            f"👤 <b>Имя:</b> {context.user_data['name']}\n"
            f"💼 <b>Опыт:</b> {context.user_data['experience']}\n"
            f"👥 <b>Тип:</b> {context.user_data['team_type']}\n"
            f"💰 <b>Объем трафика/день:</b> {context.user_data['traffic_volume']}\n"
            f"🆔 <b>User ID:</b> {user_id}\n"
            f"📱 <b>Username:</b> @{username}\n"
            f"\n{'='*40}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Принять", callback_data=f"accept_{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=application_data,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            logger.info(f"Заявка отправлена администратору от {context.user_data['name']}")
        except Exception as e:
            logger.error(f"Ошибка отправки админу: {e}")
        
        keyboard = [['Подать заявку']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "✅ Спасибо, наш модератор рассмотрит твою заявку и напишет тебе!\n\n"
            "Желаю хорошего залива! 🚀💰",
            reply_markup=reply_markup
        )
        
        context.user_data.clear()
        return MENU
    
    return CONFIRM

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, user_id = data.split('_')
    user_id = int(user_id)
    
    if action == "accept":
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"<b>🎉 Поздравляем! Твоя заявка принята!</b>\n\n"
                     f"<b>Вот ссылка на команду:</b>\n"
                     f"{TEAM_LINK}\n\n"
                     f"<b>📢 Наш канал (обязательно подпишись):</b>\n"
                     f"{CHANNEL_LINK}\n\n"
                     f"<b>Добро пожаловать в команду NEVADA TRAFFIC! 🚀</b>",
                parse_mode='HTML'
            )
            await query.edit_message_text(
                text=query.message.text + "\n\n✅ ЗАЯВКА ПРИНЯТА",
                reply_markup=None
            )
        except Exception as e:
            await query.edit_message_text(text=query.message.text + f"\n\n❌ Ошибка: {e}")
    
    elif action == "reject":
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="<b>😔 К сожалению, твоя заявка не прошла отбор.</b>\n\n"
                     "<b>Спасибо за интерес к команде NEVADA TRAFFIC!</b>\n"
                     "<b>Ты можешь попробовать еще раз позже.</b>",
                parse_mode='HTML'
            )
            await query.edit_message_text(
                text=query.message.text + "\n\n❌ ЗАЯВКА ОТКЛОНЕНА",
                reply_markup=None
            )
        except Exception as e:
            await query.edit_message_text(text=query.message.text + f"\n\n❌ Ошибка: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Подать заявку']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("Действие отменено.", reply_markup=reply_markup)
    context.user_data.clear()
    return MENU

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
            TEAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_team_type)],
            TRAFFIC_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_traffic_volume)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_application)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(admin_button_handler))
    
    logger.info("🤖 Бот запущен!")
    print("\n" + "="*50)
    print("🚀 БОТ NEVADA TRAFFIC РАБОТАЕТ!")
    print(f"👤 ID администратора: {ADMIN_ID}")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print("="*50 + "\n")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
