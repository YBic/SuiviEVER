"""
Exécute les scripts SQL de migration sur EVER_DEV.
Usage : python sql/run_migration.py
"""
import os
import re
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SRV-LANSQL-03\\MSSQLIFOPGE;"
    "DATABASE=EVER_DEV;"
    "TrustServerCertificate=yes;"
    "Trusted_Connection=yes;"
)

script_path = os.path.join(os.path.dirname(__file__), 'create_log_connexion.sql')

with open(script_path, encoding='utf-8') as f:
    sql = f.read()

# Découpe sur GO en début de ligne (séparateur T-SQL)
batches = re.split(r'^\s*GO\s*$', sql, flags=re.MULTILINE)
batches = [b.strip() for b in batches if b.strip()]

conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

for i, batch in enumerate(batches, 1):
    preview = batch[:100].replace('\n', ' ')
    print(f"[Batch {i}] {preview}...")
    try:
        cursor.execute(batch)
        print(f"  → OK")
    except pyodbc.Error as e:
        print(f"  → ERREUR : {e}")

# Vérification finale
print()
print("=== Vérification ===")
cursor.execute(
    "SELECT name, type_desc FROM sys.objects "
    "WHERE name IN ('Log_Connexion','ft_EVER_Log_Connexion') ORDER BY type_desc"
)
for r in cursor.fetchall():
    print(f"  {r[1]:<45} {r[0]}")

conn.close()
print("\nMigration terminée.")
