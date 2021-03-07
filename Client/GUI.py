import asyncio
import base64
import math
import os
import pickle
import re
import tkinter as tk
import tkinter.ttk as ttk

from collections import defaultdict
from datetime import datetime
from tkinter import messagebox, simpledialog, filedialog

from PIL import ImageTk, Image


# Initialize fonts, colors, regex
FONT1 = ("Arial Bold", 20)
FONT2 = ("Arial Bold", 13)
FONT3 = ("Arial Bold", 11)
FONT4 = ("Arial", 10)
RED = "#d9514e"
BLUE = "#2da8d8"
BLACK = "#2a2b2d"

EMAIL_REGEX = re.compile(r"^\s+@\s+\.\s+$")

# Helper Functions
def create_entry(window, text, row=0, column=0, bg=None, show=None):
    "Creates a text label and entry box using the grid layout"
    tk.Label(window, text=text, anchor="w", font=FONT3, bg=bg).grid(row=row, column=column, sticky="nsew")
    entry = tk.Entry(window, show=show)
    entry.grid(row=row+1, column=column, sticky="nsew")
    return entry


def create_submit_entry(window, label_text='', btn_text='', row=0, column=0, command=None):
    "Creates a text label and entry box along with a submit button"
    tk.Label(window, text=label_text, anchor='w', font=FONT3).grid(row=row, column=column, sticky="nsew")
    entry_frame = tk.Frame(window)
    entry_frame.grid(row=row+1, column=column, stick="nsew")

    entry = tk.Entry(entry_frame)
    entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tk.Button(entry_frame, text=btn_text, command=command).pack(fill=tk.Y, expand=True)
    return entry


def grid_column_configure(frame):
    "Gives weight 2 for column 1, and weight 1 for column 0 and 2"
    frame.columnconfigure(1, weight=2)
    [frame.columnconfigure(i, weight=1) for i in (0,2)]


def format_filesize(size):
    if size == 0:
       return "0 B"
    
    formats = ("B", "KB", "MB")
    i = math.floor(math.log(size, 1024))
    s = round(size / math.pow(1024, i), 2)
    return f"{s} {formats[i]}"


