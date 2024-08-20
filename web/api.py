from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from db import Database
from fastapi.middleware.cors import CORSMiddleware
import card
from collections import deque

app = FastAPI()
origins = [
    "*"
]

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


# 关闭数据库连接
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6688)
