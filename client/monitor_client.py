from asyncio.streams import StreamReader, StreamWriter
# from client.rpc_client import RpcClient
from os import write
import sys, getopt, os, time, asyncio, random
import message_pb2 as protocol
import rpc_client
from typing import MutableMapping, Tuple
from google.protobuf.timestamp_pb2 import Timestamp

def help():
  print('Usage:', sys.argv[0], " -k auth_key -s server_ip:server_port")

def parse_server(server_str, split=','):
  # 127.0.0.1:1000,tencent.zhangke.ste:1000
  split_result = server_str.split(split)
  servers = []
  for single_server_str in split_result:
    server_port = single_server_str.split(':')
    if len(server_port) != 2:
      continue
    else:
      servers.append((server_port[0], int(server_port[1])))
  return servers

auth_key = ''

def main():
  global auth_key, servers
  try:
    opts, _ = getopt.getopt(sys.argv[1:], "hk:s:", ["auth_key=", "server="])
  except getopt.GetoptError:
    help()
    exit(1)
  for opt, arg in opts:
    if opt == '-h':
      help()
      exit(0)
    elif opt in ('-k', '--auth_key'):
      auth_key = arg
    elif opt in ('-s', '--server'):
      server_str = arg
      servers = parse_server(server_str)
  if auth_key == '':
    print("no auth_key")
    exit(2)
  elif len(servers) == 0:
    print("no valid server")
    exit(3)

last_cpu_use_info = []

def get_cpu_info():
  with open('/proc/stat', 'r') as stat_file:
    now_time = time.time()
    cpu_usage = 0
    cpu_number = 0
    while True:
      cpu_use_info_str = stat_file.readline()
      if not cpu_use_info_str.startswith('cpu'):
        break
      cpu_use_info_split_result = cpu_use_info_str.split(' ')
      if cpu_use_info_split_result[0] == 'cpu':
        # total usage
        cpu_use_info = []
        cpu_use_info.append(now_time)
        # user
        cpu_use_info.append(int(cpu_use_info_split_result[2]))
        # nice
        cpu_use_info.append(int(cpu_use_info_split_result[3]))
        # system
        cpu_use_info.append(int(cpu_use_info_split_result[4]))
        # idle
        cpu_use_info.append(int(cpu_use_info_split_result[5]))
        global last_cpu_use_info
        if len(last_cpu_use_info) != 0:
          # 计算CPU使用率
          idle_increase = cpu_use_info[4] - last_cpu_use_info[4]
          used_incresse = cpu_use_info[1] + cpu_use_info[2] + cpu_use_info[3] - last_cpu_use_info[1] - last_cpu_use_info[2] - last_cpu_use_info[3]
          cpu_usage = int(100 * used_incresse / (used_incresse + idle_increase))
        last_cpu_use_info = cpu_use_info
      else:
        cpu_number += 1
  return (cpu_usage, cpu_number)

def get_mem_info():
  with open('/proc/meminfo', 'r') as memory_file:
    memory_info = {}
    contents = memory_file.readlines()
    for content_line in contents:
      split_result = content_line.split(':')
      if len(split_result) == 2:
        key = split_result[0]
        value_str = split_result[1].strip()
        value_split_result = value_str.split()
        if len(value_split_result) == 2:
          value = int(value_split_result[0])
          unit = value_split_result[1]
          assert(unit == 'kB')
          memory_info[key] = value
    total_mem = 0  # MB
    usage = 0      # 使用百分比
    if 'MemTotal' in memory_info and 'MemFree' in memory_info:
      memory_total = memory_info['MemTotal']
      total_mem = int(memory_total / 1024)
      memory_free = memory_info['MemFree']
      memory_used = memory_total - memory_free
      usage = int(memory_used * 100 / memory_total)
    return (total_mem, usage)

def get_load_avg():
  with open('/proc/loadavg', 'r') as load_avg_file:
    load_str = load_avg_file.readline()
    load_split_result = load_str.split(' ')
    return float(load_split_result[0])

flow_no = 1

def make_request(message_type: protocol.MessageType) -> protocol.Message:
  message = protocol.Message()
  message.head.version = 1
  message.head.random_num = random.randint(1, 2**32 - 1)
  global flow_no
  message.head.flow_no = flow_no
  flow_no += 1
  message.head.message_type = message_type
  message.head.request = True
  message.head.auth_key = auth_key
  print(message)
  return message

servers = []

async def status_report():
  client = rpc_client.RpcClient()
  while True:
    await asyncio.sleep(1)
    mem_info = get_mem_info()
    cpu_info = get_cpu_info()
    load_avg = get_load_avg()
    status_report_request = make_request(protocol.STATUS_REPORT_REQUEST)
    body = status_report_request.body.status_report_request
    body.capture_time.GetCurrentTime()
    body.cpu_number = cpu_info[1]
    body.memory_cap = mem_info[0]
    body.load = load_avg
    body.cpu_usage = cpu_info[0]
    body.memory_usage = mem_info[1]
    result = await client.send_message(servers[0], status_report_request)
    print(result)

if __name__ == '__main__':
  main()
  get_cpu_info()
  status_report_request = protocol.StatusReportRequest()
  status_report_request.cpu_number = 1
  print(status_report_request.SerializeToString())
  loop = asyncio.get_event_loop()
  loop.run_until_complete(status_report())


# 使用asyncio
# 打开链接超时如何处理
# asyncio.open_connection()
# 发送数据超时如何处理
# 链接断开如何感知
