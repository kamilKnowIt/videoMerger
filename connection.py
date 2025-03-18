import psycopg2

# Połączenie z bazą danych
conn = psycopg2.connect(
    dbname="videomerger",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)

cursor = conn.cursor()

# Pobranie struktury bazy danych (nazwy tabel i kolumn)
cursor.execute("""
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
""")

tables = {}

for table_name, column_name, data_type in cursor.fetchall():
    if table_name not in tables:
        tables[table_name] = []
    tables[table_name].append(f"{column_name} ({data_type})")

# Wydrukowanie struktury bazy danych
for table, columns in tables.items():
    print(f"\n🗂 Tabela: {table}")
    for column in columns:
        print(f"   - {column}")

# Zamknięcie połączenia
cursor.close()
conn.close()
