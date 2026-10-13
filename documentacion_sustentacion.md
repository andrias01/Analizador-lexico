# Documentación de sustentación — Quiz 3: Analizador Sintáctico Ascendente LALR(1)

> Guía de estudio y de presentación **enfocada en el Quiz 3** (Análisis Sintáctico
> Ascendente LALR(1)) del proyecto **Paisascript**, curso de Teoría de
> Compiladores, UCO.
>
> Equipo: **Angie Amaya Fernández**, **Julián David Guarnizo Castrillón**,
> **Andrés Felipe Vélez**.
>
> **Todo lo que se afirma aquí fue verificado ejecutando el código del
> repositorio** (`generador_lalr1_completo.py` + `parser_lalr.py`), no es una
> descripción de intenciones. La sección B lista las cifras medidas y la
> sección C.4 explica qué se tuvo que corregir para llegar a ellas.

---

## A. Qué exige el Quiz 3 (lectura del enunciado)

El objetivo es **integrar al compilador un módulo de análisis sintáctico
ascendente LALR(1)** que verifique si una cadena de tokens del lexer pertenece
al lenguaje de la gramática Paisascript. El enunciado es explícito en tres
cosas:

1. **No se elimina el LL(1)** del Quiz 2: el LALR(1) se agrega *en paralelo o
   como alternativa configurable*. Nuestro caso: la barra lateral de la app ya
   tiene los tres métodos (`app.py:459`), y el método 3 es
   **"3. Ascendente LALR(1)"**.
2. **Entregables** (§3 del enunciado):
   * **E1.** Código fuente del analizador LALR(1) integrado al compilador.
   * **E2.** Tabla **ACTION/GOTO completa** resultante de la fusión de estados.
   * **E3.** **Traza del análisis** para cualquier cadena ingresada: se debe
     indicar si es válida o inválida y mostrar el paso a paso con
     **(número de paso, pila, cadena de entrada restante, acción ejecutada)**.
3. **Criterios de evaluación** (§4):

   | Componente | Puntaje |
   |---|---|
   | Construcción correcta de la tabla ACTION/GOTO LALR(1) | **25 %** |
   | Traza de análisis completa y correcta | **25 %** |
   | Capacidad de responder claramente preguntas sobre la tabla LALR(1) y las acciones | **50 %** |

> **Lectura estratégica:** la mitad de la nota es **saber explicar**. La buena
> noticia es que los tres entregables ya están implementados y verificados
> (sección B), así que todo el esfuerzo de preparación puede ir a la sección F
> (preguntas con respuesta) y a la sección G (reparto de roles).

---

## B. Estado del proyecto: los tres entregables están completos

| Entregable | Estado | Evidencia en el código |
|---|---|---|
| **E1.** Analizador LALR(1) integrado | ✅ **Completo** | **Driver LR real** en `parser_lalr.py`: `ParserLALR1.parse_con_pasos()` (`:301`) es el bucle pila-estados / entrada con `desplazar`, `reducir`, `aceptar` y `error`. Se integra en la app en `app.py:322-357`, donde el método 3 **sustituye** al motor LL(1): los errores que se muestran en las pestañas AST y "Errores" provienen del LALR(1), no del LL(1). |
| **E2.** Tabla ACTION/GOTO completa | ✅ **Completo** | **ACTION y GOTO reales, indexadas por estado**, construidas desde los items del autómata fusionado: `_construir_tabla_action_estados` (`parser_lalr.py:153`) y `extract_goto_lalr1` (`generador_lalr1_completo.py:244`). `construir_dataframes_lalr1` (`parser_lalr.py:616`) las expone como **ACTION 195 × 55** y **GOTO 195 × 52**, con CSV descargable y leyenda de `r{k}`. |
| **E3.** Traza paso a paso LALR | ✅ **Completo** | `parse_con_pasos` devuelve `(árbol, traza, válido, error)` con **`Paso` · `Pila` · `Entrada` · `Acción`** más la lista **`Estados`** de la pila. La app la renderiza en la pestaña "Traza LALR(1)" (`app.py:743`) como `Pila (símbolo·estado)` · `Entrada restante` · `Acción`, con detalle por paso en expanders y descarga CSV. |
| **50 % preguntas** | 📚 Cubierto por este documento | Sección F. |

### Cifras verificadas (para citar sin dudar)

Medidas ejecutando `venv/bin/python` sobre `generar_tabla_lalr1_completa()` +
`construir_dataframes_lalr1()`:

| Métrica | Valor |
|---|---|
| Estados LR(1) canónicos | **1703** |
| Estados LALR(1) tras la fusión por núcleo | **195** |
| Estados eliminados por la fusión | **1508** |
| **Reducción** | **88.5 %** |
| Tabla **ACTION** | **195 filas × 55 columnas** = 3231 celdas |
| · de ellas, `s{n}` (desplazar) | **499** |
| · de ellas, `r{k}` (reducir) | **2730** |
| · de ellas, `acc` (aceptar) | **2** (`$` y `FIN_ARCHIVO`) |
| Tabla **GOTO** | **195 filas × 52 columnas**, **402** entradas llenas |
| No terminales | **52** |
| Producciones numeradas (`r1 … r106`) | **106** |
| **Conflictos desplazar-reducir** | **0** |
| **Conflictos reducir-reducir** | **0** |
| Tiempo de generación | **≈2.1 s** |
| No terminales sin ninguna entrada GOTO | **1** → solo `<programa>` |

> ⚠️ **Ojo con una cifra vieja:** versiones anteriores de este documento y de la
> app citaban *1878 → 325 estados y 82 entradas GOTO*. Esos números **ya no
> aplican**. Si alguien los recuerda de la presentación anterior, la cifra
> correcta hoy es **1703 → 195 (88.5 %)** y **402 entradas GOTO**.

### Cómo verificar todo en un minuto

```bash
# 1) Genera las tablas y las cifras del encabezado
venv/bin/python generador_lalr1_completo.py

# 2) Levanta la app y selecciona "3. Ascendente LALR(1)" en la barra lateral
venv/bin/streamlit run app.py

# 3) Los tres métodos conviven y analizan la misma entrada sin errores
venv/bin/python main.py     # consola (recursivo + tablas LL(1))
```

## C. Cómo está implementado (lo que hay que poder explicar)

> Esta es la sección que sostiene el 50 % de la nota. Si van a estudiar algo
> de este documento, que sea **C.1, C.2 y C.4**.

### C.1 Flujo de datos (el pipeline completo)

```
     código fuente
          │
          ▼
     lexer.py ──► lista de tokens ───────────────────────────────────────────────┐
          │                                                                      │
          ▼                                                                      ▼
 ┌───────────────────────────────┐               ┌───────────────────────────────┐
 │ generador_lalr1_completo.py   │               │ parser_lalr.py                │
 │            (~415 líneas)      │               │            (~690 líneas)      │
 │                               │               │                               │
 │ 1. FIRST / FOLLOW             │               │ generar_parser_lalr1()        │
 │    (reutiliza tabla_ll1)      │               │    ├─ ACTION   por estado     │
 │ 2. cierre LR(1)               │               │    └─ GOTO     por estado     │
 │    cerrar_lr1_v3()            │               │                               │
 │ 3. GOTO                       │               │ ParserLALR1                   │
 │    goto_lr1_v3()              │──► 195 ──►    │    .parse_con_pasos(tokens)   │
 │ 4. autómata LR(1)             │               │         └─► (árbol, traza,    │
 │    build_lr1_automaton()      │               │               válido, error)  │
 │    → 1703 estados             │               │                               │
 │ 5. fusión por núcleo          │               │ app.py  —  método 3           │
 │    merge_lr1_states_by_core   │               │    pestaña "Traza LALR(1)"    │
 │    → 195 estados (88.5 %)     │               │       (app.py:743)            │
 │ 6. transiciones               │               │    pestaña "Tabla ACTION/GOTO"│
 │    extract_goto_lalr1()       │               │       (app.py:873)            │
 │    terminal_transitions       │               │                               │
 │    → SHIFT  s{n}              │               │                               │
 └───────────────────────────────┘               └───────────────────────────────┘
```

