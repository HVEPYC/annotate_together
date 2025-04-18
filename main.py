# A simple app created to annotate images
# Made quick and hackily by HVEPYC

# Imports
import dearpygui.dearpygui as dpg
import os
import json

# Declarations:
JSON_PATH = "annotations.json"
DEFAULT_IMG_PATH = "/images"

# Sample annotations json:
# annotations_json = [
#     {
#         "image_id":"something",
#         "image_path":"path/to/image",
#         "task_type":"caption" | "vqa" | "instruction",
#         "text_ms":"question_in_malay",
#         "answer_ms":"answer_in_malay",
#         "text_en":"text_in_eng",
#         "answer_en":"answer_in_eng",
#         "language" : {
#             "source":["ms","en"],
#             "target":["ms","en"],
#         },
#         "source":"source_of_images",
#         "split":"train" | "val" | "test",
#         "difficulty":"easy"|"medium"|"hard",
#         "tags":["list","of","tags","relevant","to","image"],
#         "metadata":{
#             "license":"CC-BY",
#             "annotator_id":"string",
#             "language_quality_score":4.5,
#             "timestamp":"YYYY-MM-DDTHH:MM:SSZ"
#         }
#     }
# ]

# Reading the json file if any:
if os.path.exists(JSON_PATH):
    with open(JSON_PATH) as file:
        annotations_json = json.load(file)
else:
    annotations_json:list[dict] = []

# Starting a dearpygui instance where one can choose the folder to obtain images from


# Make a json file with all of the structure
# Then read from it and check filenames first, then go ahead with annotating
# Ask the required questions in GUI and then go ahead