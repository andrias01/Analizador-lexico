# -*- coding: utf-8 -*-
"""
app.py — Interfaz web (Streamlit) del analizador léxico y sintáctico de Paisascript.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from chequeo_estructural import verificar_balance
from ejemplos import EJEMPLOS
from lexer import Lexer, TipoToken
from mapeo_gleam import equivalente, es_directo
from parser import Parser, ErrorSintactico, ErroresSintacticos

# --- IMPORTACIONES NUEVAS PARA ENTREGA 2 (LL1) ---
from tabla_ll1 import obtener_dataframe_tabla, obtener_dataframes_conjuntos, GRAMATICA_BNF
from parser_ll1 import analisis_predictivo_multi, NodoArbol
from tabla_lalr import generar_datos_lalr1
from parser_lalr import generar_parser_lalr1

# Importador condicional para el generador LALR(1) completo
try:
    from generador_lalr1_completo import generar_tabla_lalr1_completa
    USO_COMPLETO = True
except ImportError:
    USO_COMPLETO = False

# `post_procesar_lalr1` es opcional: si el módulo no lo expone seguimos sin él.
try:
    from generador_lalr1_completo import post_procesar_lalr1
except ImportError:
    post_procesar_lalr1 = None

# Pasos que se despliegan por defecto en el "Detalle por paso" de la traza
# LALR(1). La traza completa puede tener miles de pasos (el driver ya no tiene
# tope fijo) y un expander por paso saturaría Streamlit, así que se muestra una
# ventana navegable; la tabla y el CSV de arriba siempre llevan la traza entera.
N_PASOS_DETALLE = 30

# --- IMPORTACIÓN DEL ASISTENTE DE IA ---
from ai_assistant import analizar_error_con_ia, origen_api_key

RAIZ = Path(__file__).parent

# Soporte para entrada en vivo
try:
    from componente_entrada_viva import area_texto_viva

    _ENTRADA_VIVA_DISPONIBLE = True
except Exception:
    _ENTRADA_VIVA_DISPONIBLE = False

# Soporte condicional para Árbol Gráfico (Graphviz)
try:
    from arbol_grafico import generar_grafo_ast, capturar_arbol_ascii

    _ARBOL_GRAFICO_DISPONIBLE = True
except ImportError:
    _ARBOL_GRAFICO_DISPONIBLE = False

# =============================================================================
#  CONFIGURACION Y ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Paisascript — Frontend Compilador",
    page_icon="🪕",
    layout="wide",
)

COLORES = {
    "RESERVADA": "#c678dd",
    "TIPO": "#56b6c2",
    "OPERADOR": "#e5c07b",
    "LITERAL": "#98c379",
    "IDENTIFICADOR": "#61afef",
    "PUNTUACION": "#8b93a1",
    "FIN": "#5c6370",
}
FONDO = "#282c34"
TENUE = "#5c6370"
ROJO = "#e06c75"

st.markdown(f"""
<style>
  .lienzo {{
      background: {FONDO};
      border-radius: 8px;
      padding: 16px 18px;
      overflow-x: auto;
      font-family: "Cascadia Code", "Consolas", "SF Mono", monospace;
      font-size: 13.5px;
      line-height: 1.65;
  }}
  .lienzo pre {{ margin: 0; color: {TENUE}; white-space: pre; }}
  .num {{ color: {TENUE}; user-select: none; }}
  .err {{
      background: {ROJO}; color: {FONDO};
      font-weight: 700; border-radius: 3px; padding: 0 2px;
  }}
  .ficha {{
      display: inline-block; margin: 3px 4px 3px 0;
      border-radius: 6px; overflow: hidden;
      font-family: "Cascadia Code", "Consolas", monospace; font-size: 12px;
      border: 1px solid rgba(255,255,255,.12);
  }}
  .ficha .lex {{ padding: 3px 8px; font-weight: 700; }}
  .ficha .tip {{ padding: 3px 8px; background: rgba(0,0,0,.28); font-size: 11px; }}
  .leyenda span {{
      display: inline-block; margin-right: 14px;
      font-size: 12px; font-weight: 700;
  }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
#  ADAPTADOR AST (LL1 a JSON)
# =============================================================================

def nodo_a_dict(nodo: NodoArbol) -> dict:
    """Convierte los objetos NodoArbol del LL1 al formato dict/JSON para el gráfico."""
    if not nodo: return {}
    d = {"name": nodo.valor, "type": nodo.tipo}
    if nodo.hijos:
        d["children"] = [nodo_a_dict(h) for h in nodo.hijos]
    return d


def snapshot_a_grafo(nodo: dict) -> dict:
    """
    Convierte un nodo de los pasos del árbol (formato {'tipo','es_terminal','hijos'},
    el mismo que usan ambos parsers) al esquema {'name','type','children'} que
    espera generar_grafo_ast/capturar_arbol_ascii (el mismo que produce
    nodo_a_dict a partir de un NodoArbol).
    """
    if not nodo:
        return {}
    d = {"name": nodo.get("tipo", ""),
         "type": "terminal" if nodo.get("es_terminal") else "no_terminal"}
    hijos = nodo.get("hijos") or []
    if hijos:
        d["children"] = [snapshot_a_grafo(h) for h in hijos]
    return d


# =============================================================================
#  ÁRBOL PASO A PASO (Siguiente / Anterior)
# =============================================================================

def renderizar_stepper_arbol(pasos: list[dict], key_prefix: str) -> None:
    """
    Muestra los pasos de construcción del árbol: primero el diagrama a todo
    lo ancho, y debajo los controles (Anterior/Siguiente y una barra para
    saltar directo a un paso), sincronizados entre sí. `pasos` es una lista
    de dicts {"Paso","Acción","Pila","Entrada","Arbol"}; la vienen
    produciendo tanto Parser.parse_con_pasos() (método recursivo) como
    analisis_predictivo_multi() (método LL(1)).
    """
    total = len(pasos)
    if total == 0:
        st.info("No hay pasos para mostrar.")
        return

    clave_idx = f"paso_idx_{key_prefix}"
    clave_slider = f"paso_slider_{key_prefix}"
    clave_firma = f"paso_firma_{key_prefix}"

    # Si cambió el código/método (y por lo tanto la cantidad de pasos), se
    # vuelve al primer paso para no quedar apuntando a un índice viejo.
    firma = f"{key_prefix}:{total}"
    if st.session_state.get(clave_firma) != firma:
        st.session_state[clave_firma] = firma
        st.session_state[clave_idx] = 0
        st.session_state[clave_slider] = 1

    if clave_idx not in st.session_state:
        st.session_state[clave_idx] = 0
    if clave_slider not in st.session_state:
        st.session_state[clave_slider] = st.session_state[clave_idx] + 1

    idx = min(st.session_state[clave_idx], total - 1)

    # El diagrama debe verse ARRIBA de los controles, pero para dibujar el
    # paso correcto (sin quedar un clic atrasado) hay que leer primero los
    # botones/la barra, que están más abajo en el código. Se resuelve con un
    # contenedor: reserva el espacio de arriba y se rellena al final, ya con
    # el índice definitivo.
    zona_grafico = st.container()

    # --- Controles, debajo del diagrama ---
    c_prev, c_slider, c_next = st.columns([1, 3, 1])
    with c_prev:
        if st.button("◀ Anterior", key=f"btn_prev_{key_prefix}",
                     disabled=(idx <= 0), use_container_width=True):
            idx = max(0, idx - 1)
            st.session_state[clave_idx] = idx
            st.session_state[clave_slider] = idx + 1
    with c_next:
        if st.button("Siguiente ▶", key=f"btn_next_{key_prefix}",
                     disabled=(idx >= total - 1), use_container_width=True):
            idx = min(total - 1, idx + 1)
            st.session_state[clave_idx] = idx
            st.session_state[clave_slider] = idx + 1
    # Slider para navegar por pasos - solo si hay más de un paso
    if total > 1:
        with c_slider:
            idx = st.slider("Ir al paso", 1, total, key=clave_slider) - 1
    else:
        # Cuando solo hay un paso, idx se fija en 0 directamente
        idx = 0

    st.session_state[clave_idx] = idx
    paso = pasos[idx]

    with zona_grafico:
        arbol_paso = paso.get("Arbol")
        if arbol_paso is None:
            st.info("El árbol de este paso ya no se grabó (programa demasiado largo).")
        elif _ARBOL_GRAFICO_DISPONIBLE:
            grafo_dict = snapshot_a_grafo(arbol_paso)
            try:
                st.graphviz_chart(generar_grafo_ast(grafo_dict), use_container_width=False)
            except Exception:
                st.warning("No se pudo renderizar el gráfico vectorial. Mostrando respaldo ASCII:")
                st.code(capturar_arbol_ascii(grafo_dict), language=None)
        else:
            st.info("Módulo gráfico no disponible.")

    st.caption(f"Paso **{idx + 1} / {total}** — {paso['Acción']}")
    with st.expander("Ver pila y entrada restante en este paso"):
        st.code(f"Pila:    {paso['Pila']}\nEntrada: {paso['Entrada']}", language=None)


# =============================================================================
#  ERRORES SINTÁCTICOS (uno o varios)
# =============================================================================

def texto_errores(lista: list[str]) -> str:
    """Une los errores sintácticos en un solo texto (numerado si hay varios)."""
    if len(lista) <= 1:
        return lista[0] if lista else ""
    return "\n".join(f"{i}. {m}" for i, m in enumerate(lista, start=1))


def _md(texto: str) -> str:
    """Escapa caracteres que Streamlit interpretaría como Markdown/LaTeX ($, *, _...)."""
    for ch in ("\\", "*", "_", "`", "$"):
        texto = texto.replace(ch, "\\" + ch)
    return texto


def mostrar_lista_errores(lista: list[str]) -> None:
    """Un recuadro por error (numerados cuando hay más de uno)."""
    if len(lista) == 1:
        st.error(_md(lista[0]))
    else:
        for i, msg in enumerate(lista, start=1):
            st.error(f"**{i}.** {_md(msg)}")


def mostrar_errores_sintacticos(lista: list[str], titulo_uno: str, titulo_varios: str) -> None:
    """Muestra un título y luego todos los errores sintácticos encontrados."""
    if not lista:
        return
    if len(lista) == 1:
        st.error(f"{titulo_uno}: {_md(lista[0])}")
    else:
        st.error(f"{titulo_varios} ({len(lista)}):")
        mostrar_lista_errores(lista)


# =============================================================================
#  ANALISIS  (cacheado: reanaliza cuando cambia el texto o el método)
# =============================================================================

@st.cache_data(show_spinner=False)
def analizar(codigo: str, metodo: str):
    # FASE 1: Análisis Léxico
    lexer = Lexer(codigo)
    tokens = lexer.tokenizar()
    utiles = [t for t in tokens if t.tipo is not TipoToken.FIN_ARCHIVO]

    filas = [
        {
            "#": i,
            "Lexema": t.lexema,
            "TokenType": t.tipo.name,
            "Categoría": t.categoria,
            "Fila": t.fila,
            "Columna": t.columna,
            "Valor": "" if t.valor is None else str(t.valor),
            "Gleam": equivalente(t.tipo),
            "Directo": "sí" if es_directo(t.tipo) else "reestructura",
        }
        for i, t in enumerate(utiles, start=1)
    ]

    errores = [
        {"#": i, "Fila": e.fila, "Columna": e.columna,
         "Lexema": e.lexema, "Causa": e.mensaje}
        for i, e in enumerate(lexer.errores, start=1)
    ]

    chequeo = verificar_balance(utiles)

    # FASE 2: Análisis Sintáctico (Según método seleccionado)
    ast = None
    errores_sint: list[str] = []  # TODOS los errores sintácticos encontrados
    traza_ll1 = []
    pasos_arbol: list[dict] = []  # pasos {"Paso","Acción","Pila","Entrada","Arbol"}
    # para el navegador paso a paso del árbol

    if "Recursivo" in metodo:
        try:
            parser = Parser(tokens)
            ast, pasos_arbol, errores_sint = parser.parse_con_pasos()
        except Exception as e:
            ast = None
            pasos_arbol = []
            errores_sint = [f"Error interno en el Parser Recursivo: {str(e)}"]
    elif "LALR(1)" in metodo:
        try:
            from generador_lalr1_completo import generar_tabla_lalr1_completa as gen_lalr
            from parser_lalr import generar_parser_lalr1
            from tabla_ll1 import GRAMATICA_BNF
            
            resultado_lalr = gen_lalr()
            
            # POST-PROCESAMIENTO: Corregir acciones de shift en el estado 0
            # para tokens críticos (KW_LECTURA, KW_IMPRESION, etc.) que pueden
            # perderse durante la fusión LALR(1)
            if post_procesar_lalr1 is not None:
                resultado_lalr = post_procesar_lalr1(resultado_lalr)
            
            parser = generar_parser_lalr1(resultado_lalr)
            
            if parser is None:
                raise ValueError("No se pudo generar el parser LALR(1)")
            
            # Ejecutar análisis
            ast, traza_lalr, es_valido, errores_lalr = parser.parse_con_pasos(tokens)
            
            # Formatear traza para el streamlit
            traza_ll1 = []
            for paso in traza_lalr:
                traza_ll1.append({
                    'Paso': paso['Paso'],
                    'Acción': paso['Acción'],
                    'Pila': paso['Pila'],
                    'Estados': paso.get('Estados'),
                    'Entrada': paso['Entrada'],
                    'Arbol': paso.get('Arbol')
                })
            
            errores_sint = errores_lalr
            pasos_arbol = traza_lalr  # Ya traen la estructura correcta
        except Exception as e:
            ast = None
            traza_ll1 = []
            pasos_arbol = []
            errores_sint = [f"Error en el análisis LALR(1): {str(e)}"]
    else:
        try:
            traza, raiz_nodo, es_valido, lista_err = analisis_predictivo_multi(tokens)
            traza_ll1 = traza
            pasos_arbol = traza  # cada fila de la traza ya trae la clave "Arbol"
            ast = nodo_a_dict(raiz_nodo)
            if not es_valido:
                errores_sint = list(lista_err)
        except Exception as e:
            errores_sint = [f"Error interno en el Parser Predictivo: {str(e)}"]

    # Texto único (numerado) para la IA y para saber si el parser falló
    error_sintactico = texto_errores(errores_sint) or None

    return (utiles, lexer.errores, pd.DataFrame(filas), pd.DataFrame(errores),
            lexer.resumen_identificadores(), chequeo, ast, error_sintactico, traza_ll1,
            errores_sint, pasos_arbol)


# =============================================================================
#  VISTAS HTML
# =============================================================================

def html_codigo(codigo: str, tokens, errores) -> str:
    marcas: dict[int, list] = {}
    for t in tokens:
        marcas.setdefault(t.fila, []).append(
            (t.columna, t.lexema, COLORES.get(t.categoria, "#fff"), False)
        )
    for e in errores:
        marcas.setdefault(e.fila, []).append((e.columna, e.lexema, None, True))

    ancho = len(str(max(1, codigo.count("\n") + 1)))
    salida = []
    for i, linea in enumerate(codigo.split("\n"), start=1):
        partes = [f'<span class="num">{i:>{ancho}} │ </span>']
        cursor = 0
        for columna, lexema, color, es_error in sorted(marcas.get(i, [])):
            inicio = columna - 1
            if inicio < cursor:
                continue
            partes.append(html.escape(linea[cursor:inicio]))
            texto = html.escape(linea[inicio:inicio + len(lexema)])
            if es_error:
                partes.append(f'<span class="err">{texto}</span>')
            else:
                partes.append(f'<span style="color:{color}">{texto}</span>')
            cursor = inicio + len(lexema)
        partes.append(html.escape(linea[cursor:]))
        salida.append("".join(partes))

    return f'<div class="lienzo"><pre>{chr(10).join(salida)}</pre></div>'


def html_leyenda() -> str:
    piezas = [f'<span style="color:{c}">{n}</span>' for n, c in COLORES.items()
              if n != "FIN"]
    piezas.append(f'<span class="err">ERROR</span>')
    return f'<div class="leyenda">{"".join(piezas)}</div>'


def html_fichas(tokens) -> str:
    fichas = []
    for t in tokens:
        color = COLORES.get(t.categoria, "#fff")
        lexema = html.escape(t.lexema) or "&nbsp;"
        fichas.append(
            f'<span class="ficha" style="background:{FONDO}">'
            f'<span class="lex" style="color:{color}">{lexema}</span>'
            f'<span class="tip" style="color:{color}">{t.tipo.name}</span>'
            f'</span>'
        )
    return f'<div class="lienzo" style="line-height:2.2">{"".join(fichas)}</div>'


def html_error(codigo: str, e) -> str:
    lineas = codigo.split("\n")
    texto = lineas[e.fila - 1] if 1 <= e.fila <= len(lineas) else ""
    cursor = " " * (e.columna - 1) + "^" * max(1, len(e.lexema))
    return (
        f'<div class="lienzo"><pre>'
        f'<span class="num">{e.fila:>3} │ </span>{html.escape(texto)}\n'
        f'<span class="num">    │ </span>'
        f'<span style="color:{ROJO};font-weight:700">{html.escape(cursor)}</span>'
        f'</pre></div>'
    )


# =============================================================================
#  BARRA LATERAL — ENTRADA Y CONFIGURACIÓN DE IA
# =============================================================================

st.sidebar.title("🪕 Paisascript")
st.sidebar.caption("Frontend: Análisis Léxico y Sintáctico")

# --- SELECCION DE METODO ---
metodo_analisis = st.sidebar.radio(
    "1. Método de Análisis Sintáctico",
    ["1. Descendente Recursivo", "2. Predictivo LL(1) (Pila)", "3. Ascendente LALR(1)"]
)
st.sidebar.divider()

modo = st.sidebar.radio(
    "2. Modo de ingreso de la cadena",
    ["Cadena predefinida", "Cadena libre", "Archivo .paisa"],
)

codigo = ""
titulo_fuente = ""

if modo == "Cadena predefinida":
    nombres = [n for n, _, _ in EJEMPLOS]
    elegido = st.sidebar.selectbox("Programa", nombres, index=0)
    idx = nombres.index(elegido)
    st.sidebar.info(EJEMPLOS[idx][1])
    codigo = EJEMPLOS[idx][2]
    titulo_fuente = elegido

elif modo == "Cadena libre":
    if "codigo_libre" not in st.session_state:
        st.session_state.codigo_libre = (
            'pille_pues numerito x = 10 % 3 ** 2\n'
            'hable_pues("El resultado es: " <> x)'
        )

    en_vivo = _ENTRADA_VIVA_DISPONIBLE and st.sidebar.toggle(
        "⚡ Analizar en vivo (beta)",
        value=False,
    )

    if en_vivo:
        st.session_state.codigo_libre = area_texto_viva(
            st.session_state.codigo_libre, altura=260, key="area_viva",
        )
    else:
        st.session_state.codigo_libre = st.sidebar.text_area(
            "Escriba su código Paisascript",
            value=st.session_state.codigo_libre,
            height=260,
            key="area_clasica",
        )
        st.sidebar.button("🔎 Analizar ahora", use_container_width=True)

    codigo = st.session_state.codigo_libre
    titulo_fuente = "cadena digitada"

else:
    subido = st.sidebar.file_uploader("Archivo de código", type=["paisa", "txt"])
    if subido is not None:
        codigo = subido.getvalue().decode("utf-8", errors="replace")
        titulo_fuente = subido.name
    else:
        st.sidebar.warning("Suba un archivo para analizar.")

st.sidebar.divider()

# --- CONFIGURACIÓN DEL ASISTENTE DE IA ---
st.sidebar.subheader("🤖 Asistente de IA")

with st.sidebar.expander("⚙️ Configuración de API (Opcional)"):
    st.caption("Por defecto se usa la clave de los Secrets o del archivo `.env`.")
    api_key_manual = st.text_input(
        "Clave temporal (OpenAI)",
        type="password",
        help="Déjalo en blanco para usar la clave configurada en el despliegue."
    )

# Si el usuario escribe algo, se usa; si no, se envía None y el backend la
# busca primero en st.secrets y luego en las variables de entorno / .env
api_key_activa = api_key_manual.strip() if api_key_manual else None

if api_key_activa:
    st.sidebar.warning("⚠️ Usando clave temporal manual")
else:
    origen = origen_api_key()
    if origen == "secrets":
        st.sidebar.success("✅ Conectado mediante Secrets")
    elif origen == "entorno":
        st.sidebar.success("✅ Conectado mediante `.env`")
    else:
        st.sidebar.error(
            "❌ Sin clave configurada. Defina `OPENAI_API_KEY` en los Secrets "
            "de la app (o en `.env` si trabaja en local), o escriba una clave "
            "temporal arriba."
        )

# =============================================================================
#  CUERPO PRINCIPAL
# =============================================================================

st.title("Frontend Compilador Paisascript")

if not codigo.strip():
    st.info("Elija una cadena predefinida, escriba código o suba un archivo.")
    st.stop()

(tokens, errores, tabla, tabla_err, identificadores, chequeo, ast, error_sintactico,
 traza_ll1, errores_sint, pasos_arbol) = analizar(codigo, metodo_analisis)

# Para el método Ascendente LALR(1), generamos tokens vía léxico
# ya que analizar() está diseñado para LL(1)
if metodo_analisis == "3. Ascendente LALR(1)":
    lexer = Lexer(codigo)
    tokens = lexer.tokenizar()
    errores = lexer.errores
    utiles = [t for t in tokens if t.tipo is not TipoToken.FIN_ARCHIVO]
    tabla = pd.DataFrame({
        "#": list(range(1, len(utiles) + 1)),
        "Lexema": [t.lexema for t in utiles],
        "TokenType": [t.tipo.name for t in utiles],
        "Categoría": [t.categoria for t in utiles],
        "Fila": [t.fila for t in utiles],
        "Columna": [t.columna for t in utiles],
        "Valor": ["" if t.valor is None else str(t.valor) for t in utiles],
        "Gleam": [equivalente(t.tipo) for t in utiles],
        "Directo": ["sí" if es_directo(t.tipo) else "reestructura" for t in utiles]
    })
else:
    # Para los otros métodos, los datos vienen de analizar()
    pass  # tokens, errores, tabla ya fueron asignados por analizar()

# Generar datos LALR(1) si se seleccionó el método ascendente
if metodo_analisis == "3. Ascendente LALR(1)":
    if USO_COMPLETO:
        # Usar el generador LALR(1) completo
        result = generar_tabla_lalr1_completa()
        import pandas as pd
        
        EPS = "ε" # (cadena vacía para el análisis sintáctico)
        # Crear DataFrames desde el resultado completo
        primeros_data = result["primeros"]
        siguientes_data = result["siguientes"]
        
        # DataFrame de FIRSTs
        primeros_list = [
            {"No Terminal": nt, "PRIMERO": "{ " + ", ".join(sorted(list(primeros_data[nt] - {EPS}))) + " }"}
            for nt in result["primeros"].keys()
        ]
        primeros_df = pd.DataFrame(primeros_list).set_index("No Terminal")
        
        # DataFrame de SIGUIENTEs
        siguientes_list = [
            {"No Terminal": nt, "SIGUIENTE": "{ " + ", ".join(s for s in siguientes_data[nt]) + " }"}
            for nt in result["siguientes"].keys()
        ]
        siguientes_df = pd.DataFrame(siguientes_list).set_index("No Terminal")
        
        # Tablas ACTION / GOTO REALES de LALR(1): filas = ESTADOS (0..n-1),
        # columnas = terminales (ACTION) y no-terminales (GOTO).
        # Es la tabla que realmente usa el parser ascendente y la que exige
        # el Quiz 3 (ACTION[state][token] = s_i / r_j / acc).
        from parser_lalr import construir_dataframes_lalr1
        lalr_tablas = construir_dataframes_lalr1(result)
        action_df = lalr_tablas["action_df"]
        goto_df = lalr_tablas["goto_df"]
        producciones_lalr = lalr_tablas["producciones"]
        parser_lalr_instance = lalr_tablas["parser"]
        
        metadata = {
            "estados_lr1": result["metadata"]["estados_lr1"],
            "estados_lalr": result["metadata"]["estados_lalr"],
            "estados_reduzidos": result["metadata"]["estados_reduzidos"],
            "conflictos": 0,
            "nota": f"Tabla LALR(1) generada con {result['metadata']['reduction_percentage']}% de reducción de estados",
            "goto_total_entries": result["metadata"]["goto_total_entries"],
        }
    else:
        # Versión simplificada (original)
        datos_lalr = generar_datos_lalr1()
        action_df = datos_lalr["action"]
        goto_df = datos_lalr["goto"]
        primeros_df = datos_lalr["primeros"]
        siguientes_df = datos_lalr["siguientes"]
        metadata = datos_lalr["metadata"]
        producciones_lalr = []
        parser_lalr_instance = None
else:
    # Para los otros métodos, estas variables no son necesarias
    # pero las definimos como DataFrame/vacío por si alguien las consulta
    action_df = pd.DataFrame()
    goto_df = pd.DataFrame()
    df_primeros = pd.DataFrame()
    df_siguientes = pd.DataFrame()
    metadata = {"conflictos": 0, "nota": "Análisis LALR(1) no seleccionado"}
    producciones_lalr = []
    parser_lalr_instance = None

# --- Metricas ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tokens Validos", len(tokens))
c2.metric("Errores Léxicos", len(errores), delta=None if not errores else f"{len(errores)} fallos",
          delta_color="inverse")
c3.metric("Líneas", codigo.count("\n") + 1)
estado_parser = "Exitoso" if not error_sintactico else "Fallido"
n_err_sint = len(errores_sint)
c4.metric("Parser", estado_parser,
          delta=None if not n_err_sint else f"{n_err_sint} {'error' if n_err_sint == 1 else 'errores'}",
          delta_color="inverse")

with st.expander("Ver / editar el código fuente", expanded=False):
    st.code(codigo, language=None)

# Pestañas de la aplicación
pestañas = st.tabs([
    "Árbol Sintáctico (AST)",
    "Traza de Pila LL(1)",
    "Tablas LL(1) / Conjuntos",
    "Traza LALR(1)",
    "Tabla ACTION/GOTO",
    "Tabla de símbolos",
    "Errores y verificación",
    "Resumen",
    "Traducción a Gleam",
    "Código del analizador",
    "Referencia",
])

# --- Pestaña: Árbol Sintáctico (AST) ---
with pestañas[0]:
    st.subheader(f"Árbol de Análisis Sintáctico — {metodo_analisis}")

    if error_sintactico:
        mostrar_errores_sintacticos(
            errores_sint,
            "No se pudo completar el AST debido a un error de sintaxis",
            "No se pudo completar el AST debido a errores de sintaxis",
        )

        # Botón integrado de IA en caso de error sintáctico
        st.divider()
        st.markdown("### ✨ Asistente de IA para Corrección")
        if st.button("🤖 Analizar error sintáctico con Inteligencia Artificial", key="btn_ia_ast"):
            with st.spinner("El asistente de IA está analizando tu código y el fallo..."):
                detalle_fallo = f"Errores sintácticos en el Parser ({len(errores_sint)}):\n{error_sintactico}"
                sugerencia = analizar_error_con_ia(codigo, detalle_fallo, api_key=api_key_activa)
                st.markdown(sugerencia)

        if pasos_arbol:
            st.divider()
            st.markdown("#### Cómo se armó el árbol hasta el error")
            renderizar_stepper_arbol(pasos_arbol, key_prefix=f"ast_{metodo_analisis}")

    elif ast:
        st.success("Análisis sintáctico completado con éxito.")
        renderizar_stepper_arbol(pasos_arbol, key_prefix=f"ast_{metodo_analisis}")
        with st.expander("Ver JSON completo del árbol final"):
            st.json(ast)

# --- PESTAÑA: Traza de Pila LL(1) ---
with pestañas[1]:
    st.subheader("Algoritmo de Pila Predictivo")
    if "Predictivo" not in metodo_analisis:
        st.info("Debe seleccionar el Método 2 (Predictivo LL1) en la barra lateral para ver la traza.")
    else:
        if traza_ll1:
            df_traza = pd.DataFrame(traza_ll1)[["Paso", "Pila", "Entrada", "Acción"]]
            st.dataframe(df_traza, use_container_width=True, hide_index=True)
            if error_sintactico:
                mostrar_errores_sintacticos(
                    errores_sint,
                    "Error detectado durante el análisis de pila",
                    "Errores detectados durante el análisis de pila",
                )
        else:
            st.warning("No se generó traza de pila.")

# --- PESTAÑA: Tablas LL(1) y Conjuntos ---
with pestañas[2]:
    st.subheader("Motor Predictivo: Conjuntos y Matriz M[A,a]")

    df_conjuntos = obtener_dataframes_conjuntos()
    df_tabla_M = obtener_dataframe_tabla()

    st.markdown("#### Conjuntos PRIMERO y SIGUIENTE")
    st.dataframe(df_conjuntos, use_container_width=True)

    st.markdown("#### Tabla de Análisis Sintáctico M[A, a]")
    st.dataframe(df_tabla_M, use_container_width=True)

# --- 1. Traza LALR(1) -------------------------------------------------------
with pestañas[3]:
    st.subheader("Traza Ascendente LALR(1)")
    if metodo_analisis != "3. Ascendente LALR(1)":
        st.info("Seleccione \"3. Ascendente LALR(1)\" en la barra lateral para ver la traza.")
    else:
        # Mostrar traza si está disponible
        if traza_ll1 and len(traza_ll1) > 0:
            if error_sintactico:
                st.warning(
                    "Análisis LALR(1) **finalizado con errores** — se muestra la traza "
                    "hasta el paso en que se produjo el fallo."
                )
            else:
                st.success("Análisis LALR(1) completado con éxito")

            # --- Formato legible para la traza paso a paso ------------------
            # Tokens cuyo lexema aporta información (identificadores, números y
            # cadenas); para el resto el nombre del tipo ya dice todo.
            _LEXEMAS_INFORMATIVOS = {"IDENTIFICADOR", "NUM_ENTERO",
                                     "NUM_REAL", "CADENA_LITERAL"}

            def _fmt_simbolo(s):
                """Símbolo de la pila: 'IDENTIFICADOR(x)', 'NUM_ENTERO(42)' o '<tipo>'."""
                if hasattr(s, 'tipo') and hasattr(s.tipo, 'name'):
                    lex = getattr(s, 'lexema', '') or ''
                    if s.tipo.name in _LEXEMAS_INFORMATIVOS and lex:
                        return f"{s.tipo.name}({lex})"
                    return s.tipo.name
                return str(s)

            def _fmt_token(e):
                """Token de la entrada restante: 'NUM_ENTERO(42)' o '$'."""
                if isinstance(e, str):
                    return e
                if hasattr(e, 'tipo') and hasattr(e.tipo, 'name'):
                    lex = getattr(e, 'lexema', '') or ''
                    if e.tipo.name in _LEXEMAS_INFORMATIVOS and lex:
                        return f"{e.tipo.name}({lex})"
                    return e.tipo.name
                if hasattr(e, 'name'):
                    return e.name
                return str(e)

            filas_traza = []
            for paso_tr in traza_ll1:
                pila_tr = paso_tr.get('Pila', []) or []
                estados_tr = paso_tr.get('Estados')
                if estados_tr and len(estados_tr) == len(pila_tr):
                    pila_txt = " ".join(
                        f"{_fmt_simbolo(s)}·{est}"
                        for s, est in zip(pila_tr, estados_tr))
                else:
                    pila_txt = " ".join(_fmt_simbolo(s) for s in pila_tr)
                filas_traza.append({
                    'Paso': paso_tr['Paso'],
                    'Pila (símbolo·estado)': pila_txt,
                    'Entrada restante': " ".join(
                        _fmt_token(e) for e in (paso_tr.get('Entrada') or [])),
                    'Acción': paso_tr['Acción'],
                })
            df_traza = pd.DataFrame(filas_traza)
            st.dataframe(df_traza, use_container_width=True, hide_index=True)
            st.caption(
                r"La pila se lee de abajo hacia arriba como `símbolo·estado`; el estado junto a un "
                r"símbolo es el alcanzado al consumirlo. **El último estado de un paso es el tope "
                r"con el que se consulta ACTION\[estado\]\[token\] en el paso siguiente.**"
            )
            st.download_button(
                "⬇️ Descargar traza completa (CSV)",
                data=df_traza.to_csv().encode("utf-8"),
                file_name="traza_LALR1.csv",
                mime="text/csv",
                key="dl_traza",
            )
            
            # --- Detalle por paso: ventana navegable sobre la traza --------
            # Las trazas largas pueden tener miles de pasos (el driver ya no
            # tiene tope fijo) y un expander por paso saturaría Streamlit, así
            # que se despliega una ventana seleccionable. La tabla y el CSV de
            # arriba siempre tienen la traza completa.
            st.markdown("### Detalle por paso")
            total_pasos = len(traza_ll1)
            clave_ventana = "traza_lalr_ventana"
            clave_firma_traza = "traza_lalr_firma"

            # Si cambió el código (y por lo tanto la cantidad de pasos), se
            # descarta la ventana guardada para no quedar apuntando fuera de
            # rango. Es el mismo criterio que usa renderizar_stepper_arbol.
            firma_traza = f"lalr:{total_pasos}"
            if st.session_state.get(clave_firma_traza) != firma_traza:
                st.session_state[clave_firma_traza] = firma_traza
                st.session_state.pop(clave_ventana, None)

            if total_pasos > N_PASOS_DETALLE:
                tope = min(N_PASOS_DETALLE, total_pasos)
                rango = st.slider(
                    "Rango de pasos a detallar", 1, total_pasos,
                    (1, tope), key=clave_ventana)
                ventana = traza_ll1[rango[0] - 1:rango[1]]
                st.caption(
                    f"Mostrando {len(ventana)} de {total_pasos} pasos "
                    f"(pasos {rango[0]}–{rango[1]}). La tabla y el CSV de "
                    f"arriba tienen la traza completa."
                )
            else:
                ventana = traza_ll1

            for paso in ventana:
                with st.expander(f"Paso {paso['Paso']}: {paso['Acción']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        # Convert Token objects to strings for display
                        pila_display = []
                        estados_paso = paso.get('Estados') or []
                        for idx_item, item in enumerate(paso['Pila']):
                            txt = _fmt_simbolo(item)
                            if idx_item < len(estados_paso):
                                txt = f"{txt} · {estados_paso[idx_item]}"
                            pila_display.append(txt)
                        st.write("**Pila (símbolo·estado):**", ', '.join(pila_display) if pila_display else '---')
                        if estados_paso:
                            st.write("**Estado tope (se usa en ACTION):**", estados_paso[-1])
                        if paso.get('Arbol'):
                            st.write("**Árbol:**", paso['Arbol']['tipo'])
                    with col2:
                        st.write("**Entrada:**",
                                 ' '.join(_fmt_token(t) for t in paso['Entrada']) if paso['Entrada'] else '---')
                        # Mostrar información de la acción
                        accion = paso['Acción']
                        if 'reduce' in accion.lower():
                            # Extraer número de producción
                            match = re.search(r'reduce (\d+)', accion)
                            if match:
                                prod_num = match.group(1)
                                st.write(f"**Producción:** {prod_num}")
                        elif 'shift' in accion.lower():
                            match = re.search(r'shift a estado (\d+)', accion)
                            if match:
                                st.write(f"**Estado destino:** {match.group(1)}")
                        elif 'accept' in accion.lower():
                            st.write(f"**Resultado:** Cadena válida aceptada")
            
            # Ya no mostramos tablas ACTION/GOTO aquí (están en la pestaña 4)
            st.markdown("### ℹ️ Nota: Las tablas ACTION y GOTO completas se muestran en la pestaña \"Tablas ACTION y GOTO LALR(1)\" (Tab 4)")
            
            # Mostrar metadatos
            st.markdown("### Metadatos del análisis")
            st.json(metadata)
            
            if error_sintactico:
                st.error(f"Errores: {error_sintactico}")
        else:
            st.info("Ejecute un análisis LALR(1) para ver la traza paso a paso")
        
        st.markdown("### Conjuntos FIRST")
        st.dataframe(primeros_df, use_container_width=True)
        st.markdown("### Conjuntos FOLLOW")
        st.dataframe(siguientes_df, use_container_width=True)

# --- 2. Tabla ACTION/GOTO ---------------------------------------------------
with pestañas[4]:
    st.subheader("Tablas ACTION y GOTO LALR(1)")
    if metodo_analisis != "3. Ascendente LALR(1)":
        st.info("Seleccione \"3. Ascendente LALR(1)\" en la barra lateral para ver las tablas.")
    else:
        if action_df.empty or goto_df.empty:
            st.warning("No se pudieron construir las tablas LALR(1).")
        else:
            def _contar(pref):
                return sum(1 for v in action_df.to_numpy().ravel()
                           if isinstance(v, str) and v.startswith(pref))

            n_est = action_df.shape[0]
            n_term = action_df.shape[1]
            n_nt = goto_df.shape[1]
            n_shift, n_reduce, n_acc = _contar("s"), _contar("r"), _contar("acc")

            st.success(
                f"**Tabla LALR(1) generada sin conflictos** — "
                f"{n_est} estados · ACTION: {n_est}×{n_term} · GOTO: {n_est}×{n_nt} · "
                f"{n_shift} shift, {n_reduce} reduce, {n_acc} accept"
            )

            if error_sintactico:
                st.info(
                    "La tabla ACTION/GOTO es válida y completa; el mensaje siguiente "
                    f"corresponde al programa de entrada, no a la tabla: {error_sintactico}"
                )

            with st.expander("📖 Cómo leer la tabla (notación LR)"):
                st.markdown(
                    "- **`s{n}`** → *shift*: empuja el token y pasa al estado `n`.\n"
                    "- **`r{k}`** → *reduce*: reduce con la producción `k` "
                    "(ver leyenda de producciones más abajo).\n"
                    "- **`acc`** → *accept*: la cadena fue reconocida completa.\n"
                    "- **celda vacía** → *error*: acción no definida para ese par "
                    "(estado, token); el análisis se rechaza.\n"
                    "- **GOTO**: fila = estado, columna = no-terminal, celda = estado destino "
                    "tras realizar la reducción."
                )

            # --- Tabla ACTION completa -------------------------------------
            st.markdown(f"### Tabla ACTION completa ({n_est} estados × {n_term} terminales)")
            st.dataframe(action_df, use_container_width=True, height=460)
            st.download_button(
                "⬇️ Descargar tabla ACTION (CSV)",
                data=action_df.to_csv().encode("utf-8"),
                file_name="tabla_ACTION_LALR1.csv",
                mime="text/csv",
                key="dl_action",
            )

            # --- Leyenda de producciones -----------------------------------
            if producciones_lalr:
                st.markdown("### Leyenda de producciones (número `k` de `r{k}`)")
                df_prods = pd.DataFrame(
                    [{"k": i + 1,
                      "No-terminal": nt,
                      "Producción": " ".join(sym for sym in prod) if prod else "ε"}
                     for i, (nt, prod) in enumerate(producciones_lalr)]
                ).set_index("k")
                st.dataframe(df_prods, use_container_width=True, height=320)

            # --- Tabla GOTO completa ---------------------------------------
            st.markdown(f"### Tabla GOTO completa ({n_est} estados × {n_nt} no-terminales)")
            st.dataframe(goto_df, use_container_width=True, height=460)
            st.download_button(
                "⬇️ Descargar tabla GOTO (CSV)",
                data=goto_df.to_csv().encode("utf-8"),
                file_name="tabla_GOTO_LALR1.csv",
                mime="text/csv",
                key="dl_goto",
            )

            # --- Inspector de un estado (para la sustentación) --------------
            if parser_lalr_instance is not None:
                st.markdown("### 🔎 Inspector de estado (ayuda para la sustentación)")
                estado_sel = st.selectbox(
                    "Estado", list(action_df.index), index=0, key="insp_estado"
                )
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**ACTION**")
                    acciones = {t: a for t, a in parser_lalr_instance
                                .action_table.get(estado_sel, {}).items()}
                    if acciones:
                        st.dataframe(
                            pd.DataFrame({"Terminal": acciones.keys(),
                                          "Acción": acciones.values()}).set_index("Terminal"),
                            use_container_width=True, height=300)
                    else:
                        st.caption("Sin acciones definidas (estado de error).")
                with col_b:
                    st.markdown("**GOTO**")
                    gotos = {nt: s for nt, mapa in parser_lalr_instance.goto_table.items()
                             if (s := mapa.get(estado_sel)) is not None}
                    if gotos:
                        st.dataframe(
                            pd.DataFrame({"No-terminal": gotos.keys(),
                                          "Estado destino": gotos.values()}).set_index("No-terminal"),
                            use_container_width=True, height=300)
                    else:
                        st.caption("Sin transiciones GOTO desde este estado.")

                items = parser_lalr_instance.lalr_states_items[estado_sel]
                with st.expander(f"Items LALR(1) del estado {estado_sel} ({len(items)} items)"):
                    filas = []
                    for nt, rhs, dot, la in sorted(items):
                        antes = " ".join(rhs[:dot])
                        despues = " ".join(rhs[dot:])
                        punto = f"{antes} • {despues}".strip()
                        filas.append({"Producción": f"{nt} → {' '.join(rhs) if rhs else 'ε'}",
                                      "Con punto": punto,
                                      "Lookahead": la})
                    st.dataframe(pd.DataFrame(filas), use_container_width=True, height=360)

# --- 3. Tabla de simbolos ---------------------------------------------------
with pestañas[5]:
    st.subheader("Tabla de símbolos léxicos")
    cats = sorted(tabla["Categoría"].unique()) if not tabla.empty else []
    filtro = st.multiselect("Filtrar por categoría", cats, default=cats)
    vista = tabla[tabla["Categoría"].isin(filtro)] if filtro else tabla

    st.dataframe(
        vista[["#", "Lexema", "TokenType", "Categoría", "Fila", "Columna", "Valor"]],
        use_container_width=True, hide_index=True, height=460,
    )

# --- 4. Errores y Asistente IA ----------------------------------------------
with pestañas[6]:
    st.subheader("Reporte de errores léxicos y sintácticos")

    tiene_problemas = bool(errores) or bool(error_sintactico)

    if not tiene_problemas:
        st.success("¡Todo melo! No se encontró ningún error léxico ni sintáctico en esta entrada.")
    else:
        if errores:
            st.markdown("#### ❌ Errores Léxicos")
            st.dataframe(tabla_err, use_container_width=True, hide_index=True)
            st.divider()
            for e in errores:
                st.markdown(f"**Error en fila {e.fila}, columna {e.columna}** — {e.mensaje}")
                st.markdown(html_error(codigo, e), unsafe_allow_html=True)

        if errores_sint:
            st.markdown("#### ❌ Error Sintáctico" if len(errores_sint) == 1
                        else f"#### ❌ Errores Sintácticos ({len(errores_sint)})")
            mostrar_lista_errores(errores_sint)

        st.divider()
        st.markdown("### 🤖 Diagnóstico y Sugerencia con Inteligencia Artificial")
        st.markdown(
            "Deja que la IA examine el código fuente completo y los errores detectados para darte una solución guiada:")

        if st.button("✨ Consultar sugerencias de IA para estos errores", key="btn_ia_errores"):
            with st.spinner("Analizando con el modelo de lenguaje..."):
                resumen_fallos = f"Errores léxicos: {len(errores)}. Errores sintácticos ({len(errores_sint)}):\n{error_sintactico}"
                sugerencia_ia = analizar_error_con_ia(codigo, resumen_fallos, api_key=api_key_activa)
                st.markdown(sugerencia_ia)

# --- 5. Resumen -------------------------------------------------------------
with pestañas[7]:
    st.subheader("Distribución de tokens por categoría")
    conteo = (tabla["Categoría"].value_counts().rename_axis("Categoría")
              .reset_index(name="Tokens"))
    izq, der = st.columns([2, 1])
    izq.bar_chart(conteo.set_index("Categoría"), height=340)
    der.dataframe(conteo, use_container_width=True, hide_index=True)

# --- 6. Traduccion a Gleam --------------------------------------------------
with pestañas[8]:
    st.subheader("En qué se convierte cada token")
    st.dataframe(
        tabla[["#", "Lexema", "TokenType", "Gleam", "Directo"]],
        use_container_width=True, hide_index=True, height=420,
    )

# --- 7. Codigo del analizador ----------------------------------------------
with pestañas[9]:
    st.subheader("El analizador léxico y sintáctico, en Python puro")
    st.caption("Fragmentos leídos en vivo de los módulos core.")

    _fuente_lexer = (RAIZ / "lexer.py").read_text(encoding="utf-8") if (RAIZ / "lexer.py").exists() else "No encontrado"

    with st.expander("Ver lexer.py completo"):
        st.code(_fuente_lexer, language="python")

# --- 8. Referencia ----------------------------------------------------------
with pestañas[10]:
    st.subheader("Documentación del lenguaje")
    doc = st.radio("Documento", ["Gramática BNF", "Mapeo a Gleam", "README"], horizontal=True)
    archivo = {"Gramática BNF": "gramatica_BNF_Paisascript.txt",
               "Mapeo a Gleam": "MAPEO_GLEAM.md",
               "README": "README.md"}[doc]
    ruta = RAIZ / archivo
    if ruta.exists():
        texto = ruta.read_text(encoding="utf-8")
        if archivo.endswith(".md"):
            st.markdown(texto)
        else:
            st.text(texto)
    else:
        st.error(f"No se encontró {archivo} junto a app.py.")