**Punto único de verdad de la gramática:** `generador_lalr1_completo.py:18`
importa `GRAMATICA_BNF` desde `tabla_ll1.py` (la misma gramática del Quiz 2).
`parser_lalr.py:20` mantiene **su propia copia** con los mismos **52 no
terminales** y **106 producciones**, escrita con los nombres de token del lexer
(`KW_DECLARACION`, `KW_IMPRESION`, …). Si preguntan "¿por qué dos copias?",
la respuesta honesta es: *porque el parser necesita la gramática en el mismo
módulo que el driver para construir `r{k}`; conviene unificarlas en un solo
módulo, pero hoy ambas coinciden en conteo y contenido*.

### C.2 De dónde sale cada acción de la tabla

Es la pregunta que más probablemente harán con la tabla en la mano
(`_construir_tabla_action_estados`, `parser_lalr.py:153`):

1. **`s{n}` — desplazar.** Sale de las **transiciones por terminales**
   (`terminal_transitions`, calculadas directamente de los items del estado:
   el terminal que está *justo después del punto*). Si en el estado `i` el
   punto está antes del terminal `a` y `GOTO(i, a) = j`, la celda es `s{j}`.
2. **`r{k}` — reducir.** Sale de los **items con el punto al final**
   (`[A → α·, a]`). El lookahead usado es el **lookahead del item unido con
   SIGUIENTE(A)**. `k` es el índice de la producción en la lista de 106.
3. **`acc` — aceptar.** Se escribe en el estado donde
   `[<programa> → <programa>·, $]` está completo: `ACTION[i, '$'] = 'acc'`
   (`parser_lalr.py:217-222`). Como el lexer emite el token `FIN_ARCHIVO` y no
   `$`, la misma aceptación se duplica en `ACTION[i, 'FIN_ARCHIVO']`
   (`:224-226`) — de ahí que haya **2** celdas `acc` y no una. No es un error:
   es el puente entre el marcador teórico `$` y el token real del lexer.
4. **vacío — error sintáctico.** Ninguna de las anteriores.
5. **`GOTO[i, A]`.** Columnas de no terminales: estado destino al que se llega
   al empujar `A` en el estado `i` (`extract_goto_lalr1`, `generador_lalr1_completo.py:244`).

**Orden de escritura y resolución de conflictos.** En cada estado se escriben
primero los **shift** y luego los **reduce**, y un reduce **solo llena celdas
aún vacías**. Eso implementa la regla estándar *"gana el desplazar"*. Pero
medimos el caso y **nunca llegó a hacer falta arbitrar**:

> **Verificado:** sobre las 195 filas reales hay **0** celdas donde convivan
> dos `r{k}` distintos y **0** celdas donde un shift y un reduce compitan.
> Es decir: la tabla no tiene conflictos *ni siquiera resueltos por prioridad*.

### C.3 El driver LR y su traza

`ParserLALR1.parse_con_pasos()` (`parser_lalr.py:301`) es el bucle clásico:

```
pila = [símbolo, estado]      entrada = tokens + [FIN_ARCHIVO, "$"]
bucle:
    i = estado en la cima de la pila
    a = primer token de la entrada
    acción = ACTION[i][a]
      "s{n}"  → desapila nada; apila (a, n); avanza la entrada
      "r{k}"  → desapila 2·|α| elementos (k símbolos + k estados);
                j = estado que queda en la cima;
                apila (A, GOTO[j][A]);     la entrada NO avanza
      "acc"   → termina: cadena válida
      vacío   → termina: error sintáctico en el paso exacto
```

Cada vuelta registra un paso con `Paso`, `Pila`, `Estados`, `Entrada` y
`Acción` a través del cerradura `_registrar` (`parser_lalr.py:325`).

**Convención de la pila (importante para la sustentación):** la pila se
muestra como pares `símbolo·estado`, y **el estado que aparece al lado de un
símbolo es el estado alcanzado tras consumir ese símbolo**. El estado que se
consulta en ACTION del paso siguiente es **el último de la lista**. Esto
permite leer la traza sin tener que contar niveles en el texto plano.

### C.4 Los seis bichos que hubo que cazar

> Si preguntan **"¿qué fue lo más difícil?"**, esta es la respuesta. Cada
> hallazgo tiene síntoma, causa y arreglo. Practíquenla en voz alta: demuestra
> depuración real, que es lo que separa un proyecto escrito de uno entendido.

| # | Síntoma | Causa | Arreglo |
|---|---|---|---|
| **1** | **"No hay definida acción para Estado[0] / Entrada[KW_LECTURA('escuche_pues')]"** — el error original del proyecto. | `merge_lr1_states_by_core` agrupaba los estados LR(1) **de a pares**: solo juntaba dos estados cuyo núcleo coincidiera *en ese momento*, dejando **300** estados en lugar de 195 y transiciones apuntando a réplicas distintas del mismo núcleo. | Agrupar **todos** los items por núcleo en un solo `defaultdict` antes de reconstruir los estados: **300 → 195**. |
| **2** | El parser desplazaba, pero a un estado equivocado. | `_construir_tabla_action_estados` "seguía" recursivamente las transiciones GOTO de **no terminales** y terminaba registrando el estado destino *final* como si fuera un shift inmediato. | Eliminar el seguimiento recursivo: un shift solo nace de una transición por **terminal**. |
| **3** | `"Pila insuficiente para reduce"`. | Las producciones ε se representaban como `['ε']`, así que el driver intentaba desapilar **un** símbolo y **un** estado para una producción que no consume nada. | Normalizar ε a `[]`/`()` en toda la lógica: se desapilan **0** elementos; `ε` se muestra solo en la interfaz. |
| **4** | No aparecían los `r{k}` de las producciones vacías (p. ej. `<sufijo_id> → ε` sobre `PAR_CIERRA`). | `prod_list` y `prod_to_num` no normalizaban la clave de la producción: `('ε',)` y `()` son claves distintas, así que la búsqueda fallaba en silencio. | Clave canónica `()` para toda producción ε en ambos diccionarios (`parser_lalr.py:177-183`). |
| **5** | **Bucles infinitos** al reducir. | Como respaldo, si no existía el `GOTO` pedido se tomaba **el de cualquier otro no terminal**. Eso manda a estados arbitrarios y el parser nunca converge. | Eliminar el respaldo: `GOTO` ausente ⇒ **error explícito**. |
| **6** | Se rompían los programas con **varias sentencias**. | `extract_goto_lalr1` y `terminal_transitions` descartaban toda transición con `next_idx == state_idx`, confundiendo un **bucle propio legítimo** con una transición inválida. Eso borraba `GOTO(1, <declaracion>) = 1`. | Dejar de excluir los bucles propios. Es el que permite que `<declaracion>` en el estado 1 reciba una sentencia tras otra. |

> **Frase útil para la sustentación:** *"el 88.5 % de reducción suena bien, pero
> no sirve de nada si la fusión no remapea las transiciones: los seis primeros
> problemas que tuvimos eran exactamente eso."*

### C.5 Decisiones de diseño que conviene poder justificar

* **ε en `[]`/`()` adentro, `ε` en pantalla.** Evita pops fantasma (hallazgo 3)
  y mantiene la tabla legible.
* **El lookahead de reduce es `lookahead del item ∪ SIGUIENTE(A)`.** Es una
  unión **redundante** respecto al LALR puro (el item ya trae su lookahead
  correcto); la dejamos como red de seguridad. **Medimos su efecto: 0 solapes**,
  así que no diluye la tabla. Si preguntan por ella, díganlo así: *era una
  redundancia defensiva y comprobamos que no introduce conflictos*.
* **Shift primero, reduce después y solo en celdas vacías.** Implementa "gana el
  desplazar" de forma estructural, sin una rama especial de resolución.
* **`FIN_ARCHIVO` duplica a `$` en la aceptación** (ver C.2 punto 3).
* **Los lexemas solo se muestran donde aportan información**
  (`IDENTIFICADOR`, `NUM_ENTERO`, `NUM_REAL`, `CADENA_LITERAL`); para el resto
  el nombre del tipo ya dice todo. Es lo que hace legible una pila como
  `$·0 KW_IMPRESION·17 PAR_ABRE·33 NUM_ENTERO(42)·50` en lugar de
  `$·0 KW_IMPRESION(hable_pues)·17 PAR_ABRE(()·33 NUM_ENTERO(42)·50`.

