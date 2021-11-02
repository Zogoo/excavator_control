#!/usr/bin/env python3

from Excavator import Excavator
import json
import socket

class MotorNode:
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
    def __init__(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.HOST, self.PORT))
        self.socket.listen()

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

    def accept_socket(self):
        self.conn, self.addr = self.socket.accept()
        print("Connected by", self.addr)

    def listen_commands(self, instructions):
        while True:
            self.data = self.conn.recv(1024)
            if not self.data:
                break
            dict_data = self._binary_to_dict(self.data)        
            action = dict_data.get("action")
            query = dict_data.get("value")
            instructions.get(action)['cmd']()
            instructions.get(action)['fire'](int(query))
        
            self.conn.sendall(b"ok")
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
motor_node.accept_socket()
motor_node.listen_commands(instructions)
