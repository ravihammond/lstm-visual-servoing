#!/usr/bin/env python3
import argparse
import sys
import os

from pytorch import VisualServo
import torch
torch.cuda.set_device(0)

# Check validity of model directory
def check_model_directory(model_dir):
    print("checking model dir: ", model_dir)
    # Ensures training data directory exists
    if not os.path.exists(model_dir):
        sys.exit("Error: model directory %s does not exist")

    model_path = os.path.join(model_dir, "best_model.pt")
    print("model path: ", model_path)

    # Ensures training data directory exists
    if not os.path.exists(model_path):
        sys.exit("Error: model directory %s does not contail model.py file")

    return model_path

# Main function
if __name__ == "__main__" :
    # Argument parser gets the model directory
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--model", dest="model", help="name of directory to load model from")
    args = parser.parse_known_args()[0]

    home_path = r"/root/catkin_ws/models/"
    training_dir = os.path.join(home_path, args.model)
    model_path = check_model_directory(training_dir)

    visual_servo = VisualServo(model_path)
    visual_servo.run()

