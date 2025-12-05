import sys
import os
import json

from PySide6.QtWidgets import ( # type: ignore
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QScrollArea, QDialog,
    QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QEvent, QPropertyAnimation
from PySide6.QtGui import QPixmap, QImage, QTextOption

from gpt_client import GPTClient
from capture_engine import capture_full_screen
from utils import (
    save_json, load_json, now_timestamp,
    image_to_base64, base64_to_image
)
import ctypes
from ctypes import wintypes

from PySide6.QtGui import QPixmap, QImage, QTextOption, QIcon
from PySide6.QtCore import QTimer

from PIL import Image




def enable_blur(hwnd):
    # ACCENT_POLICY 구조체
    class ACCENTPOLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_int),
            ("AccentFlags", ctypes.c_int),
            ("GradientColor", ctypes.c_int),
            ("AnimationId", ctypes.c_int)
        ]

    # WINDOWCOMPOSITIONATTRIBDATA 구조체
    class WINCOMPATTRDATA(ctypes.Structure):
        _fields_ = [
            ("Attribute", ctypes.c_int),
            ("Data", ctypes.POINTER(ACCENTPOLICY)),
            ("SizeOfData", ctypes.c_size_t)
        ]

    accent = ACCENTPOLICY()
    accent.AccentState = 3   # ACCENT_ENABLE_BLURBEHIND

    data = WINCOMPATTRDATA()
    data.Attribute = 19      # WCA_ACCENT_POLICY
    data.Data = ctypes.pointer(accent)
    data.SizeOfData = ctypes.sizeof(accent)

    setWindowCompositionAttribute = ctypes.windll.user32.SetWindowCompositionAttribute
    setWindowCompositionAttribute(hwnd, ctypes.byref(data))


# --------------------------------------------------------
# 날짜 유틸
# --------------------------------------------------------
def today_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

def format_korean_date(date_str):
    y, m, d = date_str.split("-")
    return f"{y}년 {int(m)}월 {int(d)}일"

#--------------------------
# 이미지 붙여넣기 기능
#--------------------------

class ChatInputBox(QTextEdit):
    def insertFromMimeData(self, source):
        # 클립보드에 이미지가 있으면
        if source.hasImage():
            img = source.imageData()
            self.parent().handle_paste_image(img)  # MainWindow 메서드 호출
        else:
            super().insertFromMimeData(source)

# --------------------------------------------------------
# API Key 입력
# --------------------------------------------------------
class ApiKeyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("API Key 설정")
        self.resize(350, 150)

        layout = QVBoxLayout()
        label = QLabel("OpenAI API Key 입력:")
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        btn = QPushButton("저장")
        btn.clicked.connect(self.save_key)

        layout.addWidget(label)
        layout.addWidget(self.edit)
        layout.addWidget(btn)
        self.setLayout(layout)

        data = load_json("storage/api_key.json")
        if data and "api_key" in data:
            self.edit.setText(data["api_key"])

    def save_key(self):
        key = self.edit.text().strip()
        if key:
            save_json("storage/api_key.json", {"api_key": key})
            self.accept()


# --------------------------------------------------------
# 날짜 구분선
# --------------------------------------------------------
class DateSeparator(QWidget):
    def __init__(self, date_text):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)

        l1 = QLabel("──────────")
        l2 = QLabel(f"  {date_text}  ")
        l3 = QLabel("──────────")

        for l in (l1, l2, l3):
            l.setStyleSheet("color:#555; font-size:12px;")

        layout.addWidget(l1)
        layout.addWidget(l2)
        layout.addWidget(l3)
        self.setLayout(layout)


