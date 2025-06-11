# -*- coding: utf-8 -*-
import datetime
import pickle
import os
from collections import defaultdict
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Конфігурація бота
TOKEN = "8067399638:AAEGVvs-cyW1jEAVw_8hrA5EFiYTrAtAV1A"
DAYS_OF_WEEK = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
DATA_FILE = "bot_data.pkl"

class StudentAssistantBot:
    def __init__(self):
        # Стандартний розклад
        self.schedule = {
            0: ["Математика", "Фізика", "Програмування"],
            1: ["Англійська", "Історія", "Фізкультура"],
            2: ["Програмування", "Математика", "Хімія"],
            3: ["Фізика", "Англійська", "Література"],
            4: ["Хімія", "Фізкультура", "Історія"],
            5: [],
            6: []
        }
        self.custom_subjects = set()  # Для зберігання додаткових предметів
        self.tasks = defaultdict(list)
        self.user_state = {}
        self.load_data()

    def save_data(self):
        """Зберегти дані бота у файл"""
        data = {
            'schedule': self.schedule,
            'custom_subjects': self.custom_subjects,
            'tasks': dict(self.tasks)
        }
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(data, f)

    def load_data(self):
        """Завантажити дані бота з файлу"""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'rb') as f:
                data = pickle.load(f)
                self.schedule = data.get('schedule', self.schedule)
                self.custom_subjects = data.get('custom_subjects', set())
                self.tasks = defaultdict(list, data.get('tasks', {}))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /start"""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Вітаю, {user.first_name}! Я твій навчальний помічник.\n"
            "📌 Доступні команди:\n"
            "/today - Розклад на сьогодні\n"
            "/tomorrow - Розклад на завтра\n"
            "/add_task - Додати завдання\n"
            "/tasks - Всі завдання\n"
            "/add_subject - Додати новий предмет\n"
            "/help - Довідка"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /help"""
        await update.message.reply_text(
            "ℹ️ Доступні команди:\n"
            "/today - Сьогоднішній розклад\n"
            "/tomorrow - Завтрашній розклад\n"
            "/add_task - Додати нове завдання\n"
            "/tasks - Список всіх завдань\n"
            "/add_subject - Додати новий предмет\n"
            "/help - Ця довідка"
        )

    async def add_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Додати новий предмет"""
        await update.message.reply_text(
            "📚 Введіть назву нового предмета:"
        )
        self.user_state[update.effective_user.id] = "waiting_for_subject"

    async def add_subject_finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершення додавання предмета"""
        new_subject = update.message.text.strip()
        if new_subject:
            self.custom_subjects.add(new_subject)
            await update.message.reply_text(f"✅ Предмет '{new_subject}' успішно додано!")
            self.save_data()
        else:
            await update.message.reply_text("❌ Назва предмета не може бути порожньою!")
        self.user_state.pop(update.effective_user.id, None)

    async def show_schedule(self, update: Update, day_offset: int):
        """Показати розклад на вказаний день"""
        today = datetime.date.today()
        target_date = today + datetime.timedelta(days=day_offset)
        day_index = target_date.weekday()
        
        schedule_text = f"📅 {DAYS_OF_WEEK[day_index]} ({target_date.strftime('%d.%m.%Y')}):\n"
        if self.schedule[day_index]:
            for i, subject in enumerate(self.schedule[day_index], 1):
                schedule_text += f"{i}. {subject}\n"
        
        # Додаємо кастомні предмети
        if day_index in [0,1,2,3,4]:  # Тільки для робочих днів
            for i, subject in enumerate(sorted(self.custom_subjects), len(self.schedule[day_index])+1):
                schedule_text += f"{i}. {subject} (додатковий)\n"
        
        if not self.schedule[day_index] and not self.custom_subjects:
            schedule_text += "🎉 Вікенд або пар немає!"
        
        await update.message.reply_text(schedule_text)

    async def today_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /today"""
        await self.show_schedule(update, 0)

    async def tomorrow_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /tomorrow"""
        await self.show_schedule(update, 1)

    async def add_task_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Початок додавання завдання"""
        await update.message.reply_text(
            "📝 Введіть завдання у форматі:\n"
            "<Предмет>, <Дата (дд.мм.рррр)>, <Опис>\n"
            "Наприклад: Математика, 25.12.2023, Виконати стор. 45\n\n"
            f"Доступні предмети: {', '.join(sorted(self.custom_subjects))}"
        )
        self.user_state[update.effective_user.id] = "waiting_for_task"

    async def add_task_finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершення додавання завдання"""
        try:
            subject, date_str, description = [x.strip() for x in update.message.text.split(",", 2)]
            due_date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
            self.tasks[due_date].append((subject, description))
            await update.message.reply_text("✅ Завдання успішно додано!")
            self.save_data()
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Помилка! Використовуйте формат: Предмет, дата, опис")
        self.user_state.pop(update.effective_user.id, None)

    async def show_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати всі завдання"""
        if not self.tasks:
            await update.message.reply_text("📭 У вас немає жодних завдань!")
            return
        
        tasks_text = "📌 Всі завдання:\n"
        for date in sorted(self.tasks.keys()):
            tasks_text += f"\n📅 {date.strftime('%d.%m.%Y')} ({DAYS_OF_WEEK[date.weekday()]}):\n"
            for i, (subject, desc) in enumerate(self.tasks[date], 1):
                tasks_text += f"{i}. {subject}: {desc}\n"
        await update.message.reply_text(tasks_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка звичайних повідомлень"""
        user_id = update.effective_user.id
        if self.user_state.get(user_id) == "waiting_for_task":
            await self.add_task_finish(update, context)
        elif self.user_state.get(user_id) == "waiting_for_subject":
            await self.add_subject_finish(update, context)
        else:
            await update.message.reply_text("Не розумію команди. Спробуйте /help")

def main():
    """Запуск бота"""
    bot = StudentAssistantBot()
    
    # Створюємо Application
    application = Application.builder().token(TOKEN).build()
    
    # Реєструємо обробники команд
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("today", bot.today_schedule))
    application.add_handler(CommandHandler("tomorrow", bot.tomorrow_schedule))
    application.add_handler(CommandHandler("add_task", bot.add_task_start))
    application.add_handler(CommandHandler("tasks", bot.show_tasks))
    application.add_handler(CommandHandler("add_subject", bot.add_subject))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Запускаємо бота
    print("🤖 Бот запущений...")
    application.run_polling()

if __name__ == "__main__":
    main()