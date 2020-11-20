#v0.9 - Alpha 1
#v0.8
import socket
import random
import select
from threading import Thread
#import videosocket

HEADER_LENGTH = 10
NP_ROW_CHARS_SIZE = 4
NP_COL_CHARS_SIZE = 4
NP_DIM_CHARS_SIZE = 4

print('Provide IP and port for video communication server')
IP = "192.168.0.135"
#IP = input(f'IP: {socket.gethostbyname(socket.gethostname())}') or socket.gethostbyname(socket.gethostname())

PORT = 5678
#PORT = int(input(f'PORT: '))

# Create a socket
# socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
# socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# SO_ - socket option
# SOL_ - socket option level
# Sets REUSEADDR (as a socket option) to 1 on socket
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind, so server informs operating system that it's going to use given IP and port
# For a server using 0.0.0.0 means to listen on all available interfaces, useful to connect locally to 127.0.0.1 and remotely to LAN interface IP
server_socket.bind((IP, PORT))

# This makes server listen to new connections
server_socket.listen()

# List of sockets for select.select()
sockets_list = [server_socket]
sockets_list_removed = []
# List of connected clients - socket as a key, user header and name as data
clients = {}

print(f'Video chat server: Listening for connections on {IP}:{PORT}...')

# Handles message receiving
def receive_message(client_socket, receive_size=HEADER_LENGTH, split_flag=False):
    try:
        message_header = ''.encode('utf-8')
        totrec = 0
        while totrec<receive_size :
            chunk = client_socket.recv(receive_size - totrec)
            #print("1",chunk)
            #print(chunk)
            #if chunk == '':
            if chunk is False:
                print("In receive_message: received 0 bytes during receive of data size.")
                #raise RuntimeError("Socket connection broken")
                #break
                return False
            totrec += len(chunk)
            message_header = message_header + chunk


        # If we received no data, client gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
        if not len(message_header):
            return False

        # Convert header to int value
        message_length = int(message_header.decode('utf-8').strip())

        message_data = ''.encode('utf-8')
        totrec = 0
        while totrec<message_length :
            chunk = client_socket.recv(message_length - totrec)
            #print("2",chunk)

            #if chunk == '':
            if chunk is False:
                print("In receive_message: received 0 bytes during receive of data.")
                #raise RuntimeError("Socket connection broken")
                #break
                return False
            totrec += len(chunk)
            message_data = message_data + chunk

        if not len(message_data):
            return False

        # Return an object of message header and message data
        #return {'header': message_header, 'data': client_socket.recv(message_length)}
        if(split_flag == True):
            message_split = message_data.split(':'.encode('utf-8'), 1)
            message_header = f"{len(message_split[1]):<{HEADER_LENGTH}}".encode('utf-8')
            return {'header': message_header, 'keyword': message_split[0], 'data': message_split[1]}

        return {'header': message_header, 'data': message_data}

    except:

        # If we are here, client closed connection violently, for example by pressing ctrl+c on his script
        # or just lost his connection
        # socket.close() also invokes socket.shutdown(socket.SHUT_RDWR) what sends information about closing the socket (shutdown read/write)
        # and that's also a cause when we receive an empty message
        return False

def send_message(client_socket, message_bytes):
    try:
        # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
        send_size = len(message_bytes)
        tot_sent = 0
        while tot_sent < send_size:
            ret = client_socket.send(message_bytes[tot_sent:send_size])
            tot_sent += ret
        #client_socket_video.send(message_header + message)
    except Exception as e:
        print(f'Exception in send_message: {e}')

def send_ack(client_socket, message):
    try:
        # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
        message = message.encode('utf-8')
        message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
        #client_socket.send(message_header + message)
        send_message(client_socket, message_header + message)
        return client_socket
    except Exception as e:
        print(f'Exception in send_ack: {e}')


