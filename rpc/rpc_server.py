import asyncio, struct, logging
from asyncio.streams import StreamReader, StreamWriter
import message_pb2 as protocol
from typing import MutableMapping, Tuple
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='server.log', level=logging.DEBUG, format=LOG_FORMAT)

class RpcServer:
  conn_id = 0
  alive_connections = MutableMapping[int, Tuple[StreamReader, StreamWriter]]
  message_handles = {}

  def __init__(self) -> None:
    self.conn_id = 0
    self.alive_connections = {}
    self.message_handles = {}

  def start(self):
    coro = asyncio.start_server(self.connect_handle, '127.0.0.1', 8888)
    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(coro)

  async def connect_handle(self, reader: StreamReader, writer: StreamWriter):
    self.conn_id += 1
    self.alive_connections[self.conn_id] = (reader, writer)
    logging.info('Accept from:%s conn_id:%d', writer.transport.get_extra_info('peername'), self.conn_id)
    asyncio.ensure_future(self.read_and_parse(self.conn_id))

  def remove_connection(self, conn_id: int):
    if not conn_id in self.alive_connections.keys():
      logging.warning("Remove connection not exist conn_id:%d", conn_id)
      return
    address = self.alive_connections[conn_id][0].transport.get_extra_info('peername')
    logging.info("Remove connection address:%s conn_id:%d", address, conn_id)
    self.alive_connections.pop(conn_id)

  async def read_and_parse(self, conn_id: int):
    if not conn_id in self.alive_connections.keys():
      return
    reader: StreamReader = self.alive_connections[conn_id][0]
    writer: StreamWriter = self.alive_connections[conn_id][1]
    address = writer.transport.get_extra_info('peername')
    logging.debug('Read from address:%s conn_id:%d', address, conn_id)
    buffer = bytes()
    while True:
      try:
        content = await reader.read(8 * 1024)
      except Exception as ex:
        logging.warning("read excpetion, address:%s conn_id:%d exception:%s", address, conn_id, ex)
        remove_connection(conn_id)
        return
      if len(content) == 0:
        logging.info("read eof, address:%s conn_id:%d", address, conn_id)
        remove_connection(conn_id)
        return
      buffer += content
      while True:
        if len(buffer) < 4:
          break
        except_length = struct.unpack('!I', buffer[0: 4])[0]
        if except_length + 4 > len(buffer):
          break
        message_bytes = buffer[4: except_length + 4]
        request_message = protocol.Message()
        request_message.ParseFromString(message_bytes)
        logging.debug("recv request from address:%s request:%s", address, request_message)
        message_type = request_message.head.message_type
        if message_type in self.message_handles.keys():
          response = self.message_handles[message_type](request_message)
          logging.debug("send response to address:%s response:%s", address, response)
          encode_str = response.SerializeToString()
          writer.write(struct.pack('!I', len(encode_str)))
          writer.write(encode_str)
        else:
          logging.warning("unregister message_type:%d", message_type)
        buffer = buffer[except_length + 4:]
    

  def register_handle(self, message_type, message_handle):
    self.message_handles[message_type] = message_handle
