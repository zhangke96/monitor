FROM uhub.service.ucloud.cn/library/python
ADD ./ /root
WORKDIR /root
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
ENTRYPOINT python /root/ping_monitor_server.py
