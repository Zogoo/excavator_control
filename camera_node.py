#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
from Camera import Camera

from client_message import Message

class CameraNode:
    def __init__(self) -> None:
        self.sel = selectors.DefaultSelector()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.sel.close()
        except RuntimeWarning:
            return True

    def create_request(self, action, value, encode="utf-8"):
        if encode == "bin":
            return dict(
                type="binary/custom-client-binary-type",
                encoding="binary",
                content=bytes(action + value, encoding="utf-8"),
            )
        else:
            return dict(
                type="text/json",
                encoding="utf-8",
                content=dict(action=action, value=value),
            )

    def start_connection(self):
        self.addr = ('127.0.0.1', 65432)
        print("starting connection to", self.addr)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex(self.addr)

    def send_instruction(self):
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        message = Message(self.sel, self.sock, self.addr)
        self.sel.register(self.sock, events, data=message)

        try:
            while True:
                events = self.sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

    def send_request(self, action, value):
        request = self.create_request(action, value)
        self.start_connection(request)
        self.send_instruction()

def find_object(results, labels, sizes, distances, obj_name):
    cnode = CameraNode()
    score = 0

    for obj in results:
        if labels[obj['class_id']] == obj_name:
            score = obj['score']

    obj_size = next((size for size in sizes if size["name"] == obj_name), None)
    obj_dist = next((dist for dist in distances if dist["name"] == obj_name), None)

    while score < 0.5:
        cnode.send_request("left", "4")
        cnode.send_request("right", "4")

    cnode.send_request("stop", "all")

    while obj_dist > 100:
        cnode.send_request("forward", "1")

    cnode.send_request("stop", "all")

tl_models = [
    {
        'name': 'shovel',
        'model_path': './trained_model/shovel_model/model.tflite',
        'label_path': './trained_model/shovel_model/model-dict.txt',
        'function': None
    },
    {
        'name': 'apple',
        'model_path': './trained_model/object/detect.tflite',
        'label_path': './trained_model/object/coco_labels.txt',
        'function': find_object
    }
]

camera = Camera(tl_models)
camera.execute_command()
