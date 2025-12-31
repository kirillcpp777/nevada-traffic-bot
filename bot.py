import logging
import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.error import TimedOut, NetworkError

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки (Замініть 'ВАШ_ТОКЕН' на реальний, якщо не використовуєте Environment Variables)
ADMIN_ID = int(os.getenv('ADMIN_ID', '5553120504'))
BOT_TOKEN = os.getenv('BOT_TOKEN', '8421620746:AAErfrKNdODpr4jgaMB5-FZ6xDAJItrBKR8') 
TEAM_LINK = os.getenv('TEAM_LINK', 'https://t.me/+h4CjQYaOkIhmZjFi')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+47T4lfz3KutlNDQy')

DB_FILE = 'applications.json'

MENU, NAME, EXPERIENCE, TEAM_TYPE, TRAFFIC_VOLUME, CONFIRM = range(6)

# --- Функции БД (без змін) ---
def load_applications():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки БД: {e}")
        return []

def save_application(application_data):
    try:
        applications = load_applications()
        app_id = len(applications) + 1
        application_data['application_id'] = app_id
        applications.append(application_data)
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(applications, f, ensure_ascii=False, indent=2)
        return app_id
    except Exception as e:
        logger.error(f"Ошибка сохранения в БД: {e}")
        return None

def update_application_status(user_id, status):
    try:
        applications = load_applications()
        for app in reversed(applications):
            if app['user_id'] == user_id:
                app['status'] = status
                app['status_updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(applications, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка обновления статуса: {e}")

def get_stats():
    applications = load_applications()
    return {
        'total': len(applications),
        'accepted': sum(1 for app in applications if app.get('status') == 'accepted'),
        'rejected': sum(1 for app in applications if app.get('status') == 'rejected'),
        'pending': sum(1 for app in applications if app.get('status') == 'pending')
    }

# --- Обработчики (Ваші оригінальні функції) ---
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    s = get_stats()
    stats_text = (f"📊 <b>СТАТИСТИКА NEVADA TRAFFIC</b>\n{'='*30}\n\n"
                  f"📝 Всего заявок: <b>{s['total']}</b>\n✅ Принято: <b>{s['accepted']}</b>\n"
                  f"❌ Отклонено: <b>{s['rejected']}</b>\n⏳ В обработке: <b>{s['pending']}</b>")
    await update.message.reply_text(stats_text, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Очищуємо дані користувача, щоб почати "з чистого листа"
    context.user_data.clear()
    
    keyboard = [['Подать заявку']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Привет! 👋\n\nЯ бот команды NEVADA TRAFFIC. Новые участники проходят отбор.\n"
        "Нажмите кнопку ниже, чтобы подать заявку.",
        reply_markup=reply_markup
    )
    # Повертаємо стан MENU, щоб бот знав, що ми на початку
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Подать заявку":
        await update.message.reply_text("Укажите ваше имя:", reply_markup=ReplyKeyboardRemove())
        return NAME
    return MENU

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Есть опыт в арбитраже?", 
                                  reply_markup=ReplyKeyboardMarkup([['Да'], ['Нет']], one_time_keyboard=True, resize_keyboard=True))
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['experience'] = update.message.text
    await update.message.reply_text("Формат работы:", 
                                  reply_markup=ReplyKeyboardMarkup([['Соло'], ['Команда']], one_time_keyboard=True, resize_keyboard=True))
    return TEAM_TYPE

async def get_team_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['team_type'] = update.message.text
    await update.message.reply_text("Сколько трафика (дейли) вы проливаете? (Введите число):")
    return TRAFFIC_VOLUME

async def get_traffic_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Пожалуйста, введите только число.")
        return TRAFFIC_VOLUME
    context.user_data['traffic_volume'] = text
    await update.message.reply_text("Проверьте данные и отправьте заявку.", 
                                  reply_markup=ReplyKeyboardMarkup([['ОТПРАВИТЬ ЗАЯВКУ']], resize_keyboard=True))
    return CONFIRM

async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "ОТПРАВИТЬ ЗАЯВКУ":
        user_id = update.effective_user.id
        username = update.effective_user.username or 'нет'
        app_record = {
            'user_id': user_id, 'username': username, 'name': context.user_data['name'],
            'experience': context.user_data['experience'], 'team_type': context.user_data['team_type'],
            'traffic_volume': context.user_data['traffic_volume'], 'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        app_id = save_application(app_record)
        admin_text = (f"📝 <b>НОВАЯ ЗАЯВКА #{app_id}</b>\n👤 <b>Имя:</b> {app_record['name']}\n"
                      f"💼 <b>Опыт:</b> {app_record['experience']}\n💰 <b>Трафик:</b> {app_record['traffic_volume']}\n"
                      f"📱 <b>Юзер:</b> @{username} (<code>{user_id}</code>)")
        keyboard = [[InlineKeyboardButton("✅ Принять", callback_data=f"accept_{user_id}"),
                     InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")]]
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        await update.message.reply_text("✅ Заявка отправлена!", reply_markup=ReplyKeyboardMarkup([['Подать заявку']], resize_keyboard=True))
        context.user_data.clear()
        return MENU
    return CONFIRM

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id = query.data.split('_')
    user_id = int(user_id)
    if action == "accept":
        update_application_status(user_id, 'accepted')
        await context.bot.send_message(chat_id=user_id, text=f"<b>🎉 Одобрено!</b>\n\nКоманда: {TEAM_LINK}", parse_mode='HTML')
    elif action == "reject":
        update_application_status(user_id, 'rejected')
        await context.bot.send_message(chat_id=user_id, text="<b>Отклонено.</b>", parse_mode='HTML')
    await query.edit_message_text(text=f"{query.message.text}\n\nЗАКРЫТО", reply_markup=None)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardMarkup([['Подать заявку']], resize_keyboard=True))
    context.user_data.clear()
    return MENU

# Глобальний обробник помилок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, (TimedOut, NetworkError)):
        logger.warning(f"Мережева затримка: {context.error}")
    else:
        logger.error("Помилка:", exc_info=context.error)

def main():
    # Оптимізовані таймаути: не ставимо занадто великі, щоб бот не "тупив"
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(10.0)
        .read_timeout(10.0)
        .build()
    )
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)], # Тепер старт працює завжди
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
            TEAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_team_type)],
            TRAFFIC_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_traffic_volume)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_application)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
        allow_reentry=True # КЛЮЧОВА ФІШКА: дозволяє перезапуск діалогу
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(admin_button_handler))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_error_handler(error_handler)
    
    print("🚀 Бот запущен!")
    # Використовуємо звичайний polling без екстремальних налаштувань
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
