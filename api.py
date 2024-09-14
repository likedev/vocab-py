import time
from typing import Dict, List
from db import *
from fastapi.middleware.cors import CORSMiddleware
import card
from collections import deque
from pathlib import Path
from datetime import datetime
from fastapi import File, UploadFile
import uuid
from config import *
import json
from fastapi import Query
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
import asyncio
import vocab

app = FastAPI()
origins = [
    "*"
]

UPLOAD_DIR = Path(UPLOAD_DIR_PATH)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()


# 请求体模型
class LearnLog(BaseModel):
    day: str
    word: str
    status: str


def ok_data(data):
    return {"code": 0, "data": data}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 检查文件是否为空
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # 根据当前时间生成子目录
    year_dir = datetime.now().strftime("%Y")
    month_day_dir = datetime.now().strftime("%m%d")
    target_dir = UPLOAD_DIR / year_dir / month_day_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    # 生成随机文件名，保留原始扩展名
    file_extension = file.filename.split('.')[-1]
    random_filename = f"{uuid.uuid4()}.{file_extension}"

    # 构建文件保存路径
    file_path = target_dir / random_filename

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(await file.read())

    base = "http://pic.xfunpark.com/"
    url = f"{base}{year_dir}/{month_day_dir}/{random_filename}"

    # 返回文件的路径或 URL
    return ok_data({"url": url})


@app.get("/word/{word}")
async def get_word_details(word: str) -> Dict:
    return ok_data(await card.get_vocab_detail(word))


@app.post("/add_mem_result")
async def learn_word(log: LearnLog) -> Dict:
    result = await card.add_mem_result(log.day, log.word, log.status)
    return ok_data(result)


@app.post("/gen-batch")
async def gen_batch() -> Dict:
    gen_num = await card.generate_next_batch()
    return ok_data(gen_num)


G_prev_set = deque(maxlen=3)


@app.get("/card/next")
async def get_next_word() -> Dict:
    global G_prev_set
    word = ''
    for i in range(3):
        word = await card.get_next_card()
        if word == "finish":
            return ok_data(word)
        if word['word'] in G_prev_set:
            continue
        break
    G_prev_set.append(word)
    return ok_data(word)


@app.get("/logs/date")
async def get_logs_by_date(date: str) -> List[Dict]:
    sql = "SELECT * FROM learn_log WHERE DATE(ctime) = %s"
    logs = await db.query(sql, (date,))
    return logs


@app.get("/today_progress")
async def get_progress():
    data = await card.today_progress()
    return ok_data(data)


@app.post("/auth/login")
def admin_login(data: Dict) -> Dict:
    if data["username"] == "xxd" and data["password"] == "889977":
        result = {
            "accessToken": "123",
            "desc": "desc",
            "realName": "realName",
            "refreshToken": "123",
            "userId": "123",
            "username": "超级小蛋"
        }
        return ok_data(result)
    return ok_data("failed")


@app.get("/auth/codes")
def auth_codes():
    result = ["AC_100100", "AC_100030", "AC_1000001"]
    return ok_data(result)


@app.get("/logs/count")
async def get_logs_count_by_date(date: Optional[str] = None, status: Optional[str] = None) -> Dict:
    sql = "SELECT DATE(ctime) as date, COUNT(*) as count FROM learn_log WHERE 1=1"
    params = []
    if date:
        sql += " AND DATE(ctime) = %s"
        params.append(date)
    if status:
        sql += " AND status = %s"
        params.append(status)
    sql += " GROUP BY DATE(ctime)"

    logs_count = await db.query(sql, params)
    return {"logs_count": logs_count}


@app.get("/user/info")
def get_user_info() -> Dict:
    map = {}
    map["desc"] = "简单描述"
    map['homePath'] = "google.com"
    map['token'] = "123"
    map["avatar"] = "https://i.pravatar.cc/150?u=a042581f4e29026704d"
    map["realName"] = "真名哈啊哈"
    map["roles"] = ["super", "admin"]
    map["userId"] = "123"
    map["username"] = "超级小蛋"
    return ok_data(map)


class TypeDataItem(BaseModel):
    id: int = None  # 可选的id参数
    type: str
    data: dict  # 数据作为 JSON 字典


