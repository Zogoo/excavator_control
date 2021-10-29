# python3
#
# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Example using TF Lite to detect objects with the Raspberry Pi camera."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import io
import re
import time

from annotation import Annotator

import numpy as np
import picamera

from PIL import Image
from tflite_runtime.interpreter import Interpreter

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


def load_labels(path):
    """Loads the labels file. Supports files with or without index numbers."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        labels = {}
        for row_number, content in enumerate(lines):
            pair = re.split(r'[:\s]+', content.strip(), maxsplit=1)
            if len(pair) == 2 and pair[0].strip().isdigit():
                labels[int(pair[0])] = pair[1].strip()
            else:
                labels[row_number] = pair[0].strip()
    return labels


def set_input_tensor(interpreter, image):
    """Sets the input tensor."""
    tensor_index = interpreter.get_input_details()[0]['index']
    input_tensor = interpreter.tensor(tensor_index)()[0]
    input_tensor[:, :] = image


def get_output_tensor(interpreter, index):
    """Returns the output tensor at the given index."""
    output_details = interpreter.get_output_details()[index]
    tensor = np.squeeze(interpreter.get_tensor(output_details['index']))
    return tensor


def detect_objects(interpreter, image, threshold):
    """Returns a list of detection results, each a dictionary of object info."""
    set_input_tensor(interpreter, image)
    interpreter.invoke()

    # Get all output details
    boxes = get_output_tensor(interpreter, 0)
    classes = get_output_tensor(interpreter, 1)
    scores = get_output_tensor(interpreter, 2)
    count = int(get_output_tensor(interpreter, 3))

    results = []
    for i in range(count):
        if scores[i] >= threshold:
            result = {
                'bounding_box': boxes[i],
                'class_id': classes[i],
                'score': scores[i]
            }
            results.append(result)
    return results


def annotate_objects(annotator, results, labels):
    """Draws the bounding box and label for each object in the results."""
    for obj in results:
        # Convert the bounding box figures from relative coordinates
        # to absolute coordinates based on the original resolution
        ymin, xmin, ymax, xmax = obj['bounding_box']
        xmin = int(xmin * CAMERA_WIDTH)
        xmax = int(xmax * CAMERA_WIDTH)
        ymin = int(ymin * CAMERA_HEIGHT)
        ymax = int(ymax * CAMERA_HEIGHT)

        # Overlay the box, label, and score on the camera preview
        annotator.bounding_box([xmin, ymin, xmax, ymax])
        annotator.text([xmin, ymin],
                       '%s\n%.2f' % (labels[obj['class_id']], obj['score']))


def detect_simple_objects():
    labels = load_labels('./trained_model/object/coco_labels.txt')
    interpreter = Interpreter(
        './trained_model/object/detect.tflite'
    )
    interpreter.allocate_tensors()
    return interpreter.get_input_details()[0]['shape'], labels, interpreter


def detect_shovel():
    labels = load_labels('./trained_model/shovel_model/model-dict.txt')
    interpreter = Interpreter('./trained_model/shovel_model/model.tflite')
    interpreter.allocate_tensors()
    return interpreter.get_input_details()[0]['shape'], labels, interpreter


def print_objects(results, labels):
    # Print to command line
    result_str = ""
    for obj in results:
        ymin, xmin, ymax, xmax = obj['bounding_box']
        xmin = int(xmin * CAMERA_WIDTH)
        xmax = int(xmax * CAMERA_WIDTH)
        ymin = int(ymin * CAMERA_HEIGHT)
        ymax = int(ymax * CAMERA_HEIGHT)
        result_str += "X-min: " + str(xmin) + ", Y-min: " + str(ymin) + \
            ", X-max: " + str(xmax) + ", Y-max: " + str(ymax) + \
            ", Object: " + labels[obj['class_id']] + \
            ", Percent: " + str(obj['score']) + "\n"
    print(result_str)


def detect_shovel_size(results, labels):
    sizes = []
    for obj in results:
        ymin, xmin, ymax, xmax = obj['bounding_box']
        xmin = int(xmin * CAMERA_WIDTH)
        xmax = int(xmax * CAMERA_WIDTH)
        ymin = int(ymin * CAMERA_HEIGHT)
        ymax = int(ymax * CAMERA_HEIGHT)
        if labels[obj['class_id']] == 'shovel':
            obj = {}
            obj['height'] = xmax - xmin
            obj['width'] = ymax - ymin
            # 55mm width, 80mm height
            obj['pixel_metric'] = (obj['width'] / 55 + obj['height'] / 80) / 2
            print("Pixel metrics: " +
                  str(round(obj['pixel_metric'], 1)) + "\n")
            sizes.append(obj)
    return sizes


def detect_shovel_distance(results, labels):
    distances = []
    for obj in results:
        ymin, xmin, ymax, xmax = obj['bounding_box']
        xmin = int(xmin * CAMERA_WIDTH)
        xmax = int(xmax * CAMERA_WIDTH)
        ymin = int(ymin * CAMERA_HEIGHT)
        ymax = int(ymax * CAMERA_HEIGHT)
        if labels[obj['class_id']] == 'shovel':
            obj = {}
            obj['height'] = xmax - xmin
            obj['width'] = ymax - ymin
            # When pixel metric 2.1 distance will 155mm
            obj['focal_distance'] = (
                (obj['width'] * 155) / 55 + obj['height'] * 155 / 80) / 2
            print("Focal distance: " +
                  str(round(obj['focal_distance'], 1)) + "\n")
            distances.append(obj)
    return distances


def main():
    obj_shape, obj_labels, obj_interpreter = detect_simple_objects()
    shovel_shape, shovel_labels, shovel_interpreter = detect_shovel()

    with picamera.PiCamera(
            resolution=(CAMERA_WIDTH, CAMERA_HEIGHT), framerate=30) as camera:
        camera.start_preview()
        try:
            stream = io.BytesIO()
            annotator = Annotator(camera)
            for _ in camera.capture_continuous(
                    stream, format='jpeg', use_video_port=True):
                stream.seek(0)
                image = Image.open(stream).convert('RGB')
                start_time = time.monotonic()
                shovel_image = image.resize(
                    (shovel_shape[1], shovel_shape[2]), Image.ANTIALIAS)
                shovel_result = detect_objects(
                    shovel_interpreter, shovel_image, 0.4)
                obj_image = image.resize(
                    (obj_shape[1], obj_shape[2]), Image.ANTIALIAS)
                obj_result = detect_objects(obj_interpreter, obj_image, 0.4)
                elapsed_ms = (time.monotonic() - start_time) * 1000

                annotator.clear()
                # Detect size
                detect_shovel_size(shovel_result, shovel_labels)
                detect_shovel_distance(shovel_result, shovel_labels)
                # annotate_objects(annotator, shovel_result, shovel_labels)
                # annotate_objects(annotator, obj_result, obj_labels)
                # Annotate shovel
                print_objects(shovel_result, shovel_labels)
                # Annotate simple objects
                # print_objects(obj_result, obj_labels)
                annotator.text([5, 0], '%.1fms' % (elapsed_ms))
                annotator.update()

                stream.seek(0)
                stream.truncate()

        finally:
            camera.stop_preview()


if __name__ == '__main__':
    main()
