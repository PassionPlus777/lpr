import cv2
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

class VideoCaptureWidget(QLabel):
    
    clicked = pyqtSignal()  # Signal to be emitted when the widget is clicked
        
    def __init__(self, rtsp_url, width, height, parent=None):
        super().__init__(parent)
        self.rtsp_url = rtsp_url
        self.width = width
        self.height = height
        self.capture = cv2.VideoCapture(self.rtsp_url)
        # self.capture = cv2.VideoCapture("E:/Practice/Python/Lpr System/4.mp4")

        # Set up a QTimer to periodically capture frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30 milliseconds

    def update_frame(self):
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (self.width, self.height))
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.setPixmap(QPixmap.fromImage(q_image))

    def close(self):
        self.capture.release()
        self.timer.stop()

    def closeEvent(self, event):
        self.close()
        event.accept()
        
    # def mousePressEvent(self, event):
    #     self.clicked.emit()  # Emit the clicked signal when the widget is clicked
    #     super().mousePressEvent(event)
