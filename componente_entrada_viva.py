# -*- coding: utf-8 -*-
"""
componente_entrada_viva.py — Cuadro de texto que reporta cada tecla al vuelo.

`st.text_area` de Streamlit solo entrega su valor a Python cuando el usuario
sale del cuadro o presiona Ctrl+Enter; no hay forma de cambiar eso con sus
parametros publicos. Este modulo declara un componente ESTATICO (un solo
archivo HTML/JS, sin React ni npm ni CDN) que envia el texto a Python en
cada pulsacion de tecla, usando directamente el protocolo publico de
mensajeria de Streamlit (`window.postMessage`). El HTML vive en
`componentes/entrada_viva/index.html`.

Es EXPERIMENTAL: no hay forma de ejecutar un navegador real desde este
entorno de desarrollo para verificar visualmente el intercambio de mensajes,
asi que `app.py` lo ofrece como modo opcional ("en vivo") y deja el
`st.text_area` clasico como opcion por defecto, ya probada.
"""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_RUTA = Path(__file__).parent / "componentes" / "entrada_viva"

_componente = components.declare_component("entrada_viva", path=str(_RUTA))


def area_texto_viva(
    valor: str,
    *,
    altura: int = 280,
    placeholder: str = "",
    key: str | None = None,
) -> str:
    """Un textarea que devuelve su contenido en cada tecla (con debounce).

    `valor` es el texto a mostrar cuando el componente cambia por una razon
    ajena a la escritura del usuario (por ejemplo, al cargar un ejemplo
    predefinido). Mientras el usuario escribe, el componente ignora ese
    argumento para no pisarle el cursor a mitad de una palabra.
    """
    resultado = _componente(
        valor=valor,
        altura=altura,
        placeholder=placeholder,
        key=key,
        default=valor,
    )
    return resultado if isinstance(resultado, str) else valor
