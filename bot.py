from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import asyncio
from datetime import datetime
import os
import sys

TOKEN = "8432034617:AAFBROdOxySAe6opmCEGhDLGTXCpymjlFYY"
ADMIN_ID = 1197348954  # <-- твой Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Структура пользователей
users = {}  # user_id -> {"times": ["08:00", "12:00"], "taken_today": {"08:00": False}}

# Основная клавиатура навигации
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить время")],
        [KeyboardButton(text="Показать напоминания")],
        [KeyboardButton(text="Удалить напоминание")],
        [KeyboardButton(text="Редактировать напоминание")],
        [KeyboardButton(text="Перезапустить бота")]
    ],
    resize_keyboard=True
)

# Inline кнопка "Я выпил(-а)"
button_taken = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Я выпил(-а)", callback_data="taken")]]
)

# ====== /start ======
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Привет! 👋 Я буду напоминать тебе про витамины.\n"
        "Используй кнопки ниже для навигации.",
        reply_markup=main_keyboard
    )

# ====== Основной обработчик навигации ======
@dp.message()
async def handle_buttons(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    if text == "Добавить время":
        await message.answer("Отправь время в формате HH:MM (например, 08:30).")
    elif text == "Показать напоминания":
        if user_id in users and users[user_id]["times"]:
            times = ", ".join(users[user_id]["times"])
            await message.answer(f"Твои напоминания: {times}")
        else:
            await message.answer("У тебя ещё нет напоминаний.")
    elif text == "Удалить напоминание":
        await show_delete_buttons(user_id, message)
    elif text == "Редактировать напоминание":
        await show_edit_buttons(user_id, message)
    elif text == "Перезапустить бота":
        if user_id == ADMIN_ID:
            await message.answer("♻️ Бот перезапускается...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await message.answer("❌ У тебя нет прав для перезапуска бота.")
    else:
        # Если пользователь прислал время
        try:
            datetime.strptime(text, "%H:%M")
            if user_id not in users:
                users[user_id] = {"times": [], "taken_today": {}}
            if text not in users[user_id]["times"]:
                users[user_id]["times"].append(text)
                users[user_id]["taken_today"][text] = False
            await message.answer(f"Напоминание добавлено на {text}")
        except ValueError:
            await message.answer("Неправильный формат. Введи в HH:MM.")

# ====== Inline кнопки для удаления ======
async def show_delete_buttons(user_id, message):
    if user_id not in users or not users[user_id]["times"]:
        await message.answer("У тебя ещё нет напоминаний для удаления.")
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=f"del_{t}")] for t in users[user_id]["times"]
        ]
    )
    await message.answer("Выбери время, которое хочешь удалить:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("del_"))
async def delete_reminder(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    time_to_del = callback.data[4:]
    if user_id in users and time_to_del in users[user_id]["times"]:
        users[user_id]["times"].remove(time_to_del)
        users[user_id]["taken_today"].pop(time_to_del, None)
        await callback.message.edit_text(f"Напоминание {time_to_del} удалено ✅")
        await callback.answer()
    else:
        await callback.answer("Не удалось удалить напоминание.", show_alert=True)

# ====== Inline кнопки для редактирования ======
async def show_edit_buttons(user_id, message):
    if user_id not in users or not users[user_id]["times"]:
        await message.answer("У тебя ещё нет напоминаний для редактирования.")
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=f"edit_{t}")] for t in users[user_id]["times"]
        ]
    )
    await message.answer("Выбери напоминание, которое хочешь изменить:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_reminder(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    time_to_edit = callback.data[5:]
    await callback.message.edit_text(f"Отправь новое время для напоминания {time_to_edit} в формате HH:MM:")

    # Сохраняем в state (временно) что редактируем это время
    if 'edit_state' not in users[user_id]:
        users[user_id]['edit_state'] = {}
    users[user_id]['edit_state']['old_time'] = time_to_edit
    await callback.answer()

# ====== Перехват нового времени для редактирования ======
@dp.message()
async def edit_time_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in users and 'edit_state' in users[user_id] and 'old_time' in users[user_id]['edit_state']:
        old_time = users[user_id]['edit_state']['old_time']
        new_time = message.text
        try:
            datetime.strptime(new_time, "%H:%M")
            # Заменяем старое время новым
            index = users[user_id]['times'].index(old_time)
            users[user_id]['times'][index] = new_time
            users[user_id]['taken_today'].pop(old_time, None)
            users[user_id]['taken_today'][new_time] = False
            # Удаляем state
            users[user_id].pop('edit_state', None)
            await message.answer(f"Напоминание {old_time} изменено на {new_time} ✅", reply_markup=main_keyboard)
        except ValueError:
            await message.answer("Неправильный формат. Введи в HH:MM.")
        return

# ====== Inline кнопка "Я выпил(-а)" ======
@dp.callback_query(lambda c: c.data == "taken")
async def taken_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    msg_time = callback.message.date.strftime("%H:%M")
    if user_id in users:
        for t in users[user_id]["times"]:
            if not users[user_id]["taken_today"][t] and abs(datetime.strptime(t, "%H:%M") - datetime.strptime(msg_time, "%H:%M")).seconds < 60:
                users[user_id]["taken_today"][t] = True
                await callback.message.edit_text(f"Отлично! 💊 Ты принял(-а) витамины на {t} сегодня.")
                await callback.answer()
                return
        await callback.answer("Напоминание уже отмечено.")

# ====== Фоновая задача напоминаний ======
async def send_reminders():
    while True:
        now = datetime.now().strftime("%H:%M")
        for user_id, data in users.items():
            for t in data["times"]:
                if t == now and not data["taken_today"][t]:
                    try:
                        await bot.send_message(user_id, f"💊 Пора принять витамины ({t})!", reply_markup=button_taken)
                    except Exception as e:
                        print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
        if now == "00:00":
            for user_id in users:
                for t in users[user_id]["times"]:
                    users[user_id]["taken_today"][t] = False
        await asyncio.sleep(60)

# ====== Главная функция ======
async def main():
    print("Бот запущен...")
    asyncio.create_task(send_reminders())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# --- Веб-сервер для health-чеков от Render ---
async def health_check(request):
    """
    Эта функция будет отвечать на HTTP-запросы Render,
    подтверждая, что сервис жив.
    """
    return web.Response(text="I am alive!")

async def start_bot_and_server(bot: Bot, dispatcher: Dispatcher):
    """
    Запускает и бота (в режиме поллинга), и веб-сервер.
    """
    # Создаем веб-приложение
    app = web.Application()
    app.router.add_get('/', health_check) # Регистрируем наш health-чек

    # Render предоставляет порт в переменной окружения PORT
    # Если ее нет (локальный запуск), используем 8080
    port = int(os.getenv('PORT', 8080))
    
    # Запускаем веб-сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Задачи для одновременного выполнения
    bot_task = asyncio.create_task(dispatcher.start_polling(bot))
    server_task = asyncio.create_task(site.start())

    logging.info(f"Веб-сервер запущен на порту {port}")
    
    # Ждем завершения обеих задач
    await asyncio.gather(bot_task, server_task)


async def main():
    if not TOKEN:
        logging.critical("Переменная окружения TOKEN не найдена!")
        return

    bot = Bot(token=TOKEN)
    await start_bot_and_server(bot, dp)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