---

## D. Fundamento teórico: cómo funciona un analizador ascendente LALR(1)

> Esta es la teoría que respalda las preguntas de la sección F. Corresponde a
> lo que el docente espera oír cuando pida "explique la tabla y las acciones".

### D.1 Bottom-up: la idea central

LL(1) es **top-down**: empieza en `<programa>` y *expande* hacia abajo hasta
casar la entrada. LALR(1) es **bottom-up**: empieza en la entrada y *reduce*
hacia arriba, reconociendo **prefijos viables** hasta que la pila contiene
`<programa>` y la entrada `$`. Es construir la **derivación al revés**.

### D.2 Items LR(1)

Un item es una producción con un punto: `[A → α · β, a]`. El punto separa lo
ya leído (`α`) de lo que falta (`β`); `a` es el **lookahead de 1 token** que
solo importa cuando el punto está al final (`[A → α·, a]` ⇒ candidato a
reducir con `a` en la mano). Sin lookaheads individuales se tendrían items
LR(0) y la gramática SLR; con lookaheads explícitos se tiene LR(1) canónico,
que es lo que construye `generador_lalr1_completo.py` (`cerrar_lr1_v3`,
`:98-147`, item = `(nt, producción, punto, lookahead)`).

### D.3 Cierre y transición (GOTO)

* **Cierre** (`cerrar_lr1_v3`): si el punto está antes de un no terminal `B`,
  se agregan los items de `B` con lookahead = `FIRST(βa)`
  (`_calcular_first_beta_la`, `:68-97`). Es la misma idea de PRIMERO que en
  LL(1), pero aplicada item por item.
* **GOTO(I, X)** (`goto_lr1_v3`, `:148-167`): mover el punto sobre `X` en todos
  los items que lo tengan y recalcular cierre. Cada GOTO distinto es un
  **estado** nuevo del autómata.

### D.4 LALR(1) = LR(1) fusionado por núcleo

El LR(1) canónico de Paisascript tiene **1703 estados**; son muchos porque
estados con el mismo "cuerpo" pero distintos lookaheads quedan separados.
**LALR(1)** fusiona en un solo estado los que comparten **núcleo** (conjunto de
items **sin** los lookaheads) y une sus lookaheads: 1703 → **195**, una
reducción del **88.5 %**. La ventaja: tablas pequeñas. El riesgo: la fusión
puede crear **conflictos de reducir-reducir** que LR(1) no tenía — aquí no
ocurrió (**0 conflictos**, medido; ver C.2). Nuestro código hace exactamente
esto en `merge_lr1_states_by_core` (`:216-243`).

### D.5 Las tablas ACTION y GOTO

* **GOTO[i, A]**: estado destino tras reducir/consumir el no terminal `A`
  estando en el estado `i`. (Solo columnas de no terminales: **195 × 52**.)
* **ACTION[i, a]**: qué hacer en el estado `i` con lookahead `a` (solo
  columnas de terminales + `$`: **195 × 55**), con exactamente tres formas:
  * **`s j` (desplazar/shift):** hay transición por terminal `a`; se empuja
    `a` y el estado `j` a la pila y se avanza la entrada.
  * **`r k` (reducir/reduce):** hay un item completo `[A → α·, a]` y `k` es el
    número de la producción `A → α`. Se desapilan `2·|α|` elementos (símbolos
    y estados), se empuja `A` y el estado `GOTO[pila.top, A]`. **La entrada NO
    avanza** (el lookahead se reexamina).
  * **`acc` (aceptar):** el item `[<programa> → <programa>·, $]` en el estado
    inicial con `$` en la entrada.
  * **vacío = error sintáctico.**
* **Regla de decisión (por qué no hay ambigüedad):** si en un estado conviven
  *desplazar* y *reducir*, gana el **desplazar** (en LALR/SLR estándar); si hay
  dos *reducir* para la misma celda, es **conflicto de reducir-reducir** y la
  gramática no es LALR(1). Nuestra gramática: **ni siquiera llega a esos casos**
  — 0 celdas de cada tipo.

### D.6 El algoritmo del parser (lo que traza la app)

Pila de **estados** (con los símbolos intercalados solo para legibilidad),
entrada con `$`, y el bucle: mirar `ACTION[pila.top, entrada[0]]` →
desplazar / reducir / aceptar / error. Cada vuelta es un **paso de la traza**
con el cuádruple que pide el enunciado: **número, pila, entrada restante,
acción**. El análisis termina cuando la acción es `acc` (válido) o vacía
(inválido, y el paso exacto del fallo es el diagnóstico).

### D.7 Relación con lo ya hecho en el Quiz 2

* El LALR(1) **no reemplaza** al LL(1): los tres métodos conviven en la app.
* **Toda gramática LL(1) es también LALR(1)** (y LR(1), y SLR): las
  transformaciones que ya hicimos — eliminar recursión por la izquierda y
  factorizar por la izquierda — no perjudican a LALR; simplemente no son
  obligatorias para él (LR no necesita esas transformaciones).
* **PRIMERO/SIGUIENTE se reutilizan**: el cierre LR(1) los usa item por item
  (`_calcular_first_beta_la`) y el propio builder de ACTION los usa como red de
  seguridad en las reducciones (C.5).

---

## E. Qué muestra la app con el método 3

Barra lateral → **`3. Ascendente LALR(1)`** (`app.py:459`). La generación tarda
≈2.1 s y alimenta dos pestañas:

| Pestaña | Contenido |
|---|---|
| **Traza LALR(1)** (`app.py:743`) | DataFrame `Paso / Pila (símbolo·estado) / Entrada restante / Acción`, con la leyenda de `r{k}`, un expander por paso (estado tope, árbol parcial), y **descarga CSV**. Arriba: `st.success("Análisis LALR(1) completado con éxito")` si terminó en `acc`, o el aviso de error si no. |
| **Tabla ACTION/GOTO** (`app.py:873`) | **ACTION 195 × 55** y **GOTO 195 × 52** con descarga CSV cada una, leyenda de las 106 producciones (`r{k}` → `nt → β`), leyenda de notación (`s`/`r`/`acc`/vacío) y un **🔎 Inspector de estado**: al elegir un estado muestra sus acciones, sus transiciones GOTO y sus **items LALR(1) con el punto y el lookahead**. |

Las demás pestañas (AST, tablas LL(1), tabla de símbolos, errores, IA) siguen
funcionando igual que en el Quiz 2 — el LALR no las tocó.

### E.1 Traza de una cadena **válida**: `hable_pues(42)` (29 pasos)

| Paso | Pila (símbolo·estado) | Entrada restante | Acción |
|---|---|---|---|
| 1 | `$·0 KW_IMPRESION·17` | `PAR_ABRE NUM_ENTERO PAR_CIERRA FIN_ARCHIVO $` | shift a estado 17 |
| 2 | `$·0 KW_IMPRESION·17 PAR_ABRE·33` | `NUM_ENTERO PAR_CIERRA FIN_ARCHIVO $` | shift a estado 33 |
| 3 | `$·0 KW_IMPRESION·17 PAR_ABRE·33 NUM_ENTERO(42)·50` | `PAR_CIERRA FIN_ARCHIVO $` | shift a estado 50 |
| 4 | `$·0 KW_IMPRESION·17 PAR_ABRE·33 <expr_primaria>·41` | `PAR_CIERRA FIN_ARCHIVO $` | reduce 36: `<expr_primaria> → NUM_ENTERO` |
| 5 | `$·0 KW_IMPRESION·17 PAR_ABRE·33 <expr_unaria>·43` | `PAR_CIERRA FIN_ARCHIVO $` | reduce 50: `<expr_unaria> → <expr_primaria>` |
| 6 | `$·0 KW_IMPRESION·17 PAR_ABRE·33 <expr_unaria>·43 <expr_potencia_p>·85` | `PAR_CIERRA FIN_ARCHIVO $` | reduce 34: `<expr_potencia_p> → ε` |
| ⋮ | ⋮ | ⋮ | ⋮ |
| 26 | `$·0 <declaracion>·1` | `FIN_ARCHIVO $` | reduce 11: `<declaracion> → <sentencia>` |
| 27 | `$·0 <declaracion>·1 <lista_declaraciones>·24` | `FIN_ARCHIVO $` | reduce 59: `<lista_declaraciones> → ε` |
| 28 | `$·0 <lista_declaraciones>·3` | `FIN_ARCHIVO $` | reduce 58: `<lista_declaraciones> → <declaracion> <lista_declaraciones>` |
| 29 | `$·0 <lista_declaraciones>·3` | *(vacía)* | **accept** |

