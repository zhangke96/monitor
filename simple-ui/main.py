from datetime import datetime, timedelta
from typing import List

import plotly.express as px
import plotly.offline as pltof
import pymongo
from flask import Flask, render_template, request as HttpRequest
from pandas import DataFrame
from selfusepy.log import Logger, LogTimeUTCOffset

app = Flask(__name__, template_folder = "templates", static_folder = "static")
app.debug = True

log = Logger(time_offset = LogTimeUTCOffset.UTC8).logger
db_session = pymongo.MongoClient(host = "localhost")
db = db_session["test"]
table = db["table"]


@app.route("/index", methods = ["GET"])
def test1():
    """
    以分钟为粒度
    :return:
    """
    log.info("index")
    if HttpRequest.args.__len__() == 0:
        return render_template("index.html")

    r_date: datetime = datetime.fromisoformat(HttpRequest.args.get("date"))
    date: datetime = datetime(year = r_date.year, month = r_date.month, day = r_date.day)

    data: List[dict] = list()
    for item in table.find({
        "status.capture_time": {
            "$lt": date + timedelta(hours = 24),
            "$gt": date
        }
    }):
        if item["status"]["capture_time"].timestamp() % 60 == 0:
            data.append(item)

    if data.__len__() < 1:
        return render_template("index.html", div = "no data")

    df_data: List[dict] = list()
    for i, item in enumerate(data):
        status: dict = item["status"]
        temp: dict = {"client": item["client"], "date": status["capture_time"],
                      "cpu使用率": 0 if status.get("cpu_usage", None) is None else status["cpu_usage"],
                      "cpu_number": status["cpu_number"], "memory_usage": status["memory_usage"],
                      "memory_cap": status["memory_cap"],
                      "内存使用率": status["memory_usage"] / status["memory_cap"] * 100
                      }
        df_data.append(temp)

    del data
    df: DataFrame = DataFrame(df_data)

    if "CPU" in HttpRequest.args.get("type", None):
        fig = px.line(df, x = "date", y = "cpu使用率", color = "client")
    else:
        fig = px.line(df, x = "date", y = "内存使用率", color = "client")

    div = pltof.plot(fig, output_type = "div", include_plotlyjs = "cdn")
    return render_template("index.html", div = div)
