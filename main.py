import requests
from bs4 import BeautifulSoup
import datetime
import logging
import re
import os
import json
import typing as tp
# TODO: rewrite through different files
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s+3h - %(levelname)s - %(name)s - %(message)s",
)
YESTERDAY = datetime.date.today() - datetime.timedelta(days=1)
channels = ['gopractice', 'productgames', 'vladimir_merkushev', 'hardclient', 'eto_analytica', 'ba_and_sa',
            'whoisdutytoday', 'aioftheday', 'artificial_stupid', 'chartomojka', 'ProductAnalytics', 'ruspm',
            'renat_alimbekov', 'product_science', 'productanalyticsfordummies', 'revealthedata', 'PMlifestyle',
            'exp_fest', 'data_publication', 'thisisdata', 'cryptovalerii']


# TODO: rewrite through asyncio
def make_request(request_type: str = 'get', **kwargs) -> tp.Optional[requests.Response]:
    attempts = 0
    while attempts < 5:
        if request_type == 'get':
            response = requests.get(**kwargs)
        elif request_type == 'post':
            response = requests.post(**kwargs)
        else:
            raise Exception("Invalid request_type")

        if response.status_code == 200:
            return response
        else:
            logger.info(f'Url {kwargs.get("url")} returned code {response.status_code}, error:\n {response.text} at '
                        f'attempt {attempts}\n\n')
            attempts += 1
    return None


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
    make_request(request_type='post', url=url, params=params)
    logger.info(f'Message for {date} sent successfully')


# TODO: check if meme
def parse_channel(channel: str, date: datetime.date) -> str:
    channel_texts = []

    result = make_request(url=f'https://t.me/s/{channel}')
    if result:
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
                if article_html and 'erid' not in article_html.text.lower() and not \
                        re.search('реклама.*ооо', article_html.text.lower()):
                    article_name = article_html.get_text(separator=' ').split('\n')[0].replace('*', '')
                    channel_texts.append('- ' + article_name + f' [ссылка]({link})')
                elif article_html and 'erid' in article_html.text.lower() and \
                        re.search('реклама.*ооо', article_html.text.lower()):
                    pass
                elif article.find('div', {'class': 'message_media_not_supported_wrap'}) \
                        and len(list(article.children)) == 9:
                    channel_texts.append('- ' + 'Лонгрид' + f' [ссылка]({link})')
                else:
                    pass
            else:
                pass
        logger.info(f'We successfully parsed channnel {channel} and got {len(channel_texts)} posts')

        answer_text = '' if len(channel_texts) == 0 else f'*{channel_name}*\n' + '\n'.join(channel_texts) + '\n\n'
        return re.sub(r'(?![\n])\s{2,}', ' ', answer_text)
    else:
        return ''


def make_short_finals(prompt: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_TOKEN')}"
    }
    proxies = {
        'http': os.getenv('STRING_PR'),
        'https': os.getenv('STRING_PR')
    }

    payload = {
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'model': 'gpt-3.5-turbo-0125'
    }

    response = make_request(request_type='post', url='https://api.openai.com/v1/chat/completions', json=payload,
                            headers=headers, proxies=proxies)
    if response:
        answer = response.json()['choices'][0]['message']['content']
        logger.info('Prompt done successfully')

        return answer
    else:
        return ''


def habr_top() -> str:
    article_texts = '*Хабр*\n'
    article_set = set()
    hub_list = ['machine_learning', 'productpm', 'mobileanalytics', 'python', 'research', 'maths', 'sql', 'bigdata',
                'opendata', 'natural_language_processing', 'data_visualization', 'data_engineering', 'data_mining']

    for hub in hub_list:
        response = make_request(url=f'https://habr.com/ru/hubs/{hub}/articles/top/daily/')
        if response:
            hub_cnt = 0
            soup = BeautifulSoup(response.text, 'html.parser')

            articles = soup.find_all('h2', {'class': 'tm-title tm-title_h2'})
            for article in articles:
                hub_cnt += 1
                name = article.find('span').text
                link = 'https://habr.com' + article.find('a')['href']
                article_set.add(f'- {name} [ссылка]({link})')
            logger.info(f'We got {hub_cnt} links from hub {hub}')

    article_texts += '\n'.join(article_set)
    logger.info(f'We got {len(article_set)} links from habr')

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
    proxies = {
        'http': os.getenv('STRING_PR'),
        'https': os.getenv('STRING_PR')
    }
    response = make_request(request_type='post',
                            url='https://medium.com/towards-data-science/load-more?sortBy=latest&limit=50',
                            headers=headers, proxies=proxies)
    if response:
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

        return article_texts
    else:
        return ''


text_from_channels = ''
for channel in channels:
    text_from_channels += parse_channel(channel, YESTERDAY)
text_from_channels += habr_top() + '\n\n' + tds_top(YESTERDAY) + '\n\n'
prompt = f"""У меня есть список сообщений вида:  
Название канала
- Выжимка из сообщения. Ссылка на сообщение
- Выжимка из сообщения. Ссылка на сообщение

Название канала
- Выжимка из сообщения. Ссылка на сообщение
- Выжимка из сообщения. Ссылка на сообщение

Выбери 5 самых релевантных для продуктового аналитика, отранжируй их по релевантности с точки зрения скиллов 
(python, SQL, знание продукта, теория вероятности, machine learning, A/B тесты, эксперименты) и выведи их в формате:
1) Выжимка из сообщения. Ссылка на сообщение
2) Выжимка из сообщения. Ссылка на сообщение

Удали пустые строчки и не давай никаких других комментариев, выведи только сообщения, без группировки по каналам и
названий каналов.
Список сообщений:\n {str(text_from_channels)}"""

text_recommended = make_short_finals(prompt)
final_text = '*Топ 5 релевантных:*\n' + text_recommended + '\n\n\n' + text_from_channels
send_to_channel(final_text, YESTERDAY)
