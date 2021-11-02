#!/usr/bin/env python3

import socket
from Camera import Camera
import json

class CameraNode:
    HOST = "127.0.0.1"  # The server's hostname or IP address
    PORT = 65432  # The port used by the server
    
    def __init__(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __enter__(self):
        return self

    def __exit__(self):
        try:
            self.socket.close()
        except RuntimeWarning:
            return True

    def _dict_to_bytes(self, dict):
        return json.dumps(dict, ensure_ascii=False).encode('utf-8')

    def connect_to_host(self):
        self.socket.connect((self.HOST, self.PORT))

    def send_command(self, data):
        self.socket.sendall(self._dict_to_bytes(data))
        resp = self.socket.recv(1024)
        print("Received", repr(resp))

def find_object(results, labels, sizes, distances, obj_name):
    cnode = CameraNode()
    cnode.connect_to_host()
    score = 0

    for obj in results:
        if labels[obj['class_id']] == obj_name:
            score = obj['score']

    obj_size = next((size for size in sizes if size["name"] == obj_name), None)
    obj_dist = next(
        (dist for dist in distances if dist["name"] == obj_name), None)
    print(obj_name, " is located far from", obj_dist, " and size is", obj_size)

    while score < 0.5:
        print("Finding object that detected 50% more percents: ", score)
        cnode.send_command({"action": "left", "value": "4"})
        cnode.send_command({"action": "right", "value": "4"})


    print("Stopping all movements")
    cnode.send_command({"action": "stop", "value": "0"})

    while obj_dist > 200:
        print("Trying to reach near as possible: ", obj_dist)
        cnode.send_command({"action": "forward", "value": "1"})

    print("Stopping all movements")
    cnode.send_command({"action": "stop", "value": "0"})

    cnode.__exit__()


tl_models = [
    {
        'name': 'shovel',
        'model_path': './trained_model/shovel_model/model.tflite',
        'label_path': './trained_model/shovel_model/model-dict.txt',
        'function': None
    },
    {
        'name': 'people',
        'model_path': './trained_model/object/detect.tflite',
        'label_path': './trained_model/object/coco_labels.txt',
        'function': find_object
    }
]

camera = Camera(tl_models, False)
camera.execute_command()
