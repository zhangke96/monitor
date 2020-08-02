import socket, threading, logging, struct, time, select
from enum import Enum

class Ping(object):
  class Status(Enum):
    READY = 0
    RUNNING = 1
    STOPING = 2
    STOP = 3

  ICMP_ECHO_REQUEST = 8

  class PingPacket(object):
    def __init__(self):
      self.type = None
      self.code = None
      self.checksum = None
      self.identifier = None
      self.seqno = None
      self.data = None
      self.ttl = None
    
    def dump(self):
      pass

    def load(self, data: bytes):
      if len(data) < 28:
        return False
      self.ttl = struct.unpack("!B", data[8:9])[0]
      self.type, self.code, self.checksum, self.identifier, self.seqno = struct.unpack("!BBHHH", data[20:28])
      return True


  def __init__(self, hostname):
    self.hostname = hostname
    self.address = None
    self.reporter = None
    self.socket = None
    self.thread = None
    self.status = self.Status.READY
    self.identifier = None
    self.seqno = 0
    self.send_time = None
    self.retry_time = 1
  
  def start(self):
    # 判断是否重复调用start
    assert not self.address
    try:
      self.address = socket.gethostbyname(self.hostname)
      logging.info("host:%s reslove to address:%s" % (self.hostname, self.address))
    except:
      logging.error("get address of host:%s failed" % self.hostname)
      return 
    self.thread = threading.Thread(target=Ping.run, args=(self,))
    self.thread.setDaemon(True)
    self.thread.start()
    
  def run(self):
    self.identifier = int(threading.current_thread().ident) & 0xFFFF
    icmp = socket.getprotobyname("icmp")
    try:
      self.socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
      self.socket.setblocking(False)
    except socket.error as e:
      print(e)
      return
    while self.status != self.Status.STOP:
      self.send_ping()
      delay = self.recv_pong()
      if self.reporter:
        self.reporter(int(self.send_time), delay)
      if delay is None:
        # 超时了
        print(self.hostname, " timeout")
        time.sleep(self.retry_time)
        if self.retry_time < 60:
          self.retry_time *= 2
      else:
        print(self.hostname, delay)
        self.retry_time = 1
        time.sleep(1)
  
  def send_ping(self):
    my_checksum = 0

    # Create a dummy heder with a 0 checksum.
    self.seqno += 1
    seqno = self.seqno & 0xFFFF
    header = struct.pack("!BBHHH", self.ICMP_ECHO_REQUEST, 0, my_checksum, self.identifier, seqno)
    data = struct.pack("I", int(time.time())) + struct.pack("I", 0)

    # Get the checksum on the data and the dummy header.
    my_checksum = self.do_checksum(header + data)
    header = struct.pack("!BBHHH", self.ICMP_ECHO_REQUEST, 0, my_checksum, self.identifier, seqno)
    packet = header + data
    self.send_time = time.time()
    self.socket.sendto(packet, (self.address, 1))

  def recv_pong(self):
    # self.socket.settimeout()
    timeout = 1.0
    delay = None
    while True:
      if timeout < 0:
        break
      start_time = time.time()
      read_socks, _, _ = select.select([self.socket], [], [], timeout)
      used_time = time.time() - start_time
      timeout -= used_time
      if len(read_socks) == 0:
        if timeout > 0:
          continue
        else:
          # timeout
          break
      else:
        # 读数据
        while True:
          try:
            recv_packet, addr = self.socket.recvfrom(1024)
            ping_packet = self.PingPacket()
            if ping_packet.load(recv_packet):
              if ping_packet.identifier == self.identifier and ping_packet.seqno == self.seqno & 0xFFFF:
                print("now time:", time.time(), " start time:", self.send_time)
                delay = time.time() * 1000000 - self.send_time * 1000000
                break
          except BlockingIOError:
            break
    return delay

  def do_checksum(self, source_string):
    """  Verify the packet integritity """
    sum = 0
    max_count = (len(source_string)/2)*2
    count = 0
    while count < max_count:

        val = source_string[count + 1]*256 + source_string[count]                   
        sum = sum + val
        sum = sum & 0xffffffff 
        count = count + 2

    if max_count<len(source_string):
        sum = sum + ord(source_string[len(source_string) - 1])
        sum = sum & 0xffffffff 

    sum = (sum >> 16)  +  (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer
    
  def stop(self):
    self.status = self.Status.STOP

  def set_reporter(self, reporter):
    self.reporter = reporter
