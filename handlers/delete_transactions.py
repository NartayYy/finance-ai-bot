# handlers/delete_transactions.py
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.db_manager import DatabaseManager
from datetime import datetime

class DeleteHandler:
    """Обработчик удаления транзакций"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def handle_delete_last(self, message: Message):
        """Удаление последней транзакции"""
        user_id = message.from_user.id
        
        # Получаем последнюю транзакцию
        last_transaction = self.db.get_last_transaction(user_id)
        
        if not last_transaction:
            await message.answer("❌ Нет транзакций для удаления")
            return
        
        # Создаем кнопки подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm_{last_transaction.id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="delete_cancel")
            ]
        ])
        
        # Показываем информацию о транзакции
        sign = "+" if last_transaction.transaction_type == "income" else "-"
        date_str = last_transaction.created_at.strftime('%d.%m.%Y %H:%M')
        
        await message.answer(
            f"🗑 **Удалить последнюю транзакцию?**\n\n"
            f"📅 {date_str}\n"
            f"💰 {sign}{last_transaction.amount:,.0f} ₸\n"
            f"📝 {last_transaction.description}\n"
            f"📂 {last_transaction.category}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    async def handle_delete_list(self, message: Message):
        """Показать список последних транзакций для удаления"""
        user_id = message.from_user.id
        
        # Получаем последние 10 транзакций
        transactions = self.db.get_recent_transactions_for_deletion(user_id, 10)
        
        if not transactions:
            await message.answer("❌ Нет транзакций для удаления")
            return
        
        # Создаем кнопки для каждой транзакции
        keyboard_buttons = []
        
        for i, t in enumerate(transactions, 1):
            sign = "+" if t.transaction_type == "income" else "-"
            date_str = t.created_at.strftime('%d.%m %H:%M')
            button_text = f"{i}. {sign}{t.amount:,.0f}₸ {t.description[:15]}..."
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=button_text, 
                    callback_data=f"delete_select_{t.id}"
                )
            ])
        
        # Добавляем кнопку отмены
        keyboard_buttons.append([
            InlineKeyboardButton(text="❌ Отмена", callback_data="delete_cancel")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(
            "🗑 **Выберите транзакцию для удаления:**\n\n"
            "Последние 10 транзакций:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    async def handle_delete_callback(self, callback: CallbackQuery):
        """Обработка callback для удаления"""
        user_id = callback.from_user.id
        data = callback.data
        
        if data == "delete_cancel":
            await callback.message.edit_text("❌ Удаление отменено")
            await callback.answer()
            return
        
        if data.startswith("delete_select_"):
            # Показываем подтверждение для выбранной транзакции
            transaction_id = int(data.split("_")[2])
            
            # Получаем информацию о транзакции
            transactions = self.db.get_recent_transactions_for_deletion(user_id, 50)
            transaction = next((t for t in transactions if t.id == transaction_id), None)
            
            if not transaction:
                await callback.message.edit_text("❌ Транзакция не найдена")
                await callback.answer()
                return
            
            # Создаем кнопки подтверждения
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm_{transaction_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="delete_cancel")
                ]
            ])
            
            sign = "+" if transaction.transaction_type == "income" else "-"
            date_str = transaction.created_at.strftime('%d.%m.%Y %H:%M')
            
            await callback.message.edit_text(
                f"🗑 **Удалить транзакцию?**\n\n"
                f"📅 {date_str}\n"
                f"💰 {sign}{transaction.amount:,.0f} ₸\n"
                f"📝 {transaction.description}\n"
                f"📂 {transaction.category}",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        if data.startswith("delete_confirm_"):
            # Подтверждение удаления
            transaction_id = int(data.split("_")[2])
            
            # Получаем информацию до удаления для отчета
            transactions = self.db.get_recent_transactions_for_deletion(user_id, 50)
            transaction = next((t for t in transactions if t.id == transaction_id), None)
            
            if not transaction:
                await callback.message.edit_text("❌ Транзакция не найдена")
                await callback.answer()
                return
            
            # Удаляем транзакцию
            success = self.db.delete_transaction(transaction_id, user_id)
            
            if success:
                # Получаем новый баланс
                new_balance = self.db.get_user_balance(user_id)
                
                sign = "+" if transaction.transaction_type == "income" else "-"
                
                await callback.message.edit_text(
                    f"✅ **Транзакция удалена!**\n\n"
                    f"💰 {sign}{transaction.amount:,.0f} ₸ - {transaction.description}\n"
                    f"💳 Новый баланс: {new_balance:,.0f} ₸",
                    parse_mode="Markdown"
                )
            else:
                await callback.message.edit_text("❌ Ошибка удаления транзакции")
            
            await callback.answer()
    
    def create_quick_delete_button(self, transaction_id: int) -> InlineKeyboardMarkup:
        """Создание кнопки быстрого удаления для только что добавленной транзакции"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить эту транзакцию", callback_data=f"delete_confirm_{transaction_id}")]
        ])
