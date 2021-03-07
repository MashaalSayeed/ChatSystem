import base64
import database as db


async def login(socket, server, body):
    "Handle login requests"
    success, user = db.login_user(server, **body)
    if success:
        socket.user = list(user)
        await socket.send('LOGIN', {'message': 'Login success!!', 'user': user})
    else:
        await socket.send('LOGIN', {'error': True, 'message': 'Invalid email id or password'})


async def register(socket, server, body):
    "Register the user"
    if db.register_user(server, **body):
        await socket.send('REGISTER', {'message': 'Registration successful!'})
    else:
        await socket.send('REGISTER', {'error': True, 'message': 'Registration was not successful'})


async def logout(socket, server, body):
    "Logs the user out, leaves all rooms"
    socket.user = None
    server.leave_all_rooms(socket)
    await socket.send('LOGOUT', {})


async def change_password(socket, server, body):
    "Change password, error if old password is invlaid"
    h, b = db.change_password(server, socket.user, **body)
    await socket.send(h, b)


async def delete_account(socket, server, body):
    "Deletes the account if exists"
    if db.delete_account(server, socket.user, **body):
        await socket.send('INFO', {'message': 'Account successfully deleted'})
        await logout(socket, server, body)
    else:
        await socket.send('ERROR', {'message': 'Invalid password'})


async def update_profile(socket, server, body):
    h, b = db.update_profile(server, socket.user, **body)
    await socket.send(h, b)
    if h != 'ERROR':
        socket.user[2:] = [body.get('username'), body.get('phone'), body.get('address')]
        print(socket.user)


async def fetch_user(socket, server, body):
    "Fetch any user from the database with their email id"
    h, b = db.fetch_user(server, socket.user, **body)
    await socket.send(h, b)


async def fetch_recent_chats(socket, server, body):
    "Fetch all messages from all rooms and private chats this user is in, ordered by their date of creation"
    recent = db.fetch_recent_chats(server, socket.user, body)
    await socket.send('RECENT_CHATS', recent)


async def fetch_members(socket, server, body):
    "Fetch data of all members from all rooms"
    members = db.fetch_members(server, socket.user, body)
    await socket.send('FETCH_MEMBERS', members)


async def fetch_friends(socket, server, body):
    "Fetch data of all chats"
    friends = db.fetch_friends(server, socket.user, **body)
    await socket.send('FETCH_FRIENDS', friends)


async def add_friend(socket, server, body):
    "Adds a friend and sends the request to the other user"
    h, data = db.add_friend(server, socket.user, **body)
    await socket.send(h, data)
    if h != 'ERROR':
        b = [data[0], *socket.user]
        await server.send_to(data[1], h, b)


async def remove_friend(socket, server, body):
    "Remove a friend and sends the data to the other user"
    h, data = db.remove_friend(server, socket.user, **body)
    await socket.send(h, data)
    if h != 'ERROR':
        friend = body.get('fuser')
        await server.send_to(friend, h, data)


async def send_message(socket, server, body):
    "Sends a message to a chat room"
    message = db.add_message(server, socket.user, **body)
    if message:
        await server.send_room(body['_id'], 'MESSAGE', ['public'] + message)
    else:
        await socket.send('ERROR', {'message': 'Message was not sent!'})


async def send_private_message(socket, server, body):
    "Sends a private message to a friend"
    message = db.add_message(server, socket.user, private=True, **body)
    if message:
        server.cursor.execute("SELECT IF(userid1=%s, userid2, userid1) FROM friends WHERE id=%s;", (socket.user[0], body.get('_id')))
        friend = server.cursor.fetchone()

        await server.send_to(friend[0], 'MESSAGE', ['private'] + message)
        await socket.send('MESSAGE', ['private'] + message)
    else:
        await socket.send('ERROR', {'message': 'Message was not sent!'})


async def download_file(socket, server, body):
    filename, actualname = body.get('filename'), body.get('actualname')
    try:
        with open(f'./uploads/{filename}', 'rb') as file:
            filedata = base64.b64encode(file.read()).decode()
            await socket.send('DOWNLOAD_FILE', [actualname, filedata])
    except:
        await socket.send('ERROR', {'message': f'File "{actualname}" does not exist anymore. Ask the author to resend the attachment'})


