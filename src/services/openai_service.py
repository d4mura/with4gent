from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.previous_responses = {}

    def get_response(self, context_key: str, user_message: str) -> str:
        system_message = {
            "role": "system",
            "content": "回答は必ず500文字以内で行ってください。",
        }
        try:
            if context_key not in self.previous_responses:
                response = self.client.responses.create(
                    model="gpt-4o-mini",
                    input=[system_message, {"role": "user", "content": user_message}],
                    store=True,
                    tools=[{"type": "web_search"}],
                )
            else:
                response = self.client.responses.create(
                    model="gpt-4o-mini",
                    input=user_message,
                    previous_response_id=self.previous_responses[context_key],
                    tools=[{"type": "web_search"}],
                )

            self.previous_responses[context_key] = response.id
            return response.output_text

        except Exception as e:
            # 本来はロガーを使うべきだが、
            # 簡易化のため例外を投げるか特定のメッセージを返す
            raise e

    def summarize(self, context_key: str) -> str:
        """現在のセッション内容をサマライズする"""
        if context_key not in self.previous_responses:
            return ""

        try:
            # Responses API を使用して、これまでの内容の要約を求める
            response = self.client.responses.create(
                model="gpt-4o-mini",
                input="これまでの会話の内容を、重要なポイントを逃さず100文字程度で簡潔に要約してください。",
                previous_response_id=self.previous_responses[context_key],
                store=False,  # サマリー自体はセッション履歴に含めない方が管理しやすい
            )
            return response.output_text
        except Exception:
            return ""

    def clear_session(self, context_key: str):
        self.previous_responses.pop(context_key, None)
