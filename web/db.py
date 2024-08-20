import pymysql
from pymysql.cursors import DictCursor


class Database:
    def __init__(self):
        # 数据库配置
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
            'database': 'vocab',
            'charset': 'utf8mb4'
        }
        self.connection = pymysql.connect(**db_config, cursorclass=DictCursor)

    def query(self, sql, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute(self, sql, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            self.connection.commit()
            return cursor.rowcount

    def close(self):
        self.connection.close()