class MainWindow:
    "The main window and controller on which frames are placed"
    def __init__(self, socket):
        self.socket = socket
        self.window = tk.Tk()

        # Define state variables, defaultdict creates element if it does not exist
        self.user = None
        self.friends = defaultdict(lambda: {'name': '', 'messages': [], 'user': []})
        self.chats = defaultdict(lambda: {'name': '', 'owner': '', 'messages': [], 'members': []})

        # Main container to hold all other frames and widgets
        container = tk.Frame(self.window)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Load frames and register core events
        self.load_frames(container, [LoginFrame, MainFrame])
        self.socket.register_event('ERROR', self.onerror)
        self.socket.register_event('INFO', self.oninfo)

    def load_frames(self, container, frames):
        "Adds all ChildFrame classes to self.frames"
        self.frames = {}
        for F in frames:
            page_name = F.__name__
            self.frames[page_name] = frame = F(container, self)
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginFrame")

    def show_frame(self, page_name):
        "Loads and displays a frame"
        frame = self.frames[page_name]
        frame.load()
        frame.tkraise()

    def add_room(self, roomid, roomname, ownerid):
        "Adds new room data or updates existing ones"
        self.chats[roomid].update({'owner': ownerid, 'name': roomname})

    def add_message(self, type, id, username, email, content, actualname, filename, created_at):
        "Creates room data for public message and friend for private, and appends message data"
        msg = [username, email, content, actualname, filename, created_at]
        if type == 'public':
            self.chats[id]['messages'].append(msg)
        else:
            self.friends[id]['messages'].append(msg)

    def add_member(self, roomid, userid, email, username):
        "Creates room data if not exists and appends member info"
        self.chats[roomid]['members'].append([userid, email, username])

    def onerror(self, body):
        messagebox.showerror('Error', body.get('message'))
    
    def oninfo(self, body):
        messagebox.showinfo('Info', body.get('message'))

    def onclose(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.window.destroy()

    async def run(self, interval=0.05):
        "Asynchronously run tkineter"
        # Run the close function when x button is pressed
        self.window.protocol('WM_DELETE_WINDOW', self.onclose)
        try:
            while True:
                self.window.update()
                await asyncio.sleep(interval)
        except tk.TclError as e:
            if "application has been destroyed" not in e.args[0]:
                print(e)
            
            # Close the socket once finished
            await self.socket.send('QUIT', {})
            quit()


class ChildFrame(tk.Frame):
    "Base class inherited by child frames"
    def __init__(self, parent, controller: MainWindow, **kwargs):
        super().__init__(parent, **kwargs)

        self.controller = controller
        self.socket = controller.socket
    
    def load(self):
        pass


class LoginFrame(ChildFrame):
    "Main Login Frame - handles login/registration"
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.socket.register_event('LOGIN', self.do_login)
        self.socket.register_event('REGISTER', self.do_signup)
        self.socket.register_event('RECONNECT', self.reconnect)
        self.remember = tk.IntVar()
        self.credentials = {}
        self.make_widgets()
    
    def load(self):
        self.controller.window.geometry('500x300')
        self.configure(bg=BLUE)
    
    def make_widgets(self):
        tk.Label(self, text="Welcome to SQL Chat", bg=RED, height=2, foreground='white', font=FONT1).grid(columnspan=3, sticky="nesw")
        tk.Button(self, text="Login", font=FONT2, command=self.login).grid(row=2, column=1, sticky='nsew')
        tk.Button(self, text="Sign Up", font=FONT2, command=self.sign_up).grid(row=4, column=1, sticky='nsew')

        grid_column_configure(self)
        [self.rowconfigure(i, minsize=40) for i in range(5)]

    def login(self):
        "Create login window"
        if hasattr(self, 'login_window'):
            self.login_window.destroy()

        self.login_window = tk.Toplevel(self, bg=BLUE)
        self.login_window.title('Login')
        self.login_window.geometry("300x250")

        self.email_entry = create_entry(self.login_window, "Email ID", row=1, column=1, bg=BLUE)
        self.password_entry = create_entry(self.login_window, "Password", row=4, column=1, bg=BLUE, show="*")
        tk.Checkbutton(self.login_window, text='Remember me', bg=BLUE, anchor='w', variable=self.remember).grid(row=7, column=1, sticky='nsew')

        tk.Button(self.login_window, text="Login",font=FONT2, height=2, command=self.check_login).grid(row=8, column=1, sticky="nsew")
        try:
            # Load existing credentials if any
            with open('credentials.dat', 'rb') as file:
                data = pickle.load(file)
                self.email_entry.insert(tk.END, data.get('email'))
                self.password_entry.insert(tk.END, data.get('password'))
        except:
            pass

        grid_column_configure(self.login_window)
        [self.login_window.rowconfigure(i, minsize=15) for i in (3,6)]
        [self.login_window.rowconfigure(i, minsize=30) for i in (1,2,4,5,7)]

    def check_login(self):
        "Send login data to server"
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        self.credentials = {'email': email, 'password': password}
        self.socket.send_data('LOGIN', email=email, password=password)

    def do_login(self, body):
        if 'error' in body:
            messagebox.showwarning('Authentication Failed', body.get('message'))
            self.password_entry.delete(0, tk.END)
        else:
            "Destroy login window, update credentials and display main frame"
            if hasattr(self, 'login_window'):
                self.login_window.destroy()
            if self.remember.get():
                # Store credentials
                with open('credentials.dat', 'wb') as file:
                    pickle.dump(self.credentials, file)

            self.controller.user = body.get('user')
            print(body)
            self.controller.show_frame('MainFrame')

    def sign_up(self):
        "Create signup window"
        self.signup_window = tk.Toplevel(self, bg=BLUE)
        self.signup_window.title('Sign Up')
        self.signup_window.geometry("300x300")

        self.username_entry = create_entry(self.signup_window, "Username", row=1, column=1, bg=BLUE)
        self.email_entry = create_entry(self.signup_window, "Email ID", row=4, column=1, bg=BLUE)
        self.password_entry = create_entry(self.signup_window, "Password", row=7, column=1, bg=BLUE, show="*")

        tk.Button(self.signup_window, text="Sign Up", font=FONT2, height=2, command=self.check_signup).grid(row=10, column=1, sticky="nsew")

        grid_column_configure(self.signup_window)
        [self.signup_window.rowconfigure(i, minsize=15) for i in (3,6,9)]
        [self.signup_window.rowconfigure(i, minsize=30) for i in (1,2,4,5,7,8,10)]

    def check_signup(self):
        "Validate signup data and send to server"
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()

        # Verify email / password
        if not (3 <= len(username) <= 30): 
            return messagebox.showerror('Invalid Username', 'Username must be 3 to 30 characters long')
        elif not username.isalnum():
            return messagebox.showerror('Invalid Username', 'Username can only contain alphabets and numbers')
        elif EMAIL_REGEX.match(email):
            return messagebox.showerror('Invalid email', 'Please enter a valid email ID')
        elif len(password) < 6:
            return messagebox.showerror('Invalid Password', 'Password should be atleast 6 characters long')

        self.socket.send_data('REGISTER', username=username, email=email, password=password)

    def do_signup(self, body):
        if 'error' in body:
            messagebox.showwarning('Registration Failed', body.get('message'))
            self.password_entry.delete(0, tk.END)
        else:
            messagebox.showinfo('Sign Up Successful', body.get('message'))
            if hasattr(self, 'signup_window'):
                self.signup_window.destroy()

    def reconnect(self):
        "On reconnection, try to relogin"
        if self.controller.user:
            self.socket.send_data('LOGIN', **self.credentials)


class MainFrame(ChildFrame):
    "Main chat stuff down here"
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.socket.register_event('LOGOUT', self.logout)
        self.make_widgets()

    def load(self):
        self.controller.window.geometry('500x525')
        self.controller.window.title('SQL Chat')

        self.controller.chats.clear()
        self.controller.friends.clear()
        self.socket.send_data('FETCH_ROOMS')
        self.socket.send_data('FETCH_RECENT_CHATS')
        self.socket.send_data('FETCH_MEMBERS')
        self.socket.send_data('FETCH_FRIENDS')

        self.profile_frame.load()

    def make_widgets(self):
        title_frame = tk.Frame(self, bg=RED)
        title_frame.pack(fill=tk.X)

        main_frame = tk.Frame(self, bg="#000000")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Make and grid all frames
        self.rooms_frame = RoomsFrame(main_frame, self.controller)
        self.rooms_frame.grid(row=0, column=0, sticky="nesw")
        self.friends_frame = FriendsFrame(main_frame, self.controller)
        self.friends_frame.grid(row=0, column=0, sticky="nesw")
        self.chat_frame = ChatFrame(main_frame, self.controller)
        self.chat_frame.grid(row=0, column=0, sticky='nesw')
        self.chat_options_frame = ChatOptions(main_frame, self.controller)
        self.chat_options_frame.grid(row=0, column=0, sticky='nsew')
        self.profile_frame = ProfileFrame(main_frame, self.controller)
        self.profile_frame.grid(row=0, column=0, sticky="nesw")

        tk.Button(title_frame, text="Chat", bg=RED, height=2, font=FONT2, command=self.rooms_frame.tkraise).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(title_frame, text="Friends", bg=RED, height=2, font=FONT2, command=self.friends_frame.tkraise).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(title_frame, text="Profile", bg=RED, height=2, font=FONT2, command=self.profile_frame.tkraise).pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def open_chat(self, data, private=False):
        self.chat_frame.load_chat(data, private)
        self.chat_frame.tkraise()

    def logout(self, body={}):
        self.controller.user = None
        self.controller.show_frame('LoginFrame')


class ChatFrame(ChildFrame):
    "Frame that dynamically receives and displays chat messages"
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.room = {}
        self.id = -1
        self.private = False
        self.attachment = None
        self.make_widgets()
        self.socket.register_event('MESSAGE', self.new_message)
        self.socket.register_event('DOWNLOAD_FILE', self.download_file)

    def make_widgets(self):
        title_frame = tk.Frame(self, bd=3, relief=tk.RAISED)
        title_frame.grid(row=0, sticky='nsew')
        self.title = tk.Label(title_frame, pady=5, height=2, text='Room', font=FONT2)
        self.title.pack(side="left", fill=tk.BOTH, expand=True)
        
        self.video_btn = tk.Button(title_frame, text='Video', font=FONT3, height=2, pady=5, command=self.start_video)
        self.video_btn.pack(side='right', fill='y')
        self.option_btn = tk.Button(title_frame, text='Options', font=FONT3, height=2, pady=5, command=self.display_options)
        self.option_btn.pack(side='right', fill=tk.Y)

        self.message_frame = ScrollableFrame(self, bg='light green', height=1)
        self.message_frame.grid(row=1, sticky='nsew')#.pack(fill=tk.BOTH, expand=True)

        self.attachment_frame = tk.Frame(self)
        self.attachment_title = tk.Label(self.attachment_frame, text='')
        self.attachment_title.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Button(self.attachment_frame, text='X', width=2, command=self.close_attachment).pack(side=tk.RIGHT)

        send_frame = tk.Frame(self, bd=3, relief=tk.RAISED)
        send_frame.grid(row=3, sticky='nsew')#.pack(fill=tk.X)
        self.msg_entry = tk.Entry(send_frame, font=FONT4) # scrolledtext.ScrolledText(send_frame, font=FONT4, wrap=tk.WORD, height=2, width=15)
        self.msg_entry.pack(side='left', fill=tk.BOTH, expand=True)
        self.attachment_image = tk.PhotoImage(file='attachment.png')
        tk.Button(send_frame, height=2, text='Send', bg='green', fg="white", font=FONT3, command=self.send_message).pack(side='right', fill=tk.BOTH, expand=True)
        tk.Button(send_frame, image=self.attachment_image, command=self.get_attachment).pack(side='right', fill=tk.BOTH)
        self.msg_entry.bind('<Return>', self.send_message)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

    def start_video(self):
        self.video_window = VideoWindow(self, self.controller, self.private, self.id)

    def get_attachment(self):
        file = filedialog.askopenfile(mode='rb')
        if not file:
            return

        filesize = os.fstat(file.fileno()).st_size
        if filesize > 50 * (2**20):
            return messagebox.showerror('Error', 'Cannot send attachment greater than 50 MB') 
        # Open file and store the data and filename
        filename = os.path.basename(file.name)
        filedata = base64.b64encode(file.read()).decode()
        self.attachment = [filename, filedata]

        self.attachment_frame.grid(row=2, sticky='nsew')
        self.attachment_title.config(text=f'{filename} ({format_filesize(filesize)})')

    def download_file(self, file):
        filename, extension = os.path.splitext(file[0])
        save_file = filedialog.asksaveasfile(mode='wb', initialfile=filename, defaultextension=extension, filetypes=(("All files", "*"),))
        if save_file:
            filedata = base64.b64decode(file[1].encode())
            save_file.write(filedata)
            save_file.close()

    def close_attachment(self):
        self.attachment = None
        self.attachment_frame.grid_forget()

    def display_options(self):
        options_frame = self.controller.frames['MainFrame'].chat_options_frame
        options_frame.load_chat(self.id)
        options_frame.tkraise()
    
    def add_message(self, message):
        created_at = datetime.fromisoformat(message[5]).strftime('%d-%m-%Y %H:%M')
        if message[1] == self.controller.user[1]:
            bg, anchor = "#e0eee0", "e"
        else:
            bg, anchor = "#f0f8ff", "w"

        frame = tk.Frame(self.message_frame.frame, borderwidth=1, relief=tk.RAISED)
        frame.pack(anchor=anchor, pady=5, padx=10)
        tk.Label(frame, text=f'{message[1]} ~ {message[2]} [{created_at}]', bg=bg, font=FONT3, padx=5).pack(fill=tk.X, expand=True)
        if message[4]:
            download_cmd = lambda: self.socket.send_data('DOWNLOAD_FILE', filename=message[4], actualname=message[3])
            attachment_frame = tk.Frame(frame, padx=5, pady=5)
            attachment_frame.pack(fill=tk.X, expand=True)

            tk.Label(attachment_frame, text=f'Attachment: {message[3]}').pack(side=tk.LEFT, fill=tk.BOTH)
            tk.Button(attachment_frame, text='Download', command=download_cmd).pack(side=tk.RIGHT, fill=tk.Y)

        tk.Message(frame, text=message[0], font=FONT4, bg=bg, anchor=anchor, width=350, padx=5).pack(anchor=anchor, fill=tk.BOTH, expand=True)
    
    def new_message(self, body):
        self.controller.add_message(*body)
        if self.id == body[1]:
            self.add_message(body[2:])
            self.message_frame.canvas.yview_moveto(1)
        else:
            self.bell()

    def send_message(self, e=None):
        message = self.msg_entry.get().strip()
        if not message and not self.attachment: return
        if len(message) > 1024:
            messagebox.showerror('Max Length Exceeded', 'Message cannot be more than 1024 characters long')
        
        if self.private:
            self.socket.send_data('SEND_PRIVATE_MESSAGE', _id=self.id, content=message, attachment=self.attachment)
        else:
            self.socket.send_data('SEND_MESSAGE', _id=self.id, content=message, attachment=self.attachment)
        self.msg_entry.delete(0, tk.END)
        self.close_attachment()

    def load_chat(self, _id, private=False):
        self.message_frame.clear() # Reset Messages
        self.attachment = None
        self.private = private
        self.id = _id
        if not private:
            self.data = self.controller.chats[_id]
            self.option_btn.configure(state=tk.NORMAL)
        else:
            self.data = self.controller.friends.get(_id)
            self.option_btn.configure(state=tk.DISABLED)

        self.title.configure(text=self.data['name'])
        messages = self.data.get('messages')
        if messages:
            [self.add_message(m) for m in messages]
        else:
            # To be honest, i didnt want this, but i found no other solution
            # to fix the scrollbar
            tk.Label(self.message_frame.frame, text='Welcome! Start the conversation by sending a message', font=FONT3).pack(pady=5, padx=10)


class VideoWindow(tk.Toplevel):
    def __init__(self, parent, controller, private, id):
        super().__init__(parent)

        self.controller = controller
        self.socket = controller.socket
        self.videohandler = self.socket.videohandler
        self.audiohandler = self.socket.audiohandler
        self.private = private
        self.id = id

        self.title('Video Call')
        self.geometry('600x300')

        self.make_widgets()
        self.protocol('WM_DELETE_WINDOW', self.onclose)
        self.socket.register_event('STREAM_JOINED', self.onjoin)

    def make_widgets(self):
        video_frame = tk.Frame(self)
        video_frame.pack(fill='both', expand=True)
        self.video_labels = [tk.Label(video_frame) for _ in range(2)]
        [v.pack(side='left') for v in self.video_labels]

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill='x')
        self.join_btn = tk.Button(btn_frame, text='Connect to Stream', command=self.connect_stream)
        self.join_btn.pack(fill='x', side='left', expand=True)
        self.unmute_btn = tk.Button(btn_frame, text='Unmute', command=self.unmute)
        self.unmute_btn.pack(fill='x', side='left', expand=True)
        self.webcam_btn = tk.Button(btn_frame, text='Open Webcam', command=self.open_camera)
        self.webcam_btn.pack(fill='x', side='right', expand=True)

    def open_camera(self):
        if not self.videohandler.camera_open:
            self.videohandler.camera_open = True
            self.socket.start_video(self)
            self.webcam_btn.configure(text='Turn off camera')
        else:
            self.videohandler.camera_open = False
            self.webcam_btn.configure(text='Open Webcam')
            self.close_video(1)

    def update_video(self, frame, index):
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
        self.video_labels[index].configure(image=self.photo)
        self.video_labels[index].image = self.photo

    def close_video(self, index):
        self.video_labels[index].configure(image='')

    def unmute(self):
        if not self.audiohandler.recording:
            self.audiohandler.recording = True
            self.socket.start_audio()
            self.unmute_btn.configure(text='Mute')
        else:
            self.audiohandler.recording = False
            self.unmute_btn.configure(text='unmute')

    def connect_stream(self):
        code = 'P' if self.private else 'R'
        code += str(self.id)
        self.socket.connect_stream(self, code)

    def onjoin(self, data):
        self.videohandler.streaming = True
        self.audiohandler.join_stream()
        self.join_btn.configure(text='Leave Stream', command=self.onclose)

    def onclose(self):
        self.socket.send_data('LEAVE_STREAM')
        self.socket.events.pop('STREAM_JOINED', None)
        self.videohandler.close()
        self.audiohandler.close()
        self.destroy()


