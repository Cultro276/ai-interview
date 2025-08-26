import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")
    db_host: str = os.getenv("DB_HOST", "postgres")
    db_port: str = os.getenv("DB_PORT", "5432")
    db_name: str = os.getenv("DB_NAME", "interview")

    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_access_key_id: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_bucket: str | None = os.getenv("S3_BUCKET")
    # Retention
    @property
    def retention_media_days(self) -> int:
        try:
            return int(os.getenv("RETENTION_MEDIA_DAYS", "365"))
        except Exception:
            return 365
    @property
    def retention_transcript_days(self) -> int:
        try:
            return int(os.getenv("RETENTION_TRANSCRIPT_DAYS", "365"))
        except Exception:
            return 365

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def gemini_api_key(self) -> str | None:
        return os.getenv("GEMINI_API_KEY")

    @property
    def openai_api_key(self) -> str | None:
        return os.getenv("OPENAI_API_KEY")

    # Azure Speech
    @property
    def azure_speech_key(self) -> str | None:
        return os.getenv("AZURE_SPEECH_KEY")

    @property
    def azure_speech_region(self) -> str | None:
        return os.getenv("AZURE_SPEECH_REGION")

    # ElevenLabs
    @property
    def elevenlabs_api_key(self) -> str | None:
        return os.getenv("ELEVENLABS_API_KEY")

    @property
    def elevenlabs_voice_id(self) -> str | None:
        return os.getenv("ELEVENLABS_VOICE_ID")

    # Optional providers
    @property
    def assemblyai_api_key(self) -> str | None:
        return os.getenv("ASSEMBLYAI_API_KEY")

    @property
    def azure_face_key(self) -> str | None:
        return os.getenv("AZURE_FACE_KEY")

    @property
    def azure_face_endpoint(self) -> str | None:
        return os.getenv("AZURE_FACE_ENDPOINT")

    # Queue (SQS)
    @property
    def sqs_queue_url(self) -> str | None:
        return os.getenv("SQS_QUEUE_URL")

    # Mail (Resend)
    @property
    def resend_api_key(self) -> str | None:
        return os.getenv("RESEND_API_KEY")

    @property
    def mail_from(self) -> str | None:
        return os.getenv("MAIL_FROM")

    @property
    def mail_from_name(self) -> str | None:
        return os.getenv("MAIL_FROM_NAME")

    # Internal admin console
    @property
    def internal_admin_secret(self) -> str:
        return os.getenv("INTERNAL_ADMIN_SECRET", "dev-internal-secret")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings() 