"""DermaScan Desktop UI (PySide6): Learn feed + Scan tab. Fully offline."""
from __future__ import annotations

import numpy as np
from PIL import Image
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QTabWidget, QVBoxLayout, QWidget,
)

from classifier import Classifier
from feed import CLASS_ORDER, HIGH_CONCERN, display_names, load_feed
from paths import resolve

CONFIDENCE_THRESHOLD = 0.50
IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

GLOBAL_DISCLAIMER = (
    "Educational information only. DermaScan does not diagnose, treat, or replace "
    "professional medical advice. Only a qualified dermatologist can diagnose a skin condition."
)
LIMITATIONS = (
    "Limitations: results can be less reliable on darker skin tones, in poor or uneven lighting, "
    "with blurry photos, or for lesion types outside these 7 classes. Use a sharp, well-lit, "
    "close-up photo."
)

STYLE = """
QMainWindow, QWidget { background: #f5f7fa; font-size: 13px; color: #1f2933; }
QTabBar::tab { padding: 8px 22px; font-size: 14px; }
QFrame#card { background: white; border: 1px solid #d9e0e8; border-radius: 10px; }
QLabel#title { font-size: 18px; font-weight: bold; }
QLabel#badge { background: #e8eef5; border-radius: 6px; padding: 2px 8px; font-weight: bold; }
QLabel#badgeHigh { background: #fde2e0; color: #a12622; border-radius: 6px; padding: 2px 8px; font-weight: bold; }
QLabel#disclaimer { color: #6b7785; font-style: italic; font-size: 11px; }
QPushButton { background: #2e86c1; color: white; border: none; border-radius: 6px; padding: 8px 16px; }
QPushButton:hover { background: #2874a6; }
QPushButton:disabled { background: #aab7c4; }
QProgressBar { border: 1px solid #c9d3de; border-radius: 4px; text-align: center; height: 18px; background: white; }
"""


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    arr = np.ascontiguousarray(np.asarray(img.convert("RGB")))
    h, w, _ = arr.shape
    qimg = QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)


# ---------------------------------------------------------------- Feed tab
class PostCard(QFrame):
    def __init__(self, post: dict, global_disclaimer: str):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel(post.get("class_name", post["class_code"]))
        title.setObjectName("title")
        head.addWidget(title)
        badge = QLabel(post["class_code"].upper())
        badge.setObjectName("badge")
        head.addWidget(badge)
        if post.get("high_concern"):
            hb = QLabel("HIGH CONCERN")
            hb.setObjectName("badgeHigh")
            head.addWidget(hb)
        head.addStretch(1)
        lay.addLayout(head)

        pixmaps = []
        for im in post.get("images", []):
            p = resolve(im["path"])
            if p.exists():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    pixmaps.append((pm, im.get("alt", "")))
        if pixmaps:
            strip = QWidget()
            sl = QHBoxLayout(strip)
            sl.setContentsMargins(0, 0, 0, 0)
            for pm, alt in pixmaps:
                lab = QLabel()
                lab.setPixmap(pm.scaledToHeight(170, Qt.SmoothTransformation))
                lab.setToolTip(alt)
                sl.addWidget(lab)
            sl.addStretch(1)
            sc = QScrollArea()
            sc.setWidget(strip)
            sc.setWidgetResizable(True)
            sc.setFixedHeight(200)
            sc.setFrameShape(QFrame.NoFrame)
            lay.addWidget(sc)

        brief = QLabel(post.get("brief", ""))
        brief.setWordWrap(True)
        lay.addWidget(brief)

        tips = post.get("tips", [])
        if tips:
            t = QLabel("<b>Tips</b><br>" + "<br>".join("• " + x for x in tips))
            t.setWordWrap(True)
            lay.addWidget(t)

        paper = post.get("paper") or {}
        if paper.get("title"):
            src = f"<b>Source:</b> {paper['title']}"
            if paper.get("citation"):
                src += f"<br>{paper['citation']}"
            s = QLabel(src)
            s.setWordWrap(True)
            lay.addWidget(s)

        d = QLabel(post.get("disclaimer") or global_disclaimer)
        d.setObjectName("disclaimer")
        d.setWordWrap(True)
        lay.addWidget(d)


