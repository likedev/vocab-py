import json

import pymysql
import requests
from bs4 import BeautifulSoup
import re

LIST_DATA = None


def load_eap_list_json():
    global LIST_DATA
    if LIST_DATA is None:
        LIST_DATA = json.load(open('D:/code/py/video-eng-words/data/eap_list.json', 'r'))
    return LIST_DATA


def get_eap_word_map(min_freq=-1):
    data = load_eap_list_json()
    if min_freq > 0:
        data = data[min_freq:]
    res = {}
    for it in data:
        res[it['word']] = it
    return res


def get_alias_map(min_freq=-1):
    data = load_eap_list_json()
    if min_freq > 0:
        data = data[min_freq:]
    alias_map = {}
    for it in data:
        alias_map[it['word']] = it['word']
        for alias in it['related']:
            alias_map[alias[0]] = it['word']
    return alias_map


def parse_related_words(related_words_raw):
    # abnormal(807), abnormalities(442), abnormality(283), abnormally(149)
    # 移除所有空格和括号
    clean_str = related_words_raw.replace(' ', '').replace(")", "")
    # 以逗号分割字符串
    parts = clean_str.split(',')
    related_words = []
    for part in parts:
        sps = part.split('(')
        related_words.append((sps[0].strip(), int(sps[1].strip())))

    return related_words


def fetch_and_parse_data(url):
    print("要抓url", url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    print("code", response.status_code)
    soup = BeautifulSoup(response.content, 'html.parser')

    data = []
    tables = soup.find_all('table', class_='offset')
    for table in tables:
        rows = table.find_all('tr')
        print("tr count", len(rows))
        first = True
        for row in rows:
            if first:
                first = False
                continue
            cols = row.find_all('td')
            if len(cols) == 4:
                category = cols[0].text.strip()
                word = cols[1].text.strip()
                related_words_raw = cols[2].get_text(separator=" ").replace(u'\xa0', u' ')
                frequency = cols[3].text.strip()
                # 解析 related_words
                related_words = parse_related_words(related_words_raw)

                data.append((category, word, related_words, int(frequency)))
    return data


urls = [
    "https://www.eapfoundation.com/vocab/general/bnccoca/tablecontsAresizeXXXX.php?type=v2&limit=3k",
    "https://www.eapfoundation.com/vocab/general/bnccoca/tablecontsAresizeXXXX.php?type=v2&limit=9k",
    "https://www.eapfoundation.com/vocab/general/bnccoca/tablecontsAresizeXXXX.php?type=v2&limit=25k",
]


def crawlEapfoundation():
    words_data = []
    for url in urls:
        temp_l = fetch_and_parse_data(url)
        print("抓取数量", len(temp_l))
        words_data.extend(temp_l)
    words_data.sort(key=lambda x: x[3], reverse=True)

    print("总数量", len(words_data))

    ll = []
    for item in words_data:
        ll.append({
            "category": item[0],
            "word": item[1],
            "related": item[2],
            "frequency": item[3]
        })

    json.dump(ll, open('../data/eap_list.json', 'w'))


if __name__ == '__main__':
    import pprint
    import json

    load_eap_list_json()

    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='root',
        db='vocab',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with connection.cursor() as cursor:
            for it in load_eap_list_json():
                tier = int(it['category'].replace('k', ''))
                freq = it['frequency']
                related_words = json.dumps(it['related'], ensure_ascii=False)
                word = it['word']

                sql = """INSERT INTO vocab (word, tier, related, freq, status)
                        VALUES (%s, %s, %s, %s, %s)
                                """
                cursor.execute(sql, (word, tier, related_words, freq, 'init'))
            connection.commit()
    finally:
        connection.close()