class ChatOptions(ChildFrame):
    "Shows add member, member list and leave button for group chats"
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.roomid = -1
        self.make_widgets()
        self.socket.register_event('MEMBER_JOIN', self.member_join)
        self.socket.register_event('MEMBER_LEAVE', self.member_leave)

    def make_widgets(self):
        title_frame = tk.Frame(self, bd=3, relief=tk.RAISED)
        title_frame.grid(row=0, columnspan=3, sticky='nsew')
        self.title = tk.Label(title_frame, pady=5, height=2, text='Room', font=FONT2)
        self.title.pack(side="left", fill=tk.BOTH, expand=True)
        tk.Button(title_frame, text='Go Back', font=FONT3, height=2, pady=5, command=self.back).pack(side='right', fill=tk.Y)

        self.member_entry = create_submit_entry(self, label_text="Enter Email ID of participant", btn_text="Add", command=self.invite_member, row=2, column=1)
        self.member_list = ScrollableFrame(self, bd=2, relief=tk.SUNKEN)
        self.member_list.grid(row=5, column=1, sticky='nsew')

        tk.Button(self, text='Leave Room', font=FONT2, bg=RED, command=self.leave_room).grid(row=6, column=1, sticky='nsew', pady=15)

        grid_column_configure(self)
        self.rowconfigure(5, weight=1)
        [self.rowconfigure(i, minsize=15) for i in (1,4)]
        [self.rowconfigure(i, minsize=30) for i in (0,2,3,5,6)]

    def back(self):
        self.controller.frames['MainFrame'].chat_frame.tkraise()

    def invite_member(self):
        email = self.member_entry.get().strip()
        self.socket.send_data('INVITE_MEMBER', roomid=self.roomid, email=email)

    def kick_member(self, mid):
        self.socket.send_data('KICK_MEMBER', roomid=self.roomid, memberid=mid)
    
    def leave_room(self):
        if self.room['owner'] == self.controller.user[0]:
            self.socket.send_data('DELETE_ROOM', roomid=self.roomid)
        else:
            self.socket.send_data('LEAVE_MEMBER', roomid=self.roomid, memberid=self.controller.user[0])
        self.controller.frames['MainFrame'].rooms_frame.tkraise()

    def add_member(self, fid, femail, fname):
        member_frame = tk.Frame(self.member_list.frame, height=2, bd=5, relief=tk.GROOVE)
        member_frame.pack(fill="x", expand=True)
        tk.Label(member_frame, text=f'{femail} ~ {fname}', anchor="w").pack(side="left", fill="both", expand=True)
        if self.room['owner'] == self.controller.user[0]:
            tk.Button(member_frame, text='Kick', bg='red', fg='white', command=lambda m=fid: self.kick_member(m), padx=5).pack(padx=5, fill="y", expand=True)

    def load_chat(self, roomid):
        self.member_list.clear() # Reset Member Listing
        
        self.roomid = roomid
        self.room = self.controller.chats[roomid]
        self.title.configure(text=self.room['name'])
        [self.add_member(*m) for m in self.room['members']]

    def member_join(self, body):
        roomid, member = body
        self.controller.chats[roomid]['members'].append(member)
        if roomid == self.roomid:
            self.add_member(*member)

    def member_leave(self, body):
        roomid, memberid = body
        chat = self.controller.chats[roomid]
        chat['members'] = [m for m in chat['members'] if m[0] != memberid]
        if roomid == self.roomid:
            self.load_chat(self.roomid)


