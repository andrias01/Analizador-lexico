# De Paisascript a Gleam — mapa de traducción

Documento de apoyo a la Entrega 1. Justifica que el lenguaje fuente propuesto
es **coherente con el lenguaje destino** (principio orientador del §1 del
enunciado) mostrando, constructo por constructo, cómo se traduce.

> Nota sobre versiones: los nombres exactos de la biblioteca estándar
> (`gleam/list`, `gleam/int`, `gleam/erlang`) deben fijarse contra la versión
> de Gleam que use el equipo antes de la entrega final. Las *formas* de
> traducción de este documento no dependen de esa versión.

---

## 1. Por qué Gleam obliga a diseñar distinto

Gleam no es Python con otra sintaxis. Cuatro propiedades suyas condicionaron
todas las decisiones de Paisascript:

| Propiedad de Gleam | Consecuencia en el diseño de Paisascript |
| :--- | :--- |
| No hay mutación. `let` crea un enlace nuevo, nunca reasigna. | Paisascript **no tiene asignación sin `pille_pues`**. Toda "reasignación" es shadowing. |
| No hay `if`, `while`, `for`, `break`, `continue` ni `return`. Solo `case` y recursión. | Los cuatro constructos que el §2 exige se traducen a `case` y a recursión de cola. |
| `Int` y `Float` son tipos disjuntos, con operadores distintos (`+` vs `+.`). | El lexer emite **`NUM_ENTERO` y `NUM_REAL` como tokens separados**. |
| Todo es expresión; una función devuelve su última expresión. | `entregue_pues` en cola es trivial; anticipado exige reestructurar el flujo. |

---

## 2. Tabla de correspondencia

### 2.1 Léxico

| Paisascript | Gleam | Nota |
| :--- | :--- | :--- |
| `numerito` | `Int` | |
| `quebradito` | `Float` | |
| `cuento` | `String` | |
| `siono` | `Bool` | |
| `sizas` / `naranjas` | `True` / `False` | |
| `// comentario` | `// comentario` | idéntico |
| `años`, `niño` | `anios`, `ninio` | Gleam solo acepta identificadores ASCII |

### 2.2 Operadores

| Paisascript | Gleam (Int) | Gleam (Float) |
| :--- | :--- | :--- |
| `a + b` | `a + b` | `a +. b` |
| `a - b` | `a - b` | `a -. b` |
| `a * b` | `a * b` | `a *. b` |
| `a / b` | `a / b` | `a /. b` |
| `a % b` | `a % b` | — (no aplica) |
| `a ** b` | `int.power(a, b)` | `float.power(a, b)` |
| `a > b` | `a > b` | `a >. b` |
| `a igualito b` | `a == b` | `a == b` |
| `a distinto b` | `a != b` | `a != b` |
| `a y_tambien b` | `a && b` | |
| `a o_que b` | `a \|\| b` | |
| `nanai a` | `!a` | |

Tres puntos que exigen trabajo del generador de código:

1. **Selección de operador por tipo.** Paisascript escribe siempre `+`; el
   analizador semántico decide entre `+` y `+.` según el tipo inferido de los
   operandos. Es la razón por la que `NUM_ENTERO` y `NUM_REAL` son tokens
   distintos desde el análisis léxico.
2. **`**` devuelve `Result`.** `int.power` y `float.power` fallan para
   exponentes que no producen un resultado válido, así que devuelven
   `Result(Float, Nil)`. El generador envuelve la llamada
   (`result.unwrap(..., 0.0)` o `let assert Ok(...)`) según el contexto.
3. **`<>` no es polimórfico en Gleam.** El operador de concatenación de Gleam
   exige `String` en ambos lados. Paisascript sí admite
   `"El resultado es: " <> calculo` con `calculo: numerito`, y el generador
   inserta la conversión:

   ```gleam
   "El resultado es: " <> int.to_string(calculo)
   ```

   Se decidió así porque obligar al programador a convertir a mano rompería
   la naturalidad coloquial del lenguaje, y la información de tipos ya está
   disponible en el árbol.

---

## 3. Traducciones trabajadas

### 3.1 Función, condicional y retorno

`si_acaso` es azúcar sintáctico sobre `case` con patrones `True`/`False`, que
es la forma idiomática de escribir un condicional en Gleam.