**Qué señalar aquí (dos minutos que valen oro):**

* **Pasos 1–3 son desplazamientos:** el parser consume tokens de la entrada.
* **Pasos 4–6 son reducciones encadenadas:** mira la columna *Entrada* — no
  cambia entre el paso 4 y el 5. Eso es la prueba visual de que **reducir no
  consume entrada** (P15).
* **El paso 6 es `→ ε`:** la pila **crece** (`<expr_potencia_p>·85`) sin que se
  haya leído ningún token. Es el momento perfecto para explicar las
  producciones vacías en un parser bottom-up.
* **Los pasos 26–28 deshacen la pila:** `<declaracion>·1` y luego
  `<lista_declaraciones>·3` — el estado 3 es exactamente `GOTO[0, <lista_declaraciones>]`,
  que aparece en la fila 0 de la tabla GOTO.
* **El paso 29 es `accept`.**

### E.2 Traza de una cadena **inválida**: `si_acaso 1 > 0 entonces_pues hable_pues(1)` (61 pasos)

| Paso | Pila (símbolo·estado) | Entrada restante | Acción |
|---|---|---|---|
| 59 | `$·0 KW_SI·23 <expresion>·58 KW_ENTONCES·97 <sent_impresion>·5` | `FIN_ARCHIVO $` | reduce 80: `<sent_impresion> → KW_IMPRESION PAR_ABRE <expresion> PAR_CIERRA` |
| 60 | `$·0 KW_SI·23 <expresion>·58 KW_ENTONCES·97 <sentencia>·123` | `FIN_ARCHIVO $` | reduce 90: `<sentencia> → <sent_impresion>` |
| 61 | `$·0 KW_SI·23 <expresion>·58 KW_ENTONCES·97 <sentencia>·123` | `FIN_ARCHIVO $` | **error** |

> `Paso 61: No hay definida acción para Estado[123] / Entrada[FIN_ARCHIVO('')]`

La cadena es inválida porque le falta el `asi_quedo` que cierra el `si_acaso`.
Y la app **lo puede demostrar mirando la tabla**: en el **estado 123** hay
**15 celdas no vacías** y justo `$` no es una de ellas:

* `s14 … s23` sobre `IDENTIFICADOR`, `KW_DECLARACION`, `KW_LECTURA`,
  `KW_IMPRESION`, `KW_MIENTRAS`, `KW_PARA`, `KW_PILLEMOS`, `KW_RETORNAR`,
  `KW_SI` → *o empieza otra sentencia…*
* `r61` (`<lista_sentencias> → ε`) sobre `KW_FIN_SI`, `KW_SINO`,
  `KW_FIN_MIENTRAS`, `KW_FIN_PARA`, `KW_FIN_FUNCION`, `LLAVE_CIERRA`
  → *…o cierra el bloque con un token de cierre.*
* **`FIN_ARCHIVO`: vacía ⇒ error.**

Ese es el argumento completo: **el estado 123 acepta otra sentencia o un
cierre de bloque, pero nunca el fin del archivo**. Es lo que hace que la
gramática exija `asi_quedo`. Pueden mostrarlo en vivo con el 🔎 Inspector de
estado, seleccionando el estado 123.

### E.3 Los tres métodos, la misma entrada

Con `pille_pues numerito x = 5` + `hable_pues(x + 1)`, los tres analizadores
terminan **sin errores**:

| Método | Pasos de su traza |
|---|---|
| 1. Descendente Recursivo | **89** |
| 2. Predictivo LL(1) | **70** |
| 3. Ascendente LALR(1) | **69** |

Es un dato rápido y contundente: **el LR da trazas más cortas que el LL(1)**
porque un solo paso LR puede reducir varios niveles de la gramática, mientras
que el LL(1) empuja producciones completas a la pila en cada expansión.

---

## F. Preguntas de sustentación sobre LALR(1) con respuestas

> Concentradas en lo que el Quiz pondera (50 %): *la tabla LALR(1) y las
> acciones que se toman a partir de ella*. Cada respuesta está escrita para
> decirse en 15–30 segundos. **P1–P19** son las imprescindibles (conceptos,
> tablas y traza); **P20–P33** son las de *nuestro código*, que el Quiz pide
> explícitamente; **P34–P44** son preguntas trampa y del Quiz 2.

### F.1 Conceptos de análisis ascendente

**P1. ¿Qué es el análisis sintáctico ascendente (bottom-up)?**
Un recorrido de izquierda a derecha que, en lugar de expandir desde la raíz
como hace el descendente, va reconociendo **prefijos viables** de la entrada y
**reduce** los símbolos leídos a no terminales, hasta que la pila contiene el
símbolo inicial y la entrada está en `$`. Es construir la derivación **al
revés**: el orden de reducciones es el orden inverso de las expansiones que
haría un parser descendente.

**P2. ¿Qué es un item LR(1) y en qué se diferencia del item LR(0)?**
Una producción con un punto y un lookahead: `[A → α · β, a]`. El punto indica
qué se ha consumido (`α`) y qué falta (`β`); `a` es el único token de
anticipación, y solo se usa cuando el punto está al final
(`[A → α·, a]`): señala con qué terminales se puede **reducir** esa producción.
El item LR(0) es lo mismo **sin** el lookahead (`[A → α · β]`); con él solo se
construye SLR, que es menos preciso.

**P3. ¿Qué es el cierre (closure) de un conjunto de items?**
Regla: si `[A → α · Bβ, a]` está en el conjunto y `B` es no terminal, se
agregan todos los items `[B → ·γ, b]` con `b ∈ FIRST(βa)`. En nuestro código,
`cerrar_lr1_v3` (`generador_lalr1_completo.py:98-147`) itera hasta que no hay
items nuevos y `_calcular_first_beta_la` (`:68-97`) calcula ese FIRST(βa): si
`β` está vacío el lookahead es `a`; si `β` empieza con terminal, ese terminal;
si `β` empieza con no terminal, FIRST de ese no terminal (y si puede ser vacío,
sigue con el siguiente símbolo).

**P4. ¿Qué es GOTO y cómo se generan los estados?**
`GOTO(I, X)` = cierre del conjunto de items que resulta de **mover el punto un
paso sobre el símbolo `X`** en todos los items de `I` donde el punto esté
antes de `X`. Cada GOTO distinto es un **estado** nuevo del autómata. El
algoritmo arranca con el cierre del item inicial y aplica GOTO para cada
símbolo que aparezca después de un punto, deduplicando estados idénticos
(`build_lr1_automaton`, `:168-215`).

**P5. ¿Qué es LALR(1) exactamente y por qué se llama "fusionado"?**
Es LR(1) **reducido**: se construye el autómata LR(1) canónico y luego se
**fusionan en un solo estado** todos los que tienen el mismo **núcleo** (los
items **sin** lookaheads), uniendo sus lookaheads. "LALR" = *Look-Ahead LR*:
el lookahead es de 1 token pero los estados son los del LR(0) fusionados. En
nuestro proyecto: **1703 estados LR(1) → 195 LALR(1)**, una reducción del
**88.5 %** (`merge_lr1_states_by_core`, `:216-243`; medido ejecutando el
generador).

**P6. ¿Por qué LALR(1) y no LR(1) canónico o SLR?**
* vs **LR(1) canónico**: tendría los 1703 estados con lookaheads explícitos →
  tablas gigantes; LALR los colapsa a 195 sin perder capacidad en esta
  gramática (0 conflictos nuevos).
