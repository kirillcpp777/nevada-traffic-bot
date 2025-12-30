import logging
import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Беремо з environment variables
ADMIN_ID = int(os.getenv('ADMIN_ID', '5553120504'))
BOT_TOKEN = os.getenv('BOT_TOKEN', '8421620746:AAErfrKNdODpr4jgaMB5-FZ6xDAJItrBKR8')
TEAM_LINK = os.getenv('TEAM_LINK', 'https://t.me/+h4CjQYaOkIhmZjFi')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+47T4lfz3KutlNDQy')

# Файл для збереження заявок
DB_FILE = 'applications.json'

MENU, NAME, EXPERIENCE, TEAM_TYPE, TRAFFIC_VOLUME, CONFIRM = range(6)

# Функції для роботи з базою даних
def load_applications():
    """Завантажує заявки з JSON файлу"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Помилка завантаження БД: {e}")
        return []

def save_application(application_data):
    """Зберігає нову заявку в JSON файл"""
    try:
        applications = load_applications()
        applications.append(application_data)
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(applications, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Заявка #{len(applications)} збережена в БД")
        return len(applications)
    except Exception as e:
        logger.error(f"Помилка збереження в БД: {e}")
        return None

def update_application_status(user_id, status):
    """Оновлює статус заявки"""
    try:
        applications = load_applications()
        
        for app in reversed(applications):
            if app['user_id'] == user_id:
                app['status'] = status
                app['status_updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(applications, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Статус заявки user_id={user_id} оновлено на {status}")
    except Exception as e:
        logger.error(f"Помилка оновлення статусу: {e}")

def get_stats():
    """Отримує статистику заявок"""
    applications = load_applications()
    total = len(applications)
    accepted = sum(1 for app in applications if app.get('status') == 'accepted')
    rejected = sum(1 for app in applications if app.get('status') == 'rejected')
    pending = sum(1 for app in applications if app.get('status') == 'pending')
    
    return {
        'total': total,
        'accepted': accepted,
        'rejected': rejected,
        'pending': pending
    }

# Команда для перегляду статистики (тільки для адміна)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує статистику заявок"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    stats = get_stats()
    
    stats_text = (
        f"📊 <b>СТАТИСТИКА NEVADA TRAFFIC</b>\n"
        f"{'='*30}\n\n"
        f"📝 Всього заявок: <b>{stats['total']}</b>\n"
        f"✅ Прийнято: <b>{stats['accepted']}</b>\n"
        f"❌ Відхилено: <b>{stats['rejected']}</b>\n"
        f"⏳ В обробці: <b>{stats['pending']}</b>\n"
    )
    
    await update.message.reply_text(stats_text, parse_mode='HTML')

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
        
        # Зберігаємо в базу даних
        application_record = {
            'application_id': None,  # Буде встановлено після збереження
            'user_id': user_id,
            'username': username,
            'name': context.user_data['name'],
            'experience': context.user_data['experience'],
            'team_type': context.user_data['team_type'],
            'traffic_volume': context.user_data['traffic_volume'],
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status_updated_at': None
        }
        
        app_id = save_application(application_record)
        
        application_data = (
            f"📝 <b>НОВАЯ ЗАЯВКА #{app_id} | NEVADA TRAFFIC</b>\n"
            f"👤 <b>Имя:</b> {context.user_data['name']}\n"
            f"💼 <b>Опыт:</b> {context.user_data['experience']}\n"
            f"👥 <b>Тип:</b> {context.user_data['team_type']}\n"
            f"💰 <b>Объем трафика/день:</b> {context.user_data['traffic_volume']}\n"
            f"🆔 <b>User ID:</b> {user_id}\n"
            f"📱 <b>Username:</b> @{username}\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
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
            logger.info(f"Заявка #{app_id} отправлена администратору от {context.user_data['name']}")
        except Exception as e:
            logger.error(f"Ошибка отправки админу: {e}")
        
        keyboard = [['Подать заявку']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"✅ Спасибо, наш модератор рассмотрит твою заявку #{app_id} и напишет тебе!\n\n"
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
        # Оновлюємо статус в БД
        update_application_status(user_id, 'accepted')
        
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
        # Оновлюємо статус в БД
        update_application_status(user_id, 'rejected')
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="<b>😔 К сожалению, твоя заявка не прошла отбор.</b>\n\n"
                     "<b>Спасибо за интерес к команде NEVADA TRAFFIC!</b>\n",
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
    
    # Команда для статистики (тільки для адміна)
    application.add_handler(CommandHandler('stats', stats_command))
    
    logger.info("🤖 Бот запущен!")
    print("\n" + "="*50)
    print("🚀 БОТ NEVADA TRAFFIC РАБОТАЕТ!")
    print(f"👤 ID администратора: {ADMIN_ID}")
    print(f"💾 База данных: {DB_FILE}")
    print("="*50 + "\n")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
