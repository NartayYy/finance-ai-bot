# handlers/reports.py
import os
from datetime import datetime, timedelta
from aiogram.types import Message, FSInputFile
from aiogram import types
from database.db_manager import DatabaseManager
from ai.openrouter_client import OpenRouterClient

class ReportHandler:
    """Обработчик отчетов и статистики"""
    
    def __init__(self, db_manager: DatabaseManager, ai_client: OpenRouterClient):
        self.db = db_manager
        self.ai = ai_client
    
    async def handle_report_request(self, message: Message):
        """Обработка запроса отчета"""
        
        # Создаем inline клавиатуру для выбора периода
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="7 дней", callback_data="report_7"),
                types.InlineKeyboardButton(text="30 дней", callback_data="report_30")
            ],
            [
                types.InlineKeyboardButton(text="90 дней", callback_data="report_90"),
                types.InlineKeyboardButton(text="Весь период", callback_data="report_all")
            ]
        ])
        
        await message.answer(
            "📊 Выберите период для отчета:",
            reply_markup=keyboard
        )
    
    async def _generate_report(self, callback: types.CallbackQuery):
        """Генерация детального отчета"""
        
        user_id = callback.from_user.id
        period_str = callback.data.replace("report_", "")
        
        # Определяем количество дней
        if period_str == "7":
            days = 7
            period_name = "7 дней"
        elif period_str == "30":
            days = 30
            period_name = "30 дней"
        elif period_str == "90":
            days = 90
            period_name = "90 дней"
        else:
            days = 365 * 10  # Весь период
            period_name = "весь период"
        
        await callback.message.edit_text("📊 Генерирую отчет...")
        
        # Получаем транзакции
        transactions = self.db.get_transactions(user_id, days)
        
        if not transactions:
            await callback.message.edit_text(
                f"📭 Нет транзакций за {period_name}"
            )
            return
        
        # Генерируем отчет
        report_path = await self._create_detailed_report(
            user_id, transactions, period_name
        )
        
        # Отправляем файл
        if os.path.exists(report_path):
            document = FSInputFile(report_path)
            await callback.message.answer_document(
                document,
                caption=f"📊 Детальный отчет за {period_name}"
            )
            
            # Удаляем временный файл
            os.remove(report_path)
        else:
            await callback.message.edit_text("❌ Ошибка создания отчета")
        
        await callback.answer()
    
    async def _create_detailed_report(self, user_id: int, transactions: list, period: str) -> str:
        """Создание детального TXT отчета с AI анализом"""
        
        # Подготавливаем данные
        total_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        total_expense = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        balance = total_income - total_expense
        current_balance = self.db.get_user_balance(user_id)
        
        # Группируем по категориям
        income_by_category = {}
        expense_by_category = {}
        
        for t in transactions:
            if t.transaction_type == 'income':
                income_by_category[t.category] = income_by_category.get(t.category, 0) + t.amount
            else:
                expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount
        
        # Получаем AI анализ
        ai_analysis = await self.ai.analyze_spending(transactions, len(transactions))
        
        # Создаем отчет
        report_content = self._format_report(
            period, total_income, total_expense, balance, current_balance,
            income_by_category, expense_by_category, transactions, ai_analysis
        )
        
        # Сохраняем в файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"financial_report_{user_id}_{timestamp}.txt"
        filepath = f"temp/{filename}"
        
        # Создаем директорию если не существует
        os.makedirs("temp", exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return filepath
    
    def _format_report(self, period: str, total_income: float, total_expense: float, 
                      balance: float, current_balance: float, income_by_category: dict,
                      expense_by_category: dict, transactions: list, ai_analysis: str) -> str:
        """Форматирование отчета"""
        
        report = f"""
═══════════════════════════════════════════════════════════════
                    ФИНАНСОВЫЙ ОТЧЕТ ЗА {period.upper()}
═══════════════════════════════════════════════════════════════
Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📊 ОБЩАЯ СТАТИСТИКА
───────────────────────────────────────────────────────────────
💰 Общие доходы:     {total_income:>15,.0f} ₸
💸 Общие расходы:    {total_expense:>15,.0f} ₸
📈 Баланс за период: {balance:>15,.0f} ₸
💳 Текущий баланс:   {current_balance:>15,.0f} ₸

💰 ДОХОДЫ ПО КАТЕГОРИЯМ
───────────────────────────────────────────────────────────────
"""
        
        if income_by_category:
            for category, amount in sorted(income_by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total_income * 100) if total_income > 0 else 0
                report += f"{category:<20} {amount:>12,.0f} ₸ ({percentage:>5.1f}%)\n"
        else:
            report += "Доходов не найдено\n"
        
        report += f"""
💸 РАСХОДЫ ПО КАТЕГОРИЯМ
───────────────────────────────────────────────────────────────
"""
        
        if expense_by_category:
            for category, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total_expense * 100) if total_expense > 0 else 0
                report += f"{category:<20} {amount:>12,.0f} ₸ ({percentage:>5.1f}%)\n"
        else:
            report += "Расходов не найдено\n"
        
        report += f"""
📋 ПОСЛЕДНИЕ ТРАНЗАКЦИИ
───────────────────────────────────────────────────────────────
"""
        
        # Показываем последние 20 транзакций
        recent_transactions = sorted(transactions, key=lambda x: x.created_at, reverse=True)[:20]
        
        for t in recent_transactions:
            sign = "+" if t.transaction_type == "income" else "-"
            date_str = t.created_at.strftime('%d.%m %H:%M')
            report += f"{date_str} | {sign}{t.amount:>8,.0f} ₸ | {t.description:<25} | {t.category}\n"
        
        report += f"""

🤖 AI АНАЛИЗ И РЕКОМЕНДАЦИИ
───────────────────────────────────────────────────────────────
{ai_analysis}

═══════════════════════════════════════════════════════════════
                        КОНЕЦ ОТЧЕТА
═══════════════════════════════════════════════════════════════
"""
        
        return report
    
    async def handle_stats_request(self, message: Message):
        """Быстрая статистика за месяц"""
        
        user_id = message.from_user.id
        
        # Получаем данные за месяц
        transactions = self.db.get_transactions(user_id, 30)
        category_stats = self.db.get_category_stats(user_id, 30)
        balance = self.db.get_user_balance(user_id)
        
        if not transactions:
            await message.answer("📭 Нет транзакций за последний месяц")
            return
        
        # Считаем итоги
        total_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        total_expense = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        
        # Топ категории расходов
        expense_categories = {k: v for k, v in category_stats.items() if v.get('expense', 0) > 0}
        top_expenses = sorted(expense_categories.items(), key=lambda x: x[1]['expense'], reverse=True)[:5]
        
        stats_text = f"""📊 **Статистика за месяц**

💰 Доходы: {total_income:,.0f} ₸
💸 Расходы: {total_expense:,.0f} ₸
💳 Текущий баланс: {balance:,.0f} ₸

📈 **Топ категории расходов:**
"""
        
        for i, (category, data) in enumerate(top_expenses, 1):
            amount = data['expense']
            percentage = (amount / total_expense * 100) if total_expense > 0 else 0
            stats_text += f"{i}. {category}: {amount:,.0f} ₸ ({percentage:.1f}%)\n"
        
        await message.answer(stats_text, parse_mode="Markdown")
