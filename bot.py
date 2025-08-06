# bot.py - Основной файл бота
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

from database.db_manager import DatabaseManager
from handlers.transactions import TransactionHandler
from handlers.reports import ReportHandler
from handlers.delete_transactions import DeleteHandler
from handlers.keyboard_handler import KeyboardHandler
from ai.openrouter_client import OpenRouterClient
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinanceBot:
    def __init__(self):
        self.config = Config()
        self.bot = Bot(token=self.config.BOT_TOKEN)
        self.dp = Dispatcher()
        self.db = DatabaseManager()
        self.ai_client = OpenRouterClient(self.config.OPENROUTER_API_KEY)
        self.transaction_handler = TransactionHandler(self.db, self.ai_client)
        self.report_handler = ReportHandler(self.db, self.ai_client)
        self.delete_handler = DeleteHandler(self.db)
        self.keyboard_handler = KeyboardHandler()

        # Регистрируем обработчики
        self.register_handlers()

    def register_handlers(self):
        """Регистрация всех обработчиков команд"""

        @self.dp.message(Command("start"))
        async def start_command(message: Message):
            user_id = message.from_user.id

            # Регистрируем пользователя
            if not self.db.is_user_registered(user_id):
                success = self.db.register_user(
                    user_id, 
                    message.from_user.username, 
                    message.from_user.first_name
                )
                if success:
                    welcome_msg = f"🎉 Добро пожаловать, {message.from_user.first_name}!"
                else:
                    welcome_msg = "👋 С возвращением!"
            else:
                welcome_msg = "👋 С возвращением!"

            # Отправляем приветствие с интерактивным меню
            await message.answer(
                f"{welcome_msg}\n\n"
                "💰 **Финансовый бот с AI готов к работе OPSversion!**\n\n"
                "📝 **Как пользоваться:**\n"
                "• Пишите транзакции: `обед 1500`\n"
                "• Используйте кнопки меню внизу\n"
                "• Получайте AI советы и анализ\n\n"
                "🚀 **Начинайте прямо сейчас!**",
                reply_markup=self.keyboard_handler.get_main_menu(user_id),
                parse_mode="Markdown"
            )

        @self.dp.message(Command("help"))
        async def help_command(message: Message):
            await message.answer(
                "🤖 **Финансовый бот с AI**\n\n"
                "**💰 Добавление транзакций:**\n"
                "• `обед 1500` - расход на еду\n"
                "• `зарплата 200000` - доход\n"
                "• `120 000 кредит` - выплата кредита\n\n"
                "**📊 Отчеты и статистика:**\n"
                "• `/balance` - текущий баланс\n"
                "• `/stats` - статистика за месяц\n"
                "• `/report` - детальный отчет с AI анализом\n\n"
                "**🗑 Управление транзакциями:**\n"
                "• `/delete` - удалить последнюю\n"
                "• `/deletelist` - выбрать из списка\n"
                "• Кнопка под каждой транзакцией\n\n"
                "**🤖 AI возможности:**\n"
                "• Автоматическое определение категорий\n"
                "• Персональные советы после трат\n"
                "• Анализ паттернов и прогнозы\n\n"
                "Ваши данные видите только вы! 🔒",
                parse_mode="Markdown"
            )

        # Админские команды
        @self.dp.message(Command("admin"))
        async def admin_command(message: Message):
            user_id = message.from_user.id
            if user_id not in self.config.ADMIN_USERS:
                await message.answer("❌ Команда только для администраторов")
                return

            stats = self.db.get_user_stats()
            await message.answer(
                f"👑 **Статистика бота**\n\n"
                f"👥 Всего пользователей: {stats['total']}\n"
                f"🟢 Активных за 7 дней: {stats['active_7d']}\n"
                f"🆕 Новых за 30 дней: {stats['new_30d']}",
                parse_mode="Markdown"
            )

        @self.dp.message(Command("balance"))
        async def balance_command(message: Message):
            user_id = message.from_user.id
            balance = self.db.get_user_balance(user_id)

            await message.answer(f"💰 Текущий баланс: {balance:,.0f} ₸")

        @self.dp.message(Command("report"))
        async def report_command(message: Message):
            await self.report_handler.handle_report_request(message)

        @self.dp.message(Command("stats"))
        async def stats_command(message: Message):
            await self.report_handler.handle_stats_request(message)

        @self.dp.message(Command("delete"))
        async def delete_last_command(message: Message):
            await self.delete_handler.handle_delete_last(message)

        @self.dp.message(Command("deletelist"))
        async def delete_list_command(message: Message):
            await self.delete_handler.handle_delete_list(message)

        # Обработка всех текстовых сообщений
        @self.dp.message()
        async def handle_message(message: Message):
            # Сначала проверяем, это кнопка меню или транзакция
            is_menu_button = await self.keyboard_handler.handle_menu_button(
                message, self.db, self.report_handler, self.delete_handler
            )

            # Если это не кнопка меню, обрабатываем как транзакцию
            if not is_menu_button:
                await self.transaction_handler.handle_transaction(message)

        # Обработчик callback для отчетов и удаления
        @self.dp.callback_query()
        async def handle_callbacks(callback: types.CallbackQuery):
            if callback.data.startswith("report_"):
                await self.report_handler._generate_report(callback)
            elif callback.data.startswith("delete_"):
                await self.delete_handler.handle_delete_callback(callback)
            await callback.answer()

    async def start_polling(self):
        """Запуск бота"""
        logger.info("🤖 Финансовый бот запускается...")
        await self.dp.start_polling(self.bot)

if __name__ == "__main__":
    bot = FinanceBot()
    asyncio.run(bot.start_polling())
