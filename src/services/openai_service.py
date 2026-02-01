from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.previous_responses = {}

    def get_response(self, context_key: str, user_message: str) -> str:
        try:
            if context_key not in self.previous_responses:
                response = self.client.responses.create(
                    model="gpt-4o-mini",
                    input=user_message,
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

    def clear_session(self, context_key: str):
        self.previous_responses.pop(context_key, None)
