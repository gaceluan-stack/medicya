import time
import concurrent.futures
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

NUM_REQUESTS = 100
MAX_WORKERS = 20

def make_request(req_id):
    start_time = time.time()
    try:
        # Petición 1: Mapa público de proveedores
        res_map = client.get("/api/proveedores/mapa")
        # Petición 2: Filtro por categoría
        res_cat = client.get("/api/proveedores/mapa?categoria=Doctores")
        # Petición 3: Healthcheck
        res_health = client.get("/api/health")
        # Petición 4: HTML Index con GZip
        res_index = client.get("/", headers={"Accept-Encoding": "gzip"})
        
        elapsed = (time.time() - start_time) * 1000
        success = (
            res_map.status_code == 200 and
            res_cat.status_code == 200 and
            res_health.status_code == 200 and
            res_index.status_code == 200
        )
        return {
            "req_id": req_id,
            "success": success,
            "latency_ms": elapsed,
            "encoding": res_index.headers.get("content-encoding", "none")
        }
    except Exception as e:
        return {"req_id": req_id, "success": False, "error": str(e), "latency_ms": 0}

def run_stress_test():
    print(f"=== INICIANDO PRUEBA DE ESTRÉS: {NUM_REQUESTS} CLIENTES SIMULTÁNEOS ===")
    print(f"Pool de hilos concurrentes: {MAX_WORKERS}")
    
    start_all = time.time()
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(make_request, i) for i in range(NUM_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            
    total_duration = time.time() - start_all
    
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    latencies = [r["latency_ms"] for r in successes]
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    gzip_responses = [r for r in successes if r.get("encoding") == "gzip"]
    
    print("\n=== RESULTADOS DE LA PRUEBA DE ESTRÉS ===")
    print(f"Peticiones Totales: {NUM_REQUESTS * 4} HTTP calls en {NUM_REQUESTS} lotes concurrentes")
    print(f"Éxitos (200 OK): {len(successes)} / {NUM_REQUESTS} ({len(successes)/NUM_REQUESTS*100:.1f}%)")
    print(f"Fallos (Colapsos): {len(failures)}")
    print(f"Tiempo Total: {total_duration:.2f} segundos")
    print(f"Rendimiento: {(NUM_REQUESTS * 4) / total_duration:.1f} solicitudes/segundo")
    print(f"Latencia Promedio: {avg_latency:.2f} ms")
    print(f"Latencia Mínima: {min_latency:.2f} ms")
    print(f"Latencia Máxima: {max_latency:.2f} ms")
    print(f"Respuestas Comprimidas (GZip): {len(gzip_responses)} / {len(successes)}")
    
    if len(failures) == 0:
        print("\n[ÉXITO TOTAL] ¡La aplicación resistió la prueba de estrés sin colapsar ni registrar errores 500!")
    else:
        print(f"\n[ALERTA] Se detectaron {len(failures)} errores bajo carga.")

if __name__ == "__main__":
    run_stress_test()