async def create_room(socket, server, body):
    "Creates a room with the given list of members, and sends join data to all members"
    room = db.create_room(server, socket.user, **body)
    if room:
        await server.create_room(body['members'], room)
    else:
        await socket.send('ERROR', 'Room was not created')


async def fetch_rooms(socket, server, _):
    "Fetch all rooms this user is in and joins in them"
    rooms = db.fetch_rooms(server, socket.user)
    [server.join_room(socket, r[0]) for r in rooms] # Join all rooms this user is in
    await socket.send('FETCH_ROOMS', rooms)


async def invite_member(socket, server, body):
    "Invite a user to a room based on their email id and send them the room data"
    h,b = db.invite_member(server, socket.user, **body)
    if h != 'ERROR':
        roomid = body['roomid']
        room = db.fetch_single_room(server, roomid)
        await server.send_to(b[0], 'JOIN_ROOM', room)

        server.invite_to_room(b[0], roomid)
        await server.send_room(roomid, h, (roomid, b))
    else:
        await socket.send(h, b)


async def leave_member(socket, server, body):
    "Leaves the specified room, sends leave message to all other members"
    if db.leave_member(server, socket.user, **body):
        roomid = body['roomid']
        await socket.send('LEAVE_ROOM', roomid)
        server.leave_room(socket, roomid)
        await server.send_room(roomid, 'MEMBER_LEAVE', (roomid, socket.user[0]))
    else:
        await socket.send('ERROR', {'message': 'You are not a member of this room'})


async def kick_member(socket, server, body):
    "Kicks a member from a room and send them the data"
    if db.leave_member(server, socket.user, **body):
        memberid, roomid = body['memberid'], body['roomid']
        await server.send_to(memberid, 'LEAVE_ROOM', roomid)
        await server.send_room(roomid, 'MEMBER_LEAVE', (roomid, memberid))

        socket2 = server.find_socket(memberid)
        if socket2:
            server.leave_room(socket2, roomid)
    else:
        await socket.send("ERROR", {'message': "Could not kick that member"})


async def delete_room(socket, server, body):
    "Deletes the room if the user is the owner"
    if db.delete_room(server, socket.user, **body):
        roomid = body['roomid']
        await server.send_room(roomid, 'LEAVE_ROOM', roomid)
        server.rooms.pop(roomid, None)
    else:
        await socket.send('ERROR', {'message': 'Could not delete the room'})


async def join_stream(socket, server, body):
    code = body['code']
    server.streams[code].add(socket)
    socket.stream = code
    await socket.send('STREAM_JOINED')


async def leave_stream(socket, server, _):
    code = socket.stream
    if code in server.streams:
        server.streams[code].discard(socket)


async def video_stream(socket, server, body):
    code = socket.stream
    if code in server.streams:
        sockets = server.streams[code].difference({socket})
        await server.broadcast(sockets, 'VIDEO_STREAM', body['frame'])


async def audio_stream(socket, server, body):
    code = socket.stream
    if code in server.streams:
        sockets = server.streams[code]#.difference({socket})
        await server.broadcast(sockets, 'AUDIO_STREAM', body['audio'])


ROUTES = {
    'LOGIN': login,
    'REGISTER': register,
    'LOGOUT': logout,
    'CHANGE_PASSWORD': change_password,
    'DELETE_ACCOUNT': delete_account,
    'UPDATE_PROFILE': update_profile,
    'FETCH_USER': fetch_user,
    'FETCH_RECENT_CHATS': fetch_recent_chats,
    'FETCH_MEMBERS': fetch_members,
    'FETCH_FRIENDS': fetch_friends,
    'ADD_FRIEND': add_friend,
    'REMOVE_FRIEND': remove_friend,
    'SEND_MESSAGE': send_message,
    'SEND_PRIVATE_MESSAGE': send_private_message,
    'DOWNLOAD_FILE': download_file,
    'CREATE_ROOM': create_room,
    'FETCH_ROOMS': fetch_rooms,
    'INVITE_MEMBER': invite_member,
    'LEAVE_MEMBER': leave_member,
    'KICK_MEMBER': kick_member,
    'DELETE_ROOM': delete_room,
    'JOIN_STREAM': join_stream,
    'LEAVE_STREAM': leave_stream,
    'VIDEO_STREAM': video_stream,
    'AUDIO_STREAM': audio_stream
}
