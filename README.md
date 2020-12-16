# SQL CHAT

----------------------------

As the name of the project **SQL Chat System** suggests, it is a simple and easy to use chat system that allows you to send messages, share files with your friends and close ones. To ensure that your connections to the server are secure, it also uses SSL encryption with self signed certificates. 

To achieve this, the project uses **MySQL** as a database backend, **Tkinter** for the graphical interface. 

It is based on the Client-Server architecture, where multiple clients can connect to the same server. For this, the project uses **Asyncio Streams**, a high level module that manages connections, and enables sending data to and from the server asynchronously.


## FEATURES

- SSL encrypted using self signed certificates
- Login / Register / Logout
- Add / Remove Friends
- Create / Leave Rooms
- Add / Kick Participants
- Send Messages
- Send attachments
- Private / Group Chat
- Change Password
- Update Profile Information
 

## HOW TO RUN

1. Go to `Server/main.py`
2. Enter mysql **host**, **user**, **password**, **database**
3. Run the main file

4. Go to `Client/main.py`
5. Enter server **host** (`localhost`) and **port** (`5555`)
6. Run the main file


## NOTES
1. Requires python version **3.7+**
2. MySQL server should also be running at the given host and port
3. For ssl to work, `chatserver.crt` must be in both client and server folders
   and `chatserver.key` must be with server and **never be shared**
4. GUI requires tkinter to work (installed in python by default)
5. Only one server can run at a time, but multiple clients can connect to it
   at the same time
6. Since, the `chatserver.key` isn't uploaded, you must generate your own keys
   and certificates first. Go to https://getacert.com/selfsignedcert.html, fill in all the details and generate the certificate. Now, create `chatserver.key` in server folder with private key and replace the contents of `chatserver.crt` with the public key