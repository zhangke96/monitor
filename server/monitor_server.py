import rpc_server
import asyncio

server = rpc_server.RpcServer()
server.start()

loop = asyncio.get_event_loop()
loop.run_forever()