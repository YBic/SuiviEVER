"""Exécute grant_ever_app.sql avec le compte Windows courant."""
import re, pyodbc

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SRV-LANSQL-03\\MSSQLIFOPGE;"
    "DATABASE=EVER_DEV;"
    "TrustServerCertificate=yes;"
    "Trusted_Connection=yes;"
)

with open("sql/grant_ever_app.sql", encoding="utf-8") as f:
    sql = f.read()

batches = [b.strip() for b in re.split(r'^\s*GO\s*$', sql, flags=re.MULTILINE) if b.strip()]

conn = pyodbc.connect(conn_str, autocommit=True)
c = conn.cursor()

for i, batch in enumerate(batches, 1):
    # Ignorer les batches purement commentaires
    non_comment = "\n".join(l for l in batch.splitlines() if not l.strip().startswith("--")).strip()
    if not non_comment:
        continue
    print(f"[{i}] {batch[:80].replace(chr(10),' ')}...")
    try:
        c.execute(batch)
        print("  → OK")
    except pyodbc.Error as e:
        print(f"  → ERREUR : {e}")

conn.close()
print("\nTerminé.")
