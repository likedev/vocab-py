import asyncio
import aiomysql
from config import *


class Database:
    def __init__(self):
        # 数据库配置
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': MYSQL_PASS,
            'db': 'vocab',
            'charset': 'utf8mb4'
        }
        self.pool = None

    async def create_pool(self):
        if not self.pool:
            self.pool = await aiomysql.create_pool(**self.db_config, autocommit=True)

    async def query(self, sql, params=None):
        await self.create_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchall()
        return result

    async def execute(self, sql, params=None):
        await self.create_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                rowcount = cursor.rowcount
        return rowcount

    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()


db = Database()
