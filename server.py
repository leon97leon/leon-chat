import socket_server_video
import socket_server_audio
import socket_server_text

if __name__ == "__main__":
    socket_server_video.start()
    socket_server_audio.start()
    socket_server_text.start()
