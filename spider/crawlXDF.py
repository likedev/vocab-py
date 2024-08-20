import requests
from bs4 import BeautifulSoup

import time


def fetch_words_from_url(url):
    """
    从给定的 URL 中抓取单词和相应的链接。

    :param url: 要抓取的网页 URL。
    :return: 单词和链接的列表。
    """

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, 'html.parser')

    time.sleep(1)
    words = []
    for word_box in soup.find_all('div', class_='word-box'):
        for a in word_box.find_all('a', class_='word'):
            word = a.text.strip()
            link = 'https://www.koolearn.com' + a['href']
            words.append((word, link))

    return words


# 抓取的 URL 列表
urls = [
    'https://www.koolearn.com/dict/tag_2429_1.html',
    'https://www.koolearn.com/dict/tag_2429_2.html',
    'https://www.koolearn.com/dict/tag_2429_3.html',

    'https://www.koolearn.com/dict/tag_2457_1.html',
    'https://www.koolearn.com/dict/tag_2457_2.html',
    'https://www.koolearn.com/dict/tag_2457_3.html',
    'https://www.koolearn.com/dict/tag_2457_4.html',
    'https://www.koolearn.com/dict/tag_2457_5.html',
]

# 遍历每个 URL 并抓取数据
for url in urls:
    words = fetch_words_from_url(url)
    for word, link in words:
        print(f"{word}: {link}")
