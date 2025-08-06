# database/db_manager.py
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Transaction:
    """Модель транзакции"""
    id: Optional[int] = None
    user_id: int = None
    amount: float = None
    description: str = None
    category: str = None
    transaction_type: str = None  # 'income' или 'expense'
    created_at: Optional[datetime] = None

class DatabaseManager:
    """Менеджер базы данных SQLite"""
    
    def __init__(self, db_path: str = "data/finance_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица транзакций
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица пользователей (обновленная)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Проверяем и добавляем недостающие колонки в существующую таблицу
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'is_active' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
                
            if 'registration_date' not in columns:
                # Добавляем колонку без DEFAULT, потом заполняем
                cursor.execute("ALTER TABLE users ADD COLUMN registration_date TIMESTAMP")
                # Заполняем существующие записи
                cursor.execute("""
                    UPDATE users SET registration_date = COALESCE(created_at, CURRENT_TIMESTAMP)
                    WHERE registration_date IS NULL
                """)
            
            # Обновляем is_active для всех записей где NULL
            cursor.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
            
            conn.commit()
    
    def register_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Регистрация нового пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO users (user_id, username, first_name, is_active, registration_date, last_activity)
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (user_id, username, first_name))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка регистрации пользователя: {e}")
            return False
    
    def is_user_registered(self, user_id: int) -> bool:
        """Проверка регистрации пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM users WHERE user_id = ? AND (is_active = 1 OR is_active IS NULL)
                """, (user_id,))
            except sqlite3.OperationalError:
                # Fallback для старой структуры
                cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()[0] > 0
    
    def get_user_stats(self) -> dict:
        """Статистика пользователей (для админов)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Пробуем новую структуру
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                total_users = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE is_active = 1 AND last_activity >= datetime('now', '-7 days')
                """)
                active_users = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE is_active = 1 AND registration_date >= datetime('now', '-30 days')
                """)
                new_users = cursor.fetchone()[0]
                
            except sqlite3.OperationalError:
                # Fallback для старой структуры
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE last_activity >= datetime('now', '-7 days')
                """)
                active_users = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= datetime('now', '-30 days')
                """)
                new_users = cursor.fetchone()[0]
            
            return {
                "total": total_users,
                "active_7d": active_users,
                "new_30d": new_users
            }
    
    def get_detailed_users_list(self) -> list:
        """Подробный список пользователей (для админов)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                # Пробуем новую структуру
                cursor.execute("""
                    SELECT 
                        user_id,
                        username,
                        first_name,
                        registration_date,
                        last_activity,
                        is_active
                    FROM users 
                    WHERE is_active = 1 OR is_active IS NULL
                    ORDER BY last_activity DESC
                """)
                
            except sqlite3.OperationalError:
                # Fallback для старой структуры
                cursor.execute("""
                    SELECT 
                        user_id,
                        username,
                        first_name,
                        created_at as registration_date,
                        last_activity,
                        1 as is_active
                    FROM users 
                    ORDER BY last_activity DESC
                """)
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'first_name': row['first_name'],
                    'registration_date': row['registration_date'],
                    'last_activity': row['last_activity'],
                    'is_active': row['is_active']
                })
            
            return users
    
    def get_user_transaction_stats(self, user_id: int) -> dict:
        """Статистика транзакций конкретного пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Количество транзакций
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
            total_transactions = cursor.fetchone()[0]
            
            # Баланс
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) as income,
                    COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) as expense
                FROM transactions 
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            income, expense = result[0], result[1]
            balance = income - expense
            
            # Последняя транзакция
            cursor.execute("""
                SELECT created_at FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            last_transaction = cursor.fetchone()
            last_transaction_date = last_transaction[0] if last_transaction else None
            
            return {
                'transactions': total_transactions,
                'income': income,
                'expense': expense,
                'balance': balance,
                'last_transaction': last_transaction_date
            }
    
    def add_transaction(self, user_id: int, amount: float, description: str, 
                       category: str, transaction_type: str) -> bool:
        """Добавление транзакции"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions (user_id, amount, description, category, transaction_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, amount, description, category, transaction_type))
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка добавления транзакции: {e}")
            return False
    
    def get_user_balance(self, user_id: int) -> float:
        """Получение баланса пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Сумма доходов
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE user_id = ? AND transaction_type = 'income'
            """, (user_id,))
            income = cursor.fetchone()[0]
            
            # Сумма расходов
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE user_id = ? AND transaction_type = 'expense'
            """, (user_id,))
            expenses = cursor.fetchone()[0]
            
            return income - expenses
    
    def get_transactions(self, user_id: int, days: int = 30) -> List[Transaction]:
        """Получение транзакций за период"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC
            """.format(days), (user_id,))
            
            rows = cursor.fetchall()
            transactions = []
            
            for row in rows:
                transactions.append(Transaction(
                    id=row['id'],
                    user_id=row['user_id'],
                    amount=row['amount'],
                    description=row['description'],
                    category=row['category'],
                    transaction_type=row['transaction_type'],
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            
            return transactions
    
    def update_user_activity(self, user_id: int, username: str = None, first_name: str = None):
        """Обновление активности пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_activity)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, username, first_name))
            conn.commit()
    
    def get_category_stats(self, user_id: int, days: int = 30) -> Dict[str, Dict]:
        """Статистика по категориям"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    category,
                    transaction_type,
                    SUM(amount) as total,
                    COUNT(*) as count
                FROM transactions 
                WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
                GROUP BY category, transaction_type
                ORDER BY total DESC
            """.format(days), (user_id,))
            
            stats = {}
            for row in cursor.fetchall():
                category, trans_type, total, count = row
                if category not in stats:
                    stats[category] = {'income': 0, 'expense': 0, 'count': 0}
                
                stats[category][trans_type] = total
                stats[category]['count'] += count
            
            return stats
    
    def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """Удаление транзакции по ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Проверяем, что транзакция принадлежит пользователю
                cursor.execute("""
                    DELETE FROM transactions 
                    WHERE id = ? AND user_id = ?
                """, (transaction_id, user_id))
                
                deleted_rows = cursor.rowcount
                conn.commit()
                return deleted_rows > 0
        except Exception as e:
            print(f"Ошибка удаления транзакции: {e}")
            return False
    
    def get_last_transaction(self, user_id: int) -> Optional[Transaction]:
        """Получение последней транзакции пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return Transaction(
                    id=row['id'],
                    user_id=row['user_id'],
                    amount=row['amount'],
                    description=row['description'],
                    category=row['category'],
                    transaction_type=row['transaction_type'],
                    created_at=datetime.fromisoformat(row['created_at'])
                )
            return None
    
    def get_recent_transactions_for_deletion(self, user_id: int, limit: int = 10) -> List[Transaction]:
        """Получение последних транзакций для удаления"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()
            transactions = []

            for row in rows:
                transactions.append(Transaction(
                    id=row['id'],
                    user_id=row['user_id'],
                    amount=row['amount'],
                    description=row['description'],
                    category=row['category'],
                    transaction_type=row['transaction_type'],
                    created_at=datetime.fromisoformat(row['created_at'])
                ))

            return transactions
