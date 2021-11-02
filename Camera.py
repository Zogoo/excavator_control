#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import io
import re
import time

from Annotation import Annotator

import numpy as np
import picamera

from PIL import Image
from time import sleep
from tflite_runtime.interpreter import Interpreter

class Camera:
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480

    def __init__(self, models, exportLog=True):
        """
        Load camera with fine resolution
        """
        self.interpreters = []
        self.camera = picamera.PiCamera()
        self.camera.resolution = (self.CAMERA_WIDTH, self.CAMERA_HEIGHT)
        self.camera.framerate = 30
        self.camera.start_preview()
        self.exportLog = exportLog
        # Camera warm-up time
        sleep(2)
        self.load_models(models)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.camera.stop_preview()
        except RuntimeWarning:
            return True

    def load_labels(self, path):
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

    def load_models(self, models):
        for model in models:
            interpreter = Interpreter(model['model_path'])
            interpreter.allocate_tensors()
            self.interpreters.append({
                'name': model['name'],
                'shape': interpreter.get_input_details()[0]['shape'],
                'labels': self.load_labels(model['label_path']),
                'interpreter': interpreter,
                'function': model['function']
            })
        return self.interpreters

    def set_input_tensor(self, interpreter, image):
        """Sets the input tensor."""
        tensor_index = interpreter.get_input_details()[0]['index']
        input_tensor = interpreter.tensor(tensor_index)()[0]
        input_tensor[:, :] = image

    def get_output_tensor(self, interpreter, index):
        """Returns the output tensor at the given index."""
        output_details = interpreter.get_output_details()[index]
        tensor = np.squeeze(interpreter.get_tensor(output_details['index']))
        return tensor

    def detect_objects(self, interpreter, image, threshold):
        """Returns a list of detection results, each a dictionary of object info."""
        self.set_input_tensor(interpreter, image)
        interpreter.invoke()

        # Get all output details
        boxes = self.get_output_tensor(interpreter, 0)
        classes = self.get_output_tensor(interpreter, 1)
        scores = self.get_output_tensor(interpreter, 2)
        count = int(self.get_output_tensor(interpreter, 3))

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

    def annotate_objects(self, annotator, results, labels):
        """Draws the bounding box and label for each object in the results."""
        for obj in results:
            # Convert the bounding box figures from relative coordinates
            # to absolute coordinates based on the original resolution
            ymin, xmin, ymax, xmax = obj['bounding_box']
            xmin = int(xmin * self.CAMERA_WIDTH)
            xmax = int(xmax * self.CAMERA_WIDTH)
            ymin = int(ymin * self.CAMERA_HEIGHT)
            ymax = int(ymax * self.CAMERA_HEIGHT)

            # Overlay the box, label, and score on the camera preview
            annotator.bounding_box([xmin, ymin, xmax, ymax])
            annotator.text([xmin, ymin],
                           '%s\n%.2f' % (labels[obj['class_id']], obj['score']))

    def detect_sizes(self, results, labels):
        sizes = []
        for obj in results:
            ymin, xmin, ymax, xmax = obj['bounding_box']
            xmin = int(xmin * self.CAMERA_WIDTH)
            xmax = int(xmax * self.CAMERA_WIDTH)
            ymin = int(ymin * self.CAMERA_HEIGHT)
            ymax = int(ymax * self.CAMERA_HEIGHT)
            size_obj = {}
            size_obj['name'] = labels[obj['class_id']]
            size_obj['height'] = xmax - xmin
            size_obj['width'] = ymax - ymin
            # 55mm width, 80mm height
            size_obj['pixel_metric'] = (
                size_obj['width'] / 55 + size_obj['height'] / 80) / 2
            if self.exportLog:
                print("Pixel metrics: " +
                    str(round(size_obj['pixel_metric'], 1)) + "\n")
            sizes.append(size_obj)
        return sizes

    def detect_distances(self, results, labels):
        distances = []
        for obj in results:
            ymin, xmin, ymax, xmax = obj['bounding_box']
            xmin = int(xmin * self.CAMERA_WIDTH)
            xmax = int(xmax * self.CAMERA_WIDTH)
            ymin = int(ymin * self.CAMERA_HEIGHT)
            ymax = int(ymax * self.CAMERA_HEIGHT)
            dist_obj = {}
            dist_obj['name'] = labels[obj['class_id']]
            dist_obj['height'] = xmax - xmin
            dist_obj['width'] = ymax - ymin
            # When pixel metric 2.1 distance will 155mm
            dist_obj['focal_distance'] = (
                (dist_obj['width'] * 155) / 55 + dist_obj['height'] * 155 / 80) / 2
            if self.exportLog:
                print("Focal distance: " +
                    str(round(dist_obj['focal_distance'], 1)) + "\n")
            distances.append(dist_obj)
        return distances

    def print_objects(self, results, labels):
        # Print to command line
        result_str = ""
        for obj in results:
            ymin, xmin, ymax, xmax = obj['bounding_box']
            xmin = int(xmin * self.CAMERA_WIDTH)
            xmax = int(xmax * self.CAMERA_WIDTH)
            ymin = int(ymin * self.CAMERA_HEIGHT)
            ymax = int(ymax * self.CAMERA_HEIGHT)
            result_str += "X-min: " + str(xmin) + ", Y-min: " + str(ymin) + \
                ", X-max: " + str(xmax) + ", Y-max: " + str(ymax) + \
                ", Object: " + labels[obj['class_id']] + \
                ", Percent: " + str(obj['score']) + "\n"
        print(result_str)

    def execute_command(self):
        with self.camera:
            try:
                stream = io.BytesIO()
                annotator = Annotator(self.camera)
                for _ in self.camera.capture_continuous(
                        stream, format='jpeg', use_video_port=True):
                    stream.seek(0)
                    image = Image.open(stream).convert('RGB')
                    start_time = time.monotonic()

                    for interpreter in self.interpreters:
                        image = image.resize(
                            (interpreter['shape'][1], interpreter['shape'][2]), Image.ANTIALIAS)
                        results = self.detect_objects(
                            interpreter['interpreter'], image, 0.5)
                        # Annotate objects in terminal
                        if self.exportLog:
                            self.print_objects(results, interpreter['labels'])
                        # Annotate object in view
                        # self.annotate_objects(annotator, result, interpreter['labels'])
                        # Detect size and distance
                        # TODO: improve with physical object with 1cm length
                        sizes = self.detect_sizes(results, interpreter['labels'])
                        distances = self.detect_distances(results, interpreter['labels'])
                        if bool(interpreter.get('function')):
                            interpreter['function'](
                                results, interpreter['labels'], sizes, distances, interpreter['name'])

                    elapsed_ms = (time.monotonic() - start_time) * 1000

                    annotator.clear()
                    annotator.text([5, 0], '%.1fms' % (elapsed_ms))
                    annotator.update()

                    stream.seek(0)
                    stream.truncate()

            finally:
                self.camera.stop_preview()
