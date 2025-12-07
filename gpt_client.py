from openai import OpenAI
from utils import load_json

# 시스템 프롬프트 불러오기 함수
def load_system_prompt():
    txt = load_json("storage/system_prompt.json")
    if txt and txt.strip():
        return txt
    return "기본 시스템 프롬프트가 비어 있습니다."

class GPTClient:

    def __init__(self):
        keydata = load_json("storage/api_key.json")
        if not keydata or "api_key" not in keydata:
            raise Exception("API Key not found.")

        self.client = OpenAI(api_key=keydata["api_key"])

        # 최근 대화 저장 (텍스트 + 이미지 포함)
        self.history = []
        self.max_history = 10   # 최근 10개 유지


    def send_message(self, text="", image_b64=None, on_delta=None):

        # 1) 사용자 메시지 만들기
        if image_b64:
            user_message = {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + image_b64
                        }
                    }
                ]
            }
        else:
            user_message = {
                "role": "user",
                "content": text
            }

        # 2) history 저장
        self.history.append(user_message)

        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # 3) 전체 메시지 준비
        messages = [
            {"role": "system", "content": load_system_prompt()}
        ]
        messages += self.history

        # 4) GPT 스트리밍 요청
        stream = self.client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            stream=True
        )

        # 5) 스트리밍 받기
        full = ""
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full += delta.content
                    if on_delta:
                        on_delta(delta.content)

        # 6) assistant 답변도 히스토리에 저장
        self.history.append({
            "role": "assistant",
            "content": full
        })
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return full