class RoomsFrame(ChildFrame):
    "Frame that displays all rooms (recent conversations) that the user is in"
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.make_widgets()
        self.socket.register_event('FETCH_ROOMS', self.fetch_rooms)
        self.socket.register_event('RECENT_CHATS', self.recent_chats)
        self.socket.register_event('FETCH_MEMBERS', self.fetch_members)
        self.socket.register_event('JOIN_ROOM', self.join_room)
        self.socket.register_event('LEAVE_ROOM', self.leave_room)

    def make_widgets(self):
        tk.Label(self, text='Recent Conversations', anchor='w', font=FONT2).grid(row=1, column=1, sticky="nsew")
        self.roomlist_frame = ScrollableFrame(self, bd=2, relief=tk.SUNKEN)
        self.roomlist_frame.grid(row=2, column=1, sticky="nsew")

        tk.Button(self, text='Create New Chat Group', bg="#184a45", fg="white", height=2, font=FONT2, command=self.create_chat_window).grid(row=3, column=1, sticky="nsew", pady=15)

        grid_column_configure(self)
        self.rowconfigure(2, weight=1)
        [self.rowconfigure(i, minsize=15) for i in (0,)]
        [self.rowconfigure(i, minsize=30) for i in (1,2,3)]
    
    def create_chat_window(self):
        ChatCreateWindow(self.master, self.controller)
    
    def add_room(self, roomid, roomname):
        main_frame = self.controller.frames['MainFrame']
        command = lambda r=roomid: main_frame.open_chat(r)
        tk.Button(self.roomlist_frame.frame, height=2, bd=5, text=f'Room: {roomname}', anchor="w", font=FONT3, command=command).pack(fill=tk.X, expand=True, pady=2)
    
    def fetch_rooms(self, body):
        [self.controller.add_room(*room) for room in body]
        self.populate_rooms()
    
    def populate_rooms(self):
        self.roomlist_frame.clear()
        for roomid, body in self.controller.chats.items():
            self.add_room(roomid, body['name'])

    def recent_chats(self, body):
        [r.update({'messages': []}) for r in self.controller.chats.values()]
        for chat in body[::-1]:
            self.controller.add_message(*chat)
        self.populate_rooms()

    def fetch_members(self, body):
        [r.update({'members': []}) for r in self.controller.chats.values()]
        for member in body:
            self.controller.add_member(*member)
    
    def join_room(self, body):
        self.controller.add_room(*body)
        self.add_room(*body[:2])

        self.socket.send_data('FETCH_RECENT_CHATS')
        self.socket.send_data('FETCH_MEMBERS')
    
    def leave_room(self, roomid):
        self.controller.chats.pop(roomid)
        self.populate_rooms()


