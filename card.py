from db import Database
from datetime import datetime
import random
from datetime import datetime, timedelta
import openai
import json
from db import *

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


async def today_progress():
    today_str = datetime.today().strftime('%Y-%m-%d')
    master_sql = "select count(*) as cnt from task where (status in ('obscure','master') or rem_cnt >=3) and day = '%s'" % today_str
    learned_sql = "select count(distinct word) as cnt from learn_log where ctime >= '%s'" % today_str
    total_sql = "select count(*) as cnt from task where day = '%s'" % today_str

    async def get_cnt(sql):
        data = await db.query(sql)
        return data[0]['cnt']

    total, learned, master = await asyncio.gather(
        get_cnt(total_sql),
        get_cnt(learned_sql),
        get_cnt(master_sql)
    )
    return {
        "total": total,
        "learned": learned,
        "master": master
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


async def load_mastered_words():
    global G_masterd_words
    sql = " select word from  vocab where status in ('master','obscure') ";
    data = await db.query(sql)
    G_masterd_words = set([it['word'] for it in data])
    return G_masterd_words


async def get_today_task_words():
    today_str = datetime.today().strftime('%Y-%m-%d')
    sql = " select * from task where day = '%s' " % today_str
    data = await db.query(sql)
    return data


async def generate_next_batch(new_num=100, review_num=100):
    import random

    await load_mastered_words()
    today_str = datetime.today().strftime('%Y-%m-%d')

    # 今天已经产生的任务
    prev_data = await get_today_task_words()
    today_task_words = set([it['word'] for it in prev_data])

    result = []
    global G_masterd_words
    sql = f" select word from vocab where status in ('init','','unfamiliar') and tier >= 4 order by tier asc limit {new_num + 400} "
    new_list = await db.query(sql)
    new_words = [it['word'] for it in new_list if it['word'] not in today_task_words]
    random.shuffle(new_words)
    result.extend(new_words[:new_num])

    backtrack_record_cnt = new_num * 30
    sql = f" select word from task order by day desc limit {backtrack_record_cnt} "
    old_list = await db.query(sql)
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
        await db.execute(
            "insert into task (day,word,rem_cnt,status) values ('%s','%s',%d,'%s')" % (today_str, word, 0, 'init'))
    return len(result)


# 卡片获取下一个要处理的词
async def get_next_card():
    task_words = await get_today_task_words()
    if not task_words:
        await generate_next_batch()
    task_words = await get_today_task_words()

    global G_masterd_words
    filter_task_words = [it for it in task_words if it['status'] != 'master' and it['rem_cnt'] < 3]

    if filter_task_words:
        random.shuffle(filter_task_words)
        return filter_task_words[0]
    return "finish"


async def get_word_last_learn_log(word):
    sql = "select * from learn_log where word = '%s' order by ctime desc limit 1" % word
    data = await db.query(sql)
    if not data:
        return None
    info = data[0]
    info['time_diff_text'] = time_ago(info['ctime'])
    return info


async def get_word_learned_cnt(word):
    sql = "select count(*) as cnt from task where word = '%s' and status != 'init' " % word
    data = await db.query(sql)
    if data is None:
        return 0
    return data[0]['cnt']


async def get_vocab_detail(word):
    sql_word = "SELECT * FROM vocab WHERE word = '%s' "
    word_details = await db.query(sql_word % (word))
    if word_details:
        info = word_details[0]
        word = info['word']
        info['last_learn'] = await get_word_last_learn_log(word)
        info['learned_cnt'] = await get_word_learned_cnt(word)
        info['status_text'] = status_map[info['status']]

        freq_data = await db.query(
            " select count(*) as cnt from vocab where freq >= (select freq from vocab where word = '%s') " % word)
        info['freq'] = freq_data[0]['cnt']

        if info['ext']:
            info['ext'] = json.loads(info['ext'])
        return info
    return None


async def add_mem_result(day, word, status):
    sql_insert = "INSERT INTO learn_log (word, status, ctime) VALUES (%s, %s, NOW())"
    sql_update = "UPDATE vocab SET status = %s WHERE word = %s"

    await db.execute(sql_insert, (word, status))
    await db.execute(sql_update, (status, word))

    global G_masterd_words
    if status in ('master', 'obscure'):
        G_masterd_words.add(word)

    select_task = " select * from task where day = '%s' and word = '%s' " % (day, word)
    data = await db.query(select_task)
    task = data[0]
    rem_cnt = 0
    if status == 'rem':
        rem_cnt = task['rem_cnt'] + 1

    update_task = (" update task set rem_cnt = %d , status = '%s'"
                   " where word = '%s' and day = '%s' ") % (
                      rem_cnt, status, word, day)
    await db.execute(update_task)

    return "更新成功:" + word


async def get_learn_stats():
    # Define SQL queries
    sql_learn_cnt = "SELECT COUNT(DISTINCT word) as learn_cnt FROM learn_log"
    sql_master_cnt = """
    SELECT COUNT(*) as master_cnt FROM vocab 
    WHERE status = 'master' 
    OR word IN (
        SELECT word FROM (
            SELECT word, 
                   SUM(CASE WHEN status IN ('rem', 'master') THEN 1 ELSE 0 END) as rem_master_count,
                   COUNT(*) as total_count
            FROM (
                SELECT word, status,
                       ROW_NUMBER() OVER (PARTITION BY word ORDER BY ctime DESC) as rn
                FROM learn_log
            ) as recent_logs
            WHERE rn <= 5
            GROUP BY word
            HAVING rem_master_count = total_count
        ) as mastered_words
    )
    """
    sql_study_stats = """
    SELECT 
        COUNT(DISTINCT DATE(ctime)) as study_days,
        SUM(CASE WHEN duration <= 180 THEN duration ELSE 0 END) / 3600 as study_hours,
        COUNT(DISTINCT CASE WHEN duration <= 180 THEN word END) as total_words_learned
    FROM (
        SELECT 
            word,
            ctime,
            TIMESTAMPDIFF(SECOND, 
                LAG(ctime) OVER (PARTITION BY DATE(ctime) ORDER BY ctime), 
                ctime
            ) as duration
        FROM learn_log
    ) as log_with_duration
    WHERE duration IS NOT NULL
    """
    # Execute queries in parallel
    learn_cnt_result, master_cnt_result, study_stats_result = await asyncio.gather(
        db.query(sql_learn_cnt),
        db.query(sql_master_cnt),
        db.query(sql_study_stats)
    )
    # Process results
    learn_cnt = learn_cnt_result[0]['learn_cnt'] if learn_cnt_result else 0
    master_cnt = master_cnt_result[0]['master_cnt'] if master_cnt_result else 0
    study_stats = study_stats_result[0] if study_stats_result else {'study_days': 0, 'study_hours': 0,
                                                                    'total_words_learned': 0}

    study_days = study_stats['study_days']
    study_hours = round(study_stats['study_hours'], 2)
    study_hours_avg_day = round(study_hours / study_days, 2) if study_days > 0 else 0
    learn_cnt_avg_day = round(study_stats['total_words_learned'] / study_days, 2) if study_days > 0 else 0

    return {
        'learn_cnt': learn_cnt,
        'master_cnt': master_cnt,
        'study_hours': study_hours,
        'study_days': study_days,
        'study_hours_avg_day': study_hours_avg_day,
        'learn_cnt_avg_day': learn_cnt_avg_day
    }


async def generate_ai_note(word: str) -> str:
    """Generate an AI note for a given word."""
    prompt = f"如何记忆英语单词:{word},从词根，词的来源，词的故事，近义词，近形词，什么时候适用 等角度说明"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "辅助中国人学习英语，返回结果使用中文"},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error generating AI note for word '{word}': {str(e)}")
        return ""


async def update_word_ai_note(word: str):
    """Update or insert AI note for a word in the vocab table."""
    ai_note = await generate_ai_note(word)
    if not ai_note:
        return
    # First, try to get the existing ext data
    sql_select = "SELECT ext FROM vocab WHERE word = %s"
    result = await db.query(sql_select, (word,))

    if result:
        # Word exists, update the ext column
        ext_data = json.loads(result[0]['ext'] or '{}')
        ext_data['ai_note'] = ai_note
        sql_update = "UPDATE vocab SET ext = %s WHERE word = %s"
        await db.execute(sql_update, (json.dumps(ext_data), word))
    else:
        # Word doesn't exist, insert a new row
        ext_data = {'ai_note': ai_note}
        sql_insert = "INSERT INTO vocab (word, ext) VALUES (%s, %s)"
        await db.execute(sql_insert, (word, json.dumps(ext_data)))

    print(f"AI note updated for word: {word}")