**Paisascript**
```
hagale_pues clasificar(numerito nota) pa_que_lleve cuento dele_pues
    si_acaso nota >= 45 y_tambien nota <= 50 entonces_pues
        entregue_pues "Sobresaliente, mijo"
    sino_pues
        si_acaso nota >= 30 entonces_pues
            entregue_pues "Pasaste raspando"
        sino_pues
            entregue_pues "Se quemo, parcero"
        asi_quedo
    asi_quedo
ya_quedo
```

**Gleam**
```gleam
pub fn clasificar(nota: Int) -> String {
  case nota >= 45 && nota <= 50 {
    True -> "Sobresaliente, mijo"
    False ->
      case nota >= 30 {
        True -> "Pasaste raspando"
        False -> "Se quemo, parcero"
      }
  }
}
```

Aquí `entregue_pues` desapareció: cada rama del `case` *es* el valor de
retorno. Ese es el caso fácil, porque todos los retornos están en posición de
cola.

### 3.2 `mientras_que` → recursión de cola

Este es el constructo que más trabajo exige. El generador debe:

1. calcular qué variables redefine el cuerpo (las que aparecen a la izquierda
   de un `pille_pues` dentro del bucle) — ese es el **estado**;
2. crear una función auxiliar que reciba ese estado como parámetros;
3. traducir la condición a un `case` de dos ramas: la verdadera llama
   recursivamente con el estado actualizado, la falsa devuelve el estado.

**Paisascript**
```
hagale_pues sumatoria(numerito n) pa_que_lleve numerito dele_pues
    pille_pues numerito acumulado = 0
    pille_pues numerito i = 1
    mientras_que i <= n dele_pues
        pille_pues acumulado = acumulado + i
        pille_pues i = i + 1
    hasta_ahi
    entregue_pues acumulado
ya_quedo
```

**Gleam** — el estado del bucle es `(acumulado, i)`:
```gleam
pub fn sumatoria(n: Int) -> Int {
  let acumulado = 0
  let i = 1
  bucle_1(n, acumulado, i)
}

fn bucle_1(n: Int, acumulado: Int, i: Int) -> Int {
  case i <= n {
    True -> bucle_1(n, acumulado + i, i + 1)
    False -> acumulado
  }
}
```

La llamada `bucle_1` está en posición de cola, así que el BEAM la ejecuta en
espacio constante: el resultado no es solo correcto, es tan eficiente como el
bucle original.

### 3.3 `pa_cada` → `list.range` o recursión

Con paso 1 basta componer las funciones de `gleam/list`:

**Paisascript**
```
pa_cada n desde 2 hasta limite dele_pues
    si_acaso es_primo(n) entonces_pues
        hable_pues("Primo encontrado: " <> n)
    asi_quedo
listo_pues
```

**Gleam**
```gleam
list.range(2, limite)
|> list.each(fn(n) {
  case es_primo(n) {
    True -> io.println("Primo encontrado: " <> int.to_string(n))
    False -> Nil
  }
})
```

Nótense dos detalles: la conversión `int.to_string` que exige `<>`, y la rama
`False -> Nil`, obligatoria porque en Gleam un `case` debe cubrir todos los
casos y ambas ramas deben tener el mismo tipo.

Con paso distinto de 1 no sirve `list.range`, que no admite incremento, y se
vuelve a la recursión de cola:

**Paisascript**
```
pa_cada k desde 0 hasta 20 de_a 2 dele_pues
    hable_pues(k)
listo_pues
```

**Gleam**
```gleam
fn bucle_2(k: Int) -> Nil {
  case k <= 20 {
    True -> {
      io.println(int.to_string(k))
      bucle_2(k + 2)
    }
    False -> Nil
  }
}
```

### 3.4 `entregue_pues` anticipado

Cuando el retorno **no** está en posición de cola hay que reestructurar el
flujo. Es siempre posible porque el grafo de flujo de Paisascript es
reducible: no hay `goto`, ni `break`, ni `continue`, ni saltos arbitrarios.
La regla es: la rama que retorna produce el valor, y **el resto del cuerpo se
traslada a la rama complementaria**.

