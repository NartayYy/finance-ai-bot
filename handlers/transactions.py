# handlers/transactions.py
import re
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db_manager import DatabaseManager
from ai.openrouter_client import OpenRouterClient
from config import Config
from typing import Optional

class TransactionHandler:
    """Обработчик транзакций"""
    
    def __init__(self, db_manager: DatabaseManager, ai_client: OpenRouterClient):
        self.db = db_manager
        self.ai = ai_client
        self.config = Config()
    
    async def handle_transaction(self, message: Message):
        """Обработка текстового сообщения как транзакции"""
        
        user_id = message.from_user.id
        text = message.text.strip()
        
        # Проверяем регистрацию пользователя
        if not await self._check_user_access(message):
            return
        
        # Обновляем активность пользователя
        self.db.update_user_activity(
            user_id, 
            message.from_user.username, 
            message.from_user.first_name
        )
        
        # Парсим транзакцию
        transaction_data = self._parse_transaction(text)
        
        if not transaction_data:
            await message.answer(
                "❓ Не понял транзакцию. Примеры:\n"
                "• обед 1000\n"
                "• зарплата 240000\n"
                "• такси 1500"
            )
            return
        
        description, amount = transaction_data
        
        # Определяем категорию и тип через AI
        try:
            categorization = await self.ai.categorize_transaction(description, amount)
            transaction_type = categorization["type"]
            category = categorization["category"]
        except Exception as e:
            print(f"Ошибка AI категоризации: {e}")
            # Fallback к простому определению
            if any(keyword in description.lower() for keyword in self.config.INCOME_CATEGORIES):
                transaction_type = "income"
                category = "доход"
            else:
                transaction_type = "expense"
                category = "другое"
        
        # Сохраняем в базу
        success = self.db.add_transaction(
            user_id=user_id,
            amount=amount,
            description=description,
            category=category,
            transaction_type=transaction_type
        )
        
        if not success:
            await message.answer("❌ Ошибка сохранения транзакции")
            return
        
        # Получаем ID последней транзакции для кнопки удаления
        last_transaction = self.db.get_last_transaction(user_id)
        
        # Получаем новый баланс
        balance = self.db.get_user_balance(user_id)
        
        # Формируем ответ
        emoji = "💰" if transaction_type == "income" else "💸"
        sign = "+" if transaction_type == "income" else "-"
        
        response = (
            f"✅ Транзакция добавлена!\n\n"
            f"{emoji} {sign}{amount:,.0f} ₸\n"
            f"📝 {description}\n"
            f"📂 Категория: {category}\n"
            f"💳 Баланс: {balance:,.0f} ₸"
        )
        
        # Создаем кнопку быстрого удаления
        keyboard = None
        if last_transaction:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🗑 Удалить эту транзакцию", 
                    callback_data=f"delete_confirm_{last_transaction.id}"
                )]
            ])
        
        # Добавляем AI совет для расходов
        if transaction_type == "expense" and amount > 1000:
            try:
                advice = await self.ai.get_spending_advice(description, amount, balance)
                if advice:
                    response += f"\n\n{advice}"
            except Exception as e:
                print(f"Ошибка получения совета: {e}")
        
        await message.answer(response, reply_markup=keyboard)
        
        # Возвращаем интерактивное меню если его нет
        if not keyboard:
            from handlers.keyboard_handler import KeyboardHandler
            menu_handler = KeyboardHandler()
            await message.answer(
                "✨ Используйте меню внизу для быстрого доступа к функциям:",
                reply_markup=menu_handler.get_main_menu()
            )
    
    async def _check_user_access(self, message: Message) -> bool:
        """Проверка доступа пользователя к боту"""
        user_id = message.from_user.id
        
        # Админы всегда имеют доступ
        if user_id in self.config.ADMIN_USERS:
            # Регистрируем админа если не зарегистрирован
            if not self.db.is_user_registered(user_id):
                self.db.register_user(user_id, message.from_user.username, message.from_user.first_name)
            return True
        
        # Проверяем регистрацию
        if not self.db.is_user_registered(user_id):
            if self.config.AUTO_REGISTRATION:
                # Автоматическая регистрация
                success = self.db.register_user(user_id, message.from_user.username, message.from_user.first_name)
                if success:
                    await message.answer(
                        f"🎉 Добро пожаловать в финансовый бот, {message.from_user.first_name}!\n\n"
                        "📝 Начинайте добавлять транзакции:\n"
                        "• обед 1500\n"
                        "• зарплата 200000\n\n"
                        "📋 Команды: /help"
                    )
                return success
            else:
                await message.answer(
                    "❌ Для использования бота нужна регистрация.\n"
                    "Напишите /start для регистрации."
                )
                return False
        
        return True
    
    def _parse_transaction(self, text: str) -> Optional[tuple[str, float]]:
        """Парсинг транзакции из текста"""
        
        # Убираем лишние пробелы
        text = text.strip()
        
        # Паттерны для поиска суммы (улучшенные)
        patterns = [
            r'(.+?)\s+(\d+(?:\s+\d+)*(?:[.,]\d+)?)',  # "описание 120 434" или "описание 120,5"
            r'(\d+(?:\s+\d+)*(?:[.,]\d+)?)\s+(.+)',   # "120 434 описание"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                part1, part2 = match.groups()
                
                # Определяем, что является суммой
                try:
                    # Обрабатываем числа с пробелами: "120 434" -> "120434"
                    amount_str = part2.replace(' ', '').replace(',', '.')
                    amount = float(amount_str)
                    description = part1.strip()
                    
                    if amount > 0 and description:
                        return description, amount
                        
                except ValueError:
                    try:
                        # Пробуем наоборот
                        amount_str = part1.replace(' ', '').replace(',', '.')
                        amount = float(amount_str)
                        description = part2.strip()
                        
                        if amount > 0 and description:
                            return description, amount
                            
                    except ValueError:
                        continue
        
        # Если паттерны не сработали, ищем все числа в тексте
        # Обновленный regex для чисел с пробелами
        numbers = re.findall(r'\d+(?:\s+\d+)*(?:[.,]\d+)?', text)
        if numbers:
            try:
                # Берем самое длинное число (обычно это сумма)
                longest_number = max(numbers, key=len)
                amount = float(longest_number.replace(' ', '').replace(',', '.'))
                
                # Убираем это число из описания
                description = text.replace(longest_number, '').strip()
                # Убираем лишние пробелы
                description = re.sub(r'\s+', ' ', description)
                
                if amount > 0 and description:
                    return description, amount
                    
            except ValueError:
                pass
        
        return None