def thread_listner(notified_socket,keyclients,curve):
    global sockets_list
    global clients
    
    while True:
        keyword_dict = receive_message(notified_socket, HEADER_LENGTH)
        if( keyword_dict is False):
            temp_user = clients[notified_socket]
            print(f'keyword_dict is False, breaking connection for user={temp_user["data"].decode("utf-8")}...')
            sockets_list.remove(notified_socket)
            print('Closed connection from: {}'.format(temp_user['data'].decode('utf-8')))
            clients[notified_socket] = None
            break
        keyword_message = (keyword_dict['data'].decode('utf-8')).strip()
        if(keyword_message.upper() == 'CLOSING'):
            to_remove_socket = None
            user = clients[notified_socket]
            for client_socket in clients:
                # But don't sent it to sender
                if ((client_socket != notified_socket) and (clients[client_socket] != None)):
                    if(clients[client_socket]['keyword'] != b'SEND_SOCKET'):
                        client_socket.send(user['header'] + user['data'])
                        if(clients[client_socket]['data'] != clients[notified_socket]['data']):
                            client_socket.send(keyword_dict['header'] + keyword_dict['data'])
                        else:
                            to_remove_socket = send_ack(client_socket, 'ACK_CLOSED')

            sockets_list.remove(notified_socket)
            print('Closed connection from: {}'.format(user['data'].decode('utf-8')))
            clients[notified_socket] = None
            if(to_remove_socket):
                sockets_list.remove(to_remove_socket)
                clients[to_remove_socket] = None
            break
        elif(keyword_message.upper() == 'DATA'):
            #firsr we need to get the shape of the stream
            #first we get the rows
            shape_size_dict = receive_message(notified_socket)
            if(shape_size_dict is False):
                print('shape size dict is False, continuing...')
                continue

            #shape_size_str = (shape_size_dict['data'].decode('utf-8')).strip()

            #shape_size_split = shape_size_str.split(',')
            #message_size = int(shape_size_split[3])
            
            """shape_row_int = int(shape_size_split[0])
            shape_col_int = int(shape_size_split[1])
            shape_dim_int = int(shape_size_split[2])"""

            """message_size = int((shape_rows_dict['data'].decode('utf-8')).strip()) * \
                        int((shape_cols_dict['data'].decode('utf-8')).strip()) * \
                        int((shape_dim_dict['data'].decode('utf-8')).strip())"""

            """message_size_dict = receive_message(notified_socket, HEADER_LENGTH)
            if(message_size_dict is False):
                print('message_size_dict is False, continuing...')
                continue

            message_size = int((message_size_dict['data'].decode('utf-8')).strip())"""
            
            """message = ''.encode('utf-8')
            totrec = 0
            while totrec<message_size :
                chunk = notified_socket.recv(message_size - totrec)
                #if chunk == '':
                if chunk is False:
                    print("While receiving chunk received empty chunk of video: During receiving frame socket connection broken")
                    #raise RuntimeError("Socket connection broken")
                    break
                totrec += len(chunk)
                message = message + chunk"""


            # If False, client disconnected, cleanup
            """if message is False:
                print('message is False, continuing...')
                continue"""

            # Get user by notified socket, so we will know who sent the message
            user = clients[notified_socket]

            if(user == None):
                print("client disconnected, stoping the thread listner")
                break
            #print(f'Received message from {user["data"].decode("utf-8")}') #': {message["data"].decode("utf-8")}')

            # Iterate over connected clients and broadcast message
            for client_socket in clients:
                # But don't sent it to sender
                if ((client_socket != notified_socket) and (clients[client_socket] != None)):
                    if(clients[client_socket]['keyword'] != b'SEND_SOCKET'):
                        if(clients[client_socket]['data'] != clients[notified_socket]['data']):
                            #create a thread to send the data to currne client socket
                            """thread_client_send = Thread(target=pass_to_clients, 
                                args=(client_socket, user, keyword_dict, shape_size_dict))
                            thread_client_send.start()"""
                            send_message(client_socket, user['header'] + user['data'])
                            send_message(client_socket, keyword_dict['header'] + keyword_dict['data'])
                            send_message(client_socket, shape_size_dict['header'] + shape_size_dict['data'])
                            """totalsent = 0
                            while totalsent < message_size :
                                sent = client_socket.send(message)
                                if sent == 0:
                                    print("client_socket.send(message) returned 0 bytes, breaking send to username =  " + user['data'].decode('utf-8'))
                                    #raise RuntimeError("Socket connection broken")
                                    break
                                totalsent += sent"""


