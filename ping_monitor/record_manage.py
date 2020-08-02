from threading import Lock
from rpc.message_pb2 import PingMonitorRecord

class RecordManage():
  def __init__(self):
    self.records_map = {}
    self.lock = Lock()
  
  def delay_same(self, before_delay, now_delay):
    # 判断是否在正负5ms之内
    if before_delay == -1 and now_delay == -1:
      return True
    elif before_delay == -1 and now_delay >= 0:
      return False
    elif before_delay >= 0 and now_delay == -1:
      return False
    elif abs(before_delay - now_delay) <= 5:
      return True
    else:
      return False
  
  def add_new_record(self, monitor_records, hostname, time, delay):
    record = PingMonitorRecord()
    record.address = hostname
    record.begin_time.FromSeconds(int(time))
    record.end_time.FromSeconds(int(time))
    if delay == -1:
      # 超时记录
      record.delay_time = -1
    else:
      record.delay_time = int(delay/1000) 
    monitor_records.append(record)

  def add_record(self, hostname, time, delay):
    monitor_records = []
    with self.lock:
      if not hostname in self.records_map:
        self.records_map[hostname] = []
      monitor_records = self.records_map[hostname]
    if len(monitor_records) == 0:
      self.add_new_record(monitor_records, hostname, time, delay)
    else:
      exist_record = monitor_records[-1]
      # 判断延迟是否有变化
      now_delay = -1
      if not delay == -1:
        now_delay = int(delay/1000)
      if not self.delay_same(exist_record.delay_time, now_delay):
        # 添加新纪录
        self.add_new_record(monitor_records, hostname, time, delay)
      else:
        # 更新时间
        exist_record.end_time.FromSeconds(int(time))

  def get_record(self, hostname):
    monitor_records = []
    with self.lock:
      if hostname in self.records_map:
        monitor_records = self.records_map[hostname]
    return monitor_records
