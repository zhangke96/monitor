import rpc_server
import asyncio
import message_pb2 as protocol

def StatusReportHandle(message: protocol.Message):
  response = protocol.Message()
  response.head.version = message.head.version
  response.head.random_num = message.head.random_num
  response.head.flow_no = message.head.flow_no
  response.head.message_type = protocol.STATUS_REPORT_RESPONSE
  response.head.request = False
  return response

server = rpc_server.RpcServer()
server.register_handle(protocol.STATUS_REPORT_REQUEST, StatusReportHandle)
server.start()

loop = asyncio.get_event_loop()
loop.run_forever()