def delete_matching_read_socket(send_socket):
    user = clients[send_socket]['data']
    try:
        finditem = [key for key in clients if ((clients[key]['keyword'] == b'READ_SOCKET') and 
                                            (clients[key]['data'] == clients[send_socket]['data']))]

        for key in finditem: del clients[key]
    except Exception as e:
        print(f'Exception in delete_matching_read_socket: {e}')

def delete_socket(notified_socket):
    try:
        if( notified_socket not in sockets_list_removed):
            sockets_list_removed.append(notified_socket)

        if(notified_socket in clients):
            delete_matching_read_socket(notified_socket)
            del clients[notified_socket]
    except Exception as e:
        print(f'Exception in delete_socket: {e}')

def process_request(notified_socket):
    global sockets_list
    global clients
    # try:
    keyword_dict = receive_message(notified_socket, HEADER_LENGTH)
    if( keyword_dict is False):
        print('keyword_dict is False, Closed connection from: {}'.format(clients[notified_socket]['data'].decode('utf-8')))
        """sockets_list.remove(notified_socket)
        clients[notified_socket] = None"""
        delete_socket(notified_socket)
        return -1
    keyword_message = (keyword_dict['data'].decode('utf-8')).strip()
    if(keyword_message.upper() == 'CLOSING'):
        to_remove_socket = None
        user = clients[notified_socket]
        for client_socket in clients:
            # But don't sent it to sender
            if ((client_socket != notified_socket) and (clients[client_socket] != None)):
                if(clients[client_socket]['keyword'] != b'SEND_SOCKET'):
                    client_socket.send(user['header'] + user['data'])
                    if(clients[client_socket]['data'] != clients[notified_socket]['data']):
                        client_socket.send(keyword_dict['header'] + keyword_dict['data'])
                    else:
                        to_remove_socket = send_ack(client_socket, 'ACK_CLOSED')

        print('Closed connection from: {}'.format(user['data'].decode('utf-8')))
        """sockets_list.remove(notified_socket)
        clients[notified_socket] = None"""
        delete_socket(notified_socket)
        if(to_remove_socket):
            delete_socket(to_remove_socket)
        """if(to_remove_socket):
            sockets_list.remove(to_remove_socket)
            clients[to_remove_socket] = None"""
        return -1
    elif(keyword_message.upper() == 'DATA'):
        #firsr we need to get the shape of the stream
        #first we get the rows
        message_dict = receive_message(notified_socket)
        if(message_dict is False):
            print('shape size dict is False, continuing to next client socket...')
            delete_socket(notified_socket)
            return -2

        #shape_size_str = (shape_size_dict['data'].decode('utf-8')).strip()

        #shape_size_split = shape_size_str.split(',')
        #message_size = int(shape_size_split[3])

        """shape_row_int = int(shape_size_split[0])
        shape_col_int = int(shape_size_split[1])
        shape_dim_int = int(shape_size_split[2])"""

        """message_size = int((shape_rows_dict['data'].decode('utf-8')).strip()) * \
                    int((shape_cols_dict['data'].decode('utf-8')).strip()) * \
                    int((shape_dim_dict['data'].decode('utf-8')).strip())"""

        """message_size_dict = receive_message(notified_socket, HEADER_LENGTH)
        if(message_size_dict is False):
            print('message_size_dict is False, continuing...')
            continue

        message_size = int((message_size_dict['data'].decode('utf-8')).strip())"""

        """message = ''.encode('utf-8')
        totrec = 0
        while totrec<message_size :
            chunk = notified_socket.recv(message_size - totrec)
            #if chunk == '':
            if chunk is False:
                print("While receiving chunk received empty chunk of video: During receiving frame socket connection broken")
                #raise RuntimeError("Socket connection broken")
                break
            totrec += len(chunk)
            message = message + chunk"""


        # If False, client disconnected, cleanup
        """if message is False:
            print('message is False, continuing...')
            continue"""

        # Get user by notified socket, so we will know who sent the message
        user = clients[notified_socket]

        if(user == None):
            print("user=None. client disconnected, continuing to next client socket...")
            delete_socket(notified_socket)
            return -2

        # Iterate over connected clients and broadcast message
        for client_socket in clients:
            # But don't sent it to sender
            if ((client_socket != notified_socket) and (clients[client_socket] != None)):
                if(clients[client_socket]['keyword'] != b'SEND_SOCKET'):
                    if(clients[client_socket]['data'] != clients[notified_socket]['data']):
                        #keyclients.get(user['data'].decode('utf-8'),None) is None:
                        #create a thread to send the data to currne client socket
                        """thread_client_send = Thread(target=pass_to_clients, 
                            args=(client_socket, user, keyword_dict, shape_size_dict))
                        thread_client_send.start()"""
                        # print(clients[client_socket]['data'])
                        # key = keyclients.get(clients[client_socket]['data'].decode('utf-8'))[1]
                        # print(key)
                        # text = curve.encrypt(bg[3], key, algo="aes-256-ofb")
                        # message_dict['data'] = bg[0] + ",".encode('utf-8') + bg[1] + ",".encode('utf-8') + bg[2] + ",".encode('utf-8') + text
                        # message_dict['header'] = f"{len(message_dict['data']):<{HEADER_LENGTH}}".encode('utf-8')

                        send_message(client_socket, user['header'] + user['data'])
                        send_message(client_socket, keyword_dict['header'] + keyword_dict['data'])
                        send_message(client_socket, message_dict['header'] + message_dict['data'])
                        #print(3)
                        """totalsent = 0
                        while totalsent < message_size :
                            sent = client_socket.send(message)
                            if sent == 0:
                                print("client_socket.send(message) returned 0 bytes, breaking send to username =  " + user['data'].decode('utf-8'))
                                #raise RuntimeError("Socket connection broken")
                                break
                            totalsent += sent"""
    return 1
    # except Exception as e:
    #     print(f'Exception in process_request: {e}')
