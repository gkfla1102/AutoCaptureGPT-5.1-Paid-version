from openai import OpenAI
from utils import load_json

# 요청한 프롬프트 그대로 반영
SYSTEM_PROMPT = (
    "Keep everything within 360 characters, explain simply with metaphors or examples, "
    "focus on the core idea, and always respond in the user's input language, "
    "regardless of previous conversation history."
)
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

        """사용자가 보낸 메시지를 GPT에게 전달하고 히스토리를 유지"""

        # 1) 사용자 메시지(history에 저장할 형태로 구성)
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

        # 2) 사용자 메시지 history에 저장
        self.history.append(user_message)

        # 3) 최근 10개만 유지
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]


        # 4) GPT에 보낼 메시지 구성
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        messages += self.history   # 맥락 포함


        # 5) GPT 스트리밍 호출
        stream = self.client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            stream=True
        )

        # 6) 스트리밍 모아서 하나의 문자열로
        full = ""
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full += delta.content
                    if on_delta:
                        on_delta(delta.content)


        # 7) GPT 답변도 history에 저장
        self.history.append({
            "role": "assistant",
            "content": full
        })

        # 8) 다시 10개 유지
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return full
