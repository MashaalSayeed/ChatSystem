import asyncio
import json
import ssl

from collections import defaultdict
from routes import ROUTES


class SocketServer:
    "Main server, handles incoming connections and manages rooms"
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.sockets = []
        self.rooms = defaultdict(list)

    def find_socket(self, userid):
        "Returns the first socket with the given user id"
        for s in self.sockets:
            if s.user and s.user[0] == userid:
                return s

    def join_room(self, socket, roomid):
        "Appends the socket to the room"
        if socket not in self.rooms[roomid]:
            self.rooms[roomid].append(socket)

    def leave_all_rooms(self, socket):
        "Make the socket leave all rooms"
        [room.remove(socket) for room in self.rooms if socket in self.rooms]

    def leave_room(self, socket, roomid):
        "Makes a socket leave a room"
        if not socket:
            return
        self.rooms[roomid].remove(socket)
    
    def invite_to_room(self, userid, roomid):
        "Finds the socket and makes it join the room"
        socket = next((s for s in self.sockets if s.user and s.user[0] == userid), None)
        if socket:
            self.rooms[roomid].append(socket)
    
    async def send_to(self, userid, header, body):
        "Sends a message to particular user if connected"
        socket = next((s for s in self.sockets if s.user and s.user[0] == userid), None)
        if socket:
            await socket.send(header, body)

    async def create_room(self, members, room):
        for s in self.sockets:
            if s.user and s.user[0] in members:
                self.join_room(s, room[0])
                await s.send('JOIN_ROOM', room)

    async def connect(self):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile="chatserver.crt", keyfile="chatserver.key")
        self.server = await asyncio.start_server(self.listen, self.host, self.port, ssl=context)

        print(f'Serving on {self.host}:{self.port}')
        async with self.server:
            await self.server.serve_forever()

    async def send_room(self, roomid, header, body):
        for s in self.rooms.get(roomid, []):
            await s.send(header, body)

    async def sendall(self, header, body):
        for s in self.sockets:
            await s.send(header, body)

    async def listen(self, reader, writer):
        socket = Socket(self, reader, writer)
        print("\nConnection from:", socket.addr)
        self.sockets.append(socket)

        await socket.listen()


class Socket:
    "Manages communication to a particular client"
    def __init__(self, server: SocketServer, reader, writer):
        self.server = server
        self.reader = reader
        self.writer = writer
        self.addr = writer.get_extra_info('peername')
        self.user = None # [userid, email, username]

    async def send(self, header, body):
        data = json.dumps({
            'header': header,
            'body': body
        }, default=str).encode('utf8')
        
        size = len(data).to_bytes(4, byteorder='big')
        
        self.writer.writelines([size, data])
        await self.writer.drain()

    async def read(self):
        size = await self.reader.readexactly(4)
        data = await self.reader.readexactly(int.from_bytes(size, byteorder='big'))
        data = json.loads(data.decode('utf8'))

        return data.get('header'), data.get('body')

    async def handle_request(self, header, body):  
        if header == 'QUIT':
            return True

        login_not_required = ['LOGIN', 'REGISTER', 'QUIT']
        if header not in login_not_required and not self.user:
            return await self.send('ERROR', {'message': 'Unauthorised User'})

        if header in ROUTES:
            await ROUTES[header](self, self.server, body)

    async def listen(self):
        while True:
            try:
                header, body = await self.read()
                print(self.addr, header, body)
                finish = await self.handle_request(header, body)
                if finish:
                    print(self.addr, 'Connection Closed')
                    break
            except (asyncio.IncompleteReadError, ConnectionError) as e:
                print(self.addr, "Disconnected due to error\n", e)
                break
            except Exception as e:
                print(f'\nError at {self.addr}:\n', e)

        self.server.sockets.remove(self)
        self.writer.close()

