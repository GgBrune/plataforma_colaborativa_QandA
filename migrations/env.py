from logging.config import fileConfig

from alembic import context

from qanda import create_app
from qanda.extensions import db

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

app = create_app()
target_metadata = db.metadata


def run_migrations_offline():
    """Genera el SQL sin conectarse a la base de datos."""
    context.configure(
        url=app.config["SQLALCHEMY_DATABASE_URI"],
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Aplica las migraciones usando la configuración de la app Flask."""
    with app.app_context(), db.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
