from db import Database
from datetime import datetime
import random
from datetime import datetime, timedelta

'''
逻辑
unfamilar  不认识
vague 模糊
rem 记住了
master 掌握了



[下一个 card]

每个 batch 结束才能下一个batch
今日的下一个
1. (rem_cnt < 3 & learned)
2. (!learned)

[batch 来源：]
陌生单词： ( status in ('init','unfamiliar') )
记过单词： ( task_batch 出现过，但是 不是 master,obscure )

-- 程序化判定通过： 在两周内有三次以上的 rem_cnt > 3
'''

db = Database()

G_masterd_words = set()

status_map = {
    'bad': '不熟悉',
    'init': '没学过',
    'unfamiliar': '不熟悉',
    "vague": "模糊",
    'obscure': '太偏，不学',
    'rem': '记得',
    'master': '已掌握'
}


def today_progress():
    def get_cnt(sql):
        data = db.query(sql)
        return data[0]['cnt']

    today_str = datetime.today().strftime('%Y-%m-%d')
    master_sql = "select count(*) as cnt from task where  (status in  ('obscure','master') or rem_cnt >=3) and day = '%s' " % today_str
    learned_sql = "select count(distinct word) as cnt from learn_log where ctime >= '%s' " % today_str
    total_sql = " select count(*) as cnt from task where day = '%s' " % today_str
    return {
        "total": get_cnt(total_sql),
        "learned": get_cnt(learned_sql),
        "master": get_cnt(master_sql)
    }


def time_ago(past_time):
    now = datetime.now()
    diff = now - past_time

    if diff < timedelta(minutes=1):
        return "刚刚"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} 分钟前"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} 小时前"
    else:
        days = diff.days
        return f"{days} 天前"


def load_mastered_words():
    global G_masterd_words
    sql = " select word from  vocab where status in ('master','obscure') ";
    data = db.query(sql)
    G_masterd_words = set([it['word'] for it in data])
    return G_masterd_words


def get_today_task_words():
    today_str = datetime.today().strftime('%Y-%m-%d')
    sql = " select * from task where day = '%s' " % today_str
    data = db.query(sql)
    return data


def generate_next_batch(new_num=200, review_num=100):
    import random

    load_mastered_words()
    today_str = datetime.today().strftime('%Y-%m-%d')

    # 今天已经产生的任务
    prev_data = get_today_task_words()
    today_task_words = set([it['word'] for it in prev_data])

    result = []
    global G_masterd_words
    sql = f" select word from vocab where status in ('init','','unfamiliar') and tier >= 4 order by tier asc limit {new_num + 400} "
    new_list = db.query(sql)
    new_words = [it['word'] for it in new_list if it['word'] not in today_task_words]
    random.shuffle(new_words)
    result.extend(new_words[:new_num])

    backtrack_record_cnt = new_num * 30
    sql = f" select word from task order by day desc limit {backtrack_record_cnt} "
    old_list = db.query(sql)
    i = 0
    if old_list:
        random.shuffle(old_list)
        for it in old_list:
            if (it['word'] not in result and it['word'] not in G_masterd_words and
                    it['word'] not in today_task_words):
                result.append(it['word'])
                i = i + 1
                if i >= review_num:
                    break
    print("生成一批的数量", len(result))
    for word in result:
        db.execute(
            "insert into task (day,word,rem_cnt,status) values ('%s','%s',%d,'%s')" % (today_str, word, 0, 'init'))
    return len(result)


# 卡片获取下一个要处理的词
def get_next_card():
    task_words = get_today_task_words()
    if not task_words:
        generate_next_batch()
    task_words = get_today_task_words()

    global G_masterd_words
    filter_task_words = [it for it in task_words if it['status'] != 'master' and it['rem_cnt'] < 3]

    if filter_task_words:
        random.shuffle(filter_task_words)
        return filter_task_words[0]
    return "finish"


def get_word_last_learn_log(word):
    sql = "select * from learn_log where word = '%s' order by ctime desc limit 1" % word
    data = db.query(sql)
    if not data:
        return None
    info = data[0]
    info['time_diff_text'] = time_ago(info['ctime'])
    return info


def get_word_learned_cnt(word):
    sql = "select count(*) as cnt from task where word = '%s' and status != 'init' " % word
    data = db.query(sql)
    if data is None:
        return 0
    return data[0]['cnt']


def get_vocab_detail(word):
    sql_word = "SELECT * FROM vocab WHERE word = '%s' "
    word_details = db.query(sql_word % (word))
    if word_details:
        info = word_details[0]
        word = info['word']
        info['last_learn'] = get_word_last_learn_log(word)
        info['learned_cnt'] = get_word_learned_cnt(word)
        info['status_text'] = status_map[info['status']]
        return info
    return None


def add_mem_result(day, word, status):
    sql_insert = "INSERT INTO learn_log (word, status, ctime) VALUES (%s, %s, NOW())"
    sql_update = "UPDATE vocab SET status = %s WHERE word = %s"

    db.execute(sql_insert, (word, status))
    db.execute(sql_update, (status, word))

    global G_masterd_words
    if (status in ('master', 'obscure')):
        G_masterd_words.add(word)

    select_task = " select * from task where day = '%s' and word = '%s' " % (day, word)
    data = db.query(select_task)
    task = data[0]
    rem_cnt = 0
    if status == 'rem':
        rem_cnt = task['rem_cnt'] + 1

    update_task = (" update task set rem_cnt = %d , status = '%s'"
                   " where word = '%s' and day = '%s' ") % (
                      rem_cnt, status, word, day)
    db.execute(update_task)

    return "更新成功:" + word
