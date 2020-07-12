import asyncio, logging, sys, os
sys.path.append("..")
sys.path.extend([os.path.join(root, name) for root, dirs, _ in os.walk("../") for name in dirs])
from rpc import rpc_server
from rpc import message_pb2 as protocol
from google.protobuf.timestamp_pb2 import Timestamp
import pymongo
from datetime import datetime

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='server.log', level=logging.INFO, format=LOG_FORMAT)

exists_key = {}
db_client = pymongo.MongoClient(host='127.0.0.1', port=27017)
db = db_client['monitor']
auth_key_table = db['auth_key']
monitor_data = db['monitor_data']

def make_response(request: protocol.Message, response_message_type: protocol.MessageType):
  response = protocol.Message()
  response.head.version = request.head.version
  response.head.random_num = request.head.random_num
  response.head.flow_no = request.head.flow_no
  response.head.message_type = response_message_type
  response.head.request = False
  return response

def transfer_status_record(report_request: protocol.StatusReportRequest):
  result = {}
  capture_time = datetime.utcnow()
  if report_request.HasField("capture_time"):
    capture_time = datetime.fromtimestamp(report_request.capture_time.seconds)
  result["capture_time"] = capture_time
  result["cpu_number"] = report_request.cpu_number
  result["memory_cap"] = report_request.memory_cap
  result["load"] = report_request.load
  result["cpu_usage"] = report_request.cpu_usage
  result["memory_usage"] = report_request.memory_usage
  logging.debug("report_request:%s to_insert:%s", report_request, result)
  return result

def record_report(auth_key: str, report_request: protocol.StatusReportRequest):
  logging.info("insert record, client:%s", auth_key)
  result = monitor_data.insert_one({"client": auth_key, "status": transfer_status_record(report_request)})
  return True

def is_key_valid(auth_key: str) -> bool:
  if auth_key in exists_key:
    return True
  find_result = auth_key_table.find_one({"client": auth_key})
  return not find_result is None

def StatusReportHandle(message: protocol.Message):
  response = make_response(message, protocol.STATUS_REPORT_RESPONSE)
  body = response.body.status_report_response
  body.handle_time.GetCurrentTime()
  if not message.body.HasField("status_report_request"):
    logging.warning("not have body status_report_request:%s", message)
    body.response.retcode = protocol.FAIL
    body.response.error_message = "no body"
  else:
    auth_key = message.head.auth_key
    if not is_key_valid(auth_key):
      logging.warning("invalid key:%s", auth_key)
      body.response.retcode = protocol.INVALID_KEY
      body.response.error_message = "invalid key"
    else:
      retcord_ret = record_report(auth_key, message.body.status_report_request)
      if retcord_ret:
        logging.debug("record report success, auth_key:%s", auth_key)
        body.response.retcode = protocol.SUCCESS
        body.response.error_message = "success"
      else:
        logging.error("record report failed, auth_key:%s", auth_key)
        body.response.retcode = protocol.FAIL
        body.response.error_message = "recode fail"
  return response

server = rpc_server.RpcServer()
server.register_handle(protocol.STATUS_REPORT_REQUEST, StatusReportHandle)
server.start()

loop = asyncio.get_event_loop()
loop.run_forever()