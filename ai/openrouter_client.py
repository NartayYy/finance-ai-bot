# ai/openrouter_client.py
import requests
import json
import asyncio
from typing import Dict, List, Optional
from config import Config

class OpenRouterClient:
    """Универсальный AI клиент для Groq и OpenRouter"""
    
    def __init__(self, api_key: str):
        self.config = Config()
        
        # Определяем провайдера
        if self.config.AI_PROVIDER == "groq" and self.config.GROQ_API_KEY:
            self.api_key = self.config.GROQ_API_KEY
            self.base_url = self.config.GROQ_BASE_URL
            self.model = self.config.GROQ_MODEL
            self.provider = "groq"
        else:
            self.api_key = api_key or self.config.OPENROUTER_API_KEY
            self.base_url = self.config.OPENROUTER_BASE_URL
            self.model = self.config.OPENROUTER_MODEL
            self.provider = "openrouter"
        
        # Настройка заголовков
        if self.provider == "groq":
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/finance-ai-bot",
                "X-Title": "Finance AI Bot"
            }
        
        # Отключаем SSL предупреждения
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        print(f"🤖 AI Provider: {self.provider.upper()}")
        print(f"🧠 Model: {self.model}")
    
    async def categorize_transaction(self, description: str, amount: float) -> Dict[str, str]:
        """Определение категории и типа транзакции через AI"""
        
        # Проверяем, отключен ли AI
        if self.config.DISABLE_AI:
            return self._simple_categorize(description, amount)
        
        prompt = f"""
Проанализируй транзакцию и определи тип и категорию:

Описание: "{description}"
Сумма: {amount} ₸

ПРАВИЛА:
- Кредит, займ, долг, выплата по кредиту = РАСХОД (expense), категория "финансы"
- Возврат долга ТЕБЕ, зарплата, премия = ДОХОД (income)
- Еда, транспорт, покупки = РАСХОД (expense)

Категории доходов: зарплата, фриланс, возврат, премия, подарок, инвестиции
Категории расходов: еда, транспорт, жилье, развлечения, здоровье, одежда, образование, финансы, другое

Ответь ТОЛЬКО JSON:
{{"type": "income/expense", "category": "категория"}}
"""
        
        try:
            response = await self._make_request_async(prompt, max_tokens=100)
            # Очищаем ответ от лишних символов
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(clean_response)
            
            return {
                "type": result.get("type", "expense"),
                "category": result.get("category", "другое")
            }
        except Exception as e:
            print(f"Ошибка AI анализа: {e}")
            # Простое определение по ключевым словам как fallback
            return self._simple_categorize(description, amount)
    
    def _simple_categorize(self, description: str, amount: float) -> Dict[str, str]:
        """Простое определение категории без AI (fallback)"""
        description_lower = description.lower()
        
        # Проверяем доходы
        for income_keyword in self.config.INCOME_CATEGORIES:
            if income_keyword in description_lower:
                return {"type": "income", "category": "доход"}
        
        # Проверяем расходы
        for category, keywords in self.config.EXPENSE_CATEGORIES.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return {"type": "expense", "category": category}
        
        # По умолчанию
        if amount > 50000:  # Большие суммы скорее доходы
            return {"type": "income", "category": "доход"}
        else:
            return {"type": "expense", "category": "другое"}
    
    async def analyze_spending(self, transactions: List, period_days: int) -> str:
        """Анализ трат и советы"""
        
        if not transactions:
            return "📊 Недостаточно данных для анализа. Добавьте больше транзакций!"
        
        # Подготавливаем данные для AI
        total_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        total_expense = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        balance = total_income - total_expense
        
        # Группируем по категориям
        categories = {}
        for t in transactions:
            if t.transaction_type == 'expense':
                categories[t.category] = categories.get(t.category, 0) + t.amount
        
        top_expenses = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Проверяем, отключен ли AI
        if self.config.DISABLE_AI:
            return self._simple_analysis(total_income, total_expense, balance, top_expenses, period_days)
        
        prompt = f"""
Проанализируй финансовые данные пользователя за {period_days} дней:

💰 ОБЩАЯ СТАТИСТИКА:
- Доходы: {total_income:,.0f} ₸
- Расходы: {total_expense:,.0f} ₸
- Баланс: {balance:,.0f} ₸

📊 ТОП КАТЕГОРИИ РАСХОДОВ:
{chr(10).join([f"- {cat}: {amount:,.0f} ₸" for cat, amount in top_expenses])}

🎯 ЗАДАЧИ:
1. Дай краткий анализ (2-3 предложения)
2. Найди проблемные зоны трат
3. Дай 3 конкретных совета по экономии
4. Спрогнозируй траты на следующий месяц

Отвечай на русском языке, структурированно и полезно для пользователя из Казахстана.
"""
        
        try:
            response = await self._make_request_async(prompt)
            return response
        except Exception as e:
            print(f"Ошибка AI анализа: {e}")
            return self._simple_analysis(total_income, total_expense, balance, top_expenses, period_days)
    
    def _simple_analysis(self, total_income: float, total_expense: float, balance: float, top_expenses: list, period_days: int) -> str:
        """Простой анализ без AI"""
        
        analysis = f"""
📊 АНАЛИЗ ЗА {period_days} ДНЕЙ

💰 Ваши доходы составили {total_income:,.0f} ₸
💸 Расходы: {total_expense:,.0f} ₸
📈 Итоговый баланс: {balance:,.0f} ₸

"""
        
        if balance > 0:
            analysis += "✅ Отлично! Вы тратите меньше, чем зарабатываете.\n"
        elif balance == 0:
            analysis += "⚖️ Вы тратите ровно столько, сколько зарабатываете.\n"
        else:
            analysis += "⚠️ Внимание! Расходы превышают доходы.\n"
        
        if top_expenses:
            analysis += f"\n📊 Больше всего тратите на: {top_expenses[0][0]} ({top_expenses[0][1]:,.0f} ₸)\n"
        
        analysis += "\n💡 СОВЕТЫ:\n"
        analysis += "• Ведите ежедневный учет трат\n"
        analysis += "• Планируйте бюджет на месяц\n"
        analysis += "• Откладывайте 10% от доходов\n"
        
        return analysis
    
    async def get_spending_advice(self, description: str, amount: float, balance: float) -> str:
        """Персональный совет после транзакции"""
        
        if self.config.DISABLE_AI:
            return ""  # Отключаем советы если AI не работает
        
        prompt = f"""
Пользователь потратил {amount} ₸ на "{description}".
Текущий баланс: {balance:,.0f} ₸

Дай КОРОТКИЙ совет (1-2 предложения) на русском языке:
- Если трата разумная - поддержи
- Если трата большая - дай совет по экономии
- Учитывай баланс пользователя
"""
        
        try:
            response = await self._make_request_async(prompt, max_tokens=100)
            return f"🤖 {response}"
        except:
            return ""
    
    async def _make_request_async(self, prompt: str, max_tokens: int = 500) -> str:
        """Асинхронная обертка для синхронного запроса"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._make_request_sync, prompt, max_tokens)
    
    def _make_request_sync(self, prompt: str, max_tokens: int = 500) -> str:
        """Синхронный запрос к AI API через requests"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30,
                verify=False  # Отключаем SSL проверку
            )
            
            if response.status_code != 200:
                error_text = response.text
                raise Exception(f"API error {response.status_code}: {error_text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