class FeedTab(QWidget):
    def __init__(self, feed: dict):
        super().__init__()
        self.feed = feed
        self.posts = feed.get("posts", [])
        self.names = display_names(feed)
        self.global_disclaimer = feed.get("global_disclaimer", GLOBAL_DISCLAIMER)

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Show:"))
        self.combo = QComboBox()
        self.combo.addItem("All conditions", None)
        for code in CLASS_ORDER:
            self.combo.addItem(f"{self.names[code]} ({code})", code)
        self.combo.currentIndexChanged.connect(self.rebuild)
        bar.addWidget(self.combo)
        bar.addStretch(1)
        root.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(self.scroll)
        self.rebuild()

    def rebuild(self):
        code = self.combo.currentData()
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setSpacing(12)
        posts = [p for p in self.posts if code is None or p["class_code"] == code]
        posts.sort(key=lambda p: (CLASS_ORDER.index(p["class_code"]) if p["class_code"] in CLASS_ORDER else 99))
        for p in posts:
            lay.addWidget(PostCard(p, self.global_disclaimer))
        if not posts:
            lay.addWidget(QLabel("No posts for this condition yet."))
        lay.addStretch(1)
        self.scroll.setWidget(holder)

    def select_class(self, code: str):
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == code:
                self.combo.setCurrentIndex(i)
                return


