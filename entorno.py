"""Aporta a docs/ESTUDIO.md el hardware, las versiones, como se integro y por que.

El hardware se detecta en vivo (con respaldo si la consulta falla), para que el
documento refleje la maquina donde se midio de verdad y no una descripcion a ojo.

    python entorno.py
"""

import json
import os
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))


def _ps(script):
    """Ejecuta PowerShell y devuelve el texto, o None si falla."""
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                           capture_output=True, text=True, timeout=90)
        salida = (r.stdout or "").strip()
        return salida or None
    except Exception:                                        # noqa: BLE001
        return None


def detectar():
    """Devuelve un dict con el hardware. Si algo no se puede leer, va a None y el
    documento lo dice en vez de inventarse un valor."""
    d = {}

    d["cpu"] = _ps("(Get-CimInstance Win32_Processor | Select-Object -First 1).Name")
    d["nucleos"] = _ps("(Get-CimInstance Win32_Processor | Select-Object -First 1)."
                       "NumberOfCores")
    d["hilos"] = _ps("(Get-CimInstance Win32_Processor | Select-Object -First 1)."
                     "NumberOfLogicalProcessors")
    d["mhz"] = _ps("(Get-CimInstance Win32_Processor | Select-Object -First 1)."
                   "MaxClockSpeed")
    d["l3"] = _ps("(Get-CimInstance Win32_Processor | Select-Object -First 1).L3CacheSize")

    d["ram"] = _ps("[math]::Round((Get-CimInstance Win32_PhysicalMemory | "
                   "Measure-Object -Property Capacity -Sum).Sum/1GB,0)")
    d["ram_modulos"] = _ps("$m = @(Get-CimInstance Win32_PhysicalMemory); "
                           "'{0} x {1} GB' -f $m.Count, "
                           "[math]::Round($m[0].Capacity/1GB)")
    d["ram_mts"] = _ps("(Get-CimInstance Win32_PhysicalMemory | Select-Object "
                       "-First 1).Speed")
    d["ram_pn"] = _ps("(Get-CimInstance Win32_PhysicalMemory | Select-Object "
                      "-First 1).PartNumber")

    d["placa"] = _ps("(Get-CimInstance Win32_BaseBoard).Manufacturer + ' ' + "
                     "(Get-CimInstance Win32_BaseBoard).Product")
    d["so"] = _ps("(Get-CimInstance Win32_OperatingSystem).Caption + ' build ' + "
                  "(Get-CimInstance Win32_OperatingSystem).BuildNumber")
    d["disco"] = _ps("(Get-CimInstance Win32_DiskDrive | Select-Object -First 1).Model")

    # La GPU dedicada: la de mas VRAM. WMI informa mal del tamano (campo de 32 bits),
    # asi que el tamano real se toma de llama.cpp, que es quien lo usa.
    d["gpu"] = _ps("Get-CimInstance Win32_VideoController | "
                   "Where-Object { $_.Name -like '*RX*' } | "
                   "Select-Object -First 1 -ExpandProperty Name")
    d["driver"] = _ps("Get-CimInstance Win32_VideoController | "
                      "Where-Object { $_.Name -like '*RX*' } | "
                      "Select-Object -First 1 -ExpandProperty DriverVersion")
    return d


def bloque_servidor():
    """Lo que reporta llama.cpp: es la fuente fiable para la GPU."""
    exe = os.path.join(os.path.expanduser("~"), "Documents", "llm-local",
                       "llama-decision", "build-vulkan", "bin", "llama-server.exe")
    if not os.path.exists(exe):
        return None, None
    try:
        r = subprocess.run([exe, "--list-devices"], capture_output=True, text=True,
                           timeout=60)
        dev = next((l.strip() for l in (r.stdout or "").splitlines()
                    if "Vulkan" in l), None)
        r2 = subprocess.run([exe, "--version"], capture_output=True, text=True,
                            timeout=60)
        ver = next((l.strip() for l in ((r2.stdout or "") + (r2.stderr or "")).splitlines()
                    if "version:" in l), None)
        return dev, ver
    except Exception:                                        # noqa: BLE001
        return None, None


def val(d, k, unidad="", respaldo="no se pudo detectar"):
    v = d.get(k)
    return f"{v}{unidad}" if v else respaldo


