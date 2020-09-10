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


def detect_bucket():
    labels = load_labels('./trained_model/bucket/dict.txt')
    interpreter = Interpreter('./trained_model/bucket/model.tflite')
    interpreter.allocate_tensors()
    return interpreter.get_input_details()[0]['shape'], labels, interpreter


def print_objects(results, labels):
    # Print to command line
    result_str = ""
    for obj in results:
        ymin, xmin, ymax, xmax = obj['bounding_box']
        result_str += "X: " + str(xmin) + ", Y: " + str(ymin) + ", Object: " + \
            labels[obj['class_id']] + ", Percent: " + str(obj['score']) + "\n"
    print(result_str, end="\r")
    result_str = ""

def main():
    obj_shape, obj_labels, obj_interpreter = detect_simple_objects()
    bucket_shape, bucket_labels, bucket_interpreter = detect_bucket()

    with picamera.PiCamera(
        resolution=(CAMERA_WIDTH, CAMERA_HEIGHT), framerate=30) as camera:
        camera.start_preview()
        try:
            stream = io.BytesIO()
            annotator = Annotator(camera)
            for _ in camera.capture_continuous(
                stream, format='jpeg', use_video_port=True):
                stream.seek(0)
                # Annotate simple objects
                image = Image.open(stream).convert('RGB').resize(
                    (obj_shape[1], obj_shape[2]), Image.ANTIALIAS
                )
                start_time = time.monotonic()
                results = detect_objects(obj_interpreter, image, 0.4)
                elapsed_ms = (time.monotonic() - start_time) * 1000

                annotator.clear()
                annotate_objects(annotator, results, obj_labels)
                print_objects(results, obj_labels)
                annotator.text([5, 0], '%.1fms' % (elapsed_ms))
                annotator.update()
                # Annotate bucket
                image = Image.open(stream).convert('RGB').resize(
                    (bucket_shape[1], bucket_shape[2]), Image.ANTIALIAS)
                start_time = time.monotonic()
                results = detect_objects(bucket_interpreter, image, 0.4)
                elapsed_ms = (time.monotonic() - start_time) * 1000

                annotator.clear()
                annotate_objects(annotator, results, bucket_labels)
                print_objects(results, bucket_labels)
                annotator.text([5, 0], '%.1fms' % (elapsed_ms))
                annotator.update()

                stream.seek(0)
                stream.truncate()

        finally:
            camera.stop_preview()


if __name__ == '__main__':
    main()
