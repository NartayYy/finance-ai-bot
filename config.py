# config.py
import os
from dataclasses import dataclass, field
from typing import List

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Config:
    """Конфигурация бота"""

    # API ключи (из .env файла)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")

    # База данных
    DATABASE_PATH: str = "data/finance_bot.db"

    # AI настройки (выбираем провайдера)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "groq")  # groq или openrouter

    # Groq настройки
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # OpenRouter настройки (обновленные модели)
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Временно отключить AI если проблемы с SSL
    DISABLE_AI: bool = os.getenv("DISABLE_AI", "false").lower() == "true"

    # Разрешенные пользователи - теперь динамически из базы
    ADMIN_USERS: List[int] = field(default_factory=lambda: [143463970])  # Только админы (ты)

    # Автоматическая регистрация новых пользователей  
    AUTO_REGISTRATION: bool = os.getenv("AUTO_REGISTRATION", "true").lower() == "true"

    # Требовать регистрацию через /start
    REQUIRE_REGISTRATION: bool = os.getenv("REQUIRE_REGISTRATION", "false").lower() == "true"

    # Категории транзакций
    INCOME_CATEGORIES = [
        "зарплата", "фриланс", "возврат", "долг вернули", "премия", 
        "подарок", "инвестиции", "продажа", "аванс", "доход"
    ]

    EXPENSE_CATEGORIES = {
        "еда": ["обед", "ужин", "завтрак", "кафе", "ресторан", "продукты", "доставка", "мак"],
        "транспорт": ["бензин", "такси", "автобус", "метро", "парковка", "штраф", "заправка"],
        "жилье": ["аренда", "коммунальные", "ремонт", "мебель", "электричество", "квартплата"],
        "развлечения": ["кино", "игры", "концерт", "бар", "клуб", "развлечения"],
        "здоровье": ["аптека", "врач", "лекарства", "больница", "анализы"],
        "одежда": ["одежда", "обувь", "магазин", "торговый центр"],
        "образование": ["курсы", "книги", "обучение", "семинар"],
        "финансы": ["кредит", "займ", "долг", "проценты", "комиссия", "банк", "выплата"],
        "другое": []
    }

# .env файл (создать отдельно)
"""
BOT_TOKEN=your_telegram_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
"""