* vs **SLR**: SLR usa solo el item LR(0) y decide reducir consultando
  SIGUIENTE(A); es más simple pero **más conflictos** (reduce con tokens que
  en contexto no correspondían). LALR reparte los lookaheads por estado y
  resuelve esos conflictos.
* En la práctica: **bison/yacc son LALR(1)** — es el estándar de la industria
  para parsers generados.

**P7. ¿LALR(1) acepta más o menos gramáticas que LL(1)?**
**Más.** Toda gramática LL(1) es también LALR(1) (con la gramática aumentada),
pero no al revés: LALR no exige eliminar recursión por la izquierda ni
factorizar, porque decide **al final de cada producción** con el lookahead, no
al inicio. Por eso la gramática Paisascript, ya LL(1), es trivialmente
LALR(1) — y además lo verificamos: 0 conflictos.

**P8. ¿Cuál es la desventaja de LALR(1) frente a LR(1)?**
La fusión puede mezclar lookaheads de dos estados distintos en uno solo y
crear **conflictos de reducir-reducir** que LR(1) no tenía. Es el precio a
pagar por las tablas pequeñas. (El LR(1) acepta estrictamente más gramáticas
que LALR(1).) En Paisascript no se produjo ningún conflicto, así que la fusión
fue gratis.

### F.2 Las tablas ACTION y GOTO

**P9. ¿Qué contiene la tabla ACTION y qué la GOTO?**
* **ACTION**: filas = **estados**; columnas = **terminales + `$`**; celdas =
  `s{n}` (desplazar al estado `n`), `r{k}` (reducir con la producción `k`),
  `acc`, o vacío (error). Es la que dice **qué hacer**. En nuestro caso:
  **195 × 55**, con 499 `s`, 2730 `r` y 2 `acc`.
* **GOTO**: filas = **estados**; columnas = **no terminales**; celdas = estado
  destino al que se llega tras empujar ese no terminal. Es la que dice **a
  dónde ir** después de una reducción. En nuestro caso: **195 × 52**, con 402
  entradas llenas.
La separación ACTION (terminales) / GOTO (no terminales) refleja el hecho LR de
que el lookahead es terminal.

**P10. ¿De dónde sale cada acción en su tabla?**
* `s{n}` → de las **transiciones por terminales** del autómata: si en el estado
  `i` el punto está antes del terminal `a` y el GOTO va a `n`, la celda es
  `s{n}`.
* `r{k}` → de los **items completos** `[A → α·, a]` del estado `i`: la celda
  `ACTION[i, a]` es reducir con la producción `k`.
* `acc` → del item `[<programa> → <programa>·, $]`; se escribe en `$` y se
  duplica en `FIN_ARCHIVO` porque ese es el token real de fin de archivo del
  lexer.
* vacío → ninguna de las anteriores: **error sintáctico**.

**P11. ¿Qué hace exactamente el parser en una reducción?**
`r{k}` con `|α| = m`: (1) desapilan `2m` elementos (`m` símbolos + `m`
estados); (2) el estado que queda en la cima es `j`; (3) empujar `A` y el
estado `GOTO[j][A]`. **La entrada no avanza**: el lookahead actual se vuelve a
mirar con el nuevo estado. Por eso la traza muestra la misma entrada restante
en dos pasos seguidos cuando hay una reducción (pasos 4→5 de la traza real en
E.1).

**P12. ¿Qué es el conflicto desplazar-reducir y cómo se resuelve aquí?**
Ocurre cuando `ACTION[i, a]` tendría tanto `s{n}` como `r{k}`. La resolución
estándar (y la que vale en LALR/SLR) es: **gana el desplazar**. Nuestra
implementación lo hace estructuralmente (escribe los shift primero y los
reduce solo en celdas vacías), pero **medimos las 195 filas y hay 0 celdas de
ese tipo**: el arbitraje nunca tuvo que usarse. Si preguntan "¿y si hubiera
uno?", la respuesta es: habría que declarar **precedencia/associatividad** de
los operadores en la gramática (como hace yacc) o reescribir la regla; aquí no
hizo falta porque la jerarquía de precedencia ya está explícita en los niveles
`<expr_o>…<expr_primaria>`.

**P13. ¿Y el conflicto reducir-reducir, existe?**
**Tampoco.** Medido: 0 celdas donde dos `r{k}` distintos disputen el mismo
(estado, lookahead). Eso confirma que la fusión por núcleo no introdujo
conflictos nuevos (era el riesgo teórico de LALR(1), P8).

### F.3 La traza y el algoritmo

**P14. ¿Qué debe mostrar la traza del análisis? (Directo del enunciado)**
Cuatro campos por paso: **número de paso**, **contenido de la pila**, **cadena
de entrada restante** (hasta `$`) y **acción ejecutada** (`shift`/`reduce`/
`accept`/`error`). Nuestra app añade la columna **`Estados`** para que la pila
se lea como `símbolo·estado`, y al final indica si la cadena fue **válida**
(terminó en `accept`) o **inválida** (la acción quedó vacía en alguna celda, y
el paso donde eso pasó es el diagnóstico).

**P15. ¿Cómo se inicializa el algoritmo?**
Pila con el estado inicial (`0`), entrada = tokens del lexer + marcador `$`, y
el lookahead es el primer token. En la traza visual la pila se muestra
intercalando símbolos: `$·0 KW_IMPRESION·17 …`, pero **solo los estados
gobiernan la máquina**; los símbolos están ahí para el lector humano.

**P16. ¿Por qué la entrada NO avanza al reducir pero sí al desplazar?**
Porque *reducir* es un movimiento **interno**: no consume ningún token de la
entrada, solo reemplaza los símbolos ya reconocidos en la pila por un no
terminal. El lookahead se conserva porque, tras la reducción, la misma celda
puede pedir otra reducción (reducciones encadenadas) o un desplazar con ese
mismo token. *Desplazar*, en cambio, sí consume el token de entrada.

**P17. ¿Cuándo termina el análisis y cómo sabe si es válido?**
Termina en dos casos: (a) la acción es **`acc`** (estado con el item
`[<programa> → <programa>·, $]` y `$` como lookahead) ⇒ **cadena válida**;
(b) la acción es **vacía** ⇒ **error sintáctico**, y el paso con la pila y la
entrada congeladas indica exactamente dónde falló. Un error de ACTION vacía es
el equivalente ascendente de "celda vacía en M[A,a]" del LL(1).

**P18. Camine un ejemplo mínimo paso a paso.**
Gramática aumentada: `<programa> → <lista>` , `<lista> → a`. Entrada `a $`:

1. Pila `[0]`, entrada `a $`. `ACTION[0, a] = s2` → **desplazar**. Pila `[0 a 2]`.
2. Pila `[0 a 2]`, entrada `$`. `ACTION[2, $] = r1` → **reducir `<lista> → a`**:
   desapila `a 2`, cima `0`, `GOTO[0, <lista>] = 1`. Pila `[0 <lista> 1]`.
   La entrada **sigue en `$`**.
3. Pila `[0 <lista> 1]`, entrada `$`. `ACTION[1, $] = r0` →
   **reducir `<programa> → <lista>`**: pila `[0 <programa> 3]`.
4. `ACTION[3, $] = acc` ⇒ **válido**.

(Este es el recorrido clásico que conviene poder repetir en la pizarra. La app
muestra el equivalente real en la pestaña "Traza LALR(1)".)

**P19. ¿La traza LALR se parece a la traza LL(1) que ya tienen?**
Sí en la forma (paso/pila/entrada/acción), pero **al revés en el espíritu**: la
del LL(1) apilaba **símbolos gramaticales** y expandía de arriba hacia abajo;
la del LALR apila **estados** y reduce de abajo hacia arriba. Dato medido con
la misma entrada (`pille_pues numerito x = 5` + `hable_pues(x + 1)`):
**LL(1) 70 pasos, LALR 69 pasos, recursivo 89 pasos** — los tres sin errores.

### F.4 Preguntas sobre el código de nuestro proyecto

