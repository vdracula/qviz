from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    yandex_api_key: str = Field(..., alias="YANDEX_API_KEY")
    yandex_folder_id: str = Field(..., alias="YANDEX_FOLDER_ID")
    yandex_endpoint: str = Field(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        alias="YANDEX_ENDPOINT",
    )
    database_url: str = Field(..., alias="DATABASE_URL")  # ← добавили

    class Config:
        env_file = ".env"
        populate_by_name = True

settings = Settings()
