import time
from PIL import ImageGrab
from utils import log
from PySide6.QtWidgets import QApplication   # ★ 추가!

# ----------------------------------------------------------
# 전체 화면 캡처 (챗창 숨기고 찍기)
# ----------------------------------------------------------
def capture_full_screen(hide=None, show=None):
    """
    hide: 윈도우를 숨기는 함수
    show: 윈도우를 다시 보이게 하는 함수
    """

    try:
        # 창 숨기기
        if hide:
            try:
                hide()
                QApplication.processEvents()   # ★ 창 숨김 즉시 반영
                time.sleep(0.13)               # ★ 70ms 대기 → 안정적
            except:
                log("[capture_engine] hide() 실행 실패")

        # 전체 화면 캡처
        try:
            img = ImageGrab.grab(all_screens=True)
        except Exception:
            img = ImageGrab.grab()

        # 창 복귀
        if show:
            try:
                show()
            except:
                log("[capture_engine] show() 실행 실패")

        return img

    except Exception as e:
        log(f"[capture_engine] ERROR: {e}")

        try:
            return ImageGrab.grab()
        except:
            return None
