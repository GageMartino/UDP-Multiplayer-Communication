import socket
import json

server = ("0.0.0.0", 5083)



class Packet_Struct:  

    class types:
        init_client = 0
        remove_client = 1
        upd_position = 2



class socket_server:
    clients = []

    def get_IdFromToken(token):
        for client in socket_server.clients:
            if client["auth_token"] == token:
                return client["PlayerId"]

        

    def get_nextPlayerId():
        if len(socket_server.clients) <= 0:
            last_id = 1
            return last_id
        else:
            last_id = socket_server.clients[len(socket_server.clients) - 1]["PlayerId"]

        return int(last_id) + 1


    def add_client(addr, token):

        new_id = socket_server.get_nextPlayerId()

        new_client = {"address": addr, "auth_token": token, "PlayerId": new_id}
        socket_server.clients.append(new_client)

        print(f"[+] player {new_id} connected")



    def remove_client(token):
        for client in socket_server.clients:
            if client["auth_token"] == token:

                print(f"[+] removed player {client["PlayerId"]}")

                socket_server.clients.remove(client)

                return

        print("[-] player not found")



    def broadcast_msg(sock, msg, sender_token=None):
        for client in socket_server.clients:
            if sender_token is not None and client["auth_token"] == sender_token:
                continue
            sock.sendto(msg, client["address"])



    def Update_Position(pos, token, socket):
        try:
            playerId = socket_server.get_IdFromToken(token)
            msg = json.dumps({"playerId": playerId, "pos": pos}).encode()
            socket_server.broadcast_msg(socket, msg, sender_token=token)
        except Exception as e:
            print(e)
            

    def process_req(data, client, socket):
        try:
            type = int(data["type"])
            addr = client

            if type == Packet_Struct.types.init_client:
                socket_server.add_client(addr, data["token"])
                player_id = socket_server.get_IdFromToken(data["token"])
                return json.dumps({"type": "init_ack", "playerId": player_id}).encode()

            elif type == Packet_Struct.types.remove_client:
                socket_server.remove_client(data["token"])

            elif type == Packet_Struct.types.upd_position:
                socket_server.Update_Position(data["position"], data["token"], socket)

        except Exception as e:
            print(e)



    def start_server():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.bind(server)

        try:
            while True:
                data, client_addr = sock.recvfrom(4096)

                json_data = json.loads(data.decode("utf-8"))

                print(json_data)

                socket_server.process_req(json_data, client_addr, sock)

                sock.sendto(b"Recieved...", client_addr)

        except Exception as e:
            print(e)




socket_server.start_server()

                
