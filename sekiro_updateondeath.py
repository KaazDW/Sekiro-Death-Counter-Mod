#Sekiro

import cv2
import numpy as np
import os
import winsound
import ctypes
from PIL import ImageGrab, Image
from time import sleep, time

# Add PyQt5 for overlay display
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import sys
import threading

# plays a sound, set to false to disable
PLAYSOUND = True

def get_screen_scaling():
    """Get the screen scaling factors based on a 1920x1080 reference resolution."""
    user32 = ctypes.windll.user32
    h = int(user32.GetSystemMetrics(0) / 1920)
    w = int(user32.GetSystemMetrics(1) / 1080)
    return h, w

def get_crop_box(h, w):
    """Return the crop box coordinates for the region of interest, scaled to the screen."""
    return (795 * w, 310 * h, 1130 * w, 700 * h)

def prepare_reference_mask(crop_box, h, w):
    """Prepare and return the reference mask and color bounds from the reference image."""
    try:
        original = Image.open("SekiroDeath.png")
        original.thumbnail((h * 1920, w * 1080))
        original = np.asarray(original.crop(crop_box).convert("RGB"))
        oR, oG, oB = cv2.split(original)
        original = cv2.merge((oR, oG, oB))
        low = np.array([147, 34, 34], dtype="uint16")
        up = np.array([182, 42, 42], dtype="uint16")
        orMask = cv2.inRange(original, low, up)
        return orMask, low, up
    except Exception as e:
        print(f"Erreur lors de la préparation du masque de référence: {e}")
        raise

def read_death_count(filename="deaths.txt"):
    """Read and return the death count from the file, or initialize it if missing."""
    try:
        with open(filename, "r") as f:
            return int(f.read())
    except FileNotFoundError:
        with open(filename, "w") as f:
            f.write("0")
        return 0
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier: {e}")
        return 0

def write_death_count(count, filename="deaths.txt"):
    """Write the updated death count to the file."""
    try:
        with open(filename, "w") as f:
            f.write(str(count))
    except Exception as e:
        print(f"Erreur lors de l'écriture du fichier: {e}")

def capture_screen(crop_box):
    """Capture and return the cropped screen region as a NumPy array, or None on error."""
    try:
        img = np.asarray(ImageGrab.grab(crop_box))
        r, g, b = cv2.split(img)
        img = cv2.merge((r, g, b))
        return img
    except Exception as e:
        print(f"Erreur lors de la capture d'écran: {e}")
        return None

# Overlay w/PyQt5
class DeathCounterOverlay(QWidget):
    def __init__(self, filename="deaths.txt"):
        super().__init__()
        self.filename = filename
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.label = QLabel(self)
        self.label.setFont(QFont("Arial", 16, QFont.Bold))
        self.label.setStyleSheet("color: white; background: rgba(0,0,0,128); padding: 10px; border-radius: 10px;")
        self.update_count()
        self.resize(self.label.sizeHint())
        self.move_to_bottom_right()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_count)
        self.timer.start(500)

    def update_count(self):
        try:
            with open(self.filename, "r") as f:
                count = int(f.read())
        except Exception:
            count = 0
        self.label.setText(f"{count}")
        self.resize(self.label.sizeHint())
        self.move_to_bottom_right()

    def move_to_bottom_right(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 30
        y = screen.height() - self.height() - 30
        self.move(x, y)

def start_overlay():
    app = QApplication(sys.argv)
    overlay = DeathCounterOverlay()
    overlay.show()
    app.exec_()

def main():
    """Main loop: prepares reference, counts deaths, and updates the file and sound."""
    # Exe PyQt5 overlay in a separated thread
    overlay_thread = threading.Thread(target=start_overlay, daemon=True)
    overlay_thread.start()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    h, w = get_screen_scaling()
    crop_box = get_crop_box(h, w)
    try:
        orMask, low, up = prepare_reference_mask(crop_box, h, w)
    except Exception:
        print("Impossible de préparer le masque de référence. Arrêt du programme.")
        return
    dTime = time()
    totDeaths = read_death_count()

    while True:
        curImage = capture_screen(crop_box)
        if curImage is None:
            sleep(0.05)
            continue

        try:
            redMask = cv2.inRange(curImage, low, up)
            difference = cv2.subtract(orMask, redMask)
            difference2 = cv2.subtract(redMask, orMask)

            if (
                cv2.countNonZero(difference) <= 10000
                and cv2.countNonZero(difference2) <= 10000
                and time() - dTime > 1
            ):
                dTime = time()
                totDeaths += 1
                write_death_count(totDeaths)
                if PLAYSOUND:
                    winsound.PlaySound("yes.wav", winsound.SND_ASYNC)
        except Exception as e:
            print(f"Erreur lors du traitement d'image: {e}")

        sleep(0.5)

if __name__ == "__main__":
    main()