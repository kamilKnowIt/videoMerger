import psycopg2
import os

# Konfiguracja połączenia
DB_CONFIG = {
    "dbname": "videomerger",
    "user": "postgres",
    "password": "1234",
    "host": "localhost",
    "port": "5432"
}

DDL_FILE = os.path.join(os.path.dirname(__file__), "ddl.txt")


def connect_db():
    """Próbuje połączyć się z bazą danych."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Połączono z bazą PostgreSQL")
        return conn
    except psycopg2.OperationalError:
        print("⚠️ Baza danych nie istnieje. Tworzę ją...")
        create_database()
        return None
    except Exception as e:
        print("❌ Błąd połączenia:", e)
        return None


def create_database():
    """Tworzy bazę danych i tabele z pliku DDL."""
    try:
        # Połączenie do domyślnej bazy `postgres`
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Tworzenie bazy videomerger
        cursor.execute(f"CREATE DATABASE {DB_CONFIG['dbname']};")
        print("✅ Baza videomerger została utworzona.")

        # Zamykamy połączenie, aby przełączyć się do nowej bazy
        cursor.close()
        conn.close()

        # Połączenie do nowej bazy i wykonanie DDL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        with open(DDL_FILE, "r", encoding="utf-8") as f:
            ddl_script = f.read()
            cursor.execute(ddl_script)
        
        conn.commit()
        print("✅ Struktura bazy danych została utworzona.")

        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ Błąd podczas tworzenia bazy danych:", e)


if __name__ == "__main__":
    connect_db()
