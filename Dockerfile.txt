FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY nifty_shop_strategy.py .

CMD ["python", "nifty_shop_strategy.py"]
