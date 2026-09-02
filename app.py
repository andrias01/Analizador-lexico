# -*- coding: utf-8 -*-
"""
app.py — Interfaz web (Streamlit) del analizador lexico de Paisascript.

Es la SEGUNDA interfaz construida sobre el mismo `lexer.py`, sin modificar
una sola linea de el. Esa es la demostracion practica del requisito 15 del
enunciado: la logica del analizador esta encapsulada en un modulo
independiente y reutilizable.

    consola  ->  main.py  --.
                             >--  lexer.py  (sin cambios)
    web      ->  app.py   --'

Ejecutar:  streamlit run app.py
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

RAIZ = Path(__file__).parent

# El cuadro "en vivo" es un componente HTML/JS propio (ver
# componente_entrada_viva.py); si algo en el entorno impide cargarlo, la app
# sigue funcionando con el st.text_area clásico, sin romperse.
try:
    from componente_entrada_viva import area_texto_viva
    _ENTRADA_VIVA_DISPONIBLE = True
except Exception:
    _ENTRADA_VIVA_DISPONIBLE = False


# =============================================================================
#  CONFIGURACION Y ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Paisascript — Analizador Léxico",
    page_icon="🪕",
    layout="wide",
)

# Paleta fija sobre fondo oscuro: no depende del tema claro/oscuro que el
# usuario tenga configurado en Streamlit, asi que los colores por categoria
# se ven igual en la sustentacion sin importar la maquina.
COLORES = {
    "RESERVADA":     "#c678dd",
    "TIPO":          "#56b6c2",
    "OPERADOR":      "#e5c07b",
    "LITERAL":       "#98c379",
    "IDENTIFICADOR": "#61afef",
    "PUNTUACION":    "#8b93a1",
    "FIN":           "#5c6370",
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
#  ANALISIS  (cacheado: solo se reanaliza cuando cambia el texto)
# =============================================================================

@st.cache_data(show_spinner=False)
def analizar(codigo: str):
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
    return (utiles, lexer.errores, pd.DataFrame(filas), pd.DataFrame(errores),
            lexer.resumen_identificadores(), chequeo)


# =============================================================================
#  VISTA 1 — CODIGO RESALTADO
# =============================================================================

def html_codigo(codigo: str, tokens, errores) -> str:
    """Reimprime el fuente pintando cada lexema segun su categoria.

    Las posiciones se reconstruyen a partir de (fila, columna) de cada token:
    es la prueba visual de que el lexer sabe exactamente donde empieza y
    termina cada pieza del texto.
    """
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


# =============================================================================
#  VISTA 2 — FLUJO DE TOKENS
# =============================================================================

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


# =============================================================================
#  VISTA 5 — ERRORES CON CURSOR
# =============================================================================

def extraer_fragmento(fuente: str, inicio: str, fin: str) -> str:
    """Recorta `fuente` entre dos marcadores (ambos incluidos).

    Se usa para mostrar fragmentos REALES de lexer.py en la pestaña de
    código: se leen del archivo en vez de transcribirlos a mano, así el
    ejemplo nunca se desincroniza del código que de verdad se ejecuta.
    """
    i = fuente.index(inicio)
    j = fuente.index(fin, i) + len(fin)
    return fuente[i:j]


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
#  BARRA LATERAL — ENTRADA
# =============================================================================

st.sidebar.title("🪕 Paisascript")
st.sidebar.caption("Analizador léxico · destino **Gleam**")
st.sidebar.divider()

modo = st.sidebar.radio(
    "Modo de ingreso de la cadena",
    ["Cadena predefinida", "Cadena libre", "Archivo .paisa"],
    help="Requisito 11 del enunciado: digitación libre o selección de una "
         "lista de cadenas predefinidas.",
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
        "⚡ Analizar en vivo (beta, cada tecla)",
        value=False,
        help="Experimental: manda el texto a analizar con cada tecla, sin "
             "esperar Ctrl+Enter ni a que salga del cuadro. Es un "
             "componente propio, no viene con Streamlit — si en su "
             "navegador no reacciona, desactive esto y use el cuadro "
             "clásico de abajo.",
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
        st.sidebar.button("🔎 Analizar ahora", width="stretch")
        st.sidebar.caption(
            "No hace falta Ctrl+Enter: al hacer clic en cualquier otro "
            "lugar (este botón, una pestaña) ya se vuelve a analizar."
        )

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
st.sidebar.caption(
    "`app.py` y `main.py` usan el **mismo** `lexer.py`, sin modificarlo. "
    "Esa independencia es el requisito 15 del enunciado."
)


# =============================================================================
#  CUERPO
# =============================================================================

st.title("Analizador léxico de Paisascript")

if not codigo.strip():
    st.info("Elija una cadena predefinida, escriba código o suba un archivo.")
    st.stop()

tokens, errores, tabla, tabla_err, identificadores, chequeo = analizar(codigo)

# --- Metricas ---------------------------------------------------------------
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Tokens", len(tokens))
c2.metric("Errores léxicos", len(errores),
          delta=None if not errores else f"{len(errores)} sin abortar",
          delta_color="inverse")
c3.metric("Avisos estructurales", len(chequeo),
          delta=None if not chequeo else "bloques sin cerrar",
          delta_color="inverse")
c4.metric("Líneas", codigo.count("\n") + 1)
c5.metric("Identificadores", len(identificadores))
c6.metric("Reservadas",
          sum(1 for t in tokens if t.categoria in ("RESERVADA", "TIPO")))

if errores:
    st.warning(
        f"Se detectaron **{len(errores)} error(es) léxico(s)**. "
        "El análisis **no se detuvo**: los tokens siguientes se reconocieron "
        "igual (requisito 14)."
    )
else:
    st.success(
        "Sin errores léxicos: todo carácter de la entrada forma parte de un "
        "token válido. *(Esto no revisa la gramática ni los tipos — ver más "
        "abajo y la pestaña «Errores y verificación».)*"
    )

if chequeo:
    st.warning(
        f"Además, el chequeo estructural encontró **{len(chequeo)} bloque(s) "
        "sin cerrar bien** (ver pestaña «Errores y verificación»). Esto es "
        "un aviso adicional, no reemplaza al analizador sintáctico completo "
        "del proyecto."
    )

with st.expander("Ver / editar el código fuente", expanded=False):
    st.code(codigo, language=None)

pestañas = st.tabs([
    "Código segmentado",
    "Flujo de tokens",
    "Tabla de símbolos",
    "Errores y verificación",
    "Resumen",
    "Traducción a Gleam",
    "Código del analizador",
    "Referencia",
])

# --- 1. Codigo segmentado ---------------------------------------------------
with pestañas[0]:
    st.subheader("El fuente dividido en tokens")
    st.markdown(html_leyenda(), unsafe_allow_html=True)
    st.markdown(html_codigo(codigo, tokens, errores), unsafe_allow_html=True)
    st.caption(
        "Cada lexema se pinta según su categoría. Las posiciones se "
        "reconstruyen con la fila y la columna que el lexer guardó en cada "
        "token, no con un resaltador aparte."
    )

# --- 2. Flujo de tokens -----------------------------------------------------
with pestañas[1]:
    st.subheader("Secuencia de tokens emitida")
    st.markdown(html_leyenda(), unsafe_allow_html=True)
    st.markdown(html_fichas(tokens), unsafe_allow_html=True)
    st.caption("Esta es exactamente la lista que consumirá el analizador "
               "sintáctico descendente recursivo del proyecto.")

# --- 3. Tabla de simbolos ---------------------------------------------------
with pestañas[2]:
    st.subheader("Tabla de símbolos léxicos")

    cats = sorted(tabla["Categoría"].unique()) if not tabla.empty else []
    filtro = st.multiselect("Filtrar por categoría", cats, default=cats)
    vista = tabla[tabla["Categoría"].isin(filtro)] if filtro else tabla

    st.dataframe(
        vista[["#", "Lexema", "TokenType", "Categoría", "Fila", "Columna", "Valor"]],
        width="stretch", hide_index=True, height=460,
    )
    st.caption(f"{len(vista)} de {len(tabla)} tokens. Lexema, categoría, "
               "fila y columna, como exige el requisito 13.")

    st.download_button(
        "Descargar tabla en CSV",
        data=tabla.to_csv(index=False).encode("utf-8-sig"),
        file_name="tabla_simbolos.csv",
        mime="text/csv",
    )

    if identificadores:
        st.markdown("##### Identificadores distintos")
        st.caption("Germen de la tabla de símbolos que llenará el analizador "
                   "semántico de la entrega 3.")
        st.dataframe(
            pd.DataFrame([
                {"Identificador": n,
                 "Apariciones": len(p),
                 "Posiciones (fila:col)": ", ".join(f"{f}:{c}" for f, c in p)}
                for n, p in sorted(identificadores.items())
            ]),
            width="stretch", hide_index=True,
        )

# --- 4. Errores -------------------------------------------------------------
with pestañas[3]:
    st.subheader("Reporte de errores léxicos")
    st.caption(
        "Esto es lo que exige el requisito 14: caracteres o secuencias que "
        "no corresponden a **ningún token válido** del lenguaje."
    )
    if not errores:
        st.success("No se encontró ningún error léxico en esta entrada.")
        st.caption("Pruebe la cadena predefinida «ERRORES LEXICOS deliberados» "
                   "para ver el reporte en acción.")
    else:
        st.dataframe(tabla_err, width="stretch", hide_index=True)
        st.divider()
        for e in errores:
            st.markdown(f"**Error en fila {e.fila}, columna {e.columna}** — {e.mensaje}")
            st.markdown(html_error(codigo, e), unsafe_allow_html=True)

    st.divider()
    st.subheader("Verificación estructural (extra, no reemplaza al analizador sintáctico)")
    st.caption(
        "Esto **no** es análisis sintáctico. Es una pila que empareja "
        "aperturas y cierres de bloque (`hagale_pues`/`ya_quedo`, "
        "`si_acaso`/`asi_quedo`, `mientras_que`/`hasta_ahi`, "
        "`pa_cada`/`listo_pues`, `(` `)`, `{` `}`), igual que un "
        "emparejador de paréntesis. Atrapa el error más común al escribir "
        "Paisascript a mano — olvidar la palabra de cierre — pero **no** "
        "detecta violaciones más finas de la gramática (esas las hará el "
        "parser descendente recursivo completo) ni errores "
        "semánticos de tipos, variables o aridad (esos los hará el analizador semántico)."
    )
    if not chequeo:
        st.success("Todos los bloques abiertos se cerraron correctamente.")
    else:
        for e in chequeo:
            st.markdown(f"⚠️ **Fila {e.fila}, columna {e.columna}** — {e.mensaje}")

# --- 5. Resumen -------------------------------------------------------------
with pestañas[4]:
    st.subheader("Distribución de tokens por categoría")
    conteo = (tabla["Categoría"].value_counts().rename_axis("Categoría")
              .reset_index(name="Tokens"))
    izq, der = st.columns([2, 1])
    izq.bar_chart(conteo.set_index("Categoría"), height=340)
    der.dataframe(conteo, width="stretch", hide_index=True)

    st.markdown("##### Tokens más frecuentes")
    top = (tabla.groupby(["Lexema", "TokenType"]).size()
           .reset_index(name="Veces").sort_values("Veces", ascending=False).head(15))
    st.dataframe(top, width="stretch", hide_index=True)

# --- 6. Traduccion a Gleam --------------------------------------------------
with pestañas[5]:
    st.subheader("En qué se convierte cada token")
    st.caption(
        "El lenguaje fuente se diseñó contra un destino concreto. Esta columna "
        "sale de `mapeo_gleam.py`, el mismo módulo del que partirá el generador "
        "de código de la entrega final."
    )
    st.dataframe(
        tabla[["#", "Lexema", "TokenType", "Gleam", "Directo"]],
        width="stretch", hide_index=True, height=420,
    )

    no_directos = tabla[tabla["Directo"] != "sí"]
    if not no_directos.empty:
        st.warning(
            f"**{len(no_directos)} token(s)** de esta entrada no tienen "
            "traducción directa: Gleam no tiene `while`, `for` ni `return`. "
            "El generador debe reestructurar el árbol a recursión de cola."
        )
        st.dataframe(
            no_directos[["Lexema", "TokenType", "Fila", "Columna", "Gleam"]],
            width="stretch", hide_index=True,
        )
    else:
        st.info("Todos los tokens de esta entrada se traducen por sustitución "
                "directa.")

# --- 7. Codigo del analizador (para explicar en la sustentacion) -----------
with pestañas[6]:
    st.subheader("El analizador léxico, en Python puro")
    st.caption(
        "Fragmentos leídos en vivo de `lexer.py` — no son una copia escrita "
        "a mano, son el archivo real. Ningún fragmento usa Streamlit: es "
        "exactamente el módulo que también consume `main.py`."
    )

    _fuente_lexer = (RAIZ / "lexer.py").read_text(encoding="utf-8")

    def _mostrar(titulo_frag: str, explicacion: str, inicio: str, fin: str) -> None:
        st.markdown(f"##### {titulo_frag}")
        st.caption(explicacion)
        try:
            st.code(extraer_fragmento(_fuente_lexer, inicio, fin), language="python")
        except ValueError:
            st.error("No se encontró este fragmento en lexer.py (¿cambió el archivo?).")

    _mostrar(
        "1 · La tabla de tokens es una lista de (nombre, expresión regular)",
        "El orden importa: Python usa la PRIMERA alternativa que casa, no la "
        "más larga. Por eso ** va antes que *, y NUM_REAL antes que NUM_ENTERO.",
        '_ESPECIFICACION = [',
        're.DOTALL,\n    )',
    )

    _mostrar(
        "2 · El recorrido: una sola pasada con re.finditer",
        "Fila y columna se llevan a mano. Un error NO detiene el ciclo: se "
        "registra y se sigue con el siguiente carácter (requisito 14).",
        'def tokenizar(self) -> List[Token]:',
        'return self.tokens',
    )

    _mostrar(
        "3 · Palabras reservadas: por diccionario, no por regex",
        "El identificador se reconoce primero por completo (maximal munch) y "
        "LUEGO se consulta esta tabla. Así pille_puesx es un identificador, "
        "no la palabra reservada seguida de una x.",
        'PALABRAS_RESERVADAS = {',
        '"naranjas":      TipoToken.LIT_FALSO,\n}',
    )

    _mostrar(
        "4 · Fila y columna: aritmética simple sobre el lexema",
        "Si el lexema trae saltos de línea (una cadena multilínea) se "
        "recalcula la columna desde el último '\\n'; si no, solo se suma su largo.",
        'def _avanzar(self, lexema: str) -> None:',
        'self._columna += len(lexema)',
    )

    with st.expander("Ver lexer.py completo"):
        st.code(_fuente_lexer, language="python")
        st.download_button("Descargar lexer.py",
                           data=_fuente_lexer.encode("utf-8"),
                           file_name="lexer.py", mime="text/x-python")

# --- 8. Referencia ----------------------------------------------------------
with pestañas[7]:
    st.subheader("Documentación del lenguaje")
    doc = st.radio("Documento", ["Gramática BNF", "Mapeo a Gleam", "README"],
                   horizontal=True)
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
        st.download_button(f"Descargar {archivo}", data=texto.encode("utf-8"),
                           file_name=archivo, mime="text/plain")
    else:
        st.error(f"No se encontró {archivo} junto a app.py.")