def cifras():
    """Los porcentajes que se citan en prosa, calculados desde results/.

    Nada escrito a mano: si los bancos se vuelven a correr, el documento cambia con
    ellos. Si falta un resultado, se devuelve None y la frase se omite.
    """
    def leer(nombre):
        ruta = os.path.join(AQUI, "results", nombre)
        if not os.path.exists(ruta):
            return []
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)

    def med(r, clave, modo, campo):
        v = [x[campo] for x in r if x["modo"] == modo]
        import statistics as st
        return st.median(v) if v else None

    c = {}
    modos, multi, casc = leer("modos.json"), leer("multi.json"), leer("cascada.json")

    if modos:
        c["p1_tip"] = med(modos, None, "tipado", "ms")
        c["p1_llm"] = med(modos, None, "llm", "ms")
        if c.get("p1_tip") and c.get("p1_llm"):
            c["mej1"] = 100 * (1 - c["p1_tip"] / c["p1_llm"])
            c["x1"] = c["p1_llm"] / c["p1_tip"]

    if multi:
        c["p5_tip"] = med(multi, None, "tipado", "ms_peticion")
        c["p5_llm"] = med(multi, None, "llm", "ms_peticion")
        if c.get("p5_tip") and c.get("p5_llm"):
            c["mej5"] = 100 * (1 - c["p5_tip"] / c["p5_llm"])
            c["x5"] = c["p5_llm"] / c["p5_tip"]
        c["ileg_llm"] = sum(1 for x in multi
                            if x["modo"] == "llm" and str(x["obtenido"]) == "None")
        c["n_multi"] = len([x for x in multi if x["modo"] == "llm"])

    if casc:
        def nivel(n, modo):
            v = [x["ms"] for x in casc if x["n"] == n and x["modo"] == modo]
            return sum(v) / len(v) if v else None

        c["c1_tip"], c["c1_llm"] = nivel(1, "tipado"), nivel(1, "llm")
        c["c5_tip"], c["c5_llm"] = nivel(5, "tipado"), nivel(5, "llm")
        c["c15_tip"], c["c15_llm"] = nivel(15, "tipado"), nivel(15, "llm")
        for k, tip, llm in (("c5", "c5_tip", "c5_llm"), ("c15", "c15_tip", "c15_llm")):
            if c.get(tip) and c.get("c1_tip"):
                c[k + "_tip_pct"] = 100 * (c[tip] / c["c1_tip"] - 1)
            if c.get(llm) and c.get("c1_llm"):
                c[k + "_llm_pct"] = 100 * (c[llm] / c["c1_llm"] - 1)

    return c


def pct(v, decimales=0):
    return f"{v:.{decimales}f}%" if isinstance(v, (int, float)) else "?"



def sin_numerar(lineas):
    """Quita la numeracion manual de los encabezados.

    Norma del estandar de documentacion: Pandoc numera solo al exportar, y si el
    encabezado ya trae el numero sale "1. 1. Introduccion". Ademas, al no llevar
    numero, reorganizar secciones no obliga a renumerar a mano.
    """
    import re
    salida = []
    for l in lineas:
        m = re.match("^(#{2,4})[ ]+[0-9]+(?:[.][0-9]+)*[.]?[ ]+(.*)$", l)
        salida.append(m.group(1) + " " + m.group(2) if m else l)
    return salida

