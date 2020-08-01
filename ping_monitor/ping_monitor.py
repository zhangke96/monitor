import ping_impl as Ping
import time
ping = Ping.Ping("www.baidu.com")
ping.start()
ping2 = Ping.Ping("www.taobao.com")
ping2.start()

time.sleep(10)
