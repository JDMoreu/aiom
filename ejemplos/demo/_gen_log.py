# -*- coding: utf-8 -*-
"""Genera servidor.log (log de errores de un servidor de aplicacion) - demo AIOM.

Causa raiz: el despliegue de la v2.14.0 de la madrugada anade una consulta sobre la
tabla `pedidos` que filtra por `estado` SIN indice -> full scan de 8-9 s por consulta ->
las conexiones del pool se quedan ocupadas hasta agotarlo (max=50) -> timeouts 504 y 502
en cascada -> el disco /var/log se llena por el volumen de errores. Se resuelve creando el
indice idx_pedidos_estado.

Escribe a un temporal unico y luego os.replace (el terminal lanza cada comando dos veces).
"""
import datetime
import os
import random
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
random.seed(20260314)

L = []


def D(h, m, s=0, ms=0):
    day = 13 if h >= 23 else 14
    return datetime.datetime(2026, 3, day, h, m, s, ms * 1000)


def add(ts, ms, lvl, th, msg):
    L.append((ts, "%s.%03d %-5s [%s] %s" % (ts.strftime("%Y-%m-%d %H:%M:%S"), ms, lvl, th, msg)))


EPS_OK = ["/api/v1/catalogo", "/api/v1/usuarios", "/api/v1/auth/login",
          "/api/v1/carrito", "/api/v1/pedidos", "/api/v1/reportes"]
EPS_PED = ["/api/v1/pedidos", "/api/v1/pedidos/{id}", "/api/v1/pedidos/resumen"]


def filler(t0, t1, n, th="http-1"):
    span = (t1 - t0).total_seconds()
    for i in range(n):
        ts = t0 + datetime.timedelta(seconds=span * i / max(n, 1))
        ms = random.randint(0, 999)
        ep = random.choice(EPS_OK)
        dur = random.randint(14, 190)
        add(ts, ms, "INFO", th, "GET %s 200 %dms user=%d" % (ep, dur, random.randint(1000, 9999)))


def filler_err(t0, t1, n, codes, th="http-2"):
    span = (t1 - t0).total_seconds()
    for i in range(n):
        ts = t0 + datetime.timedelta(seconds=span * i / max(n, 1))
        ms = random.randint(0, 999)
        ep = random.choice(EPS_PED)
        code = random.choice(codes)
        dur = random.randint(1000, 30000)
        lvl = "ERROR" if code in (500, 502, 504) else "WARN"
        add(ts, ms, lvl, th, "GET %s %d %dms user=%d" % (ep, code, dur, random.randint(1000, 9999)))


# ---------------------------------------------------------------- fase 0: normal
filler(D(23, 40), D(23, 57), 22)

# ---------------------------------------------------------------- fase 1: despliegue
add(D(23, 58, 2, 118), 118, "INFO", "deploy", "Iniciando despliegue de la version v2.14.0 (commit a1f9c3e)")
add(D(23, 58, 10, 55), 55, "INFO", "deploy", "Deteniendo instancia app-1 del balanceador...")
add(D(23, 58, 41, 640), 640, "INFO", "deploy", "Instancia app-1 detenida; drenando peticiones en curso")
add(D(23, 58, 43, 12), 12, "INFO", "deploy", "Desplegando artefacto v2.14.0 en app-1")
add(D(23, 59, 5, 803), 803, "INFO", "deploy", "v2.14.0 desplegada en app-1; arrancando proceso")
add(D(23, 59, 22, 41), 41, "INFO", "app-1", "Aplicacion iniciada (v2.14.0): pool_max=50, workers=8, jvm=4G")
add(D(0, 0, 4, 902), 902, "INFO", "deploy", "Desplegando artefacto v2.14.0 en app-2")
add(D(0, 0, 37, 611), 611, "INFO", "app-2", "Aplicacion iniciada (v2.14.0): pool_max=50, workers=8, jvm=4G")
add(D(0, 0, 38, 190), 190, "INFO", "deploy", "Despliegue v2.14.0 completado en 2 instancias en 02m36s")

# ---------------------------------------------------------------- fase 2: trafico normal tras el despliegue
filler(D(0, 1), D(0, 14), 30)

