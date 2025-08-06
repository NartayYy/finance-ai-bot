
FROM python:3.9-slim

WORKDIR /app

# Обход SSL сертификатов
ENV PYTHONHTTPSVERIFY=0
ENV CURL_CA_BUNDLE=""
ENV REQUESTS_CA_BUNDLE=""

COPY requirements.txt .
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
