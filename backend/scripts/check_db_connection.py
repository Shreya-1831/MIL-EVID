from sqlalchemy import text

from app.database.session import engine


def main() -> None:
    """Verify that the application can connect to the database."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Database connection successful:", result.scalar_one())


if __name__ == "__main__":
    main()