# ---------------------------------------------------------------- Scan tab
class DropLabel(QLabel):
    file_dropped = Signal(str)
    PLACEHOLDER = "Drag & drop a skin photo here\nor click Upload Image"

    def __init__(self):
        super().__init__(self.PLACEHOLDER)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumSize(360, 300)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setStyleSheet("border: 2px dashed #9fb3c8; border-radius: 10px; background: white; color: #6b7785;")
        self._pix = None

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            path = u.toLocalFile()
            if path.lower().endswith(IMG_EXT):
                self.file_dropped.emit(path)
                break

    def show_pixmap(self, pm: QPixmap):
        self._pix = pm
        self._rescale()

    def reset(self):
        self._pix = None
        self.clear()
        self.setText(self.PLACEHOLDER)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rescale()

    def _rescale(self):
        if self._pix is not None:
            self.setPixmap(self._pix.scaled(self.size() - QSize(8, 8), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class ScanTab(QWidget):
    learn_more = Signal(str)

    def __init__(self, names: dict):
        super().__init__()
        self.names = names
        self.cap = None
        self.last_frame = None
        self.current_code = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        self.classifier = None
        self.classifier_error = None
        try:
            self.classifier = Classifier()
        except Exception as e:  # missing model etc. - feed still works
            self.classifier_error = str(e)

        root = QHBoxLayout(self)

        # left: image + buttons
        left = QVBoxLayout()
        self.drop = DropLabel()
        self.drop.file_dropped.connect(self.load_file)
        left.addWidget(self.drop, 1)
        row = QHBoxLayout()
        self.btn_upload = QPushButton("Upload Image")
        self.btn_upload.clicked.connect(self.pick_file)
        self.btn_cam = QPushButton("Start Webcam")
        self.btn_cam.clicked.connect(self.toggle_cam)
        self.btn_cap = QPushButton("Capture && Analyze")
        self.btn_cap.setEnabled(False)
        self.btn_cap.clicked.connect(self.capture)
        for b in (self.btn_upload, self.btn_cam, self.btn_cap):
            row.addWidget(b)
        left.addLayout(row)
        root.addLayout(left, 3)

        # right: results
        right = QVBoxLayout()
        self.headline = QLabel("Result will appear here")
        self.headline.setObjectName("title")
        self.headline.setWordWrap(True)
        right.addWidget(self.headline)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        right.addWidget(self.note)

        self.rows = []
        for _ in CLASS_ORDER:
            h = QHBoxLayout()
            lab = QLabel("")
            lab.setFixedWidth(210)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(0)
            bar.setFormat("")
            h.addWidget(lab)
            h.addWidget(bar)
            right.addLayout(h)
            self.rows.append((lab, bar))

        self.btn_more = QPushButton("Learn more about this condition")
        self.btn_more.setVisible(False)
        self.btn_more.clicked.connect(lambda: self.current_code and self.learn_more.emit(self.current_code))
        right.addWidget(self.btn_more)

        guide = QLabel("<b>Consult a Dermatologist.</b> This screening result is not a diagnosis. "
                       "Any spot that is new, changing, bleeding, or worrying you should be examined by a professional.")
        guide.setWordWrap(True)
        right.addWidget(guide)
        lim = QLabel(LIMITATIONS)
        lim.setWordWrap(True)
        right.addWidget(lim)
        d = QLabel(GLOBAL_DISCLAIMER)
        d.setObjectName("disclaimer")
        d.setWordWrap(True)
        right.addWidget(d)
        if self.classifier_error:
            err = QLabel("Scanner unavailable: " + self.classifier_error)
            err.setStyleSheet("color: #a12622;")
            err.setWordWrap(True)
            right.addWidget(err)
        right.addStretch(1)
        root.addLayout(right, 2)

    # --- input
    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a skin photo", "", "Images (*.jpg *.jpeg *.png *.bmp *.webp)")
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        self.stop_cam()
        try:
            img = Image.open(path).convert("RGB")
        except Exception as e:
            QMessageBox.warning(self, "DermaScan", f"Could not open image:\n{e}")
            return
        self.drop.show_pixmap(pil_to_pixmap(img))
        self.analyze(img)

    # --- webcam
    def toggle_cam(self):
        if self.cap is not None:
            self.stop_cam()
            return
        try:
            import cv2
        except ImportError:
            QMessageBox.warning(self, "DermaScan", "OpenCV is not installed.")
            return
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            QMessageBox.warning(self, "DermaScan", "No webcam found or it is in use by another app.")
            return
        self.cap = cap
        self.btn_cam.setText("Stop Webcam")
        self.btn_cap.setEnabled(True)
        self.timer.start(33)

    def stop_cam(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.btn_cam.setText("Start Webcam")
        self.btn_cap.setEnabled(False)

    def _tick(self):
        import cv2
        ok, frame = self.cap.read()
        if ok:
            self.last_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(self.last_frame)
            self.drop.show_pixmap(pil_to_pixmap(img))

    def capture(self):
        if self.last_frame is None:
            return
        img = Image.fromarray(self.last_frame)
        self.stop_cam()
        self.drop.show_pixmap(pil_to_pixmap(img))
        self.analyze(img)

    # --- inference + results
    def analyze(self, img: Image.Image):
        if self.classifier is None:
            QMessageBox.warning(self, "DermaScan", "Scanner unavailable:\n" + (self.classifier_error or ""))
            return
        probs = self.classifier.predict(img)
        self.show_results(probs)

    def show_results(self, probs: dict):
        order = sorted(probs.items(), key=lambda kv: -kv[1])
        top, p = order[0]
        inconclusive = p < CONFIDENCE_THRESHOLD

        if inconclusive:
            self.headline.setText("Inconclusive")
            self.note.setText("The model is not confident enough to suggest a class. Try a sharper, "
                              "better-lit close-up, and see a dermatologist if you are concerned.")
            self.current_code = None
            self.btn_more.setVisible(False)
        else:
            self.headline.setText(f"{self.names.get(top, top)} — {p * 100:.1f}%")
            if top in HIGH_CONCERN:
                self.note.setText("⚠ High-concern class. Please book a dermatologist appointment soon.")
            else:
                self.note.setText("This class is usually lower concern, but only a dermatologist can confirm. "
                                  "See one if the spot changes or worries you.")
            self.current_code = top
            self.btn_more.setVisible(True)

        mel = probs.get("mel", 0.0)
        if not inconclusive and top != "mel" and mel >= 0.25:
            self.note.setText(self.note.text() + f"\nMelanoma probability is elevated ({mel * 100:.1f}%).")

        for (lab, bar), (code, pr) in zip(self.rows, order):
            lab.setText(f"{self.names.get(code, code)} ({code})")
            bar.setValue(int(pr * 1000))
            bar.setFormat(f"{pr * 100:.1f}%")
            color = "#c0392b" if code in HIGH_CONCERN else "#2e86c1"
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}")


# ---------------------------------------------------------------- Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DermaScan Desktop")
        self.resize(1100, 720)
        self.setStyleSheet(STYLE)
        feed = load_feed()
        self.tabs = QTabWidget()
        self.feed_tab = FeedTab(feed)
        self.scan_tab = ScanTab(display_names(feed))
        self.scan_tab.learn_more.connect(self._open_feed)
        self.tabs.addTab(self.feed_tab, "Learn")
        self.tabs.addTab(self.scan_tab, "Scan")
        self.setCentralWidget(self.tabs)

    def _open_feed(self, code: str):
        self.feed_tab.select_class(code)
        self.tabs.setCurrentIndex(0)

    def closeEvent(self, e):
        self.scan_tab.stop_cam()
        super().closeEvent(e)
