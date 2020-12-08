+=============================================================+
|                        SQL CHAT                             |
+=============================================================+


                 FEATURES
-------------------------------------------------
-> SSL encrypted using self signed certificates
-> Login / Register / Logout
-> Add / Remove Friends
-> Create / Leave Rooms
-> Add / Kick Participants
-> Send Messages
-> Send attachments
-> Private / Group Chat
-> Change Password
-> Update Profile Information
 

                HOW TO RUN
--------------------------------------------------
1. Go to Server/main.py
2. Enter mysql host, user, password, database
3. Run the main file

4. Go to Client/main.py
5. Enter server host (localhost) and port (5555)
6. Run the main file


                    NOTES
--------------------------------------------------
1. Requires python version 3.7+
2. MySQL server should also be running at the given host and port
3. For ssl to work, chatserver.crt must be in both client and server folders
   and chatserver.key must be with server and never be shared
4. GUI requires tkinter to work (installed in python by default)
5. Only one server can run at a time, but multiple clients can connect to it
   at the same time