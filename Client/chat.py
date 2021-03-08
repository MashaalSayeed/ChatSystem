from collections import defaultdict


class ChatClient:
    def __init__(self, socket):
        
        self.socket = socket
        self.user = None
        self.friends = defaultdict(lambda: {'name': '', 'messages': [], 'user': []})
        self.chats = defaultdict(lambda: {'name': '', 'owner': '', 'messages': [], 'members': []})

    def login(self):
        pass

    def logout(self):
        pass

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

    def send_message(self, roomid, content):
        pass

    def invite_member(self, roomid, email):
        pass

    def kick_member(self, roomid):
        pass

