import os
import cv2
import sys
import requests
from dotenv import load_dotenv
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from mainwindow import Ui_MainWindow  # Import the generated UI class
from camerawindow import VideoCaptureWidget
from lprsystem import LPRSystem

load_dotenv()

backend_url = os.getenv('API_BACKEND_URL')

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.lpr_systems = []
        
        self.m_lot_id = ""
        # self.v_lot_id = ""
        self.display_data()
        
        self.ui.m_refreshButton.clicked.connect(self.display_data)
        self.ui.lotTable.cellClicked.connect(self.on_lot_row_click)
        self.ui.cameraAdd.clicked.connect(self.create_camera)
        self.ui.lotList.itemClicked.connect(self.v_display_camera_data)
        self.ui.closeButton.clicked.connect(self.close_application)

        # Load and apply stylesheet
        self.load_stylesheet("./dark_cyan.qss")
        
    def update_frame(self):
        # Capture frame-by-frame
        ret, frame = self.capture.read()
        if ret:
            # Convert frame to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

            # Update QLabel with new image
            pixmap = QPixmap.fromImage(q_image)
            self.video_label.setPixmap(pixmap)
                   
    def close_application(self):
        self.close()

    def load_stylesheet(self, style_path):
        with open(style_path, "r") as file:
            self.setStyleSheet(file.read())
    
    def on_lot_click_outside_cell(self):
        self.m_lot_id = ""
        self.ui.cameraAdd.setEnabled(False)

    def on_lot_row_click(self, row, column):
        item = self.ui.lotTable.item(row, 0)
        self.m_lot_id = item.data(QtCore.Qt.UserRole)
        self.ui.cameraAdd.setEnabled(True)
        self.m_display_camera_data()
        print(f"Cell content: {item.text()}  {self.m_lot_id}")
        
    def fetch_lot_data(self):
        response = requests.get(f"{backend_url}/lot", verify=False)
        response.raise_for_status()
        if response.status_code == 200:
            # This line converts the response content to JSON
            return response.json()
        else:
            return []
            print("Failed to fetch data:", response.status_code)

    def m_display_lot_data(self):
        lots = self.fetch_lot_data()
        # Set the number of rows and columns
        self.ui.lotTable.setRowCount(len(lots))
        for row in range(len(lots)):
            item = QtWidgets.QTableWidgetItem(str(lots[row]["siteCode"]))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            item.setData(QtCore.Qt.UserRole, lots[row]["_id"])
            self.ui.lotTable.setItem(row, 0, item)
            
            item = QtWidgets.QTableWidgetItem(str(len(lots[row]["cameras"])))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.ui.lotTable.setItem(row, 1, item)

    def v_display_lot_data(self):
        lots = self.fetch_lot_data()
        self.ui.lotList.clear()
        for lot in lots:
            item = QtWidgets.QListWidgetItem(str(lot["siteCode"]))
            item.setData(QtCore.Qt.UserRole, lot["_id"])
            self.ui.lotList.addItem(item)
    
    def fetch_camera_data(self, lot_id):
        response = requests.put(f"{backend_url}/camera/{lot_id}", verify=False)
        if response.status_code == 200:
            # This line converts the response content to JSON
            return response.json()
        else:
            return []
            self.ui.cameraTable.setRowCount(0)
            self.ui.cameraTable.clearContents()
            print("Failed to fetch data:", response.status_code)
      
    def m_display_camera_data(self):
        cameras = self.fetch_camera_data(self.m_lot_id)
        # Set the number of rows and columns
        self.ui.cameraTable.setRowCount(len(cameras))
        
        for row in range(len(cameras)):
            item = QtWidgets.QTableWidgetItem(str(cameras[row]["type"]))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            item.setData(QtCore.Qt.UserRole, cameras[row]["_id"])  # Store the unique key in the item data
            self.ui.cameraTable.setItem(row, 0, item)
            
            item = QtWidgets.QTableWidgetItem(str(cameras[row]["url"]))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.ui.cameraTable.setItem(row, 1, item)
            
            # item = QtWidgets.QTableWidgetItem(str(json_data[row]["status"]))
            # item.setTextAlignment(QtCore.Qt.AlignCenter)
            # self.ui.cameraTable.setItem(row, 2, item)
            
            if(cameras[row]["status"]):
                button = QtWidgets.QPushButton("Stop")
            else:
                button = QtWidgets.QPushButton("Resume")
            
            button.clicked.connect(lambda _, r=row: self.camera_status(cameras[r]))
            self.ui.cameraTable.setCellWidget(row, 3, button)
            
            button = QtWidgets.QPushButton("Delete")
            button.clicked.connect(lambda _, r=row: self.camera_delete(r))
            self.ui.cameraTable.setCellWidget(row, 4, button)
       
    def v_display_camera_data(self, item):
        v_lot_id = item.data(QtCore.Qt.UserRole)
        
        cameras = self.fetch_camera_data(v_lot_id)
        # Clear all widgets from the layout
        for i in reversed(range(self.ui.horizontalLayout_3.count())):
            widget = self.ui.horizontalLayout_3.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()  # This ensures the widget is properly cleaned up
            
        for camera in cameras:
            if camera['status']:
                height = int(self.ui.video_list.height())
                width = int(self.ui.video_list.height() - 30)
                video_widget = VideoCaptureWidget(camera["url"], height, width,self.ui.video_list)
                video_widget.setStyleSheet("border: none;")
                video_widget.clicked.connect(self.handle_video_click)
                self.ui.horizontalLayout_3.addWidget(video_widget)
            
    def handle_video_click(self):
        sender = self.sender()  # Get the widget that sent the signal
        # video_widget = VideoCaptureWidget(sender.rtsp_url, 600, 400,self.ui.main_video)
        # video_widget.setStyleSheet("border: 1px solid cyan;")
        
        # # Clear all widgets from the layout
        # for i in reversed(range(self.ui.main_video.count())):
        #     widget = self.ui.main_video.itemAt(i).widget()
        #     if widget is not None:
        #         widget.deleteLater()  # This ensures the widget is properly cleaned up
        
        # self.ui.main_video.addWidget(video_widget)
        
    def create_camera(self):
        cameraType = self.ui.cameraType.currentText()
        cameraUrl = self.ui.cameraUrl.text()
        errorStyleSheet = "border-color: red;color: #4dd0e1;"
            
        if not cameraUrl:
            self.ui.cameraUrl.setStyleSheet(errorStyleSheet)
            return
        else:
            self.ui.cameraUrl.setStyleSheet("color: #4dd0e1")

        response = requests.post(f"{backend_url}/camera", {"lot": self.m_lot_id, "type":cameraType, "url":cameraUrl}, verify=False)
        if response.status_code == 201:
            self.ui.cameraType.setCurrentIndex(0)
            self.ui.cameraUrl.setText("")
            self.display_data()
            self.lpr_system()
        else:
            print("Failed to create data:", response.status_code)
    
    def camera_delete(self, row):
        camera_id = self.ui.cameraTable.item(row, 0).data(QtCore.Qt.UserRole)  # Retrieve the unique key from the item data
        response = requests.delete(f"{backend_url}/camera/{self.m_lot_id}/{camera_id}", verify=False)
        if response.status_code == 200:
            self.display_data()
            self.lpr_system()
        else:
            print("Failed to delete data:", response.status_code)
    
    def camera_status(self, row):
        response = requests.put(f"{backend_url}/camera/{self.m_lot_id}/{row['_id']}/{row["status"]}", verify=False)
        if response.status_code == 200:
            self.display_data()
            self.lpr_system()
        else:
            print("Failed to delete data:", response.status_code)

    def display_data(self):
        self.m_display_lot_data()
        self.v_display_lot_data()
        self.m_display_camera_data()
    
    def closeEvent(self, event):
        for i in reversed(range(self.ui.horizontalLayout_3.count())):
            widget = self.ui.horizontalLayout_3.itemAt(i).widget()
            if widget is not None:
                widget.close()
        event.accept()
    
    def lpr_system(self):
        lots = self.fetch_lot_data()

        for lot in lots:
            for camera in lot["cameras"]:
                if camera['status']:
                    lpr_system = LPRSystem(camera)
                    self.lpr_systems.append(lpr_system)  # Store the instance

          
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showFullScreen()
    main_window.lpr_system()
    sys.exit(app.exec_())