**P20. ¿Dónde está implementado el generador LALR(1) y qué hace?**
`generador_lalr1_completo.py` (≈415 líneas): (1) calcula FIRST/FOLLOW
reutilizando `tabla_ll1.py`; (2) construye el **autómata LR(1) canónico** con
cierre y GOTO (`cerrar_lr1_v3`, `goto_lr1_v3`, `build_lr1_automaton`) → 1703
estados; (3) **fusiona por núcleo** a LALR(1) (`merge_lr1_states_by_core`) →
195 estados; (4) extrae la tabla GOTO y las transiciones por terminal
(`extract_goto_lalr1`). Ejecutado: 1703→195, 402 entradas GOTO, 0 conflictos.

**P21. ¿Cómo representa un item en el código?**
Una tupla `(no_terminal, producción, punto, lookahead)`, p. ej.
`("<sent_si>", ("KW_SI","<expresion>",…), 0, "KW_DECLARACION")`. La producción
se guarda como **tupla** para poder usarla como clave de `frozenset` y
deduplicar estados (`generador_lalr1_completo.py:98-110`).

**P22. ¿Cómo sabe el código si un símbolo es terminal o no terminal?**
El generador importa `es_terminal` / `no_terminal` desde `tabla_ll1.py`: si el
símbolo es clave del diccionario `GRAMATICA_BNF` es no terminal; si no,
terminal. Es la **misma gramática** que usa el LL(1): un solo punto de verdad
para el autómata.

**P23. ¿Qué es el "núcleo" que usa la fusión y por qué es la clave correcta?**
El núcleo de un estado es su conjunto de items **sin los lookaheads**
(`(nt, producción, punto)`). Dos estados de LR(1) son "lo mismo" para LALR si
sus núcleos coinciden; al fusionarlos se unen sus lookaheads
(`merge_lr1_states_by_core`, `:216-243`). Es la definición estándar: el núcleo
determina las transiciones de entrada/salida del estado.

**P24. ¿La ACTION que muestra la app es la LALR(1) real?**
**Sí, y se puede demostrar en vivo.** ACTION y GOTO salen de los **items del
autómata fusionado**: los shift de las transiciones por terminal y los reduce
de los items con el punto al final (`parser_lalr.py:153`). No hay ninguna
matriz LL(1) de por medio. La prueba más rápida: elegir en el 🔎 Inspector un
estado concreto y comparar sus **items LALR(1)** con la fila de ACTION — el
punto de cada item completo explica exactamente el `r{k}` de la fila.

> Si llegan con una versión vieja del código o de la presentación en la mano y
> dicen "pero esto antes era del LL(1)", la respuesta es: *correcto, esa era la
> versión anterior; hoy ACTION se construye desde el autómata y puede
> verificarlo con el inspector de estados*.

**P25. ¿Dónde está implementado el driver LR (el entregable E1)?**
En `parser_lalr.py`, clase `ParserLALR1`, método `parse_con_pasos` (`:301`).
Es el bucle pila-estados / entrada del Dragon Book: consulta
`ACTION[estado_top][lookahead]`, aplica `s{n}` / `r{k}` / `acc` / error y
registra cada paso. Se integra en la app en `app.py:322-357`, donde el método 3
**reemplaza** al motor LL(1): por eso los errores que se ven en las pestañas
AST y "Errores" cuando el método 3 está activo son del LALR(1).

**P26. ¿Cuánto tarda generar las tablas y por qué?**
≈2.1 s, porque construye los **1703 estados LR(1) canónicos** (cierre item a
item para cada transición) antes de fusionarlos a 195. Se amortiza con
`st.cache_data`; para una demo conviene seleccionar el método 3 **antes** de
empezar a hablar, para que la generación ocurra mientras se explica.

**P27. ¿Cómo representan la aceptación, si no usan `<programa>' → <programa>`?**
El item inicial del autómata es `('<programa>', (…), 0, "$")`; cuando el punto
queda al final de `<programa>` con lookahead `$`, se escribe `acc` en esa celda
(`parser_lalr.py:217-222`). Es funcionalmente equivalente a la producción
aumentada explícita. Como el lexer emite `FIN_ARCHIVO` y no `$`, la misma
aceptación se replica en `FIN_ARCHIVO` (`:224-226`) — de ahí las **2** celdas
`acc` de la tabla. Si preguntan si eso es un hack: *no, es el puente entre el
marcador teórico `$` y el token real de fin de archivo del lexer*.

**P28. ¿Reutilizan algo del Quiz 2 en el LALR(1)?**
Sí: el **lexer** (los tokens que entran al parser), la **gramática ejecutable**
`GRAMATICA_BNF` de `tabla_ll1.py` (el generador la importa directamente), los
cálculos de **FIRST/FOLLOW** (`calcular_primeros`, `calcular_siguientes`) y el
esqueleto de la app (barra lateral de métodos, pestañas, stepper). El análisis
léxico no cambia en absoluto. `parser_lalr.py` mantiene además su propia copia
de la gramática con los mismos 52 no terminales y 106 producciones.

**P29. ¿Cómo se decide qué método usa la app para cada token de entrada?**
La variable `metodo_analisis` del radio de la barra lateral (`app.py:459`):
`"1. Descendente Recursivo"` → `Parser.parse_con_pasos()`;
`"2. Predictivo LL(1) (Pila)"` → `analisis_predictivo_multi()`;
`"3. Ascendente LALR(1)"` → genera las tablas y corre
`ParserLALR1.parse_con_pasos()`. Los tres son mutuamente excluyentes y ninguno
afecta a los otros.

**P30. ¿Por qué la pila de la traza se muestra como `símbolo·estado`?**
Porque la máquina solo necesita los estados, pero la traza sin símbolos es
ilegible para un humano. La convención es que **el estado al lado de un
símbolo es el alcanzado tras consumir ese símbolo**, de modo que el **último**
elemento de la pila es siempre el estado que se consulta en ACTION en el paso
siguiente. Permite seguir la traza en texto plano sin contar niveles.

**P31. ¿Cómo se numera `r{k}`?**
Las 106 producciones se enumeran recorriendo `GRAMATICA_BNF` **ordenado por
no terminal** y, dentro de cada uno, en el orden en que aparecen
(`parser_lalr.py:177-183`). `r{k}` es la posición `k` de esa lista. La app
muestra la leyenda completa en la pestaña "Tabla ACTION/GOTO", así que en la
sustentación pueden traducir cualquier `r{k}` en pantalla al instante.

**P32. ¿Cómo manejan las producciones ε en un parser bottom-up?**
Se normalizan a la **tupla vacía `()`**: producir ε significa que la
reducción **no desapila nada** y solo empuja el no terminal y su GOTO. El
hallazgo 3 de la sección C.4 fue exactamente el bug de intentar desapilar un
símbolo `ε` fantasma. Ejemplo real en la traza: el paso 6 reduce
`<expr_potencia_p> → ε` y la pila **crece** sin que la entrada avance.

**P33. ¿Cómo detectan y reportan el error sintáctico?**
Cuando `ACTION[estado][lookahead]` está vacía, el driver se detiene y devuelve
el mensaje `Paso N: No hay definida acción para Estado[i] / Entrada[token]`
con la pila y la entrada congeladas en ese paso. Es un diagnóstico más preciso
que el del LL(1) porque **incluye el estado LR**, que codifica todo el contexto
consumido. Lo vemos en E.2: estado 123, lookahead `FIN_ARCHIVO`.

### F.5 Preguntas trampa probables

**P34. "Si su gramática es LL(1), ¿para qué quieren LALR(1)?"**
Es el objetivo del quiz: comparar los dos paradigmas sobre el mismo lenguaje.
El LL(1) es didáctico y top-down; el LALR(1) es el que usan los generadores
reales (bison/yacc) y admite gramáticas que LL(1) rechaza. Tener los tres
métodos en la app permite **contrastar trazas, tablas y errores** con la misma
entrada.

**P35. "El LALR(1) necesita que la gramática no tenga recursión izquierda,
¿verdad?"**
**No.** Esa restricción es del **descendente recursivo/LL**. LR/LALR toleran
recursión por la izquierda (de hecho la manejan eficientemente, porque la
reducen de forma natural). Nuestra gramática ya la eliminó por el LL(1), y eso
no perjudica al LALR.

