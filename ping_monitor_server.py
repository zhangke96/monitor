import asyncio, logging, sys, os
from functools import partial
from ping_monitor import ping_impl as Ping
import time
from typing import MutableMapping
from rpc import rpc_server
from rpc.rpc_server import make_response
from rpc import message_pb2 as protocol
from ping_monitor.record_manage import RecordManage

import logging

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='ping.log', level=logging.DEBUG, format=LOG_FORMAT)

# ping_hosts = MutableMapping[str, Ping]
ping_hosts = {}
record_manage = RecordManage()

def address_reporter(hostname: str, address: str):
  pass

def record_reporter(hostname: str, time: int, delay: int):
  """
  time: 监控的时间戳
  delay: 延迟时间, us
  """
  print(hostname, time, delay)
  record_manage.add_record(hostname, time, delay)

def add_monitor_host(hostname: str):
  ping = Ping.Ping(hostname)
  reporter = partial(record_reporter, hostname)
  ping.set_reporter(reporter)
  ping.start()
  ping_hosts[hostname] = ping

def ManageHandle(message: protocol.Message):
  response = make_response(message, protocol.PING_MONITOR_MANAGE_RESPONSE)
  response_body = response.body.ping_monitor_manage_response
  if not message.body.HasField("ping_monitor_manage_request"):
    response_body.retcode.retcode = protocol.FAIL
    response_body.retcode.error_message = "no body"
  else:
    action = message.body.ping_monitor_manage_request.action
    hostname = message.body.ping_monitor_manage_request.hostname
    if action == protocol.LIST_ALL_MONITOR:
      if len(ping_hosts) == 0:
        response_body.retcode.retcode = protocol.EMPTY
        response_body.retcode.error_message = "empty"
      else:
        for k in ping_hosts:
          response_body.hostnames.append(k)
        response_body.retcode.retcode = protocol.SUCCESS
        response_body.retcode.error_message = "success"
    elif action == protocol.START_MONITOR:
      if len(hostname) == 0:
        response_body.retcode.retcode = protocol.FAIL
        response_body.retcode.error_message = "hostname empty"
      elif hostname in ping_hosts:
        response_body.retcode.retcode = protocol.SUCCESS
        response_body.retcode.error_message = "exists"
      else:
        add_monitor_host(hostname)
        response_body.retcode.retcode = protocol.SUCCESS
        response_body.retcode.error_message = "success"
    elif action == protocol.STOP_MONITOR:
      if len(hostname) == 0:
        response_body.retcode.retcode = protocol.FAIL
        response_body.retcode.error_message = "hostname empty"
      elif not hostname in ping_hosts:
        response_body.retcode.retcode = protocol.NOT_EXIST
        response_body.retcode.error_message = "not exist"
      else:
        ping_hosts[hostname].stop()
        del ping_hosts[hostname]
        response_body.retcode.retcode = protocol.SUCCESS
        response_body.retcode.error_message = "stopped"
  print(response)
  return response

def GetRecordHandle(message: protocol.Message):
  response = make_response(message, protocol.PING_MONITOR_GET_RECORD_RESPONSE)
  response_body = response.body.ping_monitor_get_record_response
  if not message.body.HasField("ping_monitor_get_record_request"):
    response_body.retcode.retcode = protocol.FAIL
    response_body.retcode.error_message = "no body"
  else:
    hostname = message.body.ping_monitor_get_record_request.hostname
    if not hostname in ping_hosts:
      response_body.retcode.retcode = protocol.NOT_EXIST
      response_body.retcode.error_message = "not exists"
    else:
      monitor_records = record_manage.get_record(hostname)
      response_body.records.extend(monitor_records)
  print(response)
  return response

if __name__ == '__main__':
  server = rpc_server.RpcServer('0.0.0.0', 8888)
  server.register_handle(protocol.PING_MONITOR_MANAGE_REQUEST, ManageHandle)
  server.register_handle(protocol.PING_MONITOR_GET_RECORD_REQUEST, GetRecordHandle)
  server.start()

  loop = asyncio.get_event_loop()
  loop.run_forever()
