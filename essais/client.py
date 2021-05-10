from socketio import AsyncServer

sio = AsyncServer(async_mode="sanic")
socketio_webhook = SocketBlueprint(
            sio, self.socketio_path, "socketio_webhook", __name__
        )