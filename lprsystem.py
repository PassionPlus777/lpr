import os
import sys
import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from PyQt5.QtCore import QTimer, QDateTime

load_dotenv()

backend_url = os.getenv('API_BACKEND_URL')

class LPRSystem:
    def __init__(self, camera):
        self.camera = camera
        self.cap = cv2.VideoCapture(self.camera['url'])
        # self.cap = cv2.VideoCapture("E:/Practice/Python/Lpr System/4.mp4")
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.confidence = 0
        self.plate_image = None
        self.plate_text = None
        self.full_frame = None
        self.last_detection_time = None
        self.detection_threshold = 0.1  # Time in seconds after which a car is considered passed

        # Determine the path to the models directory
        self.model_dir = self.get_model_dir()
        
        # Define model paths
        detection_weights_path = os.path.join(self.model_dir, 'detection.weights')
        detection_cfg_path = os.path.join(self.model_dir, 'detection.cfg')
        detection_names_path = os.path.join(self.model_dir, 'detection.names')
        recognition_weights_path = os.path.join(self.model_dir, 'recognition.weights')
        recognition_cfg_path = os.path.join(self.model_dir, 'recognition.cfg')
        recognition_names_path = os.path.join(self.model_dir, 'recognition.names')
        
        # Load object detection model
        self.net = cv2.dnn.readNet(detection_weights_path, detection_cfg_path)
        with open(detection_names_path, "r") as f:
            self.classes = [line.strip() for line in f.readlines()]

        # Load text recognition model
        self.recognition_net = cv2.dnn.readNet(recognition_weights_path, recognition_cfg_path)
        with open(recognition_names_path, "r") as f:
            self.characters = [line.strip() for line in f.readlines()]

        self.timer.start(30)  # Start the timer with an interval of 30 ms
        print("LPRSystem initialized and timer started")

    def get_model_dir(self):
        if getattr(sys, 'frozen', False):
            # If running in a bundled executable
            return os.path.join(sys._MEIPASS, 'models')
        else:
            # If running in a normal Python environment
            return os.path.join(os.path.dirname(__file__), 'models')

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = self.detect_objects(frame)
        else:
            self.timer.stop()
            self.cap.release()
            self.check_and_send_data()

    def detect_objects(self, frame):
        height, width, channels = frame.shape
        # Prepare the image for the network
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (224, 224), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.get_output_layers(self.net))

        # Process the detections
        class_ids = []
        confidences = []
        boxes = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.7:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # Apply non-max suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.7, 0.4)
        if len(indices) > 0:
            self.last_detection_time = QDateTime.currentDateTime()  # Update the last detection time
            indices = indices.flatten()
            for i in indices:
                box = boxes[i]
                x, y, w, h = box[0], box[1], box[2], box[3]
                label = str(self.classes[class_ids[i]])
                cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)

                # Extract the license plate region and perform text recognition
                plate_image = frame[int(y):int(y + h), int(x):int(x + w)]
                plate_text = self.recognize_text(plate_image)
                if confidences[i] > self.confidence:
                    self.confidence = confidences[i]
                    self.full_frame = frame.copy()
                    self.plate_image = plate_image
                    self.plate_text = plate_text
        else:
            self.check_and_send_data()

        return frame

    def recognize_text(self, plate_image):
        height, width = plate_image.shape[:2]
        
        # Prepare the image for the recognition network
        blob = cv2.dnn.blobFromImage(plate_image, scalefactor=1/255.0, size=(240, 120), swapRB=True, crop=False)
        self.recognition_net.setInput(blob)
        outs = self.recognition_net.forward(self.get_output_layers(self.recognition_net))

        # Decode the predicted text
        plate_text = self.decode_text(outs, width, height)
        return plate_text

    def decode_text(self, outputs, width, height):
        # Process the outputs
        boxes = []
        confidences = []
        class_ids = []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.7:  # confidence threshold
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h, class_id])
                    confidences.append(float(confidence))

        # Apply non-maxima suppression to remove redundant boxes
        indices = cv2.dnn.NMSBoxes([box[:4] for box in boxes], confidences, score_threshold=0.6, nms_threshold=0.4)
        if len(indices) > 0:
            indices = indices.flatten()
            detected_boxes = [boxes[i] for i in indices]
            detected_boxes.sort(key=lambda b: b[0])  # Sort by x-coordinate
            detected_labels = [self.characters[box[4]] for box in detected_boxes]
            return ''.join(detected_labels)

    def get_output_layers(self, net):
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
        return output_layers

    def check_and_send_data(self):
        if self.last_detection_time and self.last_detection_time.secsTo(QDateTime.currentDateTime()) > self.detection_threshold:
            if self.plate_image is not None and self.plate_text is not None:
                self.send_data_to_backend(self.full_frame, self.plate_image, self.plate_text)
                self.plate_image = None
                self.plate_text = None
                self.confidence = 0
                self.last_detection_time = None

    def send_data_to_backend(self, full_frame, plate_image, plate_text):
        _, buffer_full_frame = cv2.imencode('.jpg', full_frame)
        full_frame_encoded = buffer_full_frame.tobytes()
        
        _, buffer_plate_image = cv2.imencode('.jpg', plate_image)
        plate_image_encoded = buffer_plate_image.tobytes()
        
        files = {
            'vehicle': ('full_frame.jpg', full_frame_encoded, 'image/jpeg'),
            'plate': ('plate_image.jpg', plate_image_encoded, 'image/jpeg')
        }
        data = {'lot' : self.camera['_id'], 'plateNumber': plate_text, 'camera' : self.camera['url'], 'direction' :self.camera['type'] }
        response = requests.post(f"{backend_url}/data", files=files, data=data, verify=False)
        print("Response from server:", response.text)

