import logging
import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки (Рекомендуется использовать переменные окружения)
ADMIN_ID = int(os.getenv('ADMIN_ID', '5553120504'))
BOT_TOKEN = os.getenv('BOT_TOKEN', 'ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ')
TEAM_LINK = os.getenv('TEAM_LINK', 'https://t.me/+h4CjQYaOkIhmZjFi')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+47T4lfz3KutlNDQy')

DB_FILE = 'applications.json'

MENU, NAME, EXPERIENCE, TEAM_TYPE, TRAFFIC_VOLUME, CONFIRM = range(6)

# --- Функции для работы с базой данных ---

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
        # Генерируем ID на основе количества записей
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

# --- Обработчики команд ---

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    s = get_stats()
    stats_text = (
        f"📊 <b>СТАТИСТИКА NEVADA TRAFFIC</b>\n"
        f"{'='*30}\n\n"
        f"📝 Всего заявок: <b>{s['total']}</b>\n"
        f"✅ Принято: <b>{s['accepted']}</b>\n"
        f"❌ Отклонено: <b>{s['rejected']}</b>\n"
        f"⏳ В обработке: <b>{s['pending']}</b>\n"
    )
    await update.message.reply_text(stats_text, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Подать заявку']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! 👋\n\nЯ бот команды NEVADA TRAFFIC. Новые участники проходят отбор.\n"
        "Нажмите кнопку ниже, чтобы подать заявку.",
        reply_markup=reply_markup
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Подать заявку":
        await update.message.reply_text("Укажите ваше имя:", reply_markup=ReplyKeyboardRemove())
        return NAME
    return MENU

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    keyboard = [['Да'], ['Нет']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Есть опыт в арбитраже?", reply_markup=reply_markup)
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['experience'] = update.message.text
    keyboard = [['Соло'], ['Команда']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Формат работы:", reply_markup=reply_markup)
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
    keyboard = [['ОТПРАВИТЬ ЗАЯВКУ']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Проверьте данные и отправьте заявку.", reply_markup=reply_markup)
    return CONFIRM

async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "ОТПРАВИТЬ ЗАЯВКУ":
        user_id = update.effective_user.id
        username = update.effective_user.username or 'нет'
        
        app_record = {
            'user_id': user_id,
            'username': username,
            'name': context.user_data['name'],
            'experience': context.user_data['experience'],
            'team_type': context.user_data['team_type'],
            'traffic_volume': context.user_data['traffic_volume'],
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        app_id = save_application(app_record)
        
        admin_text = (
            f"📝 <b>НОВАЯ ЗАЯВКА #{app_id}</b>\n"
            f"👤 <b>Имя:</b> {app_record['name']}\n"
            f"💼 <b>Опыт:</b> {app_record['experience']}\n"
            f"👥 <b>Тип:</b> {app_record['team_type']}\n"
            f"💰 <b>Трафик:</b> {app_record['traffic_volume']}\n"
            f"📱 <b>Юзер:</b> @{username} (<code>{user_id}</code>)"
        )
        
        keyboard = [[
            InlineKeyboardButton("✅ Принять", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
        ]]
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
        await update.message.reply_text(
            "✅ Заявка отправлена! Ожидайте решения модератора.",
            reply_markup=ReplyKeyboardMarkup([['Подать заявку']], resize_keyboard=True)
        )
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
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"<b>🎉 Ваша заявка одобрена!</b>\n\nКоманда: {TEAM_LINK}\nКанал: {CHANNEL_LINK}",
                parse_mode='HTML'
            )
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ ОДОБРЕНО", reply_markup=None)
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
            
    elif action == "reject":
        update_application_status(user_id, 'rejected')
        try:
            await context.bot.send_message(chat_id=user_id, text="<b>К сожалению, ваша заявка отклонена.</b>", parse_mode='HTML')
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ ОТКЛОНЕНО", reply_markup=None)
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardMarkup([['Подать заявку']], resize_keyboard=True))
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
    application.add_handler(CommandHandler('stats', stats_command))
    
    print("🚀 Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
