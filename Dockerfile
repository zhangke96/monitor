FROM uhub.service.ucloud.cn/library/python
ADD ./ /root
WORKDIR /root
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
CMD python /root/ping_monitor_server.py


# FROM uhub.service.ucloud.cn/library/python
# ADD ./requirements.txt /requirements.txt
# WORKDIR /
# RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple/
# CMD python /root/ping_monitor_server.py

# docker run --name monitor -p 8888:8888 -v /home/zhangke/code/monitor:/root zhangke/monitor:v1 python /root/ping_monitor_server.py 172.17.0.1 27017
