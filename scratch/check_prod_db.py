import os
from sqlalchemy import create_engine, MetaData, Table, select

# Corrected connection URL with '88' at the end of the password
prod_db_url = "postgresql://postgres.trsvyznppbdbatkohibp:LAgc1919942688@aws-0-ca-central-1.pooler.supabase.com:6543/postgres"

engine = create_engine(prod_db_url)
metadata = MetaData()
metadata.reflect(bind=engine)

try:
    citas_table = Table('citas_proveedores', metadata, autoload_with=engine)
    print("Found table citas_proveedores.")
    
    # Query appointments
    with engine.connect() as conn:
        result = conn.execute(select(citas_table)).fetchall()
        print(f"\nTotal appointments in production: {len(result)}")
        for r in result:
            print(f"ID: {r[0]}, Provider ID: {r[1]}, Patient: {r[3]}, Date: {r[4]}, Time: {r[5]}-{r[6]}, Status: {r[7]}")
            
except Exception as e:
    print("Error:", e)
