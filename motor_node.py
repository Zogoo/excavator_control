#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback

from server_message import Message
from Excavator import Excavator

class MotorNode:
    def __init__(self) -> None:
        self.sel = selectors.DefaultSelector()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.sel.close()
        except RuntimeWarning:
            return True

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print("accepted connection from", addr)
        conn.setblocking(False)
        message = Message(self.sel, conn, addr, instructions)
        self.sel.register(conn, selectors.EVENT_READ, data=message)

    def init_listener(self):
        addr = ('127.0.0.1', 65432)
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind(addr)
        lsock.listen()
        print("listening on", addr)
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)

    def follow_instructions(self):
        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        print("Accept wrapper is executed")
                        self.accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            print(
                                "main: error: exception for",
                                f"{message.addr}:\n{traceback.format_exc()}",
                            )
                            message.close()
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.sel.close()
    

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
motor_node.init_listener()
motor_node.follow_instructions()