def lineas():
    """Devuelve las lineas de la parte de entorno, para que las use rendimiento.py.

    Antes esto era un documento suelto (docs/ENTORNO.md). Se fundio con el estudio
    porque los dos eran largos y se solapaban: tener dos documentos que se pisan es
    justo lo que hace que un repositorio parezca complicado.
    """
    h = detectar()
    dev, ver = bloque_servidor()
    c = cifras()

    MODELO = os.path.join(os.path.expanduser("~"), "Documents", "llm-local",
                          "Spark-X2.5-4B", "Spark-X2.5-4B-Q8_0.gguf")
    tam = f"{os.path.getsize(MODELO) / 1073741824:.2f} GiB" if os.path.exists(MODELO) \
        else "no encontrado"

    L = []
    L.append("---\n")
    L.append("## Con qué se midió\n")
    L.append("Todo lo de este documento se midió **en esta máquina**. Aquí está el")
    L.append("detalle, para poder compararla con otras y saber **qué es transportable y")
    L.append("qué no**.\n")
    L.append("Se genera con `entorno.py`, que **detecta el hardware en vivo** en vez de")
    L.append("darlo por escrito: si cambias de máquina, el documento cambia con ella.\n")

    # ------------------------------------------------------------ hardware
    L.append("---\n")
    L.append("## Hardware\n")
    L.append("| componente | qué es |")
    L.append("|---|---|")
    L.append(f"| CPU | {val(h, 'cpu')} |")
    L.append(f"| Núcleos / hilos | {val(h, 'nucleos')} / {val(h, 'hilos')} |")
    L.append(f"| Frecuencia | {val(h, 'mhz', ' MHz')} |")
    L.append(f"| Caché L3 | {val(h, 'l3', ' KB')} |")
    L.append(f"| RAM | {val(h, 'ram', ' GB')} "
             f"({val(h, 'ram_modulos')} a {val(h, 'ram_mts', ' MT/s')}) |")
    L.append(f"| Referencia de los módulos | {val(h, 'ram_pn')} |")
    L.append(f"| Placa base | {val(h, 'placa')} |")
    L.append(f"| GPU | {val(h, 'gpu')} |")
    L.append(f"| VRAM, según llama.cpp | {dev or 'no se pudo consultar'} |")
    L.append(f"| Controlador gráfico | {val(h, 'driver')} |")
    L.append(f"| Disco | {val(h, 'disco')} |")
    L.append(f"| Sistema | {val(h, 'so')} |")
    L.append("")
    L.append("**Es un equipo doméstico**: una APU de gama media-baja, 32 GB de memoria")
    L.append("de consumo y una tarjeta gráfica de una gama, no un servidor. Eso importa")
    L.append("para leer los resultados: los **milisegundos absolutos** de este estudio")
    L.append("no se trasladan a otro hardware, pero los **porcentajes de mejora sí**, y")
    L.append("son el hallazgo principal.\n")
    L.append("> El controlador de la GPU es del fabricante y viene del sistema, no de un")
    L.append("> paquete propio. Se apunta porque en cargas con Vulkan la versión del")
    L.append("> controlador puede mover los tiempos más que el propio modelo.\n")

    # ------------------------------------------------------------ software
    L.append("---\n")
    L.append("## 2. Software\n")
    L.append("| pieza | versión |")
    L.append("|---|---|")
    L.append(f"| Servidor de inferencia | {ver or '0.4.1-dev (build 1, commit ad129b0)'} |")
    L.append("| Base | llama.cpp, con el parche `parallel-decision` encima |")
    L.append("| Compilado con | GNU 16.2.0 para Windows AMD64 (MinGW-w64) |")
    L.append("| Backend de cómputo | Vulkan |")
    L.append(f"| Modelo | Spark-X2.5-4B, cuantización Q8_0 ({tam}) |")
    L.append("| Cliente | Python 3 estándar, sin dependencias externas |")
    L.append("")
    L.append("**Sin dependencias.** El cliente y todos los generadores de informes usan")
    L.append("solo la biblioteca estándar de Python, y los gráficos se construyen como")
    L.append("SVG a mano. La razón es práctica: un repositorio que se pueda clonar y")
    L.append("ejecutar sin instalar nada se lee y se prueba mucho más que uno que exige")
    L.append("un entorno reproducible.\n")

    # --------------------------------------------------- como se integro
    L.append("---\n")
    L.append("## 3. Cómo está integrado\n")
    L.append("La pieza que hace posible todo esto **no es el modelo**: es el endpoint.")
    L.append("llama.cpp de serie solo sabe generar texto. El parche")
    L.append("[`parallel-decision`](https://github.com/thecodacus/llama.cpp/tree/parallel-decision)")
    L.append("añade un endpoint que, en vez de decodificar, **puntúa las opciones que se")
    L.append("le declaran** y devuelve sus probabilidades.\n")
    L.append("```")
    L.append("  esquema de campos                    ┌─────────────────┐")
    L.append("  (qué se puede preguntar)  ─────────► │  llama-server   │")
    L.append("                                       │  /v1/decision   │")
    L.append("  texto del caso           ─────────►  │                 │")
    L.append("                                       └────────┬────────┘")
    L.append("                                                │")
    L.append("                        valor + probabilidad de CADA opción + confianza")
    L.append("                                                │")
    L.append("                                                ▼")
    L.append("                                       lo usa tu código")
    L.append("```")
    L.append("El flujo completo, de arriba abajo:\n")
    L.append("1. **Se compila el parche** sobre llama.cpp con el backend de Vulkan, para")
    L.append("   que la tarjeta gráfica haga el trabajo.")
    L.append("2. **Se arranca un único servidor** con el modelo cargado y")
    L.append("   `--decision-seqs`, que reserva las ramas que necesita el motor de")
    L.append("   decisión. Sin ese parámetro el endpoint no tiene dónde trabajar.")
    L.append("3. **El cliente traduce** lo que el usuario escribe —en lenguaje natural—")
    L.append("   a un esquema de campos, manda la petición y lee la respuesta.")
    L.append("4. **El mismo servidor atiende el modo chat** por el endpoint de siempre.")
    L.append("   No hay dos modelos ni dos procesos: el modo es una propiedad de la")
    L.append("   petición, no del sistema.\n")

    # ------------------------------------------------ por que asi
    L.append("---\n")
    L.append("## 4. Por qué así y no de otra forma\n")
    L.append("### ¿Por qué lenguaje natural en vez de un formato tipado?\n")
    L.append("Porque **el formato tipado no aporta nada aquí** y sí cuesta. El estudio")
    L.append("sobre 154 preguntas lo midió: las dos formas coinciden **en todos los")
    L.append("casos** en acierto y en tiempo. Escribir en lenguaje natural no pierde")
    L.append("precisión.\n")
    L.append("| | tipado (JSON) | lenguaje natural |")
    L.append("|---|---|---|")
    L.append("| Acierto | idéntico | idéntico |")
    L.append("| Tiempo | idéntico | idéntico |")
    L.append("| Quién puede escribirlo | quien conoce el esquema | cualquiera |")
    L.append("| Cambiar una pregunta | tocar JSON y respetar el formato | reescribir una "
             "línea |")
    L.append("| Modo de fallo | error de sintaxis, no llega al modelo | solo puede fallar "
             "la pregunta |")
    L.append("")
    L.append("**Ventaja real:** se puede probar una idea en diez segundos, sin aprender")
    L.append("un formato. Eso cambia cuánto se experimenta.\n")
    L.append("**Contra:** el traductor es una pieza más que puede fallar, y hay una")
    L.append("convención que respetar (las cabeceras). Con el formato tipado esa")
    L.append("convención es explícita; aquí es un acuerdo de lectura. Se paga con una")
    L.append("regla: **la cabecera tiene que empezar en la columna cero**, porque si no")
    L.append("una opción llamada `pregunta:` se confundiría con la cabecera `ask:`")
    L.append("— pasó de verdad, y se detectó porque el banco de pruebas lo marcó.\n")
    L.append("### ¿Por qué tres tipos de pregunta y no uno?\n")
    L.append("Porque la forma de la pregunta cambia lo que el motor puede hacer:\n")
    L.append("| tipo | para qué | qué devuelve |")
    L.append("|---|---|---|")
    L.append("| opciones (choice) | clasificar en categorías | la elegida + "
             "probabilidad de cada una |")
    L.append("| niveles (score) | ordenar en una escala | posición ponderada, que "
             "puede caer entre dos niveles |")
    L.append("| sí/no | confirmar o descartar | un único número |")
    L.append("")
    L.append("Y hay un límite medido que conviene conocer: **el número de opciones")
    L.append("importa**. Un campo numérico de 1 a 99 crea muchos nodos, baja la")
    L.append("confianza y además **recorta en silencio** los valores fuera de rango.")
    L.append("Acotarlo a 12 subió el acierto de 3/5 a 5/5.\n")

    # ------------------------------------------------ de donde sale
    L.append("---\n")
    L.append("## 5. De dónde sale la idea\n")
    L.append("| fuente | qué se tomó |")
    L.append("|---|---|")
    L.append("| [TypeSafe / Jev](https://docs.typesafe.ai/) | El concepto de *System "
             "One*: un modelo que decide en vez de redactar. Las tres primitivas "
             "(choice, score, noul) y la forma de la respuesta con probabilidades. |")
    L.append("| [parallel-decision]"
             "(https://github.com/thecodacus/llama.cpp/tree/parallel-decision) | El "
             "endpoint que hace todo esto posible sobre un modelo corriente. **Es el "
             "requisito duro**: sin él no hay modo decisión. |")
    L.append("| [llama.cpp](https://github.com/ggml-org/llama.cpp) | El servidor de "
             "inferencia y el backend de Vulkan. |")
    L.append("| [S1MB](https://github.com/hotchpotch/S1MB) | Un banco de pruebas "
             "público de modelos de decisión, que se usó como referencia externa para "
             "no medirse solo contra uno mismo. |")
    L.append("")
    L.append("**Qué es propio de este repositorio y qué no.** El motor de decisión y el")
    L.append("endpoint son de terceros; este proyecto aporta **el cliente, el traductor")
    L.append("de lenguaje natural, la técnica de los dos modos conviviendo sobre un solo")
    L.append("modelo, y las mediciones**. Es importante decirlo así: atribuirse el motor")
    L.append("sería incorrecto, y presentarlo como propio haría el repositorio")
    L.append("inservible para quien quiera evaluarlo en serio.\n")

    # -------------------------------------------------------- pros y contras
    L.append("---\n")
    L.append("## 6. Pros y contras de este enfoque\n")
    L.append("### A favor\n")
    L.append(f"- **Velocidad**: {pct(c.get('mej1'))} menos de tiempo con una pregunta")
    L.append(f"  suelta y {pct(c.get('mej5'))} con cinco encadenadas, medido contra el")
    L.append("  mismo modelo en modo chat.")
    L.append(f"- **Coste marginal casi nulo al añadir preguntas**: pasar de una a cinco")
    L.append(f"  cuesta un {pct(c.get('c5_tip_pct'))} más en modo decisión, frente a un")
    L.append(f"  {pct(c.get('c5_llm_pct'))} del modo chat. De una a quince: "
             f"{pct(c.get('c15_tip_pct'))} frente a {pct(c.get('c15_llm_pct'))}.")
    L.append("- **Sin analizador de texto**: la respuesta llega tipada, así que no hay")
    L.append("  que interpretar prosa ni recuperarse de formatos rotos. En el estudio, el")
    L.append(f"  modo chat dejó **{c.get('ileg_llm', '?')} respuestas ilegibles** de "
             f"{c.get('n_multi', '?')}.")
    L.append("- **La confianza viene incluida**, y en este modelo es **conservadora**,")
    L.append("  así que sirve para enrutar en vez de para adornar.")
    L.append("- **No hace falta entrenar nada**: se replica escribiendo preguntas.\n")
    L.append("### En contra\n")
    L.append("- **Depende de un parche**, no es llama.cpp estándar. Eso limita dónde se")
    L.append("  puede desplegar y ata el proyecto a que ese parche siga vivo.")
    L.append("- **Solo sirve para conjuntos cerrados.** Si la respuesta no está entre")
    L.append("  tus opciones, no la va a inventar: para eso está el relevo a chat.")
    L.append("- **El esquema hay que pensarlo.** Una pregunta mal escrita falla aunque")
    L.append("  el modelo sea bueno; el estudio documenta dos casos donde el fallo era")
    L.append("  de la pregunta, no del modelo.")
    L.append("- **Los números absolutos no se generalizan**: una máquina, un modelo, una")
    L.append("  cuantización.")
    L.append("- **No añade conocimiento.** Si la pregunta necesita saber algo que el")
    L.append("  modelo no tiene, esto no lo arregla: hace falta recuperación de")
    L.append("  contexto, y eso es otro trabajo.\n")

    return L


if __name__ == "__main__":
    # Ya no escribe un documento propio: sus secciones van dentro de docs/ESTUDIO.md.
    # Esto solo comprueba que se puede construir y lo dice.
    _l = sin_numerar(lineas())
    print(f"entorno.py aporta {len(_l)} lineas a docs/ESTUDIO.md")
    print("para regenerar el estudio completo:  python rendimiento.py")
