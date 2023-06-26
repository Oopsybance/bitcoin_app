from dotenv import load_dotenv
import os
import requests
import telebot
from alpha_vantage.cryptocurrencies import CryptoCurrencies
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from io import BytesIO
import pandas as pd
from datetime import datetime
import matplotlib
matplotlib.use('Agg')


load_dotenv()


TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_KEY")

bot = telebot.TeleBot(TOKEN)

user_step = {}


def get_btc_price():
    """
    Получает текущую цену биткоина в USD с помощью API Coindesk.

    Returns:
        str: Текущая цена биткоина в USD.
    """
    url = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"
    data = requests.get(url).json()
    price = data["bpi"]["USD"]["rate"]
    return price


def get_btc_news():
    """
    Получает последние новости о биткоине с помощью RSS-канала Google News.

    Returns:
        list: Список новостей в формате словарей с полями 'title', 'link' и 'pubDate'.
    """
    url = "https://news.google.com/rss/search?q=Bitcoin"
    data = requests.get(url).content
    soup = BeautifulSoup(data, 'xml')
    news_items = soup.find_all('item')
    news = []
    for item in news_items[:5]:
        news.append({
            'title': item.title.text,
            'link': item.link.text,
            'pubDate': item.pubDate.text
        })
    return news


def get_historical_data():
    """
    Получает исторические данные о цене биткоина с помощью Alpha Vantage API.

    Returns:
        pandas.DataFrame: Фрейм данных с историческими данными о цене биткоина.
    """
    url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()

    df = pd.DataFrame(data['Time Series (Digital Currency Daily)']).T
    df = df[::-1]  # Реверсируем фрейм данных для получения дат в порядке возрастания.
    df['4a. close (USD)'] = df['4a. close (USD)'].astype(float)  # Преобразуем цены закрытия в числовой формат.

    return df


def get_exchange_rate(from_currency, to_currency):
    """
    Получает обменный курс между двумя валютами с помощью Alpha Vantage API.

    Args:
        from_currency (str): Код валюты, из которой конвертируется.
        to_currency (str): Код валюты, в которую конвертируется.

    Returns:
        float: Обменный курс между двумя валютами.
    """
    base_url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE'
    main_url = f'{base_url}&from_currency={from_currency}&to_currency={to_currency}&apikey={API_KEY}'

    response = requests.get(main_url)
    result = response.json()

    try:
        exchange_rate = result["Realtime Currency Exchange Rate"]['5. Exchange Rate']
        return float(exchange_rate)
    except KeyError:
        print(f'Невозможно найти обменный курс между {from_currency} и {to_currency}.')
        print(f'Ответ от сервера: {result}')
        return None


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """
    Обработчик команды /start и /help.

    Args:
        message (telebot.types.Message): Объект сообщения от пользователя.
    """
    bot.reply_to(message, 'Привет! Я могу сообщить вам текущую цену биткоина, '
                          'отобразить график цен и дать последние новости. Просто напишите '
                          '"цена", "график", "новости" или "перевести" для конвертации биткоина в другую валюту.')


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    """
    Обработчик всех сообщений.

    Args:
        message (telebot.types.Message): Объект сообщения от пользователя.
    """
    if message.text.lower() == 'цена':
        price = get_btc_price()
        bot.send_message(message.chat.id, f"Текущая цена биткоина: {price} USD")
    elif message.text.lower() == 'новости':
        news = get_btc_news()
        for item in news:
            bot.send_message(message.chat.id, f"{item['title']}\n{item['link']}\n{item['pubDate']}")
    elif message.text.lower() == 'график':
        df = get_historical_data()
        plt.figure(figsize=(10, 5))
        dates = [datetime.strptime(date, '%Y-%m-%d') for date in df.index]
        plt.plot_date(dates, df['4a. close (USD)'], '-')
        plt.xlabel('Дата')
        plt.ylabel('Цена (USD)')
        plt.title('Исторический график цены Bitcoin')
        plt.tight_layout()
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        bot.send_photo(message.chat.id, img)


def convert(message):
    """
    Обработчик команды "перевести" для конвертации биткоина в другую валюту.

    Args:
        message (telebot.types.Message): Объект сообщения от пользователя.
    """
    _, amount, to_currency = message.text.split()
    amount = float(amount)
    bitcoin_price_usd = get_btc_price()
    exchange_rate = get_exchange_rate('USD', to_currency)
    converted_amount = amount * bitcoin_price_usd * exchange_rate
    bot.send_message(message.chat.id, f'{amount} BTC = {converted_amount} {to_currency}')


bot.polling()
