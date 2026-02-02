import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    line_channel_access_token: str = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    line_channel_secret: str = os.environ.get("LINE_CHANNEL_SECRET", "")
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    port: int = int(os.environ.get("PORT", 8080))


config = Config()
