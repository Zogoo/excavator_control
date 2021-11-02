#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from Camera import Camera

def main():
    tl_models = [
        {
            'name': 'shovel',
            'model_path': './trained_model/shovel_model/model.tflite',
            'label_path': './trained_model/shovel_model/model-dict.txt',
            'function': None
        },
        {
            'name': 'person',
            'model_path': './trained_model/object/detect.tflite',
            'label_path': './trained_model/object/coco_labels.txt',
            'function': None
        }
    ]

    camera = Camera(tl_models)
    camera.execute_command()


if __name__ == '__main__':
    main()