def start():
    while True:
        #try:
            # Calls Unix select() system call or Windows select() WinSock call with three parameters:
            #   - rlist - sockets to be monitored for incoming data
            #   - wlist - sockets for data to be send to (checks if for example buffers are not full and socket is ready to send some data)
            #   - xlist - sockets to be monitored for exceptions (we want to monitor all sockets for errors, so we can use rlist)
            # Returns lists:
            #   - reading - sockets we received some data on (that way we don't have to check sockets manually)
            #   - writing - sockets ready for data to be send thru them
            #   - errors  - sockets with some exceptions
            # This is a blocking call, code execution will "wait" here and "get" notified in case any action should be taken
            read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)


            # Iterate over notified sockets
            for notified_socket in read_sockets:

                # If notified socket is a server socket - new connection, accept it
                if notified_socket == server_socket:

                    # Accept new connection
                    # That gives us new socket - client socket, connected to this given client only, it's unique for that client
                    # The other returned object is ip/port set
                    client_socket, client_address = server_socket.accept()

                    # Client should send his name right away, receive it
                    user = receive_message(client_socket, HEADER_LENGTH, True)
                    # If False - client disconnected before he sent his name
                    if user is False:
                        continue

                    # Add accepted socket to select.select() list
                    sockets_list.append(client_socket)

                    # Also save username and username header
                    clients[client_socket] = user
                    """if(user['keyword'] == b'SEND_SOCKET'):
                        listner_thread = Thread(target=thread_listner, args=(client_socket,), daemon=True)
                        listner_thread.start()"""

                    print('Accepted new connection from {}:{}, username: {}'.format(*client_address, user['data'].decode('utf-8')))


                elif (clients[notified_socket]['keyword'] == b'SEND_SOCKET'):
                    ret = process_request(notified_socket)
                    #send_message(client_socket, msg2)
                # elif (clients[notified_socket]['keyword'] == b'SEND_SOCKET'):
                #     listner_thread = Thread(target=thread_listner, args=(notified_socket,keyclients,curve,), daemon=True)
                #     listner_thread.start()
            sockets_list[:] = [x for x in sockets_list if x not in sockets_list_removed]
            sockets_list_removed.clear()

            # It's not really necessary to have this, but will handle some socket exceptions just in case
            for notified_socket in exception_sockets:

                # Remove from list for socket.socket()
                sockets_list.remove(notified_socket)

                # Remove from our list of users
                del clients[notified_socket]
        #except Exception as e:
            #print('Exception in video server - ' + str(e))
if __name__ == '__main__':
    start()