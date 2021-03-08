import asyncio
import os

import mysql.connector
from socket_server import SocketServer


class Server(SocketServer):
    "Basically gives it the sql connection"
    def __init__(self, host, port, conn, cursor):
        super().__init__(host, port)
        
        self.conn = conn
        self.cursor = cursor

# Ensure uploads folder exists
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Start mysql connection
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='24P@$#42',
    database='chatdb'
)

cursor = conn.cursor(prepared=True)
print("Connected to MySQL server")


cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
  userid INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(30) UNIQUE NOT NULL,
  email VARCHAR(254) UNIQUE NOT NULL,
  phone INT(9),
  address VARCHAR(100),
  password CHAR(108)
);""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS rooms (
  roomid INT PRIMARY KEY AUTO_INCREMENT,
  roomname VARCHAR(30),
  ownerid INT,
  FOREIGN KEY (ownerid) REFERENCES users (userid) ON DELETE CASCADE ON UPDATE CASCADE
);""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS room_members (
  userid INT,
  roomid INT,
  PRIMARY KEY (userid, roomid),
  FOREIGN KEY (userid) REFERENCES users (userid) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (roomid) REFERENCES rooms (roomid) ON DELETE CASCADE ON UPDATE CASCADE
);""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS friends (
  id INT PRIMARY KEY AUTO_INCREMENT,
  userid1 INT,
  userid2 INT,
  UNIQUE (userid1, userid2),
  FOREIGN KEY (userid1) REFERENCES users (userid) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (userid2) REFERENCES users (userid) ON DELETE CASCADE ON UPDATE CASCADE
);""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
  messageid INT PRIMARY KEY AUTO_INCREMENT,
  roomid INT,
  friendid INT,
  author INT,
  content VARCHAR(1024),
  filename CHAR(32),
  actualname VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (roomid) REFERENCES rooms (roomid) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (friendid) REFERENCES friends (id) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (author) REFERENCES users (userid) ON DELETE CASCADE ON UPDATE CASCADE
);""")


# Run server asynchronously
server = Server('0.0.0.0', 5555, conn, cursor)
asyncio.run(server.connect())