class ChatCreateWindow(tk.Toplevel):
    "A window that allows you to create a room"
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller
        self.socket = controller.socket
        self.title('Create New Chat')
        self.geometry("500x515")
        self.members = [self.controller.user]

        self.make_widgets()
        self.socket.register_event('FETCH_USER', self.add_member)
        self.protocol("WM_DELETE_WINDOW", self.ondelete)
    
    def make_widgets(self):
        self.title = create_entry(self, "Enter Title", row=1, column=1)
        self.member_entry = create_submit_entry(self, label_text="Enter Email ID of participant", btn_text="Add", command=self.fetch_member, row=4, column=1)

        self.member_list = ScrollableFrame(self, bd=2, relief=tk.SUNKEN)
        self.member_list.grid(row=7, column=1, sticky='nsew')

        tk.Button(self, text="Create Chat", bg='green', fg='white', command=self.create_room, height=2, font=FONT2).grid(row=9, column=1, sticky="nsew")

        grid_column_configure(self)
        [self.rowconfigure(i, minsize=15) for i in (0,3,6,8)]
        [self.rowconfigure(i, minsize=30) for i in (1,2,4,5,7,9)]
    
    def fetch_member(self):
        email = self.member_entry.get().strip()
        found = next((u for u in self.members if u[1] == email), None)
        if found:
            return messagebox.showerror('Error', 'This user is already a participant')
        self.member_entry.delete(0, tk.END)
        self.socket.send_data('FETCH_USER', email=email)
    
    def new_member(self, body):
        fid, femail, fname = body
        member_frame = tk.Frame(self.member_list.frame, height=2, bd=5, relief=tk.GROOVE)
        member_frame.pack(fill="x", expand=True)
        tk.Label(member_frame, text=f'{femail} ~ {fname}', anchor="w").pack(side="left", fill="both", expand=True)
        tk.Button(member_frame, text='Remove', bg='red', fg='white', padx=5, command=lambda f=fid: self.remove_member(fid)).pack(padx=5, fill="y", expand=True)

    def add_member(self, body):
        self.members.append(body)
        self.new_member(body)

    def remove_member(self, fid):
        self.members = [m for m in self.members if m[0] != fid]
        self.member_list.clear()
        [self.new_member(m) for m in self.members if m[0] != self.controller.user[0]]

    def create_room(self):
        roomname = self.title.get().strip()
        self.socket.send_data('CREATE_ROOM', roomname=roomname, members=[m[0] for m in self.members])
        self.destroy()

    def ondelete(self):
        self.socket.events.pop('FETCH_USER', None) # Remove the attached listener when deleted
        self.destroy()


