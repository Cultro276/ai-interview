import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables with validation."""

    # Database settings
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres") 
    db_host: str = os.getenv("DB_HOST", "postgres")
    db_port: str = os.getenv("DB_PORT", "5432")
    db_name: str = os.getenv("DB_NAME", "interview")
    
    # LLM Provider Configuration (NEW)
    @property
    def primary_llm_provider(self) -> str:
        """Primary LLM provider: openai, gemini, or fallback"""
        return os.getenv("PRIMARY_LLM_PROVIDER", "openai").lower()
    
    @property
    def enable_llm_caching(self) -> bool:
        """Enable LLM response caching"""
        return os.getenv("ENABLE_LLM_CACHING", "true").lower() == "true"
    
    @property  
    def llm_cache_ttl_hours(self) -> int:
        """LLM cache TTL in hours"""
        try:
            return int(os.getenv("LLM_CACHE_TTL_HOURS", "1"))
        except ValueError:
            return 1
    
    @property
    def max_parallel_llm_calls(self) -> int:
        """Maximum parallel LLM calls"""
        try:
            return int(os.getenv("MAX_PARALLEL_LLM_CALLS", "5"))
        except ValueError:
            return 5

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

    # STT provider selection
    @property
    def stt_provider(self) -> str:
        return os.getenv("STT_PROVIDER", "auto").lower()

    @property
    def enable_serverless_whisper(self) -> bool:
        return os.getenv("ENABLE_SERVERLESS_WHISPER", "false").lower() in {"1", "true", "yes"}

    @property
    def local_stt_queue(self) -> bool:
        return os.getenv("LOCAL_STT_QUEUE", "false").lower() in {"1", "true", "yes"}

    @property
    def stt_queue_name(self) -> str:
        return os.getenv("STT_QUEUE_NAME", "stt:jobs")

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

    # Redis
    @property
    def redis_url(self) -> str | None:
        val = os.getenv("REDIS_URL", "").strip()
        return val or None

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

    # OAuth: Google Calendar / Zoom
    @property
    def google_client_id(self) -> str | None:
        return os.getenv("GOOGLE_CLIENT_ID")

    @property
    def google_client_secret(self) -> str | None:
        return os.getenv("GOOGLE_CLIENT_SECRET")

    @property
    def google_redirect_uri(self) -> str | None:
        return os.getenv("GOOGLE_REDIRECT_URI")

    @property
    def zoom_client_id(self) -> str | None:
        return os.getenv("ZOOM_CLIENT_ID")

    @property
    def zoom_client_secret(self) -> str | None:
        return os.getenv("ZOOM_CLIENT_SECRET")

    @property
    def zoom_redirect_uri(self) -> str | None:
        return os.getenv("ZOOM_REDIRECT_URI")

    # External base URL for building absolute links in emails
    @property
    def external_base_url(self) -> str:
        return os.getenv("API_EXTERNAL_BASE_URL", "http://localhost:8000")

    # Public web base URL for candidate-facing links
    @property
    def web_external_base_url(self) -> str | None:
        val = os.getenv("WEB_EXTERNAL_BASE_URL", "").strip()
        return val or None

    # Security & Secrets
    @property
    def environment(self) -> str:
        return os.getenv("ENVIRONMENT", "development")

    # CORS origins (comma-separated). If empty, defaults are used in main.py
    @property
    def cors_allowed_origins(self) -> list[str]:
        raw = os.getenv("ALLOWED_ORIGINS", "").strip()
        if not raw:
            return []
        try:
            return [o.strip() for o in raw.split(",") if o.strip()]
        except Exception:
            return []

    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}

    @property
    def jwt_secret(self) -> str:
        val = os.getenv("JWT_SECRET", "")
        if self.environment == "production":
            if len(val) < 32:
                raise ValueError("JWT_SECRET must be set and at least 32 characters in production")
        else:
            if not val:
                # Dev-safe default; DO NOT use in production
                val = (os.getenv("DB_PASSWORD", "dev") + os.getenv("DB_USER", "dev")).ljust(32, "_")
        return val

    @property
    def session_secret(self) -> str:
        val = os.getenv("SESSION_SECRET", "")
        if self.environment == "production" and len(val) < 32:
            raise ValueError("SESSION_SECRET must be set and at least 32 characters in production")
        return val or "dev-session-secret-please-change".ljust(32, "_")

    @property
    def encryption_master_key(self) -> str:
        val = os.getenv("ENCRYPTION_MASTER_KEY", "")
        if self.environment == "production" and len(val) < 32:
            raise ValueError("ENCRYPTION_MASTER_KEY must be 32+ chars in production")
        return val or "dev-encryption-master-key-please-change".ljust(32, "_")

    # Internal admin console
    @property
    def internal_admin_secret(self) -> str:
        val = os.getenv("INTERNAL_ADMIN_SECRET", "dev-internal-secret")
        if self.environment == "production" and len(val) < 32:
            raise ValueError("INTERNAL_ADMIN_SECRET must be set and at least 32 characters in production")
        return val

    @property
    def webhook_secret(self) -> str:
        val = os.getenv("WEBHOOK_SECRET", "")
        if self.environment == "production" and len(val) < 32:
            raise ValueError("WEBHOOK_SECRET must be set and at least 32 characters in production")
        return val or "dev-webhook-secret-change-in-production-secure-key".ljust(32, "_")

    # Interview thresholds (tunable via env)
    @property
    def interview_max_questions_default(self) -> int:
        try:
            return int(os.getenv("INTERVIEW_MAX_Q_DEFAULT", "7"))
        except Exception:
            return 7

    @property
    def interview_overall_score_good_threshold(self) -> float:
        try:
            return float(os.getenv("INTERVIEW_SCORE_GOOD", "70"))
        except Exception:
            return 70.0

    @property
    def interview_overall_score_strong_threshold(self) -> float:
        try:
            return float(os.getenv("INTERVIEW_SCORE_STRONG", "85"))
        except Exception:
            return 85.0

    @property
    def interview_min_questions_positive(self) -> int:
        try:
            return int(os.getenv("INTERVIEW_MIN_Q_POSITIVE", "3"))
        except Exception:
            return 3

    @property
    def interview_min_questions_negative(self) -> int:
        try:
            return int(os.getenv("INTERVIEW_MIN_Q_NEGATIVE", "4"))
        except Exception:
            return 4

    @property
    def interview_min_questions_mixed(self) -> int:
        try:
            return int(os.getenv("INTERVIEW_MIN_Q_MIXED", "5"))
        except Exception:
            return 5

    @property
    def interview_low_score_threshold(self) -> float:
        try:
            return float(os.getenv("INTERVIEW_LOW_SCORE", "55"))
        except Exception:
            return 55.0

    @property
    def interview_critical_requirements_top_k(self) -> int:
        try:
            return int(os.getenv("INTERVIEW_CRITICAL_REQ_TOP_K", "3"))
        except Exception:
            return 3


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings() 