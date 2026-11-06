# -*- coding: utf-8 -*-
"""
Módulo: generar_documento_semantico.py
Descripción: Genera el documento PDF de la Parte 1 del Quiz 4 / Entrega 4.

Convención de colores exigida por el enunciado:
  - Reglas originales de la gramática  -> texto ROJO.
  - Reglas semánticas añadidas         -> texto negro sobre fondo ÁMBAR.

Flujo:
  1. Lee las producciones BNF de gramatica_BNF_Paisascript.txt.
  2. Las inserta, en rojo, en el documento HTML.
  3. Intercala las cinco reglas semánticas en ámbar junto al nodo que afectan.
  4. Convierte el HTML a PDF con LibreOffice (no requiere LaTeX).

Ejecutar:  python generar_documento_semantico.py
Salida:    gramatica_ampliada_semantica.html
           gramatica_ampliada_semantica.pdf
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).parent
FUENTE_GRAMATICA = RAIZ / "gramatica_BNF_Paisascript.txt"
HTML_SALIDA = RAIZ / "gramatica_ampliada_semantica.html"
PDF_SALIDA = RAIZ / "gramatica_ampliada_semantica.pdf"


# =============================================================================
#  LAS OCHO REGLAS SEMÁNTICAS (contenido en ámbar)
# =============================================================================

REGLAS_SEMANTICAS = [
    {
        "ancla": "sent_declaracion",
        "id": "SEM-1",
        "titulo": "Declaración de variable y compatibilidad de tipos",
        "nodos": "&lt;sent_declaracion&gt;, &lt;tipo_opcional&gt;, &lt;expresion&gt;",
        "filas": [
            ("Atributos involucrados",
             "<b>tipo_declarado</b>: <i>heredado</i> desde &lt;tipo_opcional&gt;. "
             "Dominio: {numerito, quebradito, cuento, siono} ∪ {⊥}, donde ⊥ = "
             "sin anotación.<br>"
             "<b>type(expr)</b>: <i>sintetizado</i> en &lt;expresion&gt;. "
             "Dominio: {numerito, quebradito, cuento, siono} ∪ {error}.<br>"
             "<b>tipo_simbolo</b>: <i>sintetizado</i> en &lt;sent_declaracion&gt;. "
             "Es el tipo con el que el identificador entra a la tabla de símbolos."),
            ("Restricción",
             "Si <b>tipo_declarado ≠ ⊥</b>, entonces "
             "<b>type(expr) = tipo_declarado</b>.<br>"
             "Si <b>tipo_declarado = ⊥</b>, se infiere "
             "<b>tipo_simbolo = type(expr)</b> (como el <i>let</i> de Gleam)."),
            ("Acciones del compilador",
             "1. Calcular type(expr) recorriendo la expresión (atributo sintetizado).<br>"
             "2. Comparar con tipo_declarado. Si difieren, reportar error con "
             "<b>fila, columna, lexema</b> y mensaje descriptivo.<br>"
             "3. Insertar el símbolo en el <b>ámbito actual</b> con su tipo, "
             "estado de inicialización = verdadero y posición de declaración.<br>"
             "4. El shadowing (redeclaración en el mismo ámbito) es válido: crea "
             "un enlace nuevo, no modifica el anterior.<br>"
             "5. Continuar el análisis (recuperación)."),
        ],
    },
    {
        "ancla": "sent_lectura",
        "id": "SEM-2",
        "titulo": "Uso de identificadores: declaración previa y visibilidad",
        "nodos": "&lt;expr_primaria&gt; (IDENTIFICADOR), &lt;sent_lectura&gt;",
        "filas": [
            ("Atributos involucrados",
             "<b>id.lexema</b>: <i>heredado</i> del token IDENTIFICADOR.<br>"
             "<b>id.type</b>: <i>sintetizado</i> desde la tabla de símbolos. "
             "Dominio: {numerito, quebradito, cuento, siono, desconocido} ∪ {error}.<br>"
             "<b>id.declarado</b>: <i>sintetizado</i>. Dominio: {verdadero, falso}."),
            ("Restricción",
             "<b>id.declarado = verdadero</b>: todo identificador usado en una "
             "expresión debe existir en el ámbito actual o en alguno de sus "
             "ancestros (alcance léxico anidado).<br>"
             "<b>escuche_pues(id)</b> declara el identificador si no existe y lo "
             "marca como inicializado."),
            ("Acciones del compilador",
             "1. Recorrer la pila de ámbitos de dentro hacia afuera buscando el "
             "lexema (resolución de nombres).<br>"
             "2. Si no aparece, reportar «identificador no declarado» con fila, "
             "columna y lexema.<br>"
             "3. Si aparece, sintetizar id.type con el tipo del símbolo; si es una "
             "función usada sin paréntesis, reportarlo.<br>"
             "4. En &lt;sent_lectura&gt;, declarar/inicializar el identificador y "
             "continuar."),
        ],
    },
    {
        "ancla": "expr_multiplicativa_p",
        "id": "SEM-3",
        "titulo": "Compatibilidad de operandos en operadores",
        "nodos": ("&lt;expr_aditiva&gt;, &lt;expr_multiplicativa&gt;, "
                  "&lt;expr_potencia&gt;, &lt;expr_unaria&gt;, "
                  "&lt;expr_relacional&gt;, &lt;expr_igualdad&gt;, "
                  "&lt;expr_y&gt;, &lt;expr_o&gt;, &lt;expr_concat&gt;"),
        "filas": [
            ("Atributos involucrados",
             "<b>type_izq</b> y <b>type_der</b>: <i>sintetizados</i> en los dos "
             "operandos. Dominio: tipos del lenguaje ∪ {desconocido, error}.<br>"
             "<b>type</b>: <i>sintetizado</i> en el nodo del operador (tipo del "
             "resultado)."),
            ("Restricción",
             "<b>+ − * / **</b>: type_izq = type_der y ambos ∈ {numerito, quebradito}.<br>"
             "<b>%</b>: type_izq = type_der = numerito.<br>"
             "<b>&gt; &lt; &gt;= &lt;=</b>: operandos numéricos del mismo tipo; el "
             "resultado es siono.<br>"
             "<b>y_tambien / o_que / nanai</b>: operandos siono; resultado siono.<br>"
             "<b>&lt;&gt;</b>: operandos cuento, numerito o quebradito; resultado cuento "
             "(Paisascript convierte a texto al generar Gleam)."),
            ("Acciones del compilador",
             "1. Comparar type_izq con type_der según la tabla anterior.<br>"
             "2. Si no son compatibles, reportar el operador, los dos tipos y la "
             "posición (fila, columna, lexema).<br>"
             "3. Sintetizar el tipo del resultado o <b>error</b>; el tipo error es "
             "compatible con todo para no generar errores en cascada.<br>"
             "4. Continuar con el resto de la expresión."),
        ],
    },
    {
        "ancla": "sent_mientras",
        "id": "SEM-4",
        "titulo": "Condición de control de tipo booleano",
        "nodos": ("&lt;sent_si&gt;, &lt;sent_mientras&gt;, "
                  "&lt;sent_repita&gt;"),
        "filas": [
            ("Atributos involucrados",
             "<b>type(cond)</b>: <i>sintetizado</i> en la expresión de control. "
             "Dominio: tipos del lenguaje ∪ {desconocido, error}.<br>"
             "<b>cond_esperado</b>: <i>heredado</i> desde la construcción. "
             "Dominio: {siono}."),
            ("Restricción",
             "<b>type(cond) = siono</b> en <b>si_acaso</b>, en "
             "<b>mientras_que</b> y en el <b>hasta_que</b> de "
             "<b>repita_pues</b>. Una condición numerito, cuento o quebradito "
             "no es válida.<br>"
             "En <b>repita_pues</b> la condición se evalúa en el ámbito del "
             "cuerpo, así que puede leer las variables que el cuerpo creó."),
            ("Acciones del compilador",
             "1. Evaluar el tipo sintetizado de la condición.<br>"
             "2. Compararlo con siono.<br>"
             "3. Si no coincide, reportar «la condición debe ser siono» con fila, "
             "columna y lexema.<br>"
             "4. Analizar igualmente ambos bloques (recuperación)."),
        ],
    },
    {
        "ancla": "arg_resto",
        "id": "SEM-5",
        "titulo": "Llamada a función: existencia, aridad y tipos",
        "nodos": ("&lt;sent_llamada&gt;, &lt;sufijo_id&gt; dentro de "
                  "&lt;expr_primaria&gt;, &lt;argumentos&gt;"),
        "filas": [
            ("Atributos involucrados",
             "<b>arity</b>: <i>sintetizado</i> (número de argumentos).<br>"
             "<b>arg_type[1..n]</b>: <i>sintetizados</i> en cada &lt;expresion&gt;.<br>"
             "<b>param_type[1..n]</b> y <b>return_type</b>: consultados en la firma "
             "de la tabla de símbolos.<br>"
             "<b>type</b>: <i>sintetizado</i> en la llamada = return_type."),
            ("Restricción",
             "La función debe estar declarada; <b>arity = |params|</b>; "
             "<b>arg_type[i] = param_type[i]</b> para todo i; el tipo del "
             "resultado es el tipo de retorno declarado o inferido."),
            ("Acciones del compilador",
             "1. Buscar la firma de la función en el ámbito global.<br>"
             "2. Si no existe, reportar «función no declarada» con su posición.<br>"
             "3. Comparar la aridad y reportar el número esperado y el recibido.<br>"
             "4. Comparar cada argumento con su parámetro formal y reportar los "
             "desajustes de tipo.<br>"
             "5. Sintetizar return_type y continuar."),
        ],
    },
    {
        "ancla": "sent_repita",
        "id": "SEM-6",
        "titulo": "Terminación del bucle: la condición tiene que poder cambiar",
        "nodos": "&lt;sent_mientras&gt;, &lt;sent_repita&gt;",
        "filas": [
            ("Atributos involucrados",
             "<b>leidas(cond)</b>: <i>sintetizado</i> en la expresión de "
             "control. Dominio: conjunto de identificadores que la condición "
             "consulta (sin los nombres de función).<br>"
             "<b>redefinidas(cuerpo)</b>: <i>sintetizado</i> en &lt;bloque&gt;. "
             "Dominio: conjunto de identificadores que el cuerpo vuelve a "
             "enlazar con <tt>pille_pues</tt> o <tt>escuche_pues</tt>.<br>"
             "<b>valor(cond)</b>: <i>sintetizado</i> por plegado de "
             "constantes. Dominio: {sizas, naranjas} ∪ {⊥} (⊥ = no constante).<br>"
             "<b>continua_si</b>: <i>heredado</i> de la construcción. Dominio: "
             "{verdadero} para <tt>mientras_que</tt>, {falso} para "
             "<tt>repita_pues</tt>, porque <tt>hasta_que</tt> es la condición "
             "de SALIDA, no de permanencia."),
            ("Restricción",
             "<b>valor(cond) ≠ continua_si</b>: la condición no puede ser el "
             "literal que mantiene el bucle vivo (<tt>mientras_que sizas</tt> "
             "o <tt>hasta_que naranjas</tt>).<br>"
             "<b>leidas(cond) ≠ ∅</b>: una condición sin variables tiene "
             "siempre el mismo valor.<br>"
             "<b>leidas(cond) ∩ redefinidas(cuerpo) ≠ ∅</b>: el cuerpo debe "
             "redefinir al menos una de las variables que la condición lee.<br>"
             "La regla es <i>conservadora y sólida en este lenguaje</i>: "
             "Paisascript es inmutable y sin efectos laterales, así que si esa "
             "intersección es vacía ninguna ejecución puede cambiar el valor "
             "de la condición."),
            ("Acciones del compilador",
             "1. Plegar la condición: si es un literal booleano, compararlo "
             "con continua_si y reportar «el bucle nunca termina».<br>"
             "2. Recorrer la condición y recolectar leidas(cond), descartando "
             "los identificadores que la tabla de símbolos marca como "
             "función.<br>"
             "3. Recorrer el cuerpo (incluidos los bucles anidados) y "
             "recolectar redefinidas(cuerpo) a partir de los nodos "
             "&lt;sent_declaracion&gt;, &lt;sent_lectura&gt; y "
             "&lt;sent_asignacion&gt;.<br>"
             "4. Intersecar ambos conjuntos. Si el resultado es vacío, "
             "reportar error con fila, columna y lexema del bucle, nombrando "
             "las variables de la condición que habría que hacer avanzar.<br>"
             "5. Continuar el análisis del resto del programa.<br>"
             "<i>Por qué importa para Gleam:</i> ese bucle se traduce a una "
             "recursión de cola; sin progreso, la función auxiliar nunca "
             "alcanza su caso base."),
        ],
    },
    {
        "ancla": "sent_para",
        "id": "SEM-7",
        "titulo": "La variable de control del pa_cada es de solo lectura",
        "nodos": ("&lt;sent_para&gt;, y dentro de su &lt;bloque&gt;: "
                  "&lt;sent_declaracion&gt;, &lt;sent_lectura&gt;, "
                  "&lt;sent_asignacion&gt;"),
        "filas": [
            ("Atributos involucrados",
             "<b>var_control.lexema</b>: <i>heredado</i> del IDENTIFICADOR que "
             "sigue a <tt>pa_cada</tt>.<br>"
             "<b>var_control.escribible</b>: <i>heredado</i> hacia el ámbito "
             "del bucle. Dominio: {verdadero, falso}; vale <b>falso</b> para "
             "la variable de control y verdadero para cualquier otra.<br>"
             "<b>var_control.categoria</b>: <i>sintetizado</i> al declararla. "
             "Dominio: {bucle}.<br>"
             "<b>var_control.type</b>: <i>sintetizado</i> = numerito."),
            ("Restricción",
             "Ninguna sentencia del cuerpo puede volver a enlazar la variable "
             "de control: ni <tt>pille_pues i = …</tt>, ni "
             "<tt>escuche_pues(i)</tt>, ni <tt>i = …</tt>.<br>"
             "El atributo se consulta antes de cada redefinición: solo se "
             "admite si <b>escribible = verdadero</b>.<br>"
             "Fuera del bucle el nombre vuelve a estar libre, porque el ámbito "
             "del <tt>pa_cada</tt> se cierra al terminar."),
            ("Acciones del compilador",
             "1. Al entrar al <tt>pa_cada</tt>, abrir un ámbito nuevo e "
             "insertar la variable de control con categoría = bucle, tipo = "
             "numerito, inicializada = verdadero y <b>escribible = falso</b>.<br>"
             "2. En cada <tt>pille_pues</tt> y cada <tt>escuche_pues</tt> del "
             "cuerpo, buscar el nombre en la pila de ámbitos y leer su "
             "atributo escribible.<br>"
             "3. Si es falso, reportar error con fila, columna y lexema, y "
             "sugerir otro nombre para la variable nueva.<br>"
             "4. Cerrar el ámbito al salir del bucle y continuar.<br>"
             "<i>Por qué importa para Gleam:</i> la variable de control se "
             "vuelve el parámetro de <tt>fn(i) { … }</tt> dentro de "
             "<tt>list.each</tt>; reenlazarla rompería el recorrido."),
        ],
    },
    {
        "ancla": "paso_opcional",
        "id": "SEM-8",
        "titulo": "Paso del pa_cada distinto de cero y recorrido alcanzable",
        "nodos": "&lt;sent_para&gt;, &lt;paso_opcional&gt;",
        "filas": [
            ("Atributos involucrados",
             "<b>valor(desde)</b>, <b>valor(hasta)</b>, <b>valor(paso)</b>: "
             "<i>sintetizados</i> por plegado de constantes sobre cada "
             "&lt;expresion&gt;. Dominio: ℤ ∪ {⊥}, donde ⊥ significa «no es un "
             "literal» (admite el menos unario y los paréntesis).<br>"
             "<b>paso_implicito</b>: <i>heredado</i>; vale 1 cuando "
             "&lt;paso_opcional&gt; deriva en ε.<br>"
             "<b>direccion</b>: <i>sintetizado</i> en &lt;sent_para&gt; = "
             "signo(valor(paso)). Dominio: {+1, −1}."),
            ("Restricción",
             "<b>valor(paso) ≠ 0</b>: con paso 0 la variable de control nunca "
             "avanza.<br>"
             "Si <b>valor(paso) &gt; 0</b> entonces <b>valor(desde) ≤ "
             "valor(hasta)</b>.<br>"
             "Si <b>valor(paso) &lt; 0</b> entonces <b>valor(desde) ≥ "
             "valor(hasta)</b>.<br>"
             "Las dos últimas solo se exigen cuando los tres valores son "
             "literales: con límites variables el recorrido no es decidible en "
             "tiempo de compilación y la regla calla en lugar de dar un falso "
             "positivo."),
            ("Acciones del compilador",
             "1. Plegar las tres expresiones a su valor constante; si "
             "&lt;paso_opcional&gt; es ε, usar paso_implicito = 1.<br>"
             "2. Si valor(paso) = 0, reportar error sobre el lexema del paso "
             "con fila y columna.<br>"
             "3. Si los tres son literales, comparar el signo del paso con el "
             "orden de los límites y reportar «el cuerpo nunca se ejecuta» "
             "indicando los tres valores concretos.<br>"
             "4. Si alguno no es literal, no reportar nada y seguir.<br>"
             "5. Continuar con el cuerpo del bucle.<br>"
             "<i>Por qué importa para Gleam:</i> <tt>list.range</tt> no admite "
             "paso, así que con paso ≠ 1 el generador emite recursión de cola; "
             "un paso 0 produciría una recursión infinita."),
        ],
    },
]


def _caja_semantica(regla):
    filas = "".join(
        f'<tr><td class="etq">{etiqueta}</td><td>{contenido}</td></tr>'
        for etiqueta, contenido in regla["filas"]
    )
    return f"""
    <table class="sem"><tr><td class="cuerpo" bgcolor="#FFBF00" style="background-color:#FFBF00;">
      <p class="semtitulo">REGLA {regla['id']} — {regla['titulo']}</p>
      <p class="semnodos">Nodos de la gramática: {regla['nodos']}</p>
      <table class="semtabla">{filas}</table>
    </td></tr></table>
    """


# =============================================================================
#  EXTRACCIÓN DE LAS PRODUCCIONES BNF
# =============================================================================

def extraer_bloques_gramatica():
    texto = FUENTE_GRAMATICA.read_text(encoding="utf-8")
    inicio = texto.index("3 - PRODUCCIONES BNF")
    inicio = texto.index("\n", inicio) + 1
    fin = texto.index("4 - VERIFICACION DE LA CONDICION LL(1)")
    seccion = texto[inicio:fin]
    return [bloque.strip("\n") for bloque in seccion.split("\n\n") if bloque.strip()]


def _es_produccion(bloque):
    return "::=" in bloque and not bloque.lstrip().startswith("=====")


def _producciones_definidas(bloque):
    """Nombres de los no terminales que se DEFINEN (::=) en el bloque."""
    return set(re.findall(r"<([a-z_0-9]+)>\s*::=", bloque))


def render_gramatica():
    """Devuelve el HTML de las producciones en rojo con las cajas en ámbar."""
    piezas = []
    for bloque in extraer_bloques_gramatica():
        # Se usan <br> en vez de saltos de línea literales: LibreOffice importa
        # cada salto como un párrafo nuevo (con espaciado adicional), mientras
        # que <br> conserva un bloque compacto con "white-space: pre".
        cuerpo = "<br>".join(html.escape(bloque).split("\n"))
        clase = "gram" if _es_produccion(bloque) else "comentario"
        piezas.append(f'<div class="{clase}">{cuerpo}</div>')

        definidas = _producciones_definidas(bloque)
        for regla in REGLAS_SEMANTICAS:
            if regla["ancla"] in definidas:
                piezas.append(_caja_semantica(regla))
    return "\n".join(piezas)


# =============================================================================
#  CONTENIDO DEL DOCUMENTO
# =============================================================================

CSS = """
@page { size: A4; margin: 1.8cm 1.9cm 1.8cm 1.9cm; }
/* Chromium descarta los fondos al imprimir si no se le pide lo contrario, y el
   fondo ambar de las reglas semanticas es parte de la convencion del enunciado. */
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 10pt;
       color: #111111; line-height: 1.34; }