class FriendsFrame(ChildFrame):
    "Dynamically displays all friends and allows you add/remove them"
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.make_widgets()
        self.socket.register_event('FETCH_FRIENDS', self.populate_friends)
        self.socket.register_event('ADD_FRIEND', self.add_success)
        self.socket.register_event('REMOVE_FRIEND', self.remove_friend)
    
    def make_widgets(self):
        self.member_entry = create_submit_entry(self, label_text="Enter Email ID of new friend", btn_text="Add", command=self.add_friend, row=1, column=1)
        #tk.Label(self, text='Friend List', anchor="w", font=FONT3).grid(row=4, column=1, sticky="nsew")
        
        main_tab = ttk.Notebook(self)
        main_tab.grid(row=4, column=1, sticky='nsew')
        
        self.friend_list = ScrollableFrame(self, bd=2, relief=tk.SUNKEN)
        #self.friend_list.grid(row=5, column=1, sticky="nsew")
        main_tab.add(self.friend_list, text='Friends')
        grid_column_configure(self)
        [self.rowconfigure(i, minsize=15) for i in (0,3,6,8)]
        [self.rowconfigure(i, minsize=30) for i in (1,2,4,5,7,9)]

    def add_friend(self):
        email = self.member_entry.get().strip()
        if not email: return
        self.member_entry.delete(0, tk.END)
        self.socket.send_data('ADD_FRIEND', email=email)
    
    def add_success(self, friend):
        self.controller.friends[friend[0]].update({'name': friend[2], 'user': friend})
        print(friend)
        self.new_friend(*friend)
    
    def new_friend(self, fid, uid, femail, fname):
        main_frame = self.controller.frames['MainFrame']
        friend_frame = tk.Frame(self.friend_list.frame, height=2, bd=5, relief=tk.GROOVE)
        tk.Label(friend_frame, text=f'{femail} ~ {fname}', anchor="w", font=FONT4, padx=5).pack(side="left", fill="both", expand=True)

        tk.Button(friend_frame, text='Chat', width=5, padx=5, command=lambda f=fid: main_frame.open_chat(f, private=True)).pack(padx=5, fill="y", expand=True)
        tk.Button(friend_frame, text='Remove', width=5, padx=5, bg='red', fg='white', command=lambda fid=fid, uid=uid: self.socket.send_data('REMOVE_FRIEND', fid=fid, fuser=uid)).pack(padx=5, fill="y", expand=True)
        friend_frame.pack(fill="x", expand=True)

    def remove_friend(self, fid):
        self.controller.friends.pop(fid, None)
        users = [f['user'] for f in self.controller.friends.values()]
        self.populate_friends(users)

    def populate_friends(self, friends):
        self.friend_list.clear()
        [self.add_success(f) for f in friends]


