# FlowTrace

FlowTrace is a trace visualizer designed as a "post-mortem debugger": instead of pausing and resuming, it captures calls (inputs, outputs, caller, module, duration, errors) into a hierarchical JSON so you can inspect them later without re-running.

![FlowTrace overview](images/flowtrace.jpg)
![Call details panel](images/flowtrace_calls.jpg)

## Basic flow
1. Profile a script: `python flowtrace.py -s your_script.py -o flowtrace.json`
2. Generate the viewer: `python flowtrace_visual.py -i flowtrace.json -o flowtrace.html`
3. Open `flowtrace.html` and browse:
   - Search terms: opens the matching node in a floating panel.
   - Expand/collapse nodes; open calls.
   - Controls to show/hide badges, Python internals, language (es/en), and light/dark mode.

### Passing script arguments
- Any arguments unknown to `flowtrace.py` are forwarded to the profiled script (no `--` separator required).
- Example with options: `python flowtrace.py -s samples/basic/basic_sample.py --customer "ana maria" --tier gold --coffee 3`
- Example with positionals: `python flowtrace.py -s samples/basic/basic_positional_sample.py "juan perez" silver 1 2 0 0.18`

## Features
- Captures inputs/outputs, caller, module, duration, and errors.
- Groups instances and nested calls while preserving hierarchy.
- Search with highlighting and floating panels; option to hide Python internals.
- Dark mode by default, quick controls, and multi-language.

## Included examples
- `script.py` basic example.
- `complex_app.py` with modules `demo/...` (prices, taxes, discounts).
- `conc_demo.py` with CPU-bound (multiprocessing) and IO-bound (threads) to view concurrent traces.
- `basic_positional_sample.py` shows the same flow using positional arguments.
- `error_sample.py` intentionally fails (missing config) to show the error badge.

## Backlog / ideas
- Filters by module/class/time.
- Export filtered views.
- Integration with spans/telemetry.

---

FlowTrace es un visualizador de trazas de ejecucion, pensado como un "debugger post-mortem": en lugar de parar y reanudar, captura las llamadas (inputs, outputs, caller, modulo, duracion, errores) en un JSON jerarquico para inspeccionarlo despues sin reejecutar.

![Vista general de FlowTrace](images/flowtrace.jpg)
![Panel de detalle de llamadas](images/flowtrace_calls.jpg)

## Flujo basico
1. Perfilar un script: `python flowtrace.py -s tu_script.py -o flowtrace.json`
2. Generar visor: `python flowtrace_visual.py -i flowtrace.json -o flowtrace.html`
3. Abrir `flowtrace.html` y navegar:
   - Buscar trminos: abre el nodo coincidente en panel flotante.
   - Expandir/colapsar nodos; abrir calls.
   - Controles para mostrar/ocultar badges, internals de Python, idioma (es/en) y modo claro/oscuro.

### Pasar argumentos al script
- Cualquier argumento que `flowtrace.py` no reconoce se reenvia al script perfilado (no hace falta `--`).
- Ejemplo con opciones: `python flowtrace.py -s samples/basic/basic_sample.py --customer "ana maria" --tier gold --coffee 3`
- Ejemplo con posicionales: `python flowtrace.py -s samples/basic/basic_positional_sample.py "juan perez" silver 1 2 0 0.18`

## Caracteristicas
- Captura inputs/outputs, caller, modulo, duracion y errores.
- Agrupa instancias y llamadas anidadas preservando jerarquia.
- Buscador con resaltado y paneles flotantes; opcion para ocultar internals de Python.
- Modo oscuro por defecto, controles rapidos y multilenguaje.

## Ejemplos incluidos
- `script.py` ejemplo basico.
- `complex_app.py` con modulos `demo/...` (precios, impuestos, descuentos).
- `conc_demo.py` con CPU-bound (multiproceso) e IO-bound (hilos) para ver trazas concurrentes.
- `basic_positional_sample.py` muestra el mismo flujo usando argumentos posicionales.
- `error_sample.py` falla adrede (config faltante) para ver el badge de error.

## Pendientes / ideas
- Filtros por mdulo/clase/tiempo.
- Export de vistas filtradas.
- Integracin con spans/telemetra.