# --------------------------------------------------------
# 말풍선
# --------------------------------------------------------
class ChatBubble(QWidget):
    def __init__(self, text="", is_user=False, image_b64=None, timestamp=""):
        super().__init__()

        layout = QVBoxLayout()
        bubble = QWidget()
        bubble_layout = QVBoxLayout()
        bubble_layout.setContentsMargins(10, 10, 10, 10)

        if text:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)   # ★ 추가!
            lbl.setStyleSheet("font-size:12px; color:black;")
            lbl.setMaximumWidth(230)
            
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            bubble_layout.addWidget(lbl)

        if image_b64:
            img = base64_to_image(image_b64)
            qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaledToWidth(180)
            img_lbl = QLabel()
            img_lbl.setPixmap(pix)
            bubble_layout.addWidget(img_lbl)

        bubble.setLayout(bubble_layout)

        if is_user:
            bubble.setStyleSheet("""
                background:#ffe97a;
                border-radius:10px;
                border-bottom-right-radius:2px;
            """)
            layout.addWidget(bubble, alignment=Qt.AlignRight)
        else:
            bubble.setStyleSheet("""
                background:#aee3ff;   /* 밝은 하늘색 */
                border-radius:10px;
                border-bottom-left-radius:2px;
            """)
            layout.addWidget(bubble, alignment=Qt.AlignLeft)

        ts = QLabel(timestamp)
        ts.setStyleSheet("font-size:11px; color:#444;")
        layout.addWidget(ts,
                         alignment=(Qt.AlignRight if is_user else Qt.AlignLeft))

        self.setLayout(layout)

        # fade 효과
        self.setWindowOpacity(0)
        ani = QPropertyAnimation(self, b"windowOpacity")
        ani.setDuration(150)
        ani.setStartValue(0)
        ani.setEndValue(1)
        ani.start()


