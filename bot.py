import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.error import TimedOut, NetworkError
from html import escape

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
# Добавляем ваш ID в список через запятую или используем список в коде
PRIMARY_ADMIN = int(os.getenv('ADMIN_ID', '5553120504'))
SECOND_ADMIN = 5309961138  # Ваш ID
ADMIN_LIST = [PRIMARY_ADMIN, SECOND_ADMIN]

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
TEAM_LINK = os.getenv('TEAM_LINK', 'https://t.me/+h4CjQYaOkIhmZjFi')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+47T4lfz3KutlNDQy')

MENU, NAME, EXPERIENCE, TEAM_TYPE, TRAFFIC_VOLUME, CONFIRM = range(6)

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            username TEXT,
            name TEXT,
            experience TEXT,
            team_type TEXT,
            traffic_volume TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status_updated_at TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def save_application(data):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO applications (user_id, username, name, experience, team_type, traffic_volume)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    ''', (data['user_id'], data['username'], data['name'], data['experience'], 
          data['team_type'], data['traffic_volume']))
    app_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return app_id

def update_application_status(user_id, status):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        UPDATE applications 
        SET status = %s, status_updated_at = NOW() 
        WHERE user_id = %s AND status = 'pending'
    ''', (status, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_stats():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute('SELECT status, COUNT(*) as count FROM applications GROUP BY status')
    rows = cur.fetchall()
    stats = {'total': 0, 'accepted': 0, 'rejected': 0, 'pending': 0}
    for row in rows:
        stats[row['status']] = row['count']
        stats['total'] += row['count']
    cur.close()
    conn.close()
    return stats

# --- ХЕНДЛЕРЫ БОТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [['Подать заявку']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! 👋\n\nЯ бот команды NEVADA TRAFFIC.\n\n"
        "❗ **ВАЖНО:** Указывайте только настоящие данные.\n"
        "Нажми кнопку 'Подать заявку'",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Подать заявку":
        await update.message.reply_text(
            "Начинаем заполнение анкеты.\n\n**Укажи свое имя:**", 
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
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
    await update.message.reply_text("Сколько трафика (за неделю) вы проливаете? (Введите число):")
    return TRAFFIC_VOLUME

async def get_traffic_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Пожалуйста, введите только число.")
        return TRAFFIC_VOLUME
    context.user_data['traffic_volume'] = text
    await update.message.reply_text("Всё верно? Отправляй заявку.", 
        reply_markup=ReplyKeyboardMarkup([['ОТПРАВИТЬ ЗАЯВКУ']], resize_keyboard=True))
    return CONFIRM

async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "ОТПРАВИТЬ ЗАЯВКУ":
        user_id = update.effective_user.id
        username = escape(update.effective_user.username or 'нет')
        name = escape(context.user_data['name'])
        experience = escape(context.user_data['experience'])
        traffic = escape(context.user_data['traffic_volume'])
        
        app_data = {
            'user_id': user_id, 'username': username, 'name': name,
            'experience': experience, 'team_type': context.user_data['team_type'],
            'traffic_volume': traffic
        }
        
        app_id = save_application(app_data)
        
        admin_text = (
            f"📝 <b>НОВАЯ ЗАЯВКА #{app_id}</b>\n"
            f"👤 <b>Имя:</b> {name}\n"
            f"💼 <b>Опыт:</b> {experience}\n"
            f"💰 <b>Трафик:</b> {traffic}\n"
            f"📱 <b>Юзер:</b> @{username} (<code>{user_id}</code>)"
        )
        
        keyboard = [[InlineKeyboardButton("✅ Принять", callback_data=f"accept_{user_id}"),
                     InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")]]
        
        # Рассылка всем админам
        for admin_id in ADMIN_LIST:
            try:
                await context.bot.send_message(
                    chat_id=admin_id, 
                    text=admin_text, 
                    reply_markup=InlineKeyboardMarkup(keyboard), 
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Ошибка отправки админу {admin_id}: {e}")
        
        await update.message.reply_text("✅ Заявка отправлена! Ожидайте решения.", reply_markup=ReplyKeyboardMarkup([['Подать заявку']], resize_keyboard=True))
        context.user_data.clear()
        return MENU
    return CONFIRM

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_user = update.effective_user
    await query.answer()
    
    data = query.data.split('_')
    action, user_id = data[0], int(data[1])
    
    status_text = ""
    if action == "accept":
        update_application_status(user_id, 'accepted')
        status_text = "✅ ПРИНЯТА"
        await context.bot.send_message(chat_id=user_id, text=f"<b>🎉 Одобрено!</b>\n\nКоманда: {TEAM_LINK}\n📢 Канал: {CHANNEL_LINK}", parse_mode='HTML')
    elif action == "reject":
        update_application_status(user_id, 'rejected')
        status_text = "❌ ОТКЛОНЕНА"
        await context.bot.send_message(chat_id=user_id, text="<b>Отклонено.</b>", parse_mode='HTML')
    
    # Обновляем сообщение у того админа, который нажал кнопку
    await query.edit_message_text(
        text=f"{query.message.text}\n\n{status_text}\nАдмином: @{admin_user.username or admin_user.id}", 
        reply_markup=None,
        parse_mode='HTML'
    )

    # Отправляем уведомление (лог) второму админу о действии первого
    for admin_id in ADMIN_LIST:
        if admin_id != admin_user.id:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🔔 <b>Лог действий:</b>\nАдмин @{admin_user.username or admin_user.id} изменил статус заявки пользователя <code>{user_id}</code> на {status_text}",
                    parse_mode='HTML'
                )
            except:
                pass

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_LIST: return
    s = get_stats()
    text = (f"📊 **СТАТИСТИКА**\n\n📝 Всего: {s['total']}\n✅ Принято: {s['accepted']}\n"
            f"❌ Отклонено: {s['rejected']}\n⏳ В очереди: {s['pending']}")
    await update.message.reply_text(text, parse_mode='Markdown')

def main():
    init_db()
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
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(admin_button_handler))
    application.add_handler(CommandHandler('stats', stats_command))
    
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
