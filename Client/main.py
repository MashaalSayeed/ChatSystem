import asyncio

from socket_client import SocketClient
from GUI import MainWindow


async def main():
    client = SocketClient('blacksheep.zapto.org', 5555) # Connect to server (host, port)
    GUI = MainWindow(client)

    try:
        # Run both functions simultaneously
        await asyncio.gather(
            client.connect(),
            GUI.run()
        )
    except SystemExit:
        # Catch system exit errors and close the app
        pass


# Run the main function asynchronously
asyncio.run(main())
