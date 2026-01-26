import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from html import escape

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
PRIMARY_ADMIN = int(os.getenv('ADMIN_ID', '5553120504'))
SECOND_ADMIN = 5553120504
ADMIN_LIST = [PRIMARY_ADMIN, SECOND_ADMIN]

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
TEAM_LINK = os.getenv('TEAM_LINK', 'https://t.me/+h4CjQYaOkIhmZjFi')
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+47T4lfz3KutlNDQy')

MENU, NAME, EXPERIENCE, TEAM_TYPE, TRAFFIC_VOLUME, SOURCE, CONFIRM = range(7)

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
            source TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status_updated_at TIMESTAMP
        )
    ''')
    cur.execute('''
        DO $$ BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='applications' AND column_name='source') THEN 
                ALTER TABLE applications ADD COLUMN source TEXT; 
            END IF; 
        END $$;
    ''')
    conn.commit()
    cur.close()
    conn.close()

def save_application(data):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO applications (user_id, username, name, experience, team_type, traffic_volume, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (data['user_id'], data['username'], data['name'], data['experience'], 
          data['team_type'], data['traffic_volume'], data['source']))
    app_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return app_id

def update_application_status(user_id, status):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status = %s, status_updated_at = NOW() WHERE user_id = %s AND status = 'pending'", (status, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_application_status(user_id):
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute('SELECT status FROM applications WHERE user_id = %s ORDER BY created_at DESC LIMIT 1', (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['status'] if row else None

# --- ХЕНДЛЕРЫ БОТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [['Подать заявку']]
    await update.message.reply_text(
        "Привет! 👋\n\nЯ бот команды NEVADA TRAFFIC.\n\nНажми кнопку 'Подать заявку'",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Подать заявку":
        await update.message.reply_text("Укажи свое имя:", reply_markup=ReplyKeyboardRemove())
        return NAME
    return MENU

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    keyboard = [[InlineKeyboardButton("Да", callback_data="exp_yes"), InlineKeyboardButton("Нет", callback_data="exp_no")]]
    await update.message.reply_text("Есть опыт в арбитраже? (Нажми кнопку или напиши)", reply_markup=InlineKeyboardMarkup(keyboard))
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем: нажата кнопка или прислан текст
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        context.user_data['experience'] = "Да" if query.data == "exp_yes" else "Нет"
        message_func = query.edit_message_text
    else:
        context.user_data['experience'] = update.message.text
        message_func = update.message.reply_text

    keyboard = [[InlineKeyboardButton("Соло", callback_data="team_solo"), InlineKeyboardButton("Команда", callback_data="team_group")]]
    await message_func("Формат работы:", reply_markup=InlineKeyboardMarkup(keyboard))
    return TEAM_TYPE

async def get_team_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        context.user_data['team_type'] = "Соло" if query.data == "team_solo" else "Команда"
        message_func = query.edit_message_text
    else:
        context.user_data['team_type'] = update.message.text
        message_func = update.message.reply_text
    
    keyboard = [
        [InlineKeyboardButton("0", callback_data="vol_0"), InlineKeyboardButton("Меньше 5", callback_data="vol_lt5")],
        [InlineKeyboardButton("5-10", callback_data="vol_5-10"), InlineKeyboardButton("Больше 15", callback_data="vol_gt15")]
    ]
    await message_func("Сколько трафика (за неделю) вы проливаете?", reply_markup=InlineKeyboardMarkup(keyboard))
    return TRAFFIC_VOLUME

async def get_traffic_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        volumes = {"vol_0": "0", "vol_lt5": "Меньше 5", "vol_5-10": "5-10", "vol_gt15": "Больше 15"}
        context.user_data['traffic_volume'] = volumes.get(query.data, "0")
        message_func = query.edit_message_text
    else:
        context.user_data['traffic_volume'] = update.message.text
        message_func = update.message.reply_text
    
    await message_func("Откуда ты о нас узнал?")
    return SOURCE

async def get_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['source'] = update.message.text
    summary = (
        f"<b>Проверь данные:</b>\n\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"💼 Опыт: {context.user_data['experience']}\n"
        f"👥 Формат: {context.user_data['team_type']}\n"
        f"💰 Трафик: {context.user_data['traffic_volume']}\n"
        f"ℹ️ Источник: {context.user_data['source']}"
    )
    await update.message.reply_text(summary, parse_mode='HTML', reply_markup=ReplyKeyboardMarkup([['ОТПРАВИТЬ ЗАЯВКУ']], resize_keyboard=True))
    return CONFIRM

async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "ОТПРАВИТЬ ЗАЯВКУ":
        user_id = update.effective_user.id
        username = escape(update.effective_user.username or 'нет')
        
        app_data = {
            'user_id': user_id, 'username': username,
            'name': escape(context.user_data['name']),
            'experience': escape(context.user_data['experience']),
            'team_type': escape(context.user_data['team_type']),
            'traffic_volume': escape(context.user_data['traffic_volume']),
            'source': escape(context.user_data['source'])
        }
        
        app_id = save_application(app_data)
        
        admin_text = (
            f"📝 <b>НОВАЯ ЗАЯВКА #{app_id}</b>\n"
            f"👤 <b>Имя:</b> {app_data['name']}\n"
            f"💼 <b>Опыт:</b> {app_data['experience']}\n"
            f"👥 <b>Тип:</b> {app_data['team_type']}\n"
            f"💰 <b>Трафик:</b> {app_data['traffic_volume']}\n"
            f"ℹ️ <b>Источник:</b> {app_data['source']}\n"
            f"📱 <b>Юзер:</b> @{username} (<code>{user_id}</code>)"
        )
        
        admin_kb = [[InlineKeyboardButton("✅ Принять", callback_data=f"accept_{user_id}"),
                     InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")]]
        
        for admin_id in ADMIN_LIST:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_text, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode='HTML')
            except Exception as e: logger.error(f"Error admin {admin_id}: {e}")
        
        await update.message.reply_text("✅ Заявка успешно отправлена!", reply_markup=ReplyKeyboardMarkup([['Подать заявку']], resize_keyboard=True))
        context.user_data.clear()
        return MENU
    return CONFIRM

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Игнорируем кнопки анкеты, они обрабатываются в conv_handler
    if any(query.data.startswith(x) for x in ["exp_", "team_", "vol_"]):
        return 
        
    admin_user = update.effective_user
    data = query.data.split('_')
    action, user_id = data[0], int(data[1])

    current_status = get_application_status(user_id)
    if current_status != 'pending':
        await query.answer("⚠️ Уже обработано!", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=None)
        return

    await query.answer()
    
    if action == "accept":
        update_application_status(user_id, 'accepted')
        status_text = "✅ ПРИНЯТА"
        await context.bot.send_message(chat_id=user_id, text=f"<b>🎉 Одобрено!</b>\n\nКоманда: {TEAM_LINK}", parse_mode='HTML')
    else:
        update_application_status(user_id, 'rejected')
        status_text = "❌ ОТКЛОНЕНА"
        await context.bot.send_message(chat_id=user_id, text="<b>Отклонено.</b>", parse_mode='HTML')
    
    await query.edit_message_text(text=f"{query.message.text}\n\n{status_text}\nАдмин: {admin_user.name}", reply_markup=None, parse_mode='HTML')

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            # Добавляем и CallbackQueryHandler, и MessageHandler для каждого шага
            EXPERIENCE: [CallbackQueryHandler(get_experience), MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
            TEAM_TYPE: [CallbackQueryHandler(get_team_type), MessageHandler(filters.TEXT & ~filters.COMMAND, get_team_type)],
            TRAFFIC_VOLUME: [CallbackQueryHandler(get_traffic_volume), MessageHandler(filters.TEXT & ~filters.COMMAND, get_traffic_volume)],
            SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_source)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_application)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(admin_button_handler))
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
