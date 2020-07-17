FROM python:3.7-slim-stretch
ADD ./ /home/python
WORKDIR /home/python
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
ENTRYPOINT python /home/python/client/monitor_client.py
