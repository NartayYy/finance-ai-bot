# handlers/keyboard_handler.py
import os
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram import types
from config import Config

class KeyboardHandler:
    """Обработчик интерактивного меню (Reply Keyboard)"""
    
    def __init__(self):
        self.config = Config()
    
    def _create_main_menu(self, user_id: int) -> ReplyKeyboardMarkup:
        """Создание главного меню (обычное или админское)"""
        
        # Проверяем, админ ли пользователь
        is_admin = user_id in self.config.ADMIN_USERS
        
        if is_admin:
            # Админское меню
            buttons = [
                [
                    KeyboardButton(text="💰 Баланс"),
                    KeyboardButton(text="📊 Статистика")
                ],
                [
                    KeyboardButton(text="📋 Отчет"),
                    KeyboardButton(text="🗑 Удалить")
                ],
                [
                    KeyboardButton(text="👑 Админка"),
                    KeyboardButton(text="📈 Аналитика")
                ],
                [
                    KeyboardButton(text="ℹ️ Помощь")
                ]
            ]
        else:
            # Обычное меню для пользователей
            buttons = [
                [
                    KeyboardButton(text="💰 Баланс"),
                    KeyboardButton(text="📊 Статистика")
                ],
                [
                    KeyboardButton(text="📋 Отчет"),
                    KeyboardButton(text="🗑 Удалить")
                ],
                [
                    KeyboardButton(text="ℹ️ Помощь")
                ]
            ]
        
        # Создаем клавиатуру
        keyboard = ReplyKeyboardMarkup(
            keyboard=buttons,
            resize_keyboard=True,
            one_time_keyboard=False,
            placeholder="Выберите действие..."
        )
        
        return keyboard
    
    def get_main_menu(self, user_id: int) -> ReplyKeyboardMarkup:
        """Получить главное меню для конкретного пользователя"""
        return self._create_main_menu(user_id)
    
    async def handle_menu_button(self, message: Message, db_manager, report_handler, delete_handler):
        """Обработка нажатий кнопок меню"""
        
        text = message.text
        user_id = message.from_user.id
        is_admin = user_id in self.config.ADMIN_USERS
        
        if text == "💰 Баланс":
            balance = db_manager.get_user_balance(user_id)
            await message.answer(
                "💳 **Ваш текущий баланс**\n\n"
                f"💰 {balance:,.0f} ₸",
                parse_mode="Markdown"
            )
            
        elif text == "📊 Статистика":
            await report_handler.handle_stats_request(message)
            
        elif text == "📋 Отчет":
            await report_handler.handle_report_request(message)
            
        elif text == "🗑 Удалить":
            await delete_handler.handle_delete_last(message)
        
        elif text == "👑 Админка" and is_admin:
            # Детальная админская панель
            try:
                stats = db_manager.get_user_stats()
                users_list = db_manager.get_detailed_users_list()
                
                # Сначала отправляем общую статистику
                await message.answer(
                    f"👑 АДМИНСКАЯ ПАНЕЛЬ\n\n"
                    f"📊 Общая статистика:\n"
                    f"👥 Всего пользователей: {stats['total']}\n"
                    f"🟢 Активных за 7 дней: {stats['active_7d']}\n"
                    f"🆕 Новых за 30 дней: {stats['new_30d']}\n\n"
                    f"⚙️ Управление:\n"
                    f"• Логи: sudo journalctl -u finance-bot -f\n"
                    f"• Статус: sudo systemctl status finance-bot"
                )
                
                # Затем отправляем список пользователей (простой формат)
                if users_list:
                    users_info = []
                    for user in users_list[:10]:
                        user_id_info = user['user_id']
                        username = f"@{user['username']}" if user['username'] else "без username"
                        first_name = user['first_name'] or "Имя не указано"
                        
                        # Получаем статистику транзакций
                        user_stats = db_manager.get_user_transaction_stats(user_id_info)
                        
                        # Простое форматирование без markdown
                        balance_str = f"{user_stats['balance']:,.0f}"
                        
                        user_info = (
                            f"ID: {user_id_info}\n"
                            f"Имя: {first_name}\n"
                            f"Username: {username}\n"
                            f"Баланс: {balance_str} тенге\n"
                            f"Операций: {user_stats['transactions']}"
                        )
                        users_info.append(user_info)
                    
                    # Отправляем по частям если много пользователей
                    users_text = "\n\n".join(users_info)
                    
                    if len(users_text) > 3500:
                        # Разбиваем на части
                        for i in range(0, len(users_list[:10]), 3):
                            chunk_users = users_list[i:i+3]
                            chunk_info = []
                            
                            for user in chunk_users:
                                user_id_info = user['user_id']
                                username = f"@{user['username']}" if user['username'] else "без username"
                                first_name = user['first_name'] or "Имя не указано"
                                user_stats = db_manager.get_user_transaction_stats(user_id_info)
                                balance_str = f"{user_stats['balance']:,.0f}"
                                
                                user_info = (
                                    f"ID: {user_id_info}\n"
                                    f"Имя: {first_name}\n"
                                    f"Username: {username}\n"
                                    f"Баланс: {balance_str} тенге\n"
                                    f"Операций: {user_stats['transactions']}"
                                )
                                chunk_info.append(user_info)
                            
                            chunk_text = "\n\n".join(chunk_info)
                            await message.answer(f"👤 ПОЛЬЗОВАТЕЛИ (часть {i//3 + 1}):\n\n{chunk_text}")
                    else:
                        await message.answer(f"👤 СПИСОК ПОЛЬЗОВАТЕЛЕЙ:\n\n{users_text}")
                else:
                    await message.answer("👤 Пользователи не найдены")
                    
            except Exception as e:
                await message.answer(f"❌ Ошибка получения данных: {str(e)}")
                print(f"Ошибка админки: {e}")
        
        elif text == "📈 Аналитика" and is_admin:
            # Создаем детальную аналитику в TXT файле
            await message.answer("📊 Генерирую детальную аналитику...")
            
            # Создаем аналитический отчет
            report_path = await self._create_admin_analytics_report(db_manager)
            
            # Отправляем файл
            if report_path and os.path.exists(report_path):
                from aiogram.types import FSInputFile
                document = FSInputFile(report_path)
                await message.answer_document(
                    document,
                    caption="📈 **Детальная аналитика бота**\n\nВсе данные и статистика использования",
                    parse_mode="Markdown"
                )
                
                # Удаляем временный файл
                os.remove(report_path)
            else:
                await message.answer("❌ Ошибка создания аналитики")
            
        elif text == "ℹ️ Помощь":
            help_text = (
                "🤖 **Финансовый бот с AI**\n\n"
                "**💡 Как пользоваться:**\n"
                "• Просто пишите транзакции: `обед 1500`\n"
                "• Используйте кнопки для быстрого доступа\n"
                "• Бот автоматически определяет категории\n\n"
                "**🎯 Примеры транзакций:**\n"
                "• `кофе 400` - расход на еду\n"
                "• `зарплата 200000` - доход\n"
                "• `120 000 кредит` - выплата кредита\n"
                "• `такси 1500` - транспорт\n\n"
                "**🔒 Приватность:**\n"
                "Ваши данные видите только вы!\n\n"
                "**🤖 AI помощник:**\n"
                "Дает персональные советы и анализ ваших трат."
            )
            
            # Добавляем админскую информацию только для админа
            if is_admin:
                help_text += (
                    "\n\n👑 **Админские функции:**\n"
                    "• Статистика всех пользователей\n"
                    "• Общая аналитика транзакций\n"
                    "• Мониторинг системы"
                )
            
            await message.answer(help_text, parse_mode="Markdown")
        
        else:
            # Если текст не совпадает с кнопками - это транзакция
            return False  # Вернуть False чтобы обработать как транзакцию
        
        return True  # Вернуть True если кнопка обработана
    
    async def _create_admin_analytics_report(self, db_manager) -> str:
        """Создание детального аналитического отчета для админа"""
        
        import sqlite3
        import os
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Дата создания отчета
        report_date = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        # === ОБЩАЯ СТАТИСТИКА ===
        cursor.execute("SELECT COUNT(*) FROM transactions")
        total_transactions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM transactions")
        active_users_with_transactions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_registered = cursor.fetchone()[0]
        
        # === АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ ===
        # Активные за последние 7 дней
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE last_activity >= datetime('now', '-7 days')
        """)
        active_7d = cursor.fetchone()[0]
        
        # Новые за последние 30 дней
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE registration_date >= datetime('now', '-30 days') 
            OR (registration_date IS NULL AND created_at >= datetime('now', '-30 days'))
        """)
        new_30d = cursor.fetchone()[0]
        
        # Средние операции на пользователя
        avg_operations = round(total_transactions / max(active_users_with_transactions, 1), 1)
        
        # === ПОПУЛЯРНЫЕ КАТЕГОРИИ ===
        cursor.execute("""
            SELECT category, COUNT(*) as count, 
                   ROUND(COUNT(*) * 100.0 / ?, 1) as percentage
            FROM transactions 
            WHERE transaction_type = 'expense'
            GROUP BY category 
            ORDER BY count DESC 
            LIMIT 10
        """, (total_transactions,))
        
        popular_categories = cursor.fetchall()
        
        # === СЕГМЕНТАЦИЯ ПОЛЬЗОВАТЕЛЕЙ ===
        cursor.execute("""
            SELECT 
                user_id,
                COUNT(*) as trans_count
            FROM transactions 
            GROUP BY user_id
            ORDER BY trans_count DESC
        """)
        
        user_segments = cursor.fetchall()
        high_activity = len([u for u in user_segments if u[1] >= 10])
        medium_activity = len([u for u in user_segments if 3 <= u[1] < 10])
        low_activity = len([u for u in user_segments if u[1] < 3])
        inactive_users = total_registered - len(user_segments)
        
        # === ВРЕМЕННАЯ АКТИВНОСТЬ (последние 7 дней) ===
        cursor.execute("""
            SELECT 
                date(created_at) as day,
                COUNT(*) as operations
            FROM transactions 
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY date(created_at)
            ORDER BY day DESC
        """)
        
        daily_activity = cursor.fetchall()
        
        # === ДОХОДЫ И РАСХОДЫ ПО ДНЯМ ===
        cursor.execute("""
            SELECT 
                date(created_at) as day,
                SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as expense
            FROM transactions 
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY date(created_at)
            ORDER BY day DESC
        """)
        
        financial_activity = cursor.fetchall()
        
        # === AI ЭФФЕКТИВНОСТЬ (примерная) ===
        # Считаем сколько транзакций обработано AI
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category != 'другое'")
        ai_categorized = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category = 'другое'")
        ai_uncategorized = cursor.fetchone()[0]
        
        ai_success_rate = round((ai_categorized / max(total_transactions, 1)) * 100, 1)
        
        conn.close()
        
        # === ФОРМИРОВАНИЕ ОТЧЕТА ===
        report_content = f"""
═══════════════════════════════════════════════════════════════
                    АДМИНСКАЯ АНАЛИТИКА БОТА
═══════════════════════════════════════════════════════════════
Дата создания: {report_date}

📊 ОБЩАЯ СТАТИСТИКА
───────────────────────────────────────────────────────────────
👥 Всего пользователей:          {total_registered:>10}
🟢 Активных за 7 дней:           {active_7d:>10}
🆕 Новых за 30 дней:             {new_30d:>10}
📈 Пользователей с транзакциями:  {active_users_with_transactions:>10}
💼 Всего операций:               {total_transactions:>10}
📊 Среднее операций/пользователь: {avg_operations:>10}

👥 СЕГМЕНТАЦИЯ ПОЛЬЗОВАТЕЛЕЙ
───────────────────────────────────────────────────────────────
🔥 Активные (≥10 операций):     {high_activity:>10} чел.
⚡ Умеренные (3-9 операций):    {medium_activity:>10} чел.
🌱 Новички (1-2 операции):      {low_activity:>10} чел.
😴 Без операций:                {inactive_users:>10} чел.

🏆 ПОПУЛЯРНЫЕ КАТЕГОРИИ РАСХОДОВ
───────────────────────────────────────────────────────────────
"""
        
        for i, (category, count, percentage) in enumerate(popular_categories, 1):
            report_content += f"{i:>2}. {category:<15} {count:>8} операций ({percentage:>5}%)\n"
        
        report_content += f"""
📅 АКТИВНОСТЬ ПО ДНЯМ (последние 7 дней)
───────────────────────────────────────────────────────────────
"""
        
        for day, operations in daily_activity:
            day_name = datetime.fromisoformat(day).strftime('%d.%m (%A)')[:12]
            report_content += f"{day_name:<12} {operations:>5} операций\n"
        
        report_content += f"""
💰 ФИНАНСОВАЯ АКТИВНОСТЬ ПО ДНЯМ
───────────────────────────────────────────────────────────────
"""
        
        for day, income, expense in financial_activity:
            day_name = datetime.fromisoformat(day).strftime('%d.%m')
            income_str = f"{income:,.0f}" if income else "0"
            expense_str = f"{expense:,.0f}" if expense else "0"
            report_content += f"{day_name}  Доход: {income_str:>12} ₸  Расход: {expense_str:>12} ₸\n"
        
        report_content += f"""
🤖 AI ЭФФЕКТИВНОСТЬ
───────────────────────────────────────────────────────────────
✅ Корректно категоризовано:     {ai_categorized:>10} ({ai_success_rate}%)
❓ Неопределенная категория:     {ai_uncategorized:>10} ({100-ai_success_rate:.1f}%)

📋 ТОП ПОЛЬЗОВАТЕЛИ ПО АКТИВНОСТИ
───────────────────────────────────────────────────────────────
"""
        
        # Добавляем топ пользователей
        for i, (user_id, trans_count) in enumerate(user_segments[:10], 1):
            # Получаем имя пользователя
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
            user_info = cursor.fetchone()
            conn.close()
            
            if user_info:
                name = user_info[0] or "Без имени"
                username = f"@{user_info[1]}" if user_info[1] else "без username"
                report_content += f"{i:>2}. {name:<12} {username:<15} {trans_count:>3} операций\n"
        
        report_content += f"""

═══════════════════════════════════════════════════════════════
                        КОНЕЦ ОТЧЕТА
═══════════════════════════════════════════════════════════════
"""
        
        # Сохраняем отчет
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"admin_analytics_{timestamp}.txt"
        filepath = f"temp/{filename}"
        
        # Создаем директорию если не существует
        os.makedirs("temp", exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            return filepath
        except Exception as e:
            print(f"Ошибка создания отчета: {e}")
            return None