# --------------------------------------------------------
# 메인 윈도우
# --------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.gpt = GPTClient()

        self.setWindowTitle("AutoCaptureGPT")
        self.resize(360, 600)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:black;")

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # 투명 배경 허용
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Blur(Acrylic) 적용
        # enable_blur(int(self.winId()))
        self.setStyleSheet("background-color: black;")

        # 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 대화 기록 파일
        self.history_path = "storage/chat_history.json"
        if not os.path.exists("storage"):
            os.makedirs("storage")

        # --------------------------------------------------------
        # 스크롤 영역
        # --------------------------------------------------------
        self.scroll = QScrollArea()  # ★ 반드시 있어야 함
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 스크롤바 스타일
        self.scroll.setStyleSheet("""
            QScrollBar:vertical {
                width: 10px;              /* ★ 스크롤바 두께 증가 */
                background: transparent;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #333333;      /* ★ 어두운 회색으로 변경 */
                border-radius: 4px;       /* 살짝 더 둥글게 */
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background: #999999;      /* hover 시 더 진하게 */
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        # 채팅 컨테이너
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: black;")  # ★ 배경을 까맣게
        
        self.chat_container.setSizePolicy(
            QSizePolicy.Minimum,
            QSizePolicy.Expanding
        )

        self.chat_layout = QVBoxLayout()
        self.chat_layout.setAlignment(Qt.AlignTop)

        self.chat_container.setLayout(self.chat_layout)
        self.scroll.setWidget(self.chat_container)

        layout.addWidget(self.scroll)

        # --------------------------------------------------------
        # 입력창 + 버튼
        # --------------------------------------------------------
        input_layout = QHBoxLayout()

        self.input = ChatInputBox()
        self.input.setParent(self)  # parent 설정(중요)

        self.input.setObjectName("ChatInput")
        self.input.setWordWrapMode(QTextOption.WrapAnywhere)

        self.MIN_INPUT_HEIGHT = 45
        self.MAX_INPUT_HEIGHT = 90
        self.input.setFixedHeight(self.MIN_INPUT_HEIGHT)

        self.input.setStyleSheet("""
            QTextEdit#ChatInput {
                background:white;
                font-size:14px;
                color:black;
                border-radius:6px;
                padding:10px;
            }
            QTextEdit#ChatInput QScrollBar:vertical {
                width: 0px;
                background: transparent;
            }
        """)

        self.input.textChanged.connect(self.adjust_input_area)
        self.input.installEventFilter(self)

        self.send_btn = QPushButton("전송")
        self.send_btn.setFixedWidth(70)
        self.send_btn.setFixedHeight(self.MIN_INPUT_HEIGHT)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffe97a !important;   /* 기본 노랑 */
                color: black !important;
                border-radius: 6px;
                font-size: 15px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffd44a !important;   /* hover */
                color: black !important;
            }
            QPushButton:pressed {
                background-color: #e6c239 !important;   /* 클릭 시 조금 어두운 노랑 */
                color: black !important;
            }
        """)

        self.send_btn.clicked.connect(self.send_with_capture)

        input_layout.addWidget(self.input)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        # 대화 불러오기
        self.load_chat_history()



    #붙여넣기 이미지 처리 함수

    def handle_paste_image(self, qimage):
        from utils import image_to_base64

        # QImage → bytes 변환
        qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
        width = qimage.width()
        height = qimage.height()
        bytes_data = qimage.bits().tobytes()

        # bytes → PIL.Image
        pil_img = Image.frombytes("RGBA", (width, height), bytes_data)

        img_b64 = image_to_base64(pil_img)

        # 붙여넣기 시 입력창에 안내 표시
        # self.input.setPlainText("(이미지 붙여넣기)")

        # 버블로 추가
        self.add_user_bubble("", img_b64)
        self.save_chat_history("user", "", img_b64)

    # 입력창 자동 높이
    def adjust_input_area(self):
        doc_height = self.input.document().size().height() + 12
        new_height = max(self.MIN_INPUT_HEIGHT, min(doc_height, self.MAX_INPUT_HEIGHT))

        self.input.setFixedHeight(new_height)
        self.send_btn.setFixedHeight(new_height)

    # 날짜 구분선
    def add_date_separator_if_needed(self, date_str):
        if not hasattr(self, "last_date"):
            self.last_date = None

        if self.last_date != date_str:
            sep = DateSeparator(format_korean_date(date_str))
            self.chat_layout.addWidget(sep)
            self.last_date = date_str

    # 대화 기록 저장
    def save_chat_history(self, role, text, img_b64):
        history = []
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []

        entry = {
            "role": role,
            "text": text,
            "img": img_b64,
            "timestamp": now_timestamp(),
            "date": today_str()
        }
        history.append(entry)

        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    # 대화 불러오기
    def load_chat_history(self):
        if not os.path.exists(self.history_path): return

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            return

        for entry in history:
            self.add_date_separator_if_needed(entry.get("date", today_str()))
            if entry["role"] == "user":
                self.add_user_bubble(entry["text"], entry.get("img"))
            else:
                self.add_gpt_bubble(entry["text"])

    # 엔터키 처리
    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return:

                if event.modifiers() & Qt.ControlModifier:
                    self.send_text_only()
                    return True

                if event.modifiers() & Qt.ShiftModifier:
                    return False

                self.send_with_capture()
                return True

        return super().eventFilter(obj, event)

    # 스크롤 맨 아래로
    def scroll_bottom(self):
        QApplication.processEvents()
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    # 말풍선
    def add_user_bubble(self, text, img_b64=None):
        self.add_date_separator_if_needed(today_str())
        bubble = ChatBubble(text, True, img_b64, now_timestamp())
        self.chat_layout.addWidget(bubble)
        
        QTimer.singleShot(0, self.scroll_bottom)   # ★ 여기로 교체


    def add_gpt_bubble(self, text):
        self.add_date_separator_if_needed(today_str())
        bubble = ChatBubble(text, False, None, now_timestamp())
        self.chat_layout.addWidget(bubble)

        QTimer.singleShot(0, self.scroll_bottom)   # ★ 여기로 교체

    # GPT typing 표시
    def add_typing(self):
        self.typing = QLabel("...")
        self.typing.setStyleSheet("""
            background:white;
            color:black;
            padding:10px;
            border-radius:10px;
        """)
        self.chat_layout.addWidget(self.typing)
        self.scroll_bottom()

    def remove_typing(self):
        if hasattr(self, "typing"):
            self.typing.deleteLater()

    # 텍스트만 전송
    def send_text_only(self):
        text = self.input.toPlainText().strip()
        if not text:
            return

        self.input.clear()
        self.adjust_input_area()

        self.add_user_bubble(text)
        self.save_chat_history("user", text, None)

        self.add_typing()
        res = self.gpt.send_message(text)
        self.remove_typing()

        self.add_gpt_bubble(res)
        self.save_chat_history("assistant", res, None)

    # 캡처 포함 전송
    def send_with_capture(self):
        text = self.input.toPlainText().strip()
        self.input.clear()
        self.adjust_input_area()

        img = capture_full_screen(
            hide=lambda: self.hide(),
            show=lambda: self.show()
        )
        img_b64 = image_to_base64(img)

        self.add_user_bubble(text, img_b64)
        self.save_chat_history("user", text, img_b64)

        self.add_typing()
        res = self.gpt.send_message(text, img_b64)
        self.remove_typing()

        self.add_gpt_bubble(res)
        self.save_chat_history("assistant", res, None)



# --------------------------------------------------------
# 실행
# --------------------------------------------------------
if not os.path.exists("storage"):
    os.makedirs("storage")

app = QApplication(sys.argv)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(BASE_DIR, "assets", "icons", "app.ico")

app.setWindowIcon(QIcon(icon_path))

key = load_json("storage/api_key.json")
if not key or "api_key" not in key:
    dlg = ApiKeyDialog()
    dlg.exec()

win = MainWindow()
win.show()

sys.exit(app.exec())
