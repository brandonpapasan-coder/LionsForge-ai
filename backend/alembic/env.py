from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.init_db import _active_models, _load_compatibility_models
from app.db.session import Base

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Alembic must retain the complete historical schema even though normal application
# startup registers active research and education models only. Centralize compatibility
# loading here so migration tooling does not name discontinued finance models directly.
_load_compatibility_models()
target_metadata = Base.metadata
_models = _active_models


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
