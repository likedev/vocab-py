import pymysql

connection = pymysql.connect(host='localhost',
                             user='root',
                             password='root',
                             database='vocab',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)


def insert_record( record):
    with connection.cursor() as cursor:
        sql = "INSERT INTO words (word, video_local, video_url, s, p, start, end, title) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (
            record['word'], record['video_local'], record['video_url'], record['s'], record['p'], record['start'],
            record['end'], record['title']))
        connection.commit()


def query_all_records(conn):
    """
    查询所有记录。

    :param conn: 数据库连接对象。
    :return: 查询结果，字典列表格式。
    """
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        sql = "SELECT * FROM words"
        cursor.execute(sql)
        result = cursor.fetchall()
        return result


# 使用示例
if __name__ == '__main__':
    # 数据库连接配置，请根据实际情况修改

    # 插入记录示例
    new_record = {
        'word': 'example',
        'video_local': '/path/to/video',
        'video_url': 'http://example.com/video',
        's': 1,
        'p': 2,
        'start': 123456789,
        'end': 123456799,
        'title': 'Example Title'
    }
    insert_record(connection, new_record)

    # 查询所有记录
    records = query_all_records(connection)
    print(records)

    # 关闭数据库连接
    connection.close()