**P36. "¿Qué pasaría si la fusión creara un conflicto de reducir-reducir?"**
El parser quedaría **no determinista**: dos reducciones posibles para la misma
celda. Se resolvería reescribiendo la gramática (fusionando producciones o
añadiendo contexto) o aceptando la heurística del docente (reducir con la
producción declarada primero). Aquí **no ocurrió**: 0 conflictos medidos.

**P37. "¿Cuál es la diferencia entre su LALR(1) y un SLR(1)?"**
SLR usa items **LR(0)** y decide las reducciones con el conjunto SIGUIENTE(A)
global; LALR usa items **LR(1)** fusionados y reparte los lookaheads **por
estado**, lo que elimina reducciones injustificadas. En la práctica LALR
resuelve gramáticas que SLR declara conflictivas. (Matiz honesto: en
`_construir_tabla_action_estados` **añadimos SIGUIENTE(A) como red de
seguridad** al lookahead del item; lo medimos y aporta 0 celdas extra
conflictivas, pero conviene saberlo si preguntan por SLR.)

**P38. "Si el análisis falla, ¿el LALR se recupera como el LL(1)?"**
En el algoritmo puro, la acción vacía **detiene** el análisis (es un parser
determinista con decisión única). La recuperación de errores (modo pánico,
omisión/descarte) es una capa adicional — hoy la hacen los parsers LL(1); el
LR puro reporta **el primer** error en el paso exacto donde la celda quedó
vacía, y eso ya es un diagnóstico muy preciso (pila + posición).

**P39. "¿Cuántos tokens de anticipación usa LALR(1) y cuántos el LL(1)?"**
**Uno en ambos.** La "1" es el lookahead de un token. La diferencia no es la
cantidad sino **dónde se usa**: en LL(1) decide al inicio de una producción;
en LALR(1) decide al final (cuándo reducir).

**P40. "¿Por qué su pila de LR lleva estados y no símbolos gramaticales?"**
Porque el comportamiento futuro depende **solo** de lo que se ha consumido, que
es exactamente lo que codifica el estado del autómata (el conjunto de items con
el punto). Empujar símbolos sería redundante; se muestran intercalados
únicamente para que la traza sea legible para humanos.

### F.6 Preguntas del Quiz 2 que pueden caer de refilón

(Se mantienen breves; el Quiz 3 prioriza LALR, pero el docente puede mezclar.)

**P41. ¿Qué es PRIMERO y para qué sirve en el contexto LALR?**
Conjunto de terminales con los que puede empezar una derivación (más `ε` si
puede ser vacía). En LALR lo usa el **cierre LR(1)**: el lookahead de los items
que se agregan es `FIRST(βa)` — la misma función de siempre, aplicada a la cola
de la producción y el lookahead.

**P42. ¿Qué es SIGUIENTE y en qué parte del LALR aparece?**
Conjunto de terminales que pueden seguir a un no terminal. En LALR puro no se
usa para decidir (eso es SLR); aparece al calcular FIRST(βa) cuando
`β ⇒* ε`, y en nuestro código adicionalmente como red de seguridad al
construir las acciones de reducción.

**P43. ¿Qué diferencia hay entre error léxico y sintáctico?**
Léxico: el lexer no reconoce el lexema (`@`, cadena sin cerrar, identificador
con mayúscula) — tiene fila y columna y **no detiene** el análisis. Sintáctico:
todos los tokens son válidos pero su **orden** no corresponde a ninguna
derivación del símbolo inicial — lo decide el parser (celda vacía en M[A,a]
para LL(1); acción vacía para LALR).

**P44. ¿Qué es la ambigüedad y la gramática es ambigua?**
Una gramática es ambigua si existe una cadena con **dos derivaciones** distintas
(o dos árboles). Los parsers deterministas (LL/LALR) **no pueden** procesar
gramáticas ambiguas: aparecerían conflictos (PRIMERO/PRIMERO en LL(1);
desplazar-reducir/reducir-reducir en LALR). La gramática Paisascript muestra
**0 conflictos** en ambos métodos.

---

## G. Reparto de roles (Angie, Julián, Andrés)

Basado en el guion de la presentación y en que el 50 % de la nota es responder
preguntas. Reparto por dificultad creciente:

### Angie — voz inicial, léxico y la demo de arranque (básico)

**Bloque del guion:** apertura, ingreso de código, análisis léxico, los tres
métodos en la barra lateral (≈0–3 min).
**Preguntas que debe dominar:** P1, P2, P14 (qué muestra la traza, lectura
literal del enunciado), P41, P42, P43, P44.
**Frase de arranque sugerida:** *"Somos el compilador Paisascript; el Quiz 3
agrega el analizador ascendente LALR(1) al lado del LL(1) del Quiz 2, sin
quitar nada de lo anterior. Los tres métodos conviven y analizan la misma
entrada."*
**Demo que le corresponde:** mostrar en la barra lateral los **tres métodos**,
seleccionar el `3. Ascendente LALR(1)` (así la generación de ~2.1 s ocurre
mientras habla) y pasarle el control a Julián.

### Julián — el algoritmo, la traza y los bichos (intermedio)

**Bloque del guion:** métodos de análisis sintáctico, traza paso a paso,
árbol (≈3–7 min). Es el **dueño del entregable E3**.
**Preguntas que debe dominar:** P3, P4, P5, P15, P16, P17, P18 (caminar el
ejemplo), P19, P30, P31, P32, P33, P39, P40.
**Demo que le corresponde:** con la pestaña **Traza LALR(1)**, recorrer la
traza de `hable_pues(42)`: señalar un paso de **desplazar** (1–3), otro de
**reducir** explicando por qué la entrada no avanza (4–5), el paso **ε** donde
la pila crece sin leer tokens (6), y el paso final **accept** (29). Luego
mostrar la cadena inválida y detenerse en el paso 61.
**Si preguntan "¿qué fue lo más difícil?":** secciones **C.4** y **C.5**.

### Andrés — las tablas y el inspector (técnico)

**Bloque del guion:** tablas, errores, IA (≈7–9 min). Es el **dueño de E1 y
E2**.
**Preguntas que debe dominar:** P6, P7, P8, P9, P10, P11, P12, P13, P20, P21,
P22, P23, P24, P25, P26, P27, P28, P29, P34, P35, P36, P37, P38.
**Demo que le corresponde:** la pestaña **Tabla ACTION/GOTO**. Explicar la
fila **0** de ACTION (`app.py`, inspector): 10 `s` para los tokens que pueden
iniciar un programa más `r59` (`<lista_declaraciones> → ε`) sobre `$`; y la
fila **0** de GOTO, con sus 13 transiciones. Después abrir el 🔎 Inspector en
el **estado 123** y mostrar por qué `FIN_ARCHIVO` está vacío.
**Cifras que debe citar de memoria:** 1703 → 195 estados (88.5 %), 402 entradas
GOTO, 106 producciones, 52 no terminales, 0 conflictos, ≈2.1 s.

> **Cobertura:** P1–P44 cubiertas entre los tres (Angie 7, Julián 14, Andrés
> 23). Si falta alguien, su bloque vecino cubre lo suyo.

---

## H. Trucos de demo y de sustentación

1. **Generar las tablas al inicio, no en el momento crítico:** seleccionar el
   método 3 apenas se empiece a presentar la parte LALR (la generación tarda
   ≈2.1 s). Así no se espera en silencio.
2. **Dos cadenas siempre a mano:** una **válida** corta
   (`hable_pues(42)`, 29 pasos, ideal para caminar en vivo) y una **con error**
   (`si_acaso 1 > 0 entonces_pues hable_pues(1)`, 61 pasos, falla exactamente
   en el paso 61).
3. **El detalle que convence:** en la traza válida, comparar el paso 4 con el
   paso 5. Misma entrada restante, distinta pila. Es la prueba visual de que
   **reducir no consume entrada** — no hace falta explicarlo, basta con
   señalarlo.
