import asyncio, struct
from asyncio.streams import StreamReader, StreamWriter
import message_pb2 as protocol
from typing import MutableMapping, Tuple

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
    print('Accept conn id:', self.conn_id, 'from:', writer.transport.get_extra_info('peername'))
    asyncio.ensure_future(self.read_and_parse(self.conn_id))

  async def read_and_parse(self, conn_id: int):
    if not conn_id in self.alive_connections.keys():
      return
    reader: StreamReader = self.alive_connections[conn_id][0]
    writer: StreamWriter = self.alive_connections[conn_id][1]
    print('Read from conn id:', conn_id, ' peeraddr:', writer.transport.get_extra_info('peername'))
    buffer = bytes()
    while True:
      try:
        content = await reader.read(8 * 1024)
      except Exception as ex:
        print("read excpetion", ex)
        # remove_connection
        return
      if len(content) == 0:
        print("peer shutdown")
        # remove connection
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
        # print(request_message)
        message_type = request_message.head.message_type
        if message_type in self.message_handles.keys():
          response = self.message_handles[message_type](request_message)
          encode_str = response.SerializeToString()
          writer.write(struct.pack('!I', len(encode_str)))
          writer.write(encode_str)
        buffer = buffer[except_length + 4:]
    

  def register_handle(self, message_type, message_handle):
    self.message_handles[message_type] = message_handle