class ProfileFrame(ChildFrame):
    "Displays username, email, status and allows you to change password, logout"
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.status = tk.StringVar()
        self.username = tk.StringVar()
        self.phone = tk.StringVar()
        self.address = tk.StringVar()
        self.status.set('online')
    
    def load(self):
        self.username.set(self.controller.user[2])
        self.phone.set(self.controller.user[3] or '')
        self.address.set(self.controller.user[4] or '')
        self.make_widgets()

    def make_widgets(self):
        info_frame = tk.LabelFrame(self, text=f'Welcome {self.controller.user[1]}!', font=FONT1, pady=5, padx=5)
        info_frame.grid(row=1, column=1, sticky='nsew')

        image_frame = tk.Frame(info_frame)
        image_frame.grid(row=0, sticky='nsew', pady=5, padx=5)
        image = Image.open('avatar.png').resize((150, 150))
        self.image = ImageTk.PhotoImage(image=image)
        tk.Label(image_frame, image=self.image).pack(fill='both', expand=True)
        tk.Button(image_frame, text='Upload image').pack(fill='x', expand=True)

        side_image_frame = tk.Frame(info_frame)
        side_image_frame.grid(row=0, column=1, sticky='nsew', pady=25)
        self.status_menu = tk.OptionMenu(side_image_frame, self.status, 'online', 'busy', 'do not disturb', command=self.select_status)
        self.status_menu.pack(fill=tk.X, expand=True)
        self.select_status('online')

        tk.Button(side_image_frame, text='Change Password', bg="#184a45", fg='white', font=FONT3, command=self.display_change_password).pack(fill=tk.X, expand=True)
        tk.Button(side_image_frame, text='Logout', bg='red', fg='white', font=FONT3, command=self.logout).pack(fill=tk.X, expand=True)

        ttk.Separator(info_frame, orient=tk.HORIZONTAL).grid(row=1, columnspan=2, pady=4, sticky='nsew')

        tk.Label(info_frame, text='Username:', anchor='w', font=FONT3).grid(row=2, column=0, sticky='nsew')
        tk.Entry(info_frame, textvariable=self.username, justify='center', relief=tk.SUNKEN, font=FONT3).grid(row=2, column=1, sticky='nsew', pady=5)
        tk.Label(info_frame, text='Phone Number:', anchor='w', font=FONT3).grid(row=3, column=0, sticky='nsew')
        tk.Entry(info_frame, textvariable=self.phone, justify='center', relief=tk.SUNKEN, font=FONT3).grid(row=3, column=1, sticky='nsew', pady=5)
        tk.Label(info_frame, text='Address:', anchor='w', font=FONT3).grid(row=4, column=0, sticky='nsew')
        tk.Entry(info_frame, textvariable=self.address, justify='center', relief=tk.SUNKEN, font=FONT3).grid(row=4, column=1, sticky='nsew', pady=5)

        tk.Button(info_frame, text='Save', bg='green', fg='white', font=FONT2, command=self.save_profile).grid(row=5, columnspan=2, sticky='nsew', pady=5)
        [info_frame.columnconfigure(i, weight=1) for i in (0,1)]

        tk.Button(self, text='Delete Account', bg='red', fg='white', font=FONT3, command=self.delete_user).grid(row=2, column=1, sticky='nsew', pady=5)

        grid_column_configure(self)
        [self.rowconfigure(i, minsize=15) for i in (0,)]
        [self.rowconfigure(i, minsize=30) for i in (1,2)]

    def change_password(self):
        oldpass = self.old_password.get().strip()
        newpass = self.new_password.get().strip()

        if len(newpass) < 6: 
            return messagebox.showerror('Invalid Password', 'Password must be atleast 6 characters long')
        self.socket.send_data('CHANGE_PASSWORD', oldpass=oldpass, newpass=newpass)
        if hasattr(self, 'pwindow'):
            return self.pwindow.destroy()

    def select_status(self, event):
        colors = {
            'online': ('sea green', 'white'),
            'busy': ('yellow2', 'black'), 
            'do not disturb': ('indian red', 'white')
        }
        self.status_menu.config(bg=colors[event][0], fg=colors[event][1], font=FONT3)
    
    def save_profile(self):
        username, phone, address = self.username.get(), self.phone.get(), self.address.get()
        if not (3 <= len(username) <= 30): 
            return messagebox.showerror('Invalid Username', 'Username must be 3 to 30 characters long')
        if not username.isalnum():
            return messagebox.showerror('Invalid Username', 'Username can only contain alphabets and numbers')
        if phone and not phone.isdigit() or len(phone) != 9:
            return messagebox.showerror('Invalid Phone Number', 'Phone number must contain 9 digits')
        if len(address) > 100:
            return messagebox.showerr('Invalid Address', 'Address should not be more than 100 characters long')
        
        self.socket.send_data('UPDATE_PROFILE', username=username, phone=phone, address=address)

    def logout(self):
        self.socket.send_data('LOGOUT')

    def display_change_password(self):
        if hasattr(self, 'pwindow'):
            self.pwindow.destroy()
        self.pwindow = tk.Toplevel(self, bg=BLUE)
        self.pwindow.title('Change Password')
        self.pwindow.geometry("300x250")

        self.old_password = create_entry(self.pwindow, "Old Password", row=1, column=1, bg=BLUE, show="*")
        self.new_password = create_entry(self.pwindow, "New Password", row=4, column=1, bg=BLUE, show="*")

        tk.Button(self.pwindow, text="Save", font=FONT2, height=2, command=self.change_password).grid(row=7, column=1, sticky="nsew")
        grid_column_configure(self.pwindow)
        [self.pwindow.rowconfigure(i, minsize=15) for i in (0,3,6)]
        [self.pwindow.rowconfigure(i, minsize=30) for i in (1,2,4,5,7)]

    def delete_user(self):
        if messagebox.askyesno('Delete Account', 'Are you sure you want to delete your account? This action cannot be undone'):
            password = simpledialog.askstring('Delete Account', 'Enter current password', show='*')
            if password:
                self.socket.send_data('DELETE_ACCOUNT', password=password)


class ScrollableFrame(tk.Frame):
    "Utility class that manages frames that can be scrolled and dynamically updates itself"
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Create a frame inside a canvas, pack it to left
        # Create a vertical scrollbar, pack it to right
        self.canvas = tk.Canvas(self, bd=0, background=kwargs.get('bg', 'white'))
        self.frame = tk.Frame(self.canvas, background=kwargs.get('bg', 'white'))
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Places the frame on the canvas
        # Update scroll region when any event is fired
        self.canvas_frame = self.canvas.create_window((4,4), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.update_scrollbar)
        self.canvas.bind('<Configure>', self.resize_frame)
    
    def clear(self):
        "Deletes all items on the frame and resets the scrollbar"
        for child in self.frame.winfo_children():
            child.destroy()
    
        self.canvas.yview_moveto(0)

    def resize_frame(self, event):
        "Resize frame to canvas size"
        self.canvas.itemconfigure(self.canvas_frame, width=event.width)
    
    def update_scrollbar(self, _=None):
        "Update scroll region to cover whole canvas"
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1)