**Paisascript** (el `entregue_pues naranjas` está a mitad del cuerpo)
```
hagale_pues es_primo(numerito n) pa_que_lleve siono dele_pues
    si_acaso n < 2 entonces_pues
        entregue_pues naranjas
    asi_quedo
    pille_pues numerito d = 2
    mientras_que d * d <= n dele_pues
        si_acaso n % d igualito 0 entonces_pues
            entregue_pues naranjas
        asi_quedo
        pille_pues d = d + 1
    hasta_ahi
    entregue_pues sizas
ya_quedo
```

**Gleam**
```gleam
pub fn es_primo(n: Int) -> Bool {
  case n < 2 {
    True -> False
    False -> divisor_1(n, 2)   // el resto del cuerpo vive en la rama falsa
  }
}

fn divisor_1(n: Int, d: Int) -> Bool {
  case d * d <= n {
    False -> True              // salio del bucle sin divisores: es primo
    True ->
      case n % d == 0 {
        True -> False          // el retorno anticipado del cuerpo del bucle
        False -> divisor_1(n, d + 1)
      }
  }
}
```

El retorno anticipado dentro del bucle se convierte en una rama del `case`
que simplemente **no vuelve a llamar** a la función recursiva. Salir del bucle
y retornar son la misma operación.

### 3.5 `pillemos` → `case`

La traducción más directa de todas: es token a token.

**Paisascript**
```
pillemos resultado {
    10       pa_que_lleve hable_pues("Sacaste diez, que elegancia")
    "error"  pa_que_lleve hable_pues("Algo salio mal, mijo")
    _        pa_que_lleve hable_pues("No se que paso ahi")
}
```

**Gleam**
```gleam
case resultado {
  10 -> io.println("Sacaste diez, que elegancia")
  "error" -> io.println("Algo salio mal, mijo")
  _ -> io.println("No se que paso ahi")
}
```

(El ejemplo mezcla patrones `Int` y `String` a propósito: es válido
léxicamente, y es el **analizador semántico** de la entrega 3 el que debe
rechazarlo, porque en Gleam todos los patrones de un `case` deben tener el
tipo del sujeto.)

### 3.6 Entrada y salida

| Paisascript | Gleam |
| :--- | :--- |
| `hable_pues(m)` | `io.println(m)` — con `int.to_string` / `float.to_string` si `m` no es `String` |
| `escuche_pues(x)` | `let assert Ok(x) = erlang.get_line("")` |

La lectura de consola depende del *target*: en el target Erlang se usa el
paquete `gleam_erlang`; en el target JavaScript habría que usar otro
mecanismo. El equipo debe fijar el target antes de la entrega final.

---

## 4. Programa completo de punta a punta

**Paisascript** (`ejemplos.py`, ejemplo 1)
```
// Le sube un par de anios a la edad que digite el usuario
escuche_pues(edad)
pille_pues numerito calculo = (edad * 2) + 5
pille_pues cuento mensaje = "El resultado es: " <> calculo
hable_pues(mensaje)
```

**Gleam generado**
```gleam
import gleam/erlang
import gleam/int
import gleam/io

// Le sube un par de anios a la edad que digite el usuario
pub fn main() {
  let assert Ok(edad) = erlang.get_line("")
  let assert Ok(edad) = int.parse(string.trim(edad))
  let calculo: Int = { edad * 2 } + 5
  let mensaje: String = "El resultado es: " <> int.to_string(calculo)
  io.println(mensaje)
}
```

Obsérvese que las sentencias de nivel superior de Paisascript se envuelven en
`pub fn main()`, porque en Gleam todo código ejecutable vive dentro de una
función y `main` es el punto de entrada del módulo.

---

## 5. Estado del proyecto

| Fase | Entregable | Estado |
| :--- | :--- | :--- |
| Análisis léxico | `lexer.py`, `main.py` | **Entrega 1 — completo** |
| Gramática BNF LL(1) | `gramatica_BNF_Paisascript.txt` | **Entrega 1 — completo** |
| Análisis sintáctico | parser descendente recursivo | pendiente |
| Análisis semántico | tabla de símbolos, inferencia `Int`/`Float` | pendiente (entrega 3) |
| Generación de código | emisor de Gleam | pendiente (entrega final) |

Este documento define **qué** debe producir la última fase; el `lexer.py` de
esta entrega ya emite los tokens con la granularidad que esa fase necesita
(en particular la separación `NUM_ENTERO` / `NUM_REAL`).
