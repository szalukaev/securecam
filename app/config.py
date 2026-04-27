from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # DB
    DATABASE_URL: str = "postgresql+asyncpg://securecam_user:password@127.0.0.1:5432/securecam_db"

    # Security
    SECRET_KEY: str = "change_me"

    # Admin
    ADMIN_LOGIN: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    # Email
    SMTP_HOST: str = "smtp.yandex.ru"
    SMTP_PORT: int = 465
    SMTP_SSL: bool = True
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ORDER_EMAIL: str = ""

    # Site info
    SITE_NAME: str = "СекьюрКам Екатеринбург"
    SITE_DOMAIN: str = "https://securecam-ekb.ru"
    SITE_PHONE: str = "+7 (343) 000-00-00"
    SITE_ADDRESS: str = "г. Екатеринбург"
    SITE_EMAIL: str = "info@securecam-ekb.ru"
    SITE_DESCRIPTION: str = "Продажа и установка систем видеонаблюдения в Екатеринбурге"
    SITE_KEYWORDS: str = "видеонаблюдение Екатеринбург, камеры видеонаблюдения"

    # Parser
    PARSER_SOURCES: str = ""
    PARSER_DISCOUNT_PERCENT: float = 20.0
    PARSER_CRON: str = "0 3 * * *"

    # App
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
