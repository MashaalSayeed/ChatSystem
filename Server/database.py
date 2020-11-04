import hashlib
import base64
import os

from datetime import datetime


def encrypt_password(password):
    salt = os.urandom(16)
    hashed = hashlib.sha512(password.encode('utf8')+salt).digest()
    return base64.b64encode(salt + hashed) # 108 chars fixed


def compare_password(raw, encrypted):
    try:
        decoded = base64.b64decode(encrypted)
        salt, password = decoded[:16], decoded[16:] # Get salt and sha512 password

        hashed = hashlib.sha512(raw.encode('utf8')+salt).digest() # hash input with same salt
        return hashed == password
    except Exception as e:
        return False


def change_password(server, user, oldpass, newpass):
    server.cursor.execute("SELECT password FROM users WHERE userid=%s", (user[0],))
    hashed = server.cursor.fetchone()
    if hashed and compare_password(oldpass, hashed[0]):
        hashed_pass = encrypt_password(newpass)
        server.cursor.execute("UPDATE users SET password=%s WHERE userid=%s", (hashed_pass, user[0]))
        server.conn.commit()
        return 'INFO', {'message': 'Password Updated!'}
    else:
        return 'ERROR', {'message': 'Invalid password'}


def register_user(server, email, username, password):
    try:
        hashed = encrypt_password(password)
        server.cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username,email,hashed))
        server.conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    
def login_user(server, email, password):
    server.cursor.execute("SELECT password FROM users WHERE email=%s", (email,))
    hashed = server.cursor.fetchone()
    if hashed and compare_password(password, hashed[0]):
        # Enter actual query here..
        server.cursor.execute("SELECT userid, email, username FROM users WHERE email=%s", (email,))
        return True, server.cursor.fetchone()
    else:
        return False, None


def fetch_rooms(server, user):
    server.cursor.execute("""
SELECT rooms.roomid, roomname, ownerid FROM 
  rooms, room_members
WHERE
  room_members.roomid = rooms.roomid
  AND room_members.userid = %s;""", [user[0]])

    return server.cursor.fetchall()


def fetch_members(server, user, body):
    server.cursor.execute("""
SELECT r2.roomid, users.userid, email, username
FROM room_members r1 JOIN room_members r2 ON 
  r2.roomid = r1.roomid
JOIN users ON
  users.userid = r2.userid
WHERE 
  r1.userid=%s AND r2.userid != %s""", (user[0], user[0]))

    return server.cursor.fetchall()


def fetch_recent_chats(server, user, body):
    server.cursor.execute("""
SELECT 'public', m.roomid, content, email, username, created_at FROM
  messages m, users, room_members rm
WHERE
  m.author = users.userid AND
  m.roomid = rm.roomid AND rm.userid = %s
UNION 
SELECT 'private', f.id, content, email, username, created_at FROM
  messages m, users, friends f
WHERE
  m.author = users.userid AND m.friendid = f.id AND
  (f.userid1=%s OR f.userid2=%s)
ORDER BY created_at DESC;""", [user[0]]*3)

    return server.cursor.fetchall()


def send_message(server, user, room, content):
    now = datetime.now()
    try:
        server.cursor.execute("INSERT INTO messages (roomid, author, content, created_at) VALUES (%s, %s, %s, %s)", (room, user[0], content, now))
        server.conn.commit()
        return ['public', room, content, user[1], user[2], now]
    except Exception as e:
        print(e)
        return False

def send_private_message(server, user, fid, content):
    now = datetime.now()
    try:
        server.cursor.execute('INSERT INTO messages (friendid, author, content, created_at) VALUES (%s, %s, %s, %s)', (fid, user[0], content, now))
        server.conn.commit()
        return ['private', fid, content, user[1], user[2], now]
    except Exception as e:
        print(e)
        return False

def create_room(server, user, roomname, members):
    try:
        server.cursor.execute("INSERT INTO rooms (roomname, ownerid) VALUES (%s, %s)", (roomname, user[0]))
        roomid = server.cursor.lastrowid
        
        val = [(userid, roomid) for userid in members]
        server.cursor.executemany("INSERT INTO room_members (userid, roomid) VALUES (%s, %s)", val)
        server.conn.commit()
        return roomid, roomname, user[0]
    except Exception as e:
        print(e)
        server.conn.rollback()
        return False


def invite_member(server, user, roomid, email):
    server.cursor.execute('SELECT userid, email, username FROM users WHERE email=%s', (email,))
    member = server.cursor.fetchone()
    if not member:
        return 'ERROR', {'message': 'Email ID not found'}

    try:
        server.cursor.execute("INSERT INTO room_members (userid, roomid) VALUES (%s, %s)", (member[0], roomid))
        server.conn.commit()
        return 'MEMBER_JOIN', member
    except Exception as e:
        print(e)
        return 'ERROR', {'message': 'This user is already in the room'}


def leave_member(server, user, memberid, roomid):
    try:
        server.cursor.execute("DELETE FROM room_members WHERE userid=%s AND roomid=%s", (memberid, roomid))
        server.conn.commit()
        return True
    except Exception as e:
        print(e)
        return False

def delete_room(server, user, roomid):
    try:
        server.cursor.execute("DELETE FROM rooms WHERE roomid=%s AND ownerid=%s", (roomid,user[0]))
        server.conn.commit()
        return True
    except Exception as e:
        print(e)
        return False

def fetch_friends(server, user):
    server.cursor.execute("""
SELECT f.id, u.userid, email, username FROM 
  friends f, users u
WHERE
  f.userid2 = u.userid AND f.userid1 = %s
  OR f.userid1 = u.userid AND f.userid2 = %s;
""", (user[0], user[0]))

    return server.cursor.fetchall()


def add_friend(server, user, email):
    # Make sure userid1 < userid2, so we know how the record was inserted
    server.cursor.execute("SELECT userid, email, username FROM users WHERE email=%s", (email,))
    friend = server.cursor.fetchone()
    if not friend:
        return 'ERROR', {'message': 'Email ID not found!'}

    user1, user2 = sorted([user[0], friend[0]])
    try:
        server.cursor.execute("INSERT INTO friends (userid1, userid2) VALUES (%s, %s)", (user1, user2))
        server.conn.commit()
        return 'ADD_FRIEND', (server.cursor.lastrowid, *friend)
    except Exception as e:
        print(e)
        server.conn.rollback()
        return 'ERROR', {'message': 'You already have that user as a friend'}


def remove_friend(server, user, fid, fuser):
    user1, user2 = sorted([user[0], fuser])
    try:
        server.cursor.execute("DELETE FROM friends WHERE id=%s AND userid1=%s AND userid2=%s", (fid, user1, user2))
        server.conn.commit()
        return 'REMOVE_FRIEND', fid
    except Exception as e:
        print(e)
        return 'ERROR', {'message': 'hm'}

def fetch_user(server, user, email):
    server.cursor.execute('SELECT userid, email, username FROM users WHERE email=%s', (email,))
    res = server.cursor.fetchone()
    if not res:
        return 'ERROR', {'message': 'This email ID doesnt exist'}
    else:
        return 'FETCH_USER', res

def fetch_single_room(server, roomid):
    server.cursor.execute('SELECT * FROM rooms WHERE roomid=%s', (roomid,))
    return server.cursor.fetchone()
