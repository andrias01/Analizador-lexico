# -*- coding: utf-8 -*-
"""
app.py — Interfaz web (Streamlit) del analizador léxico y sintáctico de Paisascript.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from chequeo_estructural import verificar_balance
from ejemplos import EJEMPLOS
from lexer import Lexer, TipoToken
from mapeo_gleam import equivalente, es_directo
from parser import Parser, ErrorSintactico, ErroresSintacticos

# --- IMPORTACIONES NUEVAS PARA ENTREGA 2 (LL1) ---
from tabla_ll1 import obtener_dataframe_tabla, obtener_dataframes_conjuntos
from parser_ll1 import analisis_predictivo_multi, NodoArbol

# --- IMPORTACIÓN DEL ASISTENTE DE IA ---
from ai_assistant import analizar_error_con_ia

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
    with c_slider:
        idx = st.slider("Ir al paso", 1, total, key=clave_slider) - 1

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
    ["1. Descendente Recursivo", "2. Predictivo LL(1) (Pila)"]
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
    st.caption("Por defecto se usa la clave segura del archivo `.env`.")
    api_key_manual = st.text_input(
        "Clave temporal (OpenAI)", 
        type="password", 
        help="Déjalo en blanco para usar la clave de tu entorno."
    )

# Si el usuario escribe algo, se usa; si no, se envía None y el backend lee el .env
api_key_activa = api_key_manual.strip() if api_key_manual else None

if not api_key_activa:
    st.sidebar.success("✅ Conectado mediante `.env`")
else:
    st.sidebar.warning("⚠️ Usando clave temporal manual")

# =============================================================================
#  CUERPO PRINCIPAL
# =============================================================================

st.title("Frontend Compilador Paisascript")

if not codigo.strip():
    st.info("Elija una cadena predefinida, escriba código o suba un archivo.")
    st.stop()

(tokens, errores, tabla, tabla_err, identificadores, chequeo, ast, error_sintactico,
 traza_ll1, errores_sint, pasos_arbol) = analizar(codigo, metodo_analisis)

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
    "Código segmentado",
    "Flujo de tokens",
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

# --- 1. Codigo segmentado ---------------------------------------------------
with pestañas[3]:
    st.subheader("El fuente dividido en tokens")
    st.markdown(html_leyenda(), unsafe_allow_html=True)
    st.markdown(html_codigo(codigo, tokens, errores), unsafe_allow_html=True)

# --- 2. Flujo de tokens -----------------------------------------------------
with pestañas[4]:
    st.subheader("Secuencia de tokens emitida")
    st.markdown(html_leyenda(), unsafe_allow_html=True)
    st.markdown(html_fichas(tokens), unsafe_allow_html=True)

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
