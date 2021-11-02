#!/usr/bin/env python3

from Excavator import Excavator
import json
import socket
import io

class MotorNode:
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
    def __init__(self) -> None:
        print("Opening socket")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.HOST, self.PORT))
        print("Start to listen")
        self.socket.listen()
        print("Accepting socket")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.socket.close()
        except RuntimeWarning:
            return True

    def _binary_to_dict(bin_str):
        jsn = ''.join(chr(int(x, 2)) for x in bin_str.split())
        d = json.loads(jsn)
        return d

    def _binary_to_dict(self, json_bytes):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding='utf-8', newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def listen_commands(self, instructions):
        print("Waiting instructions")
        try:
            conn, addr = self.socket.accept()
            print("Connected by", addr)
            with conn:
                while True:
                    self.data = conn.recv(1024)
                    if not self.data:
                        break
                    dict_data = self._binary_to_dict(self.data)        
                    action = dict_data.get("action")
                    query = dict_data.get("value")
                    print("Got instruction from client and going to execute it: ", action)
                    instructions.get(action)['cmd']()
                    instructions.get(action)['fire'](int(query))
                    conn.sendall(b"ok")

        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.socket.close()

excavator = Excavator()
instructions = {
    "forward": {'cmd': excavator.move_forward, 'fire': excavator.execute},
    "backward": {'cmd': excavator.move_forward, 'fire': excavator.execute},
    "left": {'cmd': excavator.forward_left_chain, 'fire': excavator.execute},
    "right": {'cmd': excavator.forward_right_chain, 'fire': excavator.execute},
    "shovel-left": {'cmd': excavator.turn_left_body, 'fire': excavator.execute},
    "shovel-right": {'cmd': excavator.turn_right_body, 'fire': excavator.execute},
    "shovel-up": {'cmd': excavator.move_up_shovel, 'fire': excavator.execute},
    "shovel-down": {'cmd': excavator.move_down_shovel, 'fire': excavator.execute},
    "stop": {'cmd': excavator.stop_all_motors}
}

motor_node = MotorNode()
motor_node.listen_commands(instructions)
