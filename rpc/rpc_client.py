import asyncio, struct, logging
from random import expovariate
from asyncio.futures import Future
from typing import MutableMapping, Tuple
from asyncio.streams import StreamReader, StreamWriter
from enum import Enum
import message_pb2 as protocol

class SendMessageResult(Enum):
  SUCCESS = 0
  TIMEOUT = 1
  FAIL = 2

class RpcClient:
  conn_id = 0
  alive_connections = MutableMapping[str, Tuple[int, StreamReader, StreamWriter]]
  connection_map = MutableMapping[int, str]
  response_futures = MutableMapping[int, MutableMapping[int, Future]]

  def __init__(self) -> None:
    self.conn_id = 0
    self.alive_connections = {}
    self.connection_map = {}
    self.response_futures = {}
  
  def get_connection_id(self, address: Tuple[str, int]) -> int:
    address_str = str(address)
    if not address_str in self.alive_connections.keys():
      logging.warning("address:%s not in alive connections", address)
      return 0
    else:
      return self.alive_connections[address_str][0]
  
  async def get_connection(self, address: Tuple[str, int]) -> StreamWriter:
    address_str = str(address)
    if address_str in self.alive_connections.keys():
      logging.debug("reuse connection to:%s", address)
      return self.alive_connections[address_str][2]
    else:
      # 尝试建立连接，超时1s
      logging.debug("try to connect:%s", address)
      fut = asyncio.open_connection(address[0], address[1])
      try:
        reader, writer = await asyncio.wait_for(fut, timeout=1)
        logging.info("connect to:%s success", address)
      except Exception as ex:
        logging.warning("connect to:%s %s", address, ex)
        return None
      self.conn_id += 1
      self.alive_connections[address_str] = (self.conn_id, reader, writer)
      self.connection_map[self.conn_id] = address_str
      logging.debug("connection to:%s conn_id:%d", address, self.conn_id)
      # 运行解析函数
      asyncio.ensure_future(self.read_and_parse(self.conn_id))
      return writer
  
  def remove_connection(self, conn_id: int):
    if not conn_id in self.connection_map.keys():
      return
    address_str = self.connection_map[conn_id]
    self.alive_connections.pop(address_str)
    self.connection_map.pop(conn_id)
    logging.debug("remove connection to address:%d conn_id:%d", address_str, conn_id)

  async def read_and_parse(self, conn_id: int):
    if not conn_id in self.connection_map.keys():
      return
    address_str = self.connection_map[conn_id]
    reader: StreamReader = self.alive_connections[address_str][1]
    buffer = bytes()
    while True:
      try:
        content = await reader.read(8 * 1024)
      except Exception as ex:
        logging.warning("read exception, address:%s conn_id:%d exception:%s", address_str, conn_id, ex)
        self.remove_connection(conn_id)
        return
      if len(content) == 0:
        # 对端shutdown write
        logging.info("read eof, address:%s conn_id:%d", address_str, conn_id)
        self.remove_connection(conn_id)
        return
      buffer += content
      while True:
        if len(buffer) < 4:
          break
        except_length = struct.unpack('!I', buffer[0: 4])[0]
        if except_length + 4 > len(buffer):
          break
        message_bytes = buffer[4: except_length + 4]
        response_message = protocol.Message()
        response_message.ParseFromString(message_bytes)
        logging.debug("recv response from address:%s response:%s", address_str, response_message)
        flow_no = response_message.head.flow_no
        future = self.get_future(conn_id, flow_no)
        if future:
          future.set_result(response_message)
        buffer = buffer[except_length + 4:]

  
  def add_future(self, conn_id: int, flow_no: int):
    assert(conn_id in self.connection_map.keys())
    if not conn_id in self.response_futures.keys():
      self.response_futures[conn_id] = {}
    logging.debug("add response future, conn_id:%d flow_no:%d", conn_id, flow_no)
    self.response_futures[conn_id][flow_no] = asyncio.get_event_loop().create_future()
  
  def get_future(self, conn_id: int, flow_no: int) -> Future:
    response_future = None
    if not conn_id in self.response_futures.keys():
      response_future = None
    elif not flow_no in self.response_futures[conn_id].keys():
      response_future = None
    else:
      response_future = self.response_futures[conn_id][flow_no]
    if not response_future:
      logging.info("not found future for conn_id:%d flow_no:%d maybe timeout", conn_id, flow_no)
    return response_future
  
  def remove_future(self, conn_id: int, flow_no: int):
    if not conn_id in self.response_futures.keys():
      return
    if not flow_no in self.response_futures[conn_id].keys():
      return
    self.response_futures[conn_id].pop(flow_no)

  async def wait_for_response(self, conn_id: int, flow_no: int, timeout: int) -> Tuple[SendMessageResult, protocol.Message]:
    future = self.get_future(conn_id, flow_no)
    if future is None:
      return (SendMessageResult.FAIL, None)
    try:
      response = await asyncio.wait_for(future, timeout)
      self.remove_future(conn_id, flow_no)
    except asyncio.TimeoutError:
      # 删除future
      self.remove_future(conn_id, flow_no)
      return (SendMessageResult.TIMEOUT, None)
    return (SendMessageResult.SUCCESS, response)

  async def send_message(self, address: Tuple[str, int], message: protocol.Message) -> Tuple[SendMessageResult, protocol.Message]:
    writer: StreamWriter = await self.get_connection(address)
    if writer is None:
      return (SendMessageResult.TIMEOUT, None)
    # set future
    conn_id = self.get_connection_id(address)
    assert(conn_id)
    self.add_future(conn_id, message.head.flow_no)
    encode_str = message.SerializeToString()
    # 捕获异常
    writer.write(struct.pack('!I', len(encode_str)))
    writer.write(encode_str)
    result, response = await self.wait_for_response(conn_id, message.head.flow_no, 1)
    return (result, response)
