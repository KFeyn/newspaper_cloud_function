import requests
from bs4 import BeautifulSoup
import datetime
import logging
import re
import os
import json

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s+3h - %(levelname)s - %(name)s - %(message)s",
)
YESTERDAY = datetime.date.today() - datetime.timedelta(days=1)
channels = ['gopractice', 'productgames', 'vladimir_merkushev', 'hardclient', 'eto_analytica', 'ba_and_sa',
            'whoisdutytoday', 'aioftheday', 'artificial_stupid', 'chartomojka', 'ProductAnalytics', 'ruspm',
            'renat_alimbekov', 'product_science', 'productanalyticsfordummies', 'revealthedata', 'PMlifestyle',
            'exp_fest']


def send_to_channel(message: str, date: datetime.date) -> None:
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = '-1002043722333'

    date = date.strftime('%Y-%m-%d')
    message += f'\n\n {date}'
    params = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    response = requests.post(url, params=params)
    if response.status_code == 200:
        logger.info(f'Message for {date} sent successfully')
    else:
        logger.info(f'Telegram sending returned code {response.status_code} and error:\n {response.text}')


def parse_channel(channel: str, date: datetime.date) -> str:
    channel_texts = []
    channel_name = ''
    result = requests.get(f'https://t.me/s/{channel}')
    if result.status_code == 200:
        soup = BeautifulSoup(result.text.replace('<br/>', '\n').replace('<br>', '\n'), 'html.parser')
        data = soup.find_all('div', {'class': 'tgme_widget_message_bubble'})[::-1]
        channel_name = soup.find('title').text.split('–')[0]

        for article in data:
            article_dt_html = article.find('a', {'class': 'tgme_widget_message_date'})
            article_dt = datetime.datetime.strptime(article_dt_html.time['datetime'][:10], '%Y-%m-%d').date()
            link = article_dt_html['href']
            if article_dt < date:
                break
            elif article_dt == date:
                article_html = article.find('div', {'class': 'tgme_widget_message_text js-message_text'})
                if article_html and 'erid' not in article_html.text.lower():
                    article_name = article_html.get_text(separator=' ').split('\n')[0].replace('*', '')
                    channel_texts.append('- ' + article_name + f' [ссылка]({link})')
                elif article_html and 'erid' in article_html.text.lower():
                    pass
                elif article.find('div', {'class': 'message_media_not_supported_wrap'}):
                    channel_texts.append('- ' + 'Лонгрид' + f' [ссылка]({link})')
                else:
                    pass
            else:
                pass
        logger.info(f'We successfully parsed channnel {channel} and got {len(channel_texts)} posts')
    else:
        logger.info(f'Channel {channel} returned code {result.status_code} and error:\n {result.text}')

    answer_text = '' if len(channel_texts) == 0 else f'*{channel_name}*\n' + '\n'.join(channel_texts) + '\n\n'
    return re.sub(r'(?![\n])\s{2,}', ' ', answer_text)


def make_short_finals(text: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_TOKEN')}"
    }
    proxies = {
        'http': os.getenv('STRING_PR'),
        'https': os.getenv('STRING_PR')
    }

    content = f"""У меня есть список сообщений вида:  
    Название канала
    - Выжимка из сообщения. Ссылка на сообщение
    - Выжимка из сообщения. Ссылка на сообщение
    
    Название канала
    - Выжимка из сообщения. Ссылка на сообщение
    - Выжимка из сообщения. Ссылка на сообщение
    
    Выбери 5 самых релевантных для продуктового аналитика, отранжируй их по релевантности и выведи их в формате:
    1) Выжимка из сообщения. Ссылка на сообщение
    2) Выжимка из сообщения. Ссылка на сообщение
    
    Удали пусые строчки и не давай никаких других комменариев, выведи только сообщения. 
    Список сообщений:\n {str(text)}"""

    payload = {
        'messages': [
            {
                'role': 'user',
                'content': content
            }
        ],
        'model': 'gpt-3.5-turbo-0125'
    }

    response = requests.post('https://api.openai.com/v1/chat/completions', json=payload, headers=headers,
                             proxies=proxies)

    if response.status_code == 200:
        answer = response.json()['choices'][0]['message']['content']
        logger.info('Summarizing done successfully')
    else:
        logger.info(f'OpenAI returned code {response.status_code} and error:\n {response.text}')
        answer = None
    return answer


