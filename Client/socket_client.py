import asyncio
import json
import ssl

from collections import defaultdict
from player import VideoHandler, AudioHandler


RECONNECT_INTERVAL = 5

class Event(list):
    "Basically a list of functions"
    def __call__(self, *args, **kwargs):
        for f in self:
            f(*args, **kwargs)


class SocketClient:
    "Connects to server and handles data transfer"
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reconnecting = True

        # Configure ssl connection (trust certificates and ignore hostnames)
        self.sslcontext = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.sslcontext.check_hostname = False
        self.sslcontext.load_verify_locations('chatserver.crt')

        self.events = defaultdict(Event)
        self.videohandler = VideoHandler()
        self.audiohandler = AudioHandler()
        self.stream_window = None
        self.register_event('VIDEO_STREAM', self.recieve_video)
        self.register_event('AUDIO_STREAM', self.recieve_audio)

    def send_data(self, header, **data):
        "Helper function to asynchronously send data to server"
        return asyncio.create_task(self.send(header, data))

    def register_event(self, eventname, func):
        "Creates an event if not exists and adds a listener"
        self.events[eventname].append(func)

    def connect_stream(self, tkwindow, code):
        self.stream_window = tkwindow
        self.send_data('JOIN_STREAM', code=code)

    def start_video(self, tkwindow):
        # Create a seperate task
        asyncio.create_task(self.videohandler.transmit_stream(self, tkwindow))
    
    def recieve_video(self, frame):
        self.videohandler.recieve_stream(frame, self.stream_window)

    def start_audio(self):
        asyncio.create_task(self.audiohandler.transmit_stream(self))

    def recieve_audio(self, audio):
        self.audiohandler.recieve_stream(audio)

    async def start(self):
        "Starts a new connection to the server"
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port, ssl=self.sslcontext)
        print(f'Connected to {self.host}:{self.port}')
        self.events['RECONNECT']()
        await self.listen()

    async def connect(self):
        "Starting point - manages reconnection to server"
        while True:
            try:
                await self.start()
            except (OSError, ConnectionError, TimeoutError):
                print('Connection Lost!')

            await asyncio.sleep(RECONNECT_INTERVAL)
            print('Reconnecting...')

    async def send(self, header, body={}):
        "Sends a message to the server"
        if not (hasattr(self, 'writer') and self.writer):
            return print('Lost connection to server.. Try again later')
        # Encode data in json, get the size and transmit the data
        data = json.dumps({
            'header': header,
            'body': body
        }).encode('utf8')
        
        size = len(data).to_bytes(4, byteorder='big')
        
        self.writer.writelines([size, data])
        await self.writer.drain()

    async def read(self):
        "Receive message sent from server"
        # First get the size of data packet
        # Then read exactly that many bytes
        # Decode json object and return header and body
        size = await self.reader.readexactly(4)
        data = await self.reader.readexactly(int.from_bytes(size, byteorder='big'))
        data = json.loads(data.decode('utf8'))

        return data.get('header'), data.get('body')
    
    async def listen(self):
        "Infinite loop to keep receiving messages from server and transmitting it to respective listeners"
        try:
            while True:
                header, body = await self.read()
                
                if header in self.events:
                    self.events[header](body)
        except asyncio.IncompleteReadError:
            print('Server Error')
