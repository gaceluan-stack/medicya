from sqlalchemy import create_engine, MetaData, Table, select, and_
import datetime

prod_db_url = "postgresql://postgres.trsvyznppbdbatkohibp:LAgc1919942688@aws-0-ca-central-1.pooler.supabase.com:6543/postgres"
engine = create_engine(prod_db_url)
metadata = MetaData()
metadata.reflect(bind=engine)

citas_table = Table('citas_proveedores', metadata, autoload_with=engine)

prov_id = '92c2f9b3-e534-4add-86ad-bebd9023d3f4'
fecha = datetime.date(2026, 8, 26)
hora_inicio = '08:30'
hora_fin = '09:00'

print(f"Simulating query for Provider: {prov_id}, Date: {fecha}, Start: {hora_inicio}, End: {hora_fin}")

query = select(citas_table).where(
    and_(
        citas_table.c.proveedor_id == prov_id,
        citas_table.c.fecha == fecha,
        citas_table.c.hora_inicio < hora_fin,
        citas_table.c.hora_fin > hora_inicio
    )
)

with engine.connect() as conn:
    row = conn.execute(query).first()
    if row:
        print("\nOverlap found! Row details:")
        print(f"ID: {row[0]}")
        print(f"Provider ID: {row[1]}")
        print(f"Patient ID: {row[2]}")
        print(f"Patient Name: {row[3]}")
        print(f"Date: {row[4]}")
        print(f"Hora Inicio: {row[5]}")
        print(f"Hora Fin: {row[6]}")
        print(f"Estado: {row[7]}")
        print(f"Servicios: {row[8]}")
    else:
        print("\nNo overlap found! The slot is free.")
