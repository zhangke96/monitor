import asyncio, getopt, sys, os
from rpc import rpc_client
from rpc.rpc_client import make_request
from rpc import message_pb2 as protocol

def help():
  print('Usage:', sys.argv[0], ' -c [list/start/stop/get] -s hostname')

server = ('127.0.0.1', 8888)

async def manage_request(command, hostname):
  manage_request = make_request(protocol.PING_MONITOR_MANAGE_REQUEST)
  body = manage_request.body.ping_monitor_manage_request
  body.action = command
  body.hostname = hostname
  print(manage_request)

  client = rpc_client.RpcClient()
  result = await client.send_message(server, manage_request)
  print(result)

async def get_record_handle(hostname):
  manage_request = make_request(protocol.PING_MONITOR_GET_RECORD_REQUEST)
  body = manage_request.body.ping_monitor_get_record_request
  body.hostname = hostname
  print(manage_request)

  client = rpc_client.RpcClient()
  result = await client.send_message(server, manage_request)
  print(result)

if __name__ == '__main__':
  try:
    opts, _ = getopt.getopt(sys.argv[1:], "hc:s:", ["command=", "server="])
  except getopt.GetoptError:
    help()
    exit(1)
  command = 0
  hostname = "None"
  get_record = False
  for opt, arg in opts:
    if opt == '-h':
      help()
      exit(0)
    elif opt in ('-c', '--command'):
      if arg == 'list':
        command = protocol.LIST_ALL_MONITOR
      elif arg == 'start':
        command = protocol.START_MONITOR
      elif arg == 'stop':
        command = protocol.STOP_MONITOR
      elif arg == 'get':
        get_record = True
    elif opt in ('-s', '--server'):
      hostname = arg
 
  loop = asyncio.get_event_loop()
  if not get_record:
    loop.run_until_complete(manage_request(command, hostname))
  else:
    loop.run_until_complete(get_record_handle(hostname))

