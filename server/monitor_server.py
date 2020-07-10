import rpc_server
import asyncio
import message_pb2 as protocol
from google.protobuf.timestamp_pb2 import Timestamp

def make_response(request: protocol.Message, response_message_type: protocol.MessageType):
  response = protocol.Message()
  response.head.version = request.head.version
  response.head.random_num = request.head.random_num
  response.head.flow_no = request.head.flow_no
  response.head.message_type = response_message_type
  response.head.request = False
  return response

def record_report(auth_key: str, report_request: protocol.StatusReportRequest):
  print(auth_key, report_request)

def StatusReportHandle(message: protocol.Message):
  response = make_response(message, protocol.STATUS_REPORT_RESPONSE)
  body = response.body.status_report_response
  body.handle_time.GetCurrentTime()
  if not message.body.HasField("status_report_request"):
    body.response.retcode = protocol.FAIL
    body.response.error_message = "no body"
  else:
    auth_key = message.head.auth_key
    record_report(auth_key, message.body.status_report_request)
    body.response.retcode = protocol.SUCCESS
    body.response.error_message = "success"
  return response

server = rpc_server.RpcServer()
server.register_handle(protocol.STATUS_REPORT_REQUEST, StatusReportHandle)
server.start()

loop = asyncio.get_event_loop()
loop.run_forever()