# ---------------------------------------------------------------- fase 3: primeras consultas lentas
add(D(0, 14, 22, 731), 731, "WARN", "db", "consulta lenta: SELECT * FROM pedidos WHERE estado = ? ORDER BY creado_en DESC -> 8213ms (umbral 1000ms)")
add(D(0, 15, 3, 40), 40, "WARN", "db", "consulta lenta: SELECT * FROM pedidos WHERE estado = ? ORDER BY creado_en DESC -> 8740ms (umbral 1000ms)")
add(D(0, 16, 55, 512), 512, "WARN", "db", "consulta lenta sobre tabla pedidos -> 9021ms; full scan sin indice (filas examinadas=4.180.233)")
add(D(0, 18, 12, 87), 87, "WARN", "db", "pool activo=21/50, en espera=0; latencia media 1.4s")
filler(D(0, 19), D(0, 28), 18)
add(D(0, 28, 44, 300), 300, "WARN", "db", "consulta lenta sobre tabla pedidos -> 9130ms; full scan sin indice")
add(D(0, 29, 9, 91), 91, "WARN", "db", "pool activo=34/50, en espera=3; latencia media 3.2s")
add(D(0, 31, 51, 640), 640, "WARN", "db", "consulta lenta sobre tabla pedidos -> 9418ms")
add(D(0, 33, 20, 12), 12, "WARN", "db", "pool activo=41/50, en espera=7; latencia media 5.6s")
add(D(0, 35, 2, 480), 480, "WARN", "http-3", "GET /api/v1/pedidos 200 12040ms user=4471 (respuesta muy lenta)")
add(D(0, 37, 44, 55), 55, "WARN", "db", "pool activo=47/50, en espera=11; latencia media 8.1s")
add(D(0, 39, 18, 733), 733, "WARN", "db", "consulta lenta sobre tabla pedidos -> 9802ms")
filler(D(0, 40), D(0, 41), 4)

# ---------------------------------------------------------------- fase 4: pool agotado + 504/502
add(D(0, 41, 7, 118), 118, "ERROR", "db", "POOL DE CONEXIONES AGOTADO: activo=50/50, en espera=12, tiempo medio de espera 30.000ms")
add(D(0, 41, 8, 240), 240, "ERROR", "http-3", "GET /api/v1/pedidos 504 Gateway Timeout tras 30000ms user=4471")
add(D(0, 41, 8, 903), 903, "ERROR", "http-3", "Exception in thread worker-3:")
add(D(0, 41, 8, 905), 905, "ERROR", "http-3", "java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30000ms.")
add(D(0, 41, 8, 906), 906, "ERROR", "http-3", "    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:213)")
add(D(0, 41, 8, 907), 907, "ERROR", "http-3", "    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:162)")
add(D(0, 41, 8, 908), 908, "ERROR", "http-3", "    at com.norte.app.dao.PedidoDAO.listar(PedidoDAO.java:88)")
add(D(0, 41, 8, 909), 909, "ERROR", "http-3", "    at com.norte.app.servicio.PedidoServicio.listar(PedidoServicio.java:41)")
add(D(0, 41, 8, 910), 910, "ERROR", "http-3", "    at com.norte.app.http.PedidoHandler.get(PedidoHandler.java:57)")
add(D(0, 41, 8, 911), 911, "ERROR", "http-3", "    ... 12 more")
add(D(0, 41, 8, 912), 912, "ERROR", "http-3", "Caused by: java.sql.SQLTimeoutException: Timeout after 30000ms of waiting for a connection.")
add(D(0, 41, 12, 4), 4, "WARN", "http-3", "reintento 1/3 de GET /api/v1/pedidos en 500ms")
add(D(0, 41, 43, 88), 88, "ERROR", "http-3", "GET /api/v1/pedidos 504 Gateway Timeout tras 30000ms (reintento 1 agotado)")
add(D(0, 42, 1, 33), 33, "WARN", "http-3", "reintento 2/3 de GET /api/v1/pedidos en 1000ms")
add(D(0, 42, 32, 51), 51, "ERROR", "http-3", "GET /api/v1/pedidos 504 Gateway Timeout (reintento 2 agotado); se devuelve 502 al cliente")
filler_err(D(0, 43), D(0, 55), 26, [504, 504, 502, 500])
add(D(0, 55, 12, 900), 900, "ERROR", "monitor", "tasa de error 5xx = 41% en la ventana de 5 min (umbral 5%)")
filler_err(D(0, 56), D(1, 5), 30, [504, 504, 504, 502])

