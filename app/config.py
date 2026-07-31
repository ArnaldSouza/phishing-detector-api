from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    postgres_test_db: str = "phishing_test_db"
    sql_echo: bool = False

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    def _url_for(self, database: str) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database}"
        )

    @property
    def database_url(self) -> str:
        return self._url_for(self.postgres_db)

    @property
    def test_database_url(self) -> str:
        return self._url_for(self.postgres_test_db)


settings = Settings()
