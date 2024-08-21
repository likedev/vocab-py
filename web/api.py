from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from db import *
from fastapi.middleware.cors import CORSMiddleware
import card
from collections import deque
from pathlib import Path
import os
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
import uuid
from config import *
import json
from fastapi import FastAPI, HTTPException, Query
from typing import Optional

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
def get_word_details(word: str) -> Dict:
    return ok_data(card.get_vocab_detail(word))


@app.post("/add_mem_result")
def learn_word(log: LearnLog) -> Dict:
    result = card.add_mem_result(log.day, log.word, log.status)
    return ok_data(result)


@app.post("/gen-batch")
def gen_batch() -> Dict:
    gen_num = card.generate_next_batch()
    return ok_data(gen_num)


G_prev_set = deque(maxlen=3)


@app.get("/card/next")
def get_next_word() -> Dict:
    global G_prev_set
    word = ''
    for i in range(3):
        word = card.get_next_card()
        if word == "finish":
            return ok_data(word)
        if word['word'] in G_prev_set:
            continue
        break
    G_prev_set.append(word)
    return ok_data(word)


@app.get("/logs/date")
def get_logs_by_date(date: str) -> List[Dict]:
    sql = "SELECT * FROM learn_log WHERE DATE(ctime) = %s"
    logs = db.query(sql, (date,))
    return logs


@app.get("/today_progress")
def get_progress():
    data = card.today_progress()
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
def get_logs_count_by_date(date: Optional[str] = None, status: Optional[str] = None) -> Dict:
    sql = "SELECT DATE(ctime) as date, COUNT(*) as count FROM learn_log WHERE 1=1"
    params = []
    if date:
        sql += " AND DATE(ctime) = %s"
        params.append(date)
    if status:
        sql += " AND status = %s"
        params.append(status)
    sql += " GROUP BY DATE(ctime)"

    logs_count = db.query(sql, params)
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
def create_or_update_data(item: TypeDataItem):
    try:
        # 将 data 字典转换为 JSON 字符串
        json_data = json.dumps(item.data)
        if item.id:
            # 如果提供了 id 参数，检查 id 是否存在且类型是否匹配
            check_sql = "SELECT * FROM type_data WHERE id = %s"
            result = db.query(check_sql, (item.id,))
            if not result:
                raise HTTPException(status_code=404, detail="Record with given id not found.")

            # 检查类型是否匹配
            if result[0]['type'] != item.type:
                raise HTTPException(status_code=400, detail="Type mismatch.")
            # 更新记录
            update_sql = "UPDATE type_data SET data = %s WHERE id = %s"
            db.execute(update_sql, (json_data, item.id))
            return ok_data({"id": item.id, "message": "Record updated successfully."})

        else:
            # 如果没有提供 id，插入新记录
            insert_sql = "INSERT INTO type_data (type, data) VALUES (%s, %s)"
            data_id = db.execute(insert_sql, (item.type, json_data))
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
def read_data_by_type(type: str, id: Optional[int] = Query(None)):
    try:
        # 基础 SQL 语句，根据 type 进行查询
        sql = "SELECT id, type, data FROM type_data WHERE type = %s"
        params = [type]

        # 如果传递了 id 参数，则添加到查询条件中
        if id is not None:
            sql += " AND id = %s"
            params.append(id)
        # 执行查询
        result = db.query(sql, params)
        # 检查是否有返回结果
        if not result:
            raise HTTPException(status_code=404, detail="No records found.")

        return ok_data(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 关闭数据库连接
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6688)
