# Créditos y procedencia

Este repositorio **no inventa la pieza que lo hace posible**. Lo que aporta es la
técnica, el cliente y la comparación. Aquí está, pieza por pieza, de quién es cada cosa
y con qué licencia.

## Lo que hace posible todo: llama.cpp y el endpoint de decisión

**llama.cpp** es el servidor de inferencia. De serie **solo sabe generar texto**; no
tiene forma de pedirle una decisión.

| | |
|---|---|
| **Qué es** | El motor de inferencia y el backend de Vulkan. |
| **Origen** | <https://github.com/ggml-org/llama.cpp> |
| **Autoría** | The ggml authors |
| **Licencia** | MIT — «Copyright (c) 2023-2026 The ggml authors» |

**parallel-decision** es el añadido que trae el endpoint `/v1/decision`. **Sin él no hay
modo decisión**: es el requisito duro del proyecto.

| | |
|---|---|
| **Qué es** | El endpoint que puntúa las opciones en vez de generar texto. |
| **Origen** | <https://github.com/thecodacus/llama.cpp>, rama `parallel-decision` |
| **Autoría** | [thecodacus](https://github.com/thecodacus) |
| **Licencia** | MIT (hereda la de llama.cpp) |

### La copia que se usó aquí

No basta con decir «el fork»: para poder reproducirlo hace falta el commit exacto.

```
origen : https://github.com/thecodacus/llama.cpp.git
rama   : parallel-decision
commit : ad129b08d9f134cd298d1f8a85efc52b1b66e18e
fecha  : 2026-09-25
título : perf(parallel-decision): score hybrid-model branches in one pass
```

Esa copia está en `C:\Users\JDMoreu\Documents\llm-local\llama-decision` **solo en esta
máquina**: el binario compilado no se versiona, porque pesa 60 MB y se regenera. Para
reconstruirlo hace falta compilarlo. Los pasos, con los dos obstáculos que aparecieron
(el backend de Vulkan y la versión de GCC), están en
[`docs/ARRANCAR.md`](docs/ARRANCAR.md):

```bash
git clone -b parallel-decision https://github.com/thecodacus/llama.cpp llama-decision
cd llama-decision
cmake -B build-vulkan -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF \
      -DCMAKE_C_FLAGS="-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00" \
      -DCMAKE_CXX_FLAGS="-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00"
cmake --build build-vulkan -j
```

Versión que reporta el binario que se midió: `0.4.1-dev (build 1, commit ad129b0)`,
compilado con GNU 16.2.0 para Windows AMD64.

## El modelo

| | |
|---|---|
| **Nombre** | Spark-X2.5-4B |
| **Autor original** | **XHToken** |
| **Página del modelo** | <https://huggingface.co/XHToken/Spark-X2.5-4B> |
| **Proyecto oficial** | <https://github.com/XHToken/Spark-X2.5> |
| **Licencia** | **Apache 2.0** |

**El fichero que se usó aquí es una conversión a GGUF hecha por un tercero**, no por
XHToken. La conversión se identifica por su tamaño exacto:

```
fichero  : Spark-X2.5-4B-Q8_0.gguf
tamaño   : 4 375 021 152 bytes (4,38 GB)
sha256   : 5c2c3c190e4337e1016b8593ca8e26e8b18c972200b107385d4ec61a25d9dea2
origen   : end000/Spark-X2.5-4B-Q8_0-GGUF  (coincidencia exacta de tamaño)
```

> **Aviso honesto:** existen **al menos cinco conversiones distintas** de este modelo a
> Q8_0 (de `end000`, `sizzlebop`, `stornic56`, `abenzerps` y `miifanboy`), y **todas
> pesan casi lo mismo pero no son el mismo fichero**: cambian en unos cientos de bytes
> de metadatos. Por eso aquí se deja el **SHA256**, que es lo único que identifica el
> fichero de verdad. Si descargas otro Q8_0 y los números no te salen igual, puede ser
> eso.

## De dónde sale la idea

| | |
|---|---|
| **TypeSafe / Jev** | El concepto de *System One* (un modelo que decide en vez de redactar) y las tres primitivas: choice, score y noul. <https://docs.typesafe.ai/> |
| **FastAPI y uvicorn** | Lo que sirve la API y la interfaz. Es la única dependencia del repositorio, y es de `api.py`, no del proyecto. <https://fastapi.tiangolo.com/> |

## Lo que es de este repositorio

Para que no haya duda de qué se está leyendo:

**No es de este repositorio:** el motor de inferencia, el endpoint de decisión y el
modelo. Todo eso es de terceros y está acreditado arriba.

**Sí es de este repositorio:**

- El cliente y el **traductor de lenguaje natural** (`preguntar.py`), que deduce el
  tipo de pregunta por la cabecera sin obligar a escribir JSON.
- La técnica de tener **los dos modos sobre un solo modelo y un solo proceso**.
- La **comparación en vivo** de las dos vías, con sus peticiones, su tiempo y sus tokens.
- El diagrama de arquitectura.

## Licencia del repositorio

MIT — ver [`LICENSE`](LICENSE). Cubre **lo propio** de este repositorio. Las piezas de
terceros mantienen su licencia (MIT para llama.cpp y parallel-decision, Apache 2.0 para
el modelo), y este repositorio **no incluye sus binarios ni sus pesos**, solo los
referencia.
