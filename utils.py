import os
import json
import base64
import datetime
import traceback

from PIL import Image
import numpy as np


# ----------------------------------------------------------
# DEBUG 출력
# ----------------------------------------------------------
DEBUG = False

def log(msg):
    if DEBUG:
        print("[DEBUG]", msg)


# ----------------------------------------------------------
# 안전한 JSON 저장
# ----------------------------------------------------------
def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"[save_json] ERROR: {e}")
        log(traceback.format_exc())


# ----------------------------------------------------------
# JSON 불러오기 (없으면 None)
# ----------------------------------------------------------
def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"[load_json] ERROR: {e}")
        log(traceback.format_exc())
        return None


# ----------------------------------------------------------
# 현재 시각 timestamp
# ----------------------------------------------------------
def now_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ----------------------------------------------------------
# PIL → Base64
# ----------------------------------------------------------
def image_to_base64(pil_img):
    try:
        import io
        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        log(f"[image_to_base64] ERROR: {e}")
        log(traceback.format_exc())
        return None


# ----------------------------------------------------------
# Base64 → PIL
# ----------------------------------------------------------
def base64_to_image(b64):
    try:
        import io
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:
        log(f"[base64_to_image] ERROR: {e}")
        log(traceback.format_exc())
        return None


# ----------------------------------------------------------
# PIL → numpy
# ----------------------------------------------------------
def pil_to_np(pil_img):
    try:
        return np.array(pil_img)
    except Exception as e:
        log(f"[pil_to_np] ERROR: {e}")
        return None


# ----------------------------------------------------------
# numpy → PIL
# ----------------------------------------------------------
def np_to_pil(np_img):
    try:
        return Image.fromarray(np_img)
    except Exception as e:
        log(f"[np_to_pil] ERROR: {e}")
        return None


def today_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")
