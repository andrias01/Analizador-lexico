# Paisascript — Analizador Léxico y Gramática BNF

**Paisascript** es un lenguaje de programación imperativo-estructurado cuyas
palabras reservadas provienen de la jerga paisa (Antioquia, Colombia). Es el
**lenguaje fuente** de un compilador fuente-a-fuente cuyo **lenguaje destino es
[Gleam](https://gleam.run)**.

Este repositorio contiene la **Entrega 1** del curso de Teoría de Compiladores:
la gramática libre de contexto en notación BNF y el analizador léxico.

---

## Tabla de contenidos

1. [Ejecutar el analizador](#ejecutar-el-analizador)
2. [Archivos del proyecto](#archivos-del-proyecto)
3. [Diccionario de palabras reservadas](#diccionario-de-palabras-reservadas)
4. [Tipos de datos](#tipos-de-datos)
5. [Operadores](#operadores)
6. [Ejemplos de código](#ejemplos-de-código)
7. [Arquitectura del lexer](#arquitectura-del-lexer)
8. [Coherencia con Gleam](#coherencia-con-gleam)
9. [Cumplimiento del enunciado](#cumplimiento-del-enunciado)

---

## Ejecutar el analizador

Hay **dos interfaces** sobre el mismo analizador. Se recomienda la web para la
sustentación.

### Interfaz web (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`. Si `streamlit` no está en el PATH:

```bash
py -3.12 -m streamlit run app.py
```

### Publicar en Streamlit Community Cloud

La app no usa disco ni estado de servidor, así que se despliega sin cambios:

1. Subir el repositorio a GitHub (`git push`).
2. Entrar a [share.streamlit.io](https://share.streamlit.io) con la cuenta de
   GitHub y elegir **New app**.
3. Seleccionar el repositorio y la rama, y poner `app.py` como *Main file path*.
4. **Deploy**. Streamlit lee `requirements.txt` e instala las dependencias solo.

El tema oscuro de `.streamlit/config.toml` se aplica también en la nube. La
pestaña «Referencia» lee la gramática y el mapeo con rutas relativas al propio
`app.py`, de modo que funcionan igual en local y desplegado.

### Interfaz de consola

```bash
python main.py
```

No requiere dependencias externas: solo la biblioteca estándar de Python 3.8+.

### Modos de entrada

Ambas interfaces ofrecen los mismos tres (requisito 11 del enunciado):

1. **Cadena predefinida** — ocho programas de ejemplo que cubren E/S, funciones,
   ambos bucles, calce de patrones, identificadores con tildes y un caso con
   errores léxicos deliberados.
2. **Cadena libre** — se escribe el código directamente. En consola se termina
   con una línea que diga `fin`.
3. **Archivo `.paisa`** — se sube o se indica la ruta.

### Qué muestra

| Vista | Contenido |
| :--- | :--- |
| Código segmentado | El fuente reimpreso con cada lexema pintado según su categoría |
| Flujo de tokens | La secuencia de fichas `lexema · TokenType` a color |
| Tabla de símbolos | Lexema, TokenType, categoría, **fila** y **columna** de cada token (filtrable y descargable en CSV en la web) |
| Identificadores | Identificadores distintos y todas sus posiciones |
| Errores léxicos | Fila, columna, causa y la línea con un `^` bajo el error |
| Resumen | Distribución de tokens por categoría y los más frecuentes |
| Traducción a Gleam | En qué se convierte cada token, y cuáles exigen reestructurar el árbol *(solo web)* |
| Referencia | La gramática, el mapeo y este README dentro de la app *(solo web)* |

---

## Archivos del proyecto

| Archivo | Contenido |
| :--- | :--- |
| `gramatica_BNF_Paisascript.txt` | Gramática BNF completa: descripción informal, terminales por categoría, 54 reglas de producción sin recursividad izquierda, **verificación LL(1)**, ejemplos válidos e inválidos y justificación de coherencia con Gleam |
| `lexer.py` | **Módulo reutilizable** del analizador léxico. No imprime ni lee nada |
| `app.py` | Interfaz web en Streamlit |
| `main.py` | Interfaz de consola con colores ANSI |
| `ejemplos.py` | Las ocho cadenas predefinidas |
| `mapeo_gleam.py` | Correspondencia token → construcción de Gleam, en código |
| `MAPEO_GLEAM.md` | Traducción trabajada de cada constructo a Gleam |
| `requirements.txt` | Dependencias de la interfaz web |
| `.streamlit/config.toml` | Tema de la interfaz web |
| `Tabla_analisis_lexico.xlsx` | Tabla de análisis léxico |

### Arquitectura

Las dos interfaces son intercambiables porque ninguna contiene lógica de
análisis:

```
main.py  (consola, ANSI)  ──┐
                            ├──►  lexer.py  ──►  mapeo_gleam.py
app.py   (web, Streamlit) ──┘     (sin cambios)
```

Esa independencia **es** el requisito 15 del enunciado, y aquí está demostrada
en la práctica: `app.py` se construyó después, sin modificar una sola línea de
`lexer.py`. El analizador sintáctico de la entrega 2 será un tercer consumidor.

---

## Diccionario de palabras reservadas

### Declaraciones y E/S

| Paisascript | Equivale a | Gleam |
| :--- | :--- | :--- |
| `pille_pues` | `let` / `var` | `let` |
| `escuche_pues` | `input` / `scanf` | `erlang.get_line` |
| `hable_pues` | `print` | `io.println` |
| `hagale_pues` | `function` | `pub fn` |
| `ya_quedo` | fin de función | `}` |
| `entregue_pues` | `return` | expresión final |

### Estructuras de control

| Paisascript | Equivale a | Gleam |
| :--- | :--- | :--- |
| `si_acaso` … `entonces_pues` … `sino_pues` … `asi_quedo` | `if` / `else` | `case c { True -> … False -> … }` |
| `mientras_que` … `dele_pues` … `hasta_ahi` | `while` | recursión de cola |
| `pa_cada` … `desde` … `hasta` … `de_a` … `dele_pues` … `listo_pues` | `for` | `list.range` + `list.each` |
| `pillemos` … `pa_que_lleve` | `switch` / `match` | `case` … `->` |

### Literales y operadores con nombre

| Paisascript | Equivale a |
| :--- | :--- |
| `sizas` / `naranjas` | `true` / `false` |
| `y_tambien` / `o_que` / `nanai` | `&&` / `\|\|` / `!` |
| `igualito` / `distinto` | `==` / `!=` |
| `_` | comodín del `match` |

---

## Tipos de datos

| Paisascript | Descripción | Gleam |
| :--- | :--- | :--- |
| `numerito` | Enteros con signo | `Int` |
| `quebradito` | Reales de punto flotante | `Float` |
| `cuento` | Cadenas UTF-8 inmutables | `String` |
| `siono` | Booleanos | `Bool` |

Los **identificadores** deben empezar en minúscula o guion bajo y admiten
tildes y la letra `ñ` (`años`, `nombre_niño`). Gleam solo acepta ASCII, así que
el generador de código los transliterará.

---

## Operadores

**Aritméticos** — `+` `-` `*` `/` `%` `**` (la potencia asocia a la derecha)

**Relacionales** — `>` `<` `>=` `<=` `igualito` `distinto`

**Lógicos** — `y_tambien` `o_que` `nanai`

**Cadenas** — `<>` (concatenación, tomado literalmente de Gleam)

**Asignación** — `=`

Precedencia, de menor a mayor:

```
o_que  <  y_tambien  <  igualito/distinto  <  relacionales  <  <>
       <  + -  <  * / %  <  **  <  unarios  <  primaria
```

**Comentarios** — `// hasta el fin de la línea`, igual que en Gleam.

---

## Ejemplos de código

### Función con condicional y retorno

```
hagale_pues clasificar(numerito nota) pa_que_lleve cuento dele_pues
    si_acaso nota >= 45 y_tambien nota <= 50 entonces_pues
        entregue_pues "Sobresaliente, mijo"
    sino_pues
        entregue_pues "Se quemo, parcero"
    asi_quedo
ya_quedo
```

### Bucle `mientras_que` con acumulador

```
pille_pues numerito acumulado = 0
pille_pues numerito i = 1
mientras_que i <= n dele_pues
    pille_pues acumulado = acumulado + i
    pille_pues i = i + 1
hasta_ahi
```

### Bucle `pa_cada` con paso

```
pa_cada k desde 0 hasta 20 de_a 2 dele_pues
    si_acaso k % 3 igualito 0 entonces_pues
        hable_pues("Multiplo de tres: " <> k)
    asi_quedo
listo_pues
```

### Calce de patrones

```
pillemos resultado {
    10       pa_que_lleve hable_pues("Sacaste diez, ¡qué elegancia!")
    "error"  pa_que_lleve hable_pues("Algo salió mal, mijo")
    _        pa_que_lleve hable_pues("No sé qué pasó ahí")
}
```

---

## Arquitectura del lexer

`lexer.py` es **independiente de la interfaz** (requisito 15 del enunciado): no
imprime ni lee nada. El parser descendente recursivo de la entrega 2 podrá
consumirlo sin modificarlo.

```python
from lexer import Lexer

lexer = Lexer(codigo_fuente)
tokens = lexer.tokenizar()      # lista de Token, termina en FIN_ARCHIVO

for t in tokens:
    print(t.tipo, t.lexema, t.fila, t.columna, t.valor)

for e in lexer.errores:         # los errores NO abortan el análisis
    print(e.fila, e.columna, e.mensaje)
```

**Estructuras expuestas**

- `TipoToken` — enumeración de las 54 categorías léxicas. La propiedad
  `.categoria` deriva la categoría general del prefijo del nombre
  (`KW_` → reservada, `OP_` → operador, …), de modo que agregar un token nuevo
  no obliga a tocar ninguna tabla aparte.
- `Token` — `tipo`, `lexema`, `fila`, `columna` y `valor` (el literal ya
  convertido a `int`, `float`, `str` o `bool`).
- `ErrorLexico` — `lexema`, `fila`, `columna`, `mensaje`.
- `Lexer.resumen_identificadores()` — identificadores distintos con todas sus
  posiciones; es el germen de la tabla de símbolos de la entrega 3.

**Estrategia.** Una sola expresión regular alternada con grupos nombrados,
recorrida con `re.finditer`. Como Python devuelve la *primera* alternativa que
casa y no la más larga, el orden de la especificación **es** la tabla de
prioridades: `//` antes que `/`, `**` antes que `*`, `<>` y `<=` antes que `<`,
y `NUM_REAL` antes que `NUM_ENTERO`.

Las palabras reservadas **no** están en la expresión regular: se reconoce
primero un identificador completo y luego se consulta el diccionario
`PALABRAS_RESERVADAS`. Así `pille_puesX` es un identificador y no la palabra
reservada `pille_pues` seguida de `X`, sin depender de trucos con `\b`.

**Errores.** Se detectan tres clases —carácter fuera del alfabeto, literal de
cadena sin cerrar e identificador que empieza en mayúscula— y ninguna detiene
el recorrido: se registran en `lexer.errores` y el análisis continúa con el
siguiente carácter.

---

## Coherencia con Gleam

Gleam es funcional, inmutable y de tipado estático. **No tiene `if`, `while`,
`for`, `break`, `continue` ni `return`**: solo `case` y recursión. Eso
condicionó el diseño de Paisascript:

- **No hay asignación sin `pille_pues`.** Toda "reasignación" es *shadowing*,
  exactamente como el `let` de Gleam. El lenguaje es inmutable.
- **`NUM_ENTERO` y `NUM_REAL` son tokens distintos** desde el análisis léxico,
  porque Gleam usa operadores diferentes para cada tipo (`+` contra `+.`).
- **Los bloques se cierran con palabra reservada** (`ya_quedo`, `asi_quedo`,
  `hasta_ahi`, `listo_pues`), lo que hace la gramática LL(1) sin tokens de
  indentación y se traduce directo a la llave de cierre de Gleam.
- **`pillemos` y `<>` se tomaron prestados de Gleam**: la traducción es token a
  token.

Los cuatro constructos que el enunciado exige y Gleam no tiene se traducen así:

| Paisascript | Gleam |
| :--- | :--- |
| `si_acaso` / `sino_pues` | `case c { True -> … False -> … }` |
| `mientras_que` | función auxiliar recursiva de cola |
| `pa_cada` | `list.range` + `list.each`, o recursión de cola si el paso ≠ 1 |
| `entregue_pues` | última expresión del cuerpo; el retorno anticipado se reestructura en las ramas del `case` |

Las traducciones trabajadas de punta a punta están en
[`MAPEO_GLEAM.md`](MAPEO_GLEAM.md).

---

## Cumplimiento del enunciado

### Entregable 1 — Gramática BNF

| Requisito | Dónde |
| :--- | :--- |
| Descripción informal (vocabulario, tipos, alcance) | §1 de la gramática |
| Conjunto de terminales por categoría | §2 |
| Producciones sin recursividad izquierda | §3 (46 producciones) |
| Verificación de la condición LL(1) | §4 (conjuntos PRIMERO y SIGUIENTE) |
| Ejemplos de programas válidos e inválidos | §5 y §6 |
| Justificación de coherencia con el destino | §7 y `MAPEO_GLEAM.md` |

### Entregable 2 — Analizador léxico

| Requisito | Dónde |
| :--- | :--- |
| Módulo reutilizable | `lexer.py`, consumido por dos interfaces sin modificarlo |
| Ingreso libre o predefinido | `app.py` y `main.py`, los tres modos |
| Visualización gráfica de tokens con colores | Pestañas «Código segmentado» y «Flujo de tokens» |
| Tabla de símbolos con fila y columna | Pestaña «Tabla de símbolos», descargable en CSV |
| Reporte de errores sin abortar | Pestaña «Errores léxicos», con cursor bajo el error |
| Código documentado + README | Este archivo |

### Capacidades mínimas del §2 del enunciado

| # | Capacidad | Paisascript |
| :-- | :--- | :--- |
| 1 | Palabras e identificadores en español, con tildes y `ñ` | ✅ |
| 2 | Suma, resta, multiplicación, división, módulo y potencia | ✅ `+ - * / % **` |
| 3 | Conjunción, disyunción, negación | ✅ `y_tambien` `o_que` `nanai` |
| 4 | Igual, distinto, menor, mayor, menor o igual, mayor o igual | ✅ |
| 5 | Condicional `si … entonces … sino … fin_si` | ✅ `si_acaso … entonces_pues … sino_pues … asi_quedo` |
| 6 | Repetición `para … hacer … fin_para` con variable de control | ✅ `pa_cada … dele_pues … listo_pues` |
| 7 | Repetición `mientras … hacer … fin_mientras` | ✅ `mientras_que … dele_pues … hasta_ahi` |
| 8 | Definición de funciones (destino de scripting/funcional) | ✅ `hagale_pues … ya_quedo` |
| 9 | Enteros, reales, cadenas y booleanos | ✅ `numerito` `quebradito` `cuento` `siono` |
| 10 | Asignación y retorno | ✅ `pille_pues` y `entregue_pues` |