# ---------------------------------------------------------------- fase 5: disco y pico de trafico
add(D(1, 5, 40, 210), 210, "WARN", "ops", "uso de disco en /var/log: 84% (umbral 80%)")
filler_err(D(1, 6), D(1, 20), 34, [504, 504, 502, 500])
add(D(1, 20, 33, 700), 700, "ERROR", "ops", "uso de disco en /var/log: 93%; la escritura de logs puede bloquearse")
filler_err(D(1, 21), D(1, 30), 28, [504, 504, 504, 502, 500])
add(D(1, 30, 2, 12), 12, "WARN", "monitor", "pico de trafico: 480 req/s (media habitual 120 req/s), coincide con la campana de la 1 a.m.")
filler_err(D(1, 31), D(1, 45), 32, [504, 504, 504, 502])
add(D(1, 45, 18, 44), 44, "ERROR", "http-1", "GET /api/v1/auth/login 200 210ms user=1188 (autenticacion NO afectada)")
filler_err(D(1, 46), D(2, 4), 34, [504, 504, 502, 504])
add(D(2, 4, 50, 8), 8, "FATAL", "ops", "disco casi lleno: 98% en /var/log; activando rotacion de emergencia")
add(D(2, 5, 3, 512), 512, "INFO", "ops", "rotacion de emergencia: servidor.log.1 comprimido (1.2 GB -> 180 MB)")
add(D(2, 6, 12, 91), 91, "INFO", "ops", "uso de disco en /var/log: 61% tras la rotacion")
add(D(2, 11, 7, 482), 482, "FATAL", "monitor", "umbral critico superado: 62% de peticiones con 5xx en la ventana de 5 min; incidente declarado")
add(D(2, 11, 8, 12), 12, "FATAL", "app-1", "worker-3 y worker-7 bloqueados esperando conexion a base de datos; saturacion del pool")
add(D(2, 11, 9, 300), 300, "FATAL", "app-2", "worker-2 bloqueado esperando conexion a base de datos; saturacion del pool")

# ---------------------------------------------------------------- fase 6: diagnostico y mitigacion
filler_err(D(2, 12), D(2, 38), 22, [504, 502, 504])
add(D(2, 40, 15, 640), 640, "INFO", "dba", "revisando las consultas lentas registradas sobre la tabla pedidos...")
add(D(2, 47, 2, 33), 33, "WARN", "dba", "la consulta de la v2.14.0 filtra por pedidos.estado SIN indice -> full scan de 4.1M filas")
add(D(2, 50, 11, 88), 88, "INFO", "dba", "creando indice idx_pedidos_estado sobre pedidos(estado, creado_en)...")
add(D(3, 1, 6, 402), 402, "INFO", "dba", "indice idx_pedidos_estado creado; tiempo de la consulta baja de 9.1s a 24ms")
add(D(3, 2, 30, 15), 15, "INFO", "ops", "reiniciando el pool de conexiones en app-1 y app-2...")
add(D(3, 5, 0, 900), 900, "INFO", "ops", "pool reiniciado: activo=6/50, en espera=0; latencia media normalizada")
add(D(3, 5, 30, 44), 44, "INFO", "monitor", "0 respuestas 504 en los ultimos 30s")

# ---------------------------------------------------------------- fase 7: cierre
add(D(3, 6, 11, 900), 900, "INFO", "monitor", "resumen del incidente: 12.480 peticiones atendidas, 3.216 fallidas (504=2.104, 502=812, 500=300)")
add(D(3, 6, 12, 10), 10, "INFO", "monitor", "ventana del incidente: 00:41 a 03:05 (2h24m); pool_max=50; causa raiz: consulta lenta sobre la tabla pedidos sin indice tras el despliegue v2.14.0")
add(D(3, 7, 0, 1), 1, "INFO", "monitor", "incidente CERRADO; se programa revision de pruebas de rendimiento para el despliegue")

# ---------------------------------------------------------------- escribir
L.sort(key=lambda x: x[0])
texto = "\n".join(linea for _, linea in L) + "\n"

ruta = os.path.join(AQUI, "servidor.log")
tmp = "%s.tmp%d" % (ruta, os.getpid())
with open(tmp, "w", encoding="utf-8", newline="\n") as f:
    f.write(texto)
for _ in range(40):
    try:
        os.replace(tmp, ruta)
        break
    except OSError:
        time.sleep(0.15)
else:
    os.replace(tmp, ruta)

print("servidor.log:", len(texto.splitlines()), "lineas")