4. **El estado 123 es su mejor amigo:** con el 🔎 Inspector, mostrar que ese
   estado tiene 15 celdas llenas y `$` no es una. Explica un error sintáctico
   **usando la tabla**, que es exactamente lo que pide el 50 % de la nota.
5. **Cifras para citar sin dudar:** 1703 → 195 estados (88.5 %), 1508 estados
   fusionados, 402 entradas GOTO, 106 producciones, 52 no terminales, 3231
   celdas ACTION (499 `s` + 2730 `r` + 2 `acc`), 0 conflictos, ≈2.1 s.
6. **Los tres métodos con la misma entrada** (recursivo 89 / LL(1) 70 / LALR 69
   pasos) es un dato rápido que demuestra que los tres analizadores están
   vivos y son consistentes.
7. **No prometer de más:** el Quiz pide que el estudiante explique *cualquier
   parte de su implementación*. Conviene saber bien la fusión por núcleo
   (C.4) y el driver (C.3), que explicar de memoria un bison que no tienen.
8. **Si preguntan por algo que no está:** el LALR(1) vive en la app
   (`streamlit run app.py`, método 3); `main.py` es la consola del Quiz 1/2 y
   no expone el método 3. Digan que es la interfaz principal del compilador y
   que agregarlo a la consola es un añadido menor.
9. **Preguntas del Quiz 2 que siguen vigentes:** si el docente abre con
   PRIMERO/SIGUIENTE o errores léxicos, responder con P41–P43 y enlazar
   rápidamente al LALR: *"eso mismo es lo que reutiliza el cierre LR(1)"*.

---

## I. Checklist de ensayo antes de la sustentación

- [ ] Ejecutar `venv/bin/python generador_lalr1_completo.py` y confirmar
      **1703 → 195, 88.5 %, 402 GOTO, 0 conflictos**.
- [ ] Levantar `venv/bin/streamlit run app.py`, método 3, y recorrer la traza
      válida (pasos 1, 4, 6, 26, 29) e inválida (paso 61).
- [ ] Abrir el 🔎 Inspector en el **estado 0** y en el **estado 123** y poder
      explicar ambos de memoria.
- [ ] Traducir tres `r{k}` al azar usando la leyenda de producciones.
- [ ] Cada integrante camina **su bloque de preguntas** de la sección G en voz
      alta, con cronómetro (15–30 s por respuesta).
- [ ] Julián repite el ejemplo de la pizarra **P18** sin apoyarse en el código.
- [ ] Practicar la respuesta a **"¿qué fue lo más difícil?"** (sección C.4):
      es casi seguro que la hagan.
- [ ] Tener a mano la respuesta honesta de la sección H.8 sobre `main.py`.

---

## J. Guion de presentación de 10 minutos, adaptado al Quiz 3

> `guion.md` es el guion del Quiz 2 y **todavía no menciona el LALR(1)**.
> Este es el guion actualizado; Angie empieza, Julián toma el algoritmo y la
> traza, Andrés cierra con las tablas.

### 1. Apertura (Angie – 1 min)

> "Hola. Hoy presentamos **Paisascript**, un compilador que traduce un lenguaje
> de jerga antioqueña a **Gleam** (funcional, tipado estático). El Quiz 3 agrega
> a nuestro compilador un **analizador sintáctico ascendente LALR(1)**, sin quitar
> nada de lo anterior: los tres métodos conviven en la app."

*(Mostrar la barra lateral con los tres métodos.)*

### 2. Ingreso de código y análisis léxico (Angie – 2 min)

> "Elegimos la forma de entrada —cadena predefinida, cadena libre o archivo
> `.paisa`— y el método de análisis. El **análisis léxico** rompe el código en
> **tokens**: `KW_DECLARACION` (`pille_pues`), `KW_IMPRESION` (`hable_pues`),
> `OP_SUMA`, `NUM_ENTERO`, `CADENA_LITERAL`… Si hay un carácter desconocido o
> una cadena sin cerrar, aparece en 'Errores léxicos' con fila y columna.
> Esto es el paso previo: **el sintáctico trabaja sobre estos tokens**."

*(Mostrar la pestaña "Código segmentado" y la tabla de símbolos.)*

### 3. Los tres métodos, el mismo lenguaje (Julián – 1 min)

> "En la barra lateral elegimos el método: **descendente recursivo**,
> **predictivo LL(1)** o, el nuevo, **ascendente LALR(1)**. Los tres analizan
> la misma entrada y terminan sin errores: el recursivo en 89 pasos, el LL(1)
> en 70 y el LALR(1) en 69. El LALR es **bottom-up**: no expande desde la raíz,
> sino que va **reconociendo prefijos viables** y **reduciendo** de abajo hacia
> arriba."

### 4. La traza LALR(1) paso a paso (Julián – 3 min)

> "Selecciono el método 3 y analizo `hable_pues(42)`. Veamos la **Traza
> LALR(1)**: número de paso, **pila** como `símbolo·estado`, **entrada
> restante** y **acción**.
>
> *Pasos 1 a 3:* tres **desplazamientos** — el parser consume tokens de la
> entrada.
>
> *Pasos 4 y 5:* dos **reducciones**. Miren la entrada: **no cambió**.
> Reducir no consume entrada; reemplaza símbolos ya reconocidos por un no
> terminal y empuja el estado al que va con `GOTO`.
>
> *Paso 6:* `<expr_potencia_p> → ε`. La pila **crece** y no se leyó ningún
> token. Así se manejan las producciones vacías: se desapilan cero elementos.
>
> *Paso 26:* la pila se vacía y aparece `<declaracion>·1`; el paso 28 llega a
> `<lista_declaraciones>·3`, que es exactamente `GOTO[0, <lista_declaraciones>]`
> de la tabla que verá Andrés.
>
> *Paso 29:* **accept** — cadena válida, en 29 pasos."

### 5. Cuando algo falla (Julián – 1 min)

> "Ahora el mismo `si_acaso` sin su `asi_quedo`. El parser corre 61 pasos y se
> detiene en el **61**: *'No hay definida acción para Estado[123] /
> Entrada[FIN_ARCHIVO]'*. No es un mensaje genérico: **la pila y la entrada
> quedan congeladas justo donde falló**. Andrés les va a mostrar por qué el
> estado 123 rechaza el fin del archivo."

### 6. Las tablas ACTION y GOTO reales (Andrés – 2 min)

> "Estas son las tablas del LALR(1), **indexadas por estado**, generadas desde
> el autómata: **ACTION 195 × 55** y **GOTO 195 × 52**. Las descargamos en CSV.
>
> Construimos el autómata **LR(1) canónico: 1703 estados** y lo **fusionamos
> por núcleo** hasta **195**: una reducción del **88.5 %**, con **0
> conflictos**.
>
> En la fila **0** de ACTION hay 10 `s` —los tokens que pueden iniciar un
> programa— y un `r59`. En la fila **0** de GOTO hay 13 transiciones.
>
> Y aquí está el estado 123 del que hablaba Julián: tiene **15 celdas
> llenas** —nueve para empezar otra sentencia y seis para cerrar el bloque—
> y **`$` no es una de ellas**. Eso es, en concreto, lo que la gramática
> exige: un `asi_quedo`."

### 7. Errores, IA y cierre (Andrés / todos – 1 min)

> "La pestaña **'Errores y verificación'** muestra los errores sintácticos y,
> si los hay, un botón para pedirle al modelo de lenguaje una sugerencia de
> corrección. Hemos recorrido el flujo completo: léxico, tres métodos
> sintácticos, la traza paso a paso del LALR(1) y sus tablas ACTION/GOTO
> reales. La app está desplegada en https://compiladorlex.streamlit.app/ y el
> código está en este repositorio. Muchas gracias, ¿dudas?"

### Notas para los presentadores

- **Seleccionar el método 3 al principio del bloque de Julián** para que la
  generación (≈2.1 s) ocurra mientras habla.
- Tener siempre a mano la cadena **válida** (`hable_pues(42)`) y la **con
  error** (`si_acaso … sin asi_quedo`).
- Si se acorta el tiempo, Angie puede resumir el paso 2 y pasar directo al
  método 3; el bloque de tablas de Andrés **no se debe recortar** porque es el
  25 % de la nota.