# 插入数据
@app.post("/type_data/")
async def create_or_update_data(item: TypeDataItem):
    try:
        # 将 data 字典转换为 JSON 字符串
        json_data = json.dumps(item.data)
        if item.id and item.id > 0:
            # 如果提供了 id 参数，检查 id 是否存在且类型是否匹配
            check_sql = "SELECT * FROM type_data WHERE id = %s"
            result = await db.query(check_sql, (item.id,))
            if not result:
                raise HTTPException(status_code=404, detail="Record with given id not found.")

            # 检查类型是否匹配
            if result[0]['type'] != item.type:
                raise HTTPException(status_code=400, detail="Type mismatch.")
            # 更新记录
            update_sql = "UPDATE type_data SET data = %s WHERE id = %s"
            await db.execute(update_sql, (json_data, item.id))
            return ok_data({"id": item.id, "message": "Record updated successfully."})

        else:
            # 如果没有提供 id，插入新记录
            insert_sql = "INSERT INTO type_data (type, data) VALUES (%s, %s)"
            data_id = await db.execute(insert_sql, (item.type, json_data))
            return ok_data({"id": data_id, "message": "Record created successfully."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


'''
CREATE TABLE IF NOT EXISTS type_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(255) NOT NULL,
    data TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

'''


# 查询所有数据
@app.get("/get_type_data/")
async def read_data_by_type(type: str, id: Optional[int] = Query(None)):
    try:
        # 基础 SQL 语句，根据 type 进行查询
        sql = "SELECT id, type, data FROM type_data WHERE type = %s"
        params = [type]

        # 如果传递了 id 参数，则添加到查询条件中
        if id is not None and id > 0:
            sql += " AND id = %s"
            params.append(id)
        # 执行查询
        result = await db.query(sql, params)
        # 检查是否有返回结果
        if not result:
            raise HTTPException(status_code=404, detail="No records found.")

        res_list = []
        for it in result:
            if it['data']:
                info = json.loads(it['data'])
                info['id'] = it['id']
                info['type'] = it['type']
                res_list.append(info)
        return ok_data(res_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query_by_sql")
async def query_by_sql(body: Dict):
    return ok_data(await db.query(body['sql']))


def get_system_info():
    import psutil
    import platform
    import shutil
    uname = platform.uname()
    memory_info = psutil.virtual_memory()
    cpu_usage = psutil.cpu_percent(interval=1)
    disk_usage = shutil.disk_usage("/")
    swap_info = psutil.swap_memory()
    load_avg = psutil.getloadavg()

    return [
        {"title": "系统", "value": uname.system},
        {"title": "节点名称", "value": uname.node},
        {"title": "发布版本", "value": uname.release},
        {"title": "版本", "value": uname.version},
        {"title": "机器类型", "value": uname.machine},
        {"title": "处理器", "value": uname.processor},
        {"title": "内存总量", "value": f"{memory_info.total / (1024 ** 3):.2f} GB"},
        {"title": "已用内存", "value": f"{memory_info.used / (1024 ** 3):.2f} GB"},
        {"title": "空闲内存", "value": f"{memory_info.free / (1024 ** 3):.2f} GB"},
        {"title": "内存占用率", "value": f"{memory_info.percent} %"},
        {"title": "CPU占用率", "value": f"{cpu_usage} %"},
        {"title": "磁盘总量", "value": f"{disk_usage.total / (1024 ** 3):.2f} GB"},
        {"title": "已用磁盘", "value": f"{disk_usage.used / (1024 ** 3):.2f} GB"},
        {"title": "空闲磁盘", "value": f"{disk_usage.free / (1024 ** 3):.2f} GB"},
        {"title": "磁盘占用率", "value": f"{(disk_usage.used / disk_usage.total) * 100:.2f} %"},
        {"title": "交换分区总量", "value": f"{swap_info.total / (1024 ** 3):.2f} GB"},
        {"title": "已用交换分区", "value": f"{swap_info.used / (1024 ** 3):.2f} GB"},
        {"title": "交换分区占用率", "value": f"{swap_info.percent} %"},
        {"title": "平均负载 (1分钟)", "value": f"{load_avg[0]:.2f}"},
        {"title": "平均负载 (5分钟)", "value": f"{load_avg[1]:.2f}"},
        {"title": "平均负载 (15分钟)", "value": f"{load_avg[2]:.2f}"}
    ]


@app.get("/system_info")
def read_system_info():
    return get_system_info()


class Bookmark(BaseModel):
    url: str = "",
    title: str = "",
    cover: str = "",
    favicon: str = "",
    content: str = "",
    time: str = ""


def extract_meta_content(soup, names):
    for name in names:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        if tag and tag.get("content"):
            return tag["content"]
    return None


def extract_favicon(soup, url):
    # 优先选择 favicon 的顺序
    favicon_link = soup.find("link", rel="icon")
    if not favicon_link:
        favicon_link = soup.find("link", rel="apple-touch-icon")
    if not favicon_link:
        favicon_link = soup.find("link", rel="shortcut icon")

    if favicon_link and favicon_link.get("href"):
        favicon_url = favicon_link["href"]
        # 如果 favicon 链接是相对路径，则将其转换为绝对路径
        return urljoin(url, favicon_url)

    # 如果未找到上述 favicon，则返回默认 favicon.ico
    parsed_url = urlparse(url)
    return urljoin(f"{parsed_url.scheme}://{parsed_url.netloc}", "favicon.ico")


@app.post("/create_bookmark")
async def create_bookmark(data: Dict):
    url = data['url']
    print("输入参数", url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url)
            content = await page.content()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error fetching page: {e}")
        finally:
            await browser.close()

    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(content, 'html.parser')

    # 提取标题
    title = extract_meta_content(soup, ['og:title']) or soup.title.string if soup.title else ''

    # 提取描述，考虑多种元标签
    description = extract_meta_content(soup, ['description', 'og:description', 'twitter:description'])

    favicon = extract_favicon(soup, url)
    # 提取封面图
    cover = extract_meta_content(soup, ['twitter:image', 'og:image', 'image'])

    if not cover:
        cover = favicon

    # 获取当前时间
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d")
    result = {
        "url": url,
        "title": title,
        "cover": cover,
        "favicon": favicon,
        "content": description,
        "time": current_time
    }
    import pprint
    pprint.pprint(result)
    return ok_data(result)


class MemoCreate(BaseModel):
    title: str
    content: str


class MemoItem(BaseModel):
    id: int
    title: str


@app.post("/memo/")
async def create_memo(memo: MemoCreate):
    sql = "INSERT INTO memo (title, content) VALUES (%s, %s)"
    rowcount = await db.execute(sql, (memo.title, memo.content))
    if rowcount == 0:
        raise HTTPException(status_code=400, detail="Failed to create memo")
    return ok_data({"message": "Memo created successfully"})


@app.get("/memos/")
async def get_memos():
    sql = "SELECT id, title FROM memo"
    result = await db.query(sql)
    return ok_data(result)


@app.get("/memo/{memo_id}")
async def get_memo(memo_id: int):
    sql = "SELECT content FROM memo WHERE id = %s"
    result = await db.query(sql, (memo_id,))
    if not result:
        raise HTTPException(status_code=404, detail="Memo not found")
    return ok_data({"content": result[0]['content']})


class KLCardCreate(BaseModel):
    title: str
    content: str
    images: List[str] = []


@app.post("/kl_card/")
async def create_kl_card(card: KLCardCreate):
    sql = "INSERT INTO kl_card (title, content, images) VALUES (%s, %s, %s)"
    rowcount = await db.execute(sql, (card.title, card.content, ','.join(card.images)))
    if rowcount == 0:
        raise HTTPException(status_code=400, detail="Failed to create knowledge card")
    return ok_data({"message": "Knowledge card created successfully"})


@app.get("/kl_cards/")
async def get_kl_cards():
    sql = "SELECT id, title, created_at, updated_at FROM kl_card"
    result = await db.query(sql)
    return ok_data(result)


@app.get("/kl_card/{card_id}")
async def get_kl_card(card_id: int):
    sql = "SELECT * FROM kl_card WHERE id = %s"
    result = await db.query(sql, (card_id,))
    if not result:
        raise HTTPException(status_code=404, detail="Knowledge card not found")
    return ok_data(result[0])


@app.get("/learn_stats")
async def get_learn_stats_api():
    stats = await card.get_learn_stats()
    return ok_data(stats)


@app.post("/update_word_ai_note/{word}")
async def update_word_ai_note_api(word: str):
    try:
        await card.update_word_ai_note(word)
        return ok_data({"message": f"AI note updated for word: {word}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating AI note: {str(e)}")


# Import the router from the book module
from book import router as book_router

# Include the book router in the main FastAPI app
app.include_router(book_router)


# Startup event handler
@app.on_event("startup")
async def startup_event():
    await vocab.initialize_vocab()

    print("Application startup complete")


# 关闭数据库连接
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6688)