def ya_gpt(text: str) -> str:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Api-Key {os.getenv('YAGPT_TOKEN')}"
    }
    system_context = """
    У меня есть список сообщений вида:  
    Название канала
    - Заголовок сообщения ссылка на сообщение
    - Заголовок сообщения ссылка на сообщение
    
    Название канала
    - Заголовок сообщения ссылка на сообщение
    - Заголовок сообщения ссылка на сообщение
    
    Выбери 5 самых актуальных для аналитика данных с точки зрения тематики заголовка сообщений на твой взгляд.
    Ввыведи их в следующем формате, без пустых строчек:
    1) Заголовок сообщения ссылка на сообщение
    2) Заголовок сообщения ссылка на сообщение
    
    Не пиши больше ничего, кроме выводимых заголовков и ссылок, не давай никаких комментариев.
    """

    user_context = f'Список сообщений:\n {str(text)}'
    prompt = {
        'modelUri': f"gpt://{os.getenv('YAGPT_CATALOG')}/yandexgpt",
        'completionOptions': {
            'temperature': 0.2,
            'maxTokens': "2000"
        },
        'messages': [
            {
                'role': 'system',
                'text': system_context
            },
            {
                'role': 'user',
                'text': user_context
            }

        ]
    }
    url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
    response = requests.post(url, headers=headers, json=prompt)
    if response.status_code == 200:
        answer = response.json()['result']['alternatives'][0]['message']['text']
        logger.info('Summarizing done successfully')
    else:
        logger.info(f'YaGPT returned code {response.status_code} and error:\n {response.text}')
        answer = None
    return answer


def habr_top() -> str:
    article_texts = '*Хабр*\n'
    response = requests.get('https://habr.com/ru/articles/top/daily/')
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('h2', {'class': 'tm-title tm-title_h2'})
        cnt = 0
        for article in articles:
            name = article.find('span').text
            link = 'https://habr.com' + article.find('a')['href']
            article_texts += f'- {name} [ссылка]({link})\n'
            cnt += 1

        logger.info(f'We got {cnt} links from habr')
    else:
        logger.info(f'Habr returned code {response.status_code} and error:\n {response.text}')

    return article_texts


def tds_top(date: datetime.date) -> str:
    article_texts = '*TDS*\n'
    headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://towardsdatascience.com",
                "Referer": "https://towardsdatascience.com/latest",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/121.0.0.0 Safari/537.36",
                "X-Xsrf-Token": "1"
    }
    response = requests.post('https://medium.com/towards-data-science/load-more?sortBy=latest&limit=50',
                             headers=headers)
    if response.status_code == 200:
        articles = json.loads(response.text[16:])['payload']['value']
        cnt = 0
        for article in articles:
            art_date = datetime.datetime.utcfromtimestamp(article['firstPublishedAt']/1000).date()
            if art_date < date:
                break
            elif art_date == date:
                name = article['title']
                link = 'https://freedium.cfd/' + 'https://towardsdatascience.com/' + article['uniqueSlug']
                article_texts += f'- {name} [ссылка]({link})\n'
                cnt += 1
            else:
                pass

        logger.info(f'We got {cnt} links from tds')
    else:
        logger.info(f'TDS returned code {response.status_code} and error:\n {response.text}')

    return article_texts


text_from_channels = ''
for channel in channels:
    text_from_channels += parse_channel(channel, YESTERDAY)

text_from_channels += habr_top() + '\n\n' + tds_top(YESTERDAY) + '\n\n'

text_recommended = make_short_finals(text_from_channels)
final_text = '*Топ 5 релевантных:*\n' + text_recommended + '\n\n\n' + text_from_channels
send_to_channel(final_text, YESTERDAY)
