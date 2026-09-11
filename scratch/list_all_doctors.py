from sqlalchemy import create_engine, MetaData, Table, select

prod_db_url = "postgresql://postgres.trsvyznppbdbatkohibp:LAgc1919942688@aws-0-ca-central-1.pooler.supabase.com:6543/postgres"

engine = create_engine(prod_db_url)
metadata = MetaData()
metadata.reflect(bind=engine)

try:
    prov_table = Table('proveedores_servicio', metadata, autoload_with=engine)
    with engine.connect() as conn:
        result = conn.execute(select(prov_table)).fetchall()
        print(f"Total doctors in production: {len(result)}")
        for r in result:
            print(f"ID: {r[0]}, Name: {r[3]}, Premium: {r[8]}, Cell: {r[7]}")
except Exception as e:
    print("Error:", e)
