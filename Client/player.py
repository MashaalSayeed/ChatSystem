import asyncio
import base64

import cv2
import numpy as np
import sounddevice as sd


class VideoHandler:
    def __init__(self):
        self.camera_open = False
        self.streaming = False
        self.recieving = False

    async def transmit_stream(self, socket, tkwindow):
        self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while self.camera_open:
            try:
                # grab the current frame
                # resize and color for display
                grabbed, frame = self.camera.read()
                frame = cv2.resize(frame, (320,240))  # resize the frame
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.flip(frame, 1)
                tkwindow.update_video(frame, 1)

                await asyncio.sleep(0.1)
                if self.streaming:
                    # Encode the frame, so it can be transmitted
                    encoded = base64.b64encode(cv2.imencode('.jpg', frame)[1]).decode()
                    await socket.send_data('VIDEO_STREAM', frame=encoded)

            except Exception as e:
                print('Error', e)
                break
        
        await socket.send_data('VIDEO_STREAM', frame=False)
        self.camera.release()

    def recieve_stream(self, frame, tkwindow):
        try:
            if frame:
                buffer = base64.b64decode(frame)
                frame = np.frombuffer(buffer, dtype=np.uint8)
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                tkwindow.update_video(frame, 0)
            else:
                tkwindow.close_video(0)
        except Exception as e:
            print(e)

    def close(self):
        cv2.destroyAllWindows()
        self.camera_open = False
        self.streaming = False



class AudioHandler:
    def __init__(self):
        self.recording = False
        self.recieving = False

        self.stream = sd.RawStream(callback=self.callback, channels=1, dtype='float32')

        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()

    async def transmit_stream(self, socket):
        while self.recording or not self.input_queue.empty():
            try:
                indata = await self.input_queue.get()
                encoded = base64.b64encode(indata).decode()
                await socket.send_data('AUDIO_STREAM', audio=encoded)
                self.input_queue.task_done()
            except Exception as e:
                print('Error', e)
                break

    def recieve_stream(self, audio):
        decoded = base64.b64decode(audio)
        self.output_queue.put_nowait(decoded)
    
    def callback(self, indata, outdata, frame_count, time_info, status):
        if self.recording:
            self.loop.call_soon_threadsafe(self.input_queue.put_nowait, indata)
        try:
            outdata[:] = self.output_queue.get_nowait()
        except asyncio.QueueEmpty:
            outdata[:] = bytearray(len(outdata))

    def join_stream(self):
        self.stream.start()

    def close(self):
        self.stream.stop()
        self.recording = False
        self.recieving = False

