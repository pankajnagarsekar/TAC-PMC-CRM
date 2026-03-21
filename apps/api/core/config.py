import os

class Settings:
    MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME: str = os.environ.get('DB_NAME', 'construction_management')
    REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL: str = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
    USE_CELERY: bool = os.environ.get('USE_CELERY', 'false').lower() == 'true'

settings = Settings()
