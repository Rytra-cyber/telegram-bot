import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import requests

# Получаем токен из переменной окружения
TOKEN = os.getenv("TOKEN")

# Список популярных валют
popular_currencies = ["USD","EUR","UAH","GBP","JPY","CHF","CAD","AUD","CNY"]

# Специальные валюты для emoji
special_currency_countries = {
    "EUR": "EU",
}

# Хранилище для выбранных валют (пользователь → выбор)
user_data = {}

def country_code_to_emoji(country_code):
    try:
        return chr(127397 + ord(country_code[0])) + chr(127397 + ord(country_code[1]))
    except:
        return "–"

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n"
        "Я — интерактивный конвертер валют.\n"
        "Нажми /convert чтобы начать конвертацию с кнопками.\n"
        "ℹ️ Напиши /help для подсказки."
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Как пользоваться ботом:*\n\n"
        "1️⃣ Нажми /convert\n"
        "2️⃣ Выбери валюту, из которой хочешь конвертировать\n"
        "3️⃣ Выбери валюту, в которую конвертировать\n"
        "4️⃣ Введи сумму — и я покажу результат 💱\n\n"
        "🔁 После результата нажми кнопку, чтобы начать заново!",
        parse_mode="Markdown"
    )

# /convert
async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"{country_code_to_emoji(special_currency_countries.get(c, c[:2]))} {c}", callback_data=f"from_{c}")] for c in popular_currencies]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💱 *Выбери валюту, из которой конвертировать:*", reply_markup=reply_markup, parse_mode="Markdown")

# Обработка кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("from_"):
        currency = data[5:]
        user_data[user_id] = {"from": currency}
        keyboard = [[InlineKeyboardButton(f"{country_code_to_emoji(special_currency_countries.get(c, c[:2]))} {c}", callback_data=f"to_{c}")] for c in popular_currencies]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"✅ Выбрана валюта *{currency}*\nТеперь выбери валюту, куда конвертировать:", reply_markup=reply_markup, parse_mode="Markdown")

    elif data.startswith("to_"):
        currency_to = data[3:]
        user_data[user_id]["to"] = currency_to
        await query.edit_message_text(f"✅ Выбрана валюта *{currency_to}*\n💰 Теперь напиши сумму для конвертации:", parse_mode="Markdown")

# Обработка ввода суммы
async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data or "from" not in user_data[user_id] or "to" not in user_data[user_id]:
        return
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Сумма должна быть числом.")
        return

    base = user_data[user_id]["from"]
    target = user_data[user_id]["to"]

    # Запрос курса
    response = requests.get(f"https://open.er-api.com/v6/latest/{base}").json()
    if response.get("result") != "success":
        await update.message.reply_text("❌ Не удалось получить курс. Попробуйте позже.")
        return

    rate = response["rates"].get(target)
    if not rate:
        await update.message.reply_text(f"⚠️ Валюта {target} недоступна.")
        return

    converted = amount * rate
    base_flag = country_code_to_emoji(special_currency_countries.get(base, base[:2]))
    target_flag = country_code_to_emoji(special_currency_countries.get(target, target[:2]))

    keyboard = [[InlineKeyboardButton("🔁 Повторить", callback_data="restart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"💱 *Результат:*\n\n{base_flag} {amount} {base} → {target_flag} {converted:.2f} {target}\n📊 *Курс:* 1 {base} = {rate:.4f} {target}", parse_mode="Markdown", reply_markup=reply_markup)

    user_data.pop(user_id)

# Кнопка "Повторить"
async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await convert_command(query, context)

# Основная функция
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("convert", convert_command))
    app.add_handler(CallbackQueryHandler(button, pattern="^(from_|to_)"))
    app.add_handler(CallbackQueryHandler(restart_handler, pattern="^restart$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