h1 { font-size: 19pt; margin: 0 0 6px 0; color: #7A3E00; }
h2 { font-size: 13.5pt; margin: 18px 0 8px 0; color: #7A3E00;
     border-bottom: 1.4px solid #B8860B; padding-bottom: 3px; }
h3 { font-size: 10.5pt; margin: 0 0 4px 0; }
p { margin: 4px 0; text-align: left; }
.portada { text-align: center; padding-top: 4.5cm; page-break-after: always; }
.portada .uni { font-size: 12pt; letter-spacing: .5px; }
.portada .titulo { font-size: 24pt; margin: 18px 0 6px 0; color: #7A3E00; }
.portada .sub { font-size: 12pt; color: #444; }
.portada .meta { margin-top: 2.5cm; font-size: 10.5pt; }
.gram { font-family: "DejaVu Sans Mono", "Courier New", monospace;
        font-size: 8.6pt; color: #C00000; white-space: pre;
        margin: 6px 0 6px 0; line-height: 1.18; page-break-inside: avoid; }
.comentario { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt;
              color: #B05050; white-space: pre; margin: 4px 0; line-height: 1.18; }
table.sem { border-collapse: collapse; width: 100%;
            margin: 8px 0 14px 0; page-break-inside: avoid; }
table.sem td.cuerpo { background-color: #FFBF00; color: #000000;
                      border: 1.6px solid #7A5A00; padding: 7px 9px; }
.semtitulo { font-weight: bold; font-size: 11pt; margin: 0 0 3px 0; }
.semnodos { font-size: 8.8pt; margin: 0 0 6px 0; }
table.semtabla { border-collapse: collapse; width: 100%; }
table.semtabla td { border: 1px solid #9A7200; padding: 3px 5px;
                    vertical-align: top; font-size: 8.9pt; text-align: left; }
table.semtabla td.etq { font-weight: bold; width: 21%;
                        background-color: #FFD97A; }
.leyenda { border: 1px solid #999; padding: 8px 10px; margin: 10px 0;
           background: #FAFAFA; font-size: 9.2pt; }
.leyenda .rojo { color: #C00000; font-family: "DejaVu Sans Mono", monospace; }
.leyenda .ambar { background-color: #FFBF00; padding: 1px 4px; }
table.resumen { border-collapse: collapse; width: 100%; font-size: 8.8pt;
                margin: 8px 0 14px 0; }
table.resumen th, table.resumen td { border: 1px solid #999; padding: 4px 5px;
                                     vertical-align: top; text-align: left; }
table.resumen td.corto, table.resumen th.corto { white-space: nowrap; }
table.resumen th { background: #F0E0B0; }
.codigo { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt;
          background: #F4F4F4; border-left: 3px solid #B8860B;
          padding: 7px 9px; white-space: pre-wrap; margin: 7px 0; }
.ia { border: 1.4px dashed #7A5A00; background: #FFF7E0; padding: 8px 10px;
      font-size: 9.2pt; margin: 8px 0; }
.salto { page-break-before: always; }
.oculto { font-size: 7pt; color: #D0D0D0; margin-top: 26px; }
"""


def construir_html():
    gramatica = render_gramatica()

    resumen = """
    <table class="resumen">
      <tr>
        <th width="8%">Regla</th><th width="26%">Nodo(s) de la gramática</th>
        <th width="30%">Atributos</th><th width="36%">Restricción que se valida</th>
      </tr>
      <tr>
        <td>SEM-1</td><td>&lt;sent_declaracion&gt;</td>
        <td>tipo_declarado (heredado), type(expr) (sintetizado)</td>
        <td>El tipo anotado coincide con el tipo inferido de la expresión.</td>
      </tr>
      <tr>
        <td>SEM-2</td><td>&lt;expr_primaria&gt;, &lt;sent_lectura&gt;</td>
        <td>id.lexema (heredado), id.type e id.declarado (sintetizados)</td>
        <td>Todo identificador usado está declarado en el ámbito actual o ancestro.</td>
      </tr>
      <tr>
        <td>SEM-3</td><td>Producciones de expresiones</td>
        <td>type_izq, type_der, type (sintetizados)</td>
        <td>Operandos compatibles: mismo tipo aritmético; lógicos y condiciones siono.</td>
      </tr>
      <tr>
        <td>SEM-4</td><td>&lt;sent_si&gt;, &lt;sent_mientras&gt;, &lt;sent_repita&gt;</td>
        <td>type(cond) (sintetizado), cond_esperado (heredado)</td>
        <td>La condición de control es de tipo siono.</td>
      </tr>
      <tr>
        <td>SEM-5</td><td>&lt;sent_llamada&gt;, &lt;sufijo_id&gt;</td>
        <td>arity, arg_type[], param_type[], return_type</td>
        <td>La función existe, la aridad coincide y cada argumento tiene el tipo del parámetro.</td>
      </tr>
      <tr>
        <td>SEM-6</td><td>&lt;sent_mientras&gt;, &lt;sent_repita&gt;</td>
        <td>leidas(cond), redefinidas(cuerpo), valor(cond) (sintetizados); continua_si (heredado)</td>
        <td>El cuerpo redefine alguna variable de la condición: el bucle puede terminar.</td>
      </tr>
      <tr>
        <td>SEM-7</td><td>&lt;sent_para&gt; y su &lt;bloque&gt;</td>
        <td>var_control.escribible (heredado), categoria y type (sintetizados)</td>
        <td>La variable de control no se puede reenlazar dentro del bucle.</td>
      </tr>
      <tr>
        <td>SEM-8</td><td>&lt;sent_para&gt;, &lt;paso_opcional&gt;</td>
        <td>valor(desde), valor(hasta), valor(paso), direccion (sintetizados); paso_implicito (heredado)</td>
        <td>El paso no es 0 y su signo concuerda con los límites: el recorrido existe.</td>
      </tr>
    </table>
    """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Paisascript — Gramática ampliada con reglas semánticas</title>
  <style>{CSS}</style>
</head>
<body>

<!-- ============================ PORTADA ============================ -->
<div class="portada">
  <div class="uni">Universidad Católica de Oriente · Facultad de Ingeniería</div>
  <div class="uni">Compiladores — Quiz 4 / Entrega 4 · Semestre 2-2026</div>
  <div class="titulo">Paisascript</div>
  <div class="sub">Gramática BNF ampliada con reglas semánticas<br>
  e implementación del análisis semántico</div>
  <div class="meta">
    <p><b>Lenguaje fuente:</b> Paisascript</p>
    <p><b>Lenguaje destino:</b> Gleam</p>
    <p><b>Integrantes:</b> Andres Felipe Velez &middot;
       Angie Amaya Fernandez &middot;
       Julian David Guarnizo Castrillon</p>
    <p><b>Repositorio:</b> github.com/JulianG08/Analizador-lexico</p>
    <p><b>App en vivo:</b> compiladorlex.streamlit.app</p>
    <p><b>Bonus:</b> Modalidad A — IA como capa adicional de validación semántica</p>
  </div>
</div>

<!-- ============================ INTRODUCCIÓN ============================ -->
<h1>1. Gramática ampliada con reglas semánticas</h1>

<p>Este documento extiende la gramática libre de contexto de Paisascript usada en
las entregas anteriores. Las <b>producciones sintácticas originales</b> se muestran
en <span class="rojo">rojo</span>. Las <b>reglas semánticas añadidas</b> se muestran
en <span class="ambar">texto negro sobre fondo ámbar</span> e indican, para cada
regla, los atributos involucrados (sintetizados o heredados) y el nodo al que
pertenecen, el dominio de valores o restricción que debe satisfacerse, y las
acciones que ejecuta el compilador para validarla.</p>

<div class="leyenda">
  <p><span class="rojo">&lt;produccion&gt; ::= ...</span> — regla original de la
  gramática (producción sintáctica sin ampliar).</p>
  <p><span class="ambar">REGLA SEM-x</span> — regla semántica añadida: atributos,
  restricción y acciones de validación.</p>
</div>

<p>Las reglas semánticas <b>exceden</b> a las sintácticas: no describen el orden de
los elementos en la cadena de entrada, sino propiedades sobre los valores que esos
elementos representan. El compilador las valida en una fase independiente
(<i>analizador_semantico.py</i>) que recorre el árbol de sintaxis y construye una
tabla de símbolos.</p>

<h2>1.1 Resumen de las ocho reglas</h2>
{resumen}

<h2>1.2 Los tres bucles de Paisascript y las reglas que los gobiernan</h2>

<p>Gleam <b>no tiene bucles</b>: no hay <tt>while</tt>, <tt>for</tt>,
<tt>break</tt> ni <tt>continue</tt>; solo <tt>case</tt> y recursión. Paisascript
sí los ofrece, porque son requisito del curso y porque su traducción es mecánica.
Las tres formas cubren los tres patrones clásicos de repetición y cada una se
apoya en una construcción distinta de Gleam:</p>

<table class="resumen">
  <tr>
    <th width="27%">Bucle en Paisascript</th><th width="15%">Clase</th>
    <th width="33%">Traducción a Gleam</th><th width="25%">Reglas que lo validan</th>
  </tr>
  <tr>
    <td><tt>mientras_que c dele_pues B hasta_ahi</tt></td>
    <td>Condición al principio (<i>pre-test</i>); puede ejecutar cero veces.</td>
    <td>Función auxiliar <b>recursiva de cola</b> cuyos parámetros son las
        variables que el cuerpo redefine; <tt>case c {{ True -&gt; bucle(estado'),
        False -&gt; estado }}</tt>.</td>
    <td>SEM-4 (condición siono) y <b>SEM-6</b> (progreso).</td>
  </tr>
  <tr>
    <td><tt>pa_cada i desde a hasta b [de_a p] dele_pues B listo_pues</tt></td>
    <td>Contador con límites y paso; recorrido conocido de antemano.</td>
    <td>Con paso 1: <tt>list.range(a, b) |&gt; list.each(fn(i) {{ B }})</tt>.
        Con paso ≠ 1: recursión de cola con incremento, porque
        <tt>list.range</tt> no admite paso.</td>
    <td>SEM-3 (límites numerito), <b>SEM-7</b> (variable de control de solo
        lectura) y <b>SEM-8</b> (paso y dirección).</td>
  </tr>
  <tr>
    <td><tt>repita_pues B hasta_que c</tt></td>
    <td>Condición al final (<i>post-test</i>); ejecuta al menos una vez.</td>
    <td>La misma recursión de cola, con el cuerpo emitido <b>antes</b> del
        <tt>case</tt>: <tt>True -&gt; estado</tt> (caso base),
        <tt>False -&gt; bucle(estado')</tt>.</td>
    <td>SEM-4 (condición siono) y <b>SEM-6</b> (progreso, con
        <tt>continua_si = falso</tt>).</td>
  </tr>
</table>

<p>Que los tres bucles se traduzcan a recursión es exactamente lo que vuelve
necesarias a SEM-6, SEM-7 y SEM-8: en un lenguaje con <tt>while</tt> de verdad un
bucle sin progreso solo se cuelga en ejecución, mientras que aquí genera una
función recursiva que nunca alcanza su caso base. El análisis semántico detecta en
tiempo de compilación lo que el lenguaje destino no podría ni expresar.</p>

<!-- ============================ PRODUCCIONES ============================ -->
<h1>2. Producciones BNF con las reglas semánticas intercaladas</h1>

<p>Se reproduce la sección de producciones de la gramática. Cada regla semántica
aparece inmediatamente después del nodo que restringe.</p>

{gramatica}

<!-- ============================ PARTE 2 ============================ -->
<h1 class="salto">3. Implementación en el compilador (Parte 2)</h1>

<p>El análisis semántico está implementado como una <b>fase claramente
diferenciada</b> del análisis sintáctico: el módulo <i>analizador_semantico.py</i>
recibe el CST que produce el parser y lo recorre con un <b>visitor</b>. El parser
no contiene lógica semántica; la interfaz (<i>app.py</i>) invoca la fase después
del análisis sintáctico.</p>

<div class="codigo">from analizador_semantico import AnalizadorSemantico

analizador = AnalizadorSemantico(cst)      # CST del parser
errores = analizador.analizar()            # lista de ErrorSemantico
tabla = analizador.tabla                   # tabla de símbolos</div>

<h2>3.1 Tabla de símbolos</h2>
<p>Estructura de datos con <b>pila de ámbitos</b> (uno por bloque, función,
<tt>mientras_que</tt>, <tt>pa_cada</tt>, <tt>repita_pues</tt> y
<tt>pillemos</tt>). Cada entrada almacena:</p>
<ul>
  <li><b>lexema</b>, <b>tipo</b> (numerito, quebradito, cuento, siono o desconocido),</li>
  <li><b>categoría</b> (variable, parámetro, función, variable de bucle o patrón),</li>
  <li><b>ámbito</b> y <b>nivel</b> de anidamiento,</li>
  <li><b>estado de inicialización</b>,</li>
  <li><b>escribible</b> (falso solo para la variable de control de un
      <tt>pa_cada</tt>; es el atributo heredado que usa SEM-7),</li>
  <li><b>fila</b> y <b>columna</b> de la declaración,</li>
  <li>para funciones: <b>parámetros</b> (nombre y tipo) y <b>tipo de retorno</b>.</li>
</ul>
<p>La búsqueda de nombres va de dentro hacia afuera (alcance léxico), de modo que
el <i>shadowing</i> es válido: una declaración nueva oculta a la anterior sin
modificarla.</p>

<h2>3.2 Detección y reporte de errores</h2>
<p>Cada violación produce un objeto <tt>ErrorSemantico</tt> con <b>fila</b>,
<b>columna</b>, <b>lexema</b>, la regla violada (SEM-1 … SEM-8) y un mensaje
descriptivo. Ejemplo real de salida:</p>

<div class="codigo">Error Semántico en [Fila 16, Columna 21] sobre 'edad':
  [SEM-1] Se declara 'edad' como numerito, pero la expresión es de tipo cuento

Error Semántico en [Fila 20, Columna 27] sobre '+':
  [SEM-3] No se pueden mezclar 'quebradito' y 'numerito' con '+':
  Gleam no convierte implícitamente entre numerito y quebradito

Error Semántico en [Fila 22, Columna 12] sobre 'saldo_disponible':
  [SEM-2] El identificador 'saldo_disponible' no ha sido declarado en el
  ámbito actual ni en uno ancestro

Error Semántico en [Fila 24, Columna 33] sobre 'sumar':
  [SEM-5] La función 'sumar' espera 2 argumento(s) y se pasaron 1</div>

<h2>3.3 Continuación del análisis (recuperación)</h2>
<p>El visitor <b>no se detiene</b> en el primer error. Tras reportar una violación
continúa recorriendo el resto del árbol; las expresiones inválidas sintetizan el
tipo especial <tt>error</tt>, que es compatible con cualquier otro tipo para evitar
errores en cascada. Por eso un programa con varios fallos reporta <b>todos</b> en
una sola pasada (verificado en <i>test_semantico.py</i>).</p>

<h2>3.4 Separación de fases</h2>
<table class="resumen">
  <tr><th class="corto" width="15%">Fase</th><th class="corto" width="32%">Módulo</th><th width="53%">Responsabilidad</th></tr>
  <tr><td class="corto">Léxica</td><td class="corto">lexer.py</td><td>Tokens con lexema, fila y columna.</td></tr>
  <tr><td class="corto">Sintáctica</td><td class="corto">parser.py</td><td>CST según la gramática BNF (LL(1) recursivo).</td></tr>
  <tr><td class="corto"><b>Semántica</b></td><td class="corto"><b>analizador_semantico.py</b></td>
      <td>Visitor sobre el CST, tabla de símbolos y reglas SEM-1 … SEM-8.</td></tr>
</table>

<!-- ============================ BONUS ============================ -->
<h1 class="salto">4. Bonus — Integración de IA (Modalidad A)</h1>

<p><b>Modalidad elegida: A — IA como capa adicional de validación.</b> Los errores
que detectan las reglas semánticas clásicas se envían a un modelo de lenguaje
(OpenAI, configurable por <tt>OPENAI_API_KEY</tt> en <tt>.env</tt> o en los Secrets
de Streamlit) junto con el código fuente, la tabla de símbolos y la gramática BNF.
El modelo devuelve una explicación de la causa y una propuesta de corrección en
lenguaje natural.</p>

<p><b>Flujo de integración:</b></p>
<ol>
  <li>El compilador ejecuta las reglas clásicas (SEM-1 … SEM-8).</li>
  <li>Si hay errores, la interfaz ofrece el botón
      «Explicar y corregir estos errores semánticos con IA».</li>
  <li><tt>ai_assistant.analizar_error_semantico_con_ia(codigo, errores, tabla)</tt>
      construye el prompt con el código, los errores y la tabla de símbolos.</li>
  <li>La respuesta se muestra como sugerencia. <b>Las reglas clásicas siguen
      siendo la fuente de verdad</b>: la IA no las reemplaza, las complementa.</li>
</ol>

<div class="codigo">from ai_assistant import analizar_error_semantico_con_ia

sugerencia = analizar_error_semantico_con_ia(
    codigo, errores_semanticos, tabla_simbolos, api_key=api_key
)</div>

<h2>4.1 Ejemplo concreto</h2>
<p><b>Código fuente (fragmento):</b></p>
<div class="codigo">pille_pues numerito edad = "veinte anios"</div>

<p><b>Error original detectado por la regla clásica:</b></p>
<div class="codigo">[SEM-1] Se declara 'edad' como numerito,
pero la expresión es de tipo cuento
(fila 16, columna 21, lexema 'edad')</div>

<p><b>Sugerencia generada por la IA (ejemplo de salida):</b></p>
<div class="ia">
<p>🔍 <b>Causa:</b> la variable <tt>edad</tt> se anotó como <tt>numerito</tt>
(entero), pero la expresión inicializadora es un literal de tipo <tt>cuento</tt>
(cadena). Paisascript tiene tipado estático y fuerte: no convierte cadenas a
números de forma implícita.</p>
<p>🛠️ <b>Corrección propuesta:</b></p>
<div class="codigo">pille_pues numerito edad = 20</div>
<p>Si el valor debe leerse de consola, use <tt>escuche_pues(edad)</tt>, que
declara e inicializa el identificador.</p>
<p>📌 <b>Regla aplicada:</b> SEM-1 — declaración y compatibilidad de tipos.</p>
</div>

<p class="oculto">los hipopótamos bailan desnudos en la playa</p>

</body>
</html>
"""


# =============================================================================
#  CONVERSIÓN A PDF
# =============================================================================

# Navegadores basados en Chromium que saben imprimir a PDF desde la linea de
# comandos. Se usan como respaldo cuando LibreOffice no esta disponible.
NAVEGADORES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _pdf_con_libreoffice():
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        return None
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf",
         "--outdir", str(RAIZ), str(HTML_SALIDA)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return PDF_SALIDA if PDF_SALIDA.exists() else None


def _pdf_con_navegador():
    """Imprime el HTML con Edge o Chrome en modo headless."""
    navegador = next(
        (ruta for ruta in NAVEGADORES if Path(ruta).exists()),
        shutil.which("msedge") or shutil.which("chrome"),
    )
    if navegador is None:
        return None
    subprocess.run(
        [str(navegador), "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={PDF_SALIDA}", HTML_SALIDA.as_uri()],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180,
    )
    return PDF_SALIDA if PDF_SALIDA.exists() else None


def convertir_a_pdf():
    """Intenta LibreOffice y, si no esta, Edge/Chrome headless."""
    for motor, nombre in ((_pdf_con_libreoffice, "LibreOffice"),
                          (_pdf_con_navegador, "Edge/Chrome headless")):
        try:
            pdf = motor()
        except Exception as e:                      # noqa: BLE001
            print(f"AVISO: {nombre} falló ({e}).")
            continue
        if pdf is not None:
            print(f"Motor de PDF: {nombre}")
            return pdf
    print("AVISO: no se encontró LibreOffice ni un navegador Chromium; "
          "se generó solo el HTML.")
    return None


def main():
    HTML_SALIDA.write_text(construir_html(), encoding="utf-8")
    print(f"HTML generado: {HTML_SALIDA}")
    pdf = convertir_a_pdf()
    if pdf:
        print(f"PDF generado : {pdf}")
    else:
        print("No se pudo generar el PDF automáticamente.")


if __name__ == "__main__":
    main()
