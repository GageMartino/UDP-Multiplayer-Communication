import socket
import json
import threading
import time
import random

import pygame

SERVER_ADDR = ("127.0.0.1", 5083)

WINDOW_W, WINDOW_H = 800, 600
SQUARE_SIZE = 30
MOVE_SPEED = 4
SEND_INTERVAL = 0.05 
STALE_TIMEOUT = 5.0  

SELF_COLOR = (70, 200, 120)
OTHER_COLOR = (200, 90, 90)
BG_COLOR = (25, 25, 35)


class Packet_Struct:
    class types:
        init_client = 0
        remove_client = 1
        upd_position = 2


class NetworkClient:



    def __init__(self, server_addr, token):
        self.server_addr = server_addr
        self.token = token
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1)

        self.player_id = None
        self.lock = threading.Lock()
        self.players = {}  
        self.running = False
        self._listener_thread = None



    def connect(self):
        self.running = True
        self._listener_thread = threading.Thread(target=self._listen, daemon=True)
        self._listener_thread.start()

        self._send({"type": Packet_Struct.types.init_client, "token": self.token})

       
        waited = 0.0
        while self.player_id is None and waited < 2.0:
            time.sleep(0.05)
            waited += 0.05

        if self.player_id is None:
            print("[-] no playerId from server (is the server patched to reply to init?)")
            self.player_id = self.token  



    def disconnect(self):
        try:
            self._send({"type": Packet_Struct.types.remove_client, "token": self.token})
        except OSError:
            pass
        self.running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=2)
        self.sock.close()



    def _send(self, payload):
        data = json.dumps(payload).encode("utf-8")
        self.sock.sendto(data, self.server_addr)



    def send_position(self, x, y):
        self._send({
            "type": Packet_Struct.types.upd_position,
            "token": self.token,
            "position": {"x": x, "y": y},
        })



    def _listen(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                msg = json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            self._handle_message(msg)



    def _handle_message(self, msg):
        if isinstance(msg, dict) and msg.get("type") == "init_ack":
            with self.lock:
                self.player_id = msg["playerId"]
            print(f"[+] server assigned us playerId {self.player_id}")
            return

        if isinstance(msg, dict) and "playerId" in msg and "pos" in msg:
            pid = msg["playerId"]
            with self.lock:
                self.players[pid] = {"pos": msg["pos"], "last_seen": time.time()}

    def snapshot_players(self):
        now = time.time()
        with self.lock:
            stale = [pid for pid, p in self.players.items()
                     if now - p["last_seen"] > STALE_TIMEOUT]
            for pid in stale:
                del self.players[pid]
            return dict(self.players)


def run_game():
    token = f"token-{random.randint(1000, 999999)}"
    net = NetworkClient(SERVER_ADDR, token)
    net.connect()

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption(f"UDP Squares - player {net.player_id}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 20)

    x, y = WINDOW_W // 2, WINDOW_H // 2
    last_sent = 0.0
    last_sent_pos = None

    running = True
    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            y -= MOVE_SPEED
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            y += MOVE_SPEED
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            x -= MOVE_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            x += MOVE_SPEED
        if keys[pygame.K_ESCAPE]:
            running = False

        x = max(0, min(WINDOW_W - SQUARE_SIZE, x))
        y = max(0, min(WINDOW_H - SQUARE_SIZE, y))

        now = time.time()
        if now - last_sent > SEND_INTERVAL and ((x, y) != last_sent_pos or now - last_sent > 1.0):
            net.send_position(x, y)
            last_sent = now
            last_sent_pos = (x, y)

        screen.fill(BG_COLOR)

        # self
        pygame.draw.rect(screen, SELF_COLOR, (x, y, SQUARE_SIZE, SQUARE_SIZE))
        screen.blit(font.render(f"you ({net.player_id})", True, (255, 255, 255)), (x, y - 18))

        # everyone else
        for pid, data in net.snapshot_players().items():
            if pid == net.player_id:
                continue
            pos = data["pos"]
            px, py = pos.get("x", 0), pos.get("y", 0)
            pygame.draw.rect(screen, OTHER_COLOR, (px, py, SQUARE_SIZE, SQUARE_SIZE))
            screen.blit(font.render(str(pid), True, (255, 255, 255)), (px, py - 18))

        pygame.display.flip()

    net.disconnect()
    pygame.quit()


if __name__ == "__main__":
    run_game()