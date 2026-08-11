"""Estado del tablero de Go: grupos, libertades, capturas, ko y legalidad."""

from . import NEGRO, BLANCO, VACIO, oponer


class Tablero:
    """Tablero de Go con reglas de captura, suicidio y ko simple."""

    def __init__(self, tamano: int = 9):
        self.tamano = tamano
        self.celdas = [[VACIO] * tamano for _ in range(tamano)]
        self.capturas = {NEGRO: 0, BLANCO: 0}
        self.punto_ko = None
        self.historial = []
        self._vacias = {(f, c) for f in range(tamano) for c in range(tamano)}

    def celdas_vacias(self):
        """Conjunto de intersecciones vacías (muy útil para búsquedas)."""
        return self._vacias.copy()

    def dentro(self, fila: int, col: int) -> bool:
        return 0 <= fila < self.tamano and 0 <= col < self.tamano

    def oponer(self, color: int) -> int:
        return oponer(color)

    def _vecinos(self, fila: int, col: int):
        n = self.tamano
        if fila > 0:
            yield fila - 1, col
        if fila < n - 1:
            yield fila + 1, col
        if col > 0:
            yield fila, col - 1
        if col < n - 1:
            yield fila, col + 1

    def obtener_grupo(self, fila: int, col: int) -> set:
        """Devuelve el conjunto de posiciones del grupo conectado en (fila, col)."""
        color = self.celdas[fila][col]
        if color == VACIO:
            return set()
        grupo = set()
        pila = [(fila, col)]
        while pila:
            f, c = pila.pop()
            if (f, c) in grupo:
                continue
            grupo.add((f, c))
            for vf, vc in self._vecinos(f, c):
                if self.celdas[vf][vc] == color and (vf, vc) not in grupo:
                    pila.append((vf, vc))
        return grupo

    def calcular_libertades(self, grupo: set) -> set:
        """Devuelve los puntos vacíos adyacentes al grupo."""
        libertades = set()
        for f, c in grupo:
            for vf, vc in self._vecinos(f, c):
                if self.celdas[vf][vc] == VACIO:
                    libertades.add((vf, vc))
        return libertades

    def _copiar(self):
        copia = Tablero(self.tamano)
        copia.celdas = [fila[:] for fila in self.celdas]
        copia.capturas = dict(self.capturas)
        copia.punto_ko = self.punto_ko
        copia._vacias = set(self._vacias)
        return copia

    def _colocar_y_capturar(self, fila: int, col: int, color: int) -> set:
        """Coloca una piedra y retira los grupos oponentes sin libertades."""
        self.celdas[fila][col] = color
        self._vacias.discard((fila, col))
        capturadas = set()
        color_oponente = self.oponer(color)
        for vf, vc in self._vecinos(fila, col):
            if self.celdas[vf][vc] == color_oponente:
                grupo = self.obtener_grupo(vf, vc)
                if not self.calcular_libertades(grupo):
                    capturadas |= grupo
        for f, c in capturadas:
            self.celdas[f][c] = VACIO
            self._vacias.add((f, c))
        return capturadas

    def es_movimiento_legal(self, fila: int, col: int, color: int, con_motivo: bool = False):
        """Valida si colocar `color` en (fila, col) es legal según las reglas.

        Análisis directo de vecinos sin copiar el tablero (rápido para Ia
        y para uso intensivo en búsqueda).
        """
        if not self.dentro(fila, col):
            return (False, "fuera del tablero") if con_motivo else False
        if self.celdas[fila][col] != VACIO:
            return (False, "la intersección ya está ocupada") if con_motivo else False
        if (fila, col) == self.punto_ko:
            return (False, "movimiento ko prohibido") if con_motivo else False

        color_oponente = oponer(color)

        # vecino vacío: nuestra piedra tiene al menos una libertad directa
        for vf, vc in self._vecinos(fila, col):
            if self.celdas[vf][vc] == VACIO:
                return (True, None) if con_motivo else True

        # el movimiento captura si algún grupo vecino queda sin libertades
        for vf, vc in self._vecinos(fila, col):
            if self.celdas[vf][vc] == color_oponente:
                grupo = self.obtener_grupo(vf, vc)
                if len(self.calcular_libertades(grupo)) == 1:
                    return (True, None) if con_motivo else True

        # sin captura: el grupo propio debe conservar al menos una libertad
        libertades_propias = set()
        for vf, vc in self._vecinos(fila, col):
            if self.celdas[vf][vc] == color:
                grupo = self.obtener_grupo(vf, vc)
                libertades_propias |= self.calcular_libertades(grupo)
        libertades_propias.discard((fila, col))

        if libertades_propias:
            return (True, None) if con_motivo else True
        return (False, "suicidio prohibido") if con_motivo else False

    def colocar_piedra(self, fila: int, col: int, color: int) -> dict:
        """Ejecuta un movimiento en el tablero tras validarlo.

        Devuelve un diccionario con la información del movimiento.
        Lanza ValueError si el movimiento es ilegal.
        """
        legal, motivo = self.es_movimiento_legal(fila, col, color, con_motivo=True)
        if not legal:
            raise ValueError(motivo)

        self.historial.append([fila[:] for fila in self.celdas])
        self.punto_ko = None
        capturadas = self._colocar_y_capturar(fila, col, color)

        if capturadas:
            self.capturas[color] += len(capturadas)
            if len(capturadas) == 1:
                pos_captura = next(iter(capturadas))
                grupo = self.obtener_grupo(fila, col)
                if len(self.calcular_libertades(grupo)) == 1:
                    self.punto_ko = pos_captura

        return {
            "fila": fila,
            "col": col,
            "color": color,
            "capturas": len(capturadas),
            "punto_ko": self.punto_ko,
        }

    def deshacer(self) -> None:
        """Restaura el estado anterior (mueve atrás)."""
        if self.historial:
            self.celdas = self.historial.pop()
            self.punto_ko = None
            self._vacias = {(f, c) for f in range(self.tamano)
                            for c in range(self.tamano)
                            if self.celdas[f][c] == VACIO}

    def obtener_movimientos_legales(self, color: int):
        """Devuelve la lista de coordenadas legales para `color`."""
        legales = []
        for fila, col in self._vacias:
            if self.es_movimiento_legal(fila, col, color):
                legales.append((fila, col))
        return legales

    def obtener_estado(self) -> list:
        """Devuelve la matriz de celdas (para codificación y persistencia)."""
        return [fila[:] for fila in self.celdas]

    def copiar(self):
        """Devuelve una copia independiente del tablero."""
        return self._copiar()

    def grupos_con_libertades(self) -> dict:
        """Resumen de grupos: {posicion: {color, libertades, tamano}}.

        Útil para heurísticas rápidas (atari y capturas estimadas).
        """

        resumen = {}
        visitado = set()
        for fila in range(self.tamano):
            for col in range(self.tamano):
                if self.celdas[fila][col] == VACIO or (fila, col) in visitado:
                    continue
                color = self.celdas[fila][col]
                grupo = self.obtener_grupo(fila, col)
                libertades = len(self.calcular_libertades(grupo))
                for pos in grupo:
                    visitado.add(pos)
                    resumen[pos] = {
                        "color": color,
                        "libertades": libertades,
                        "tamano": len(grupo),
                    }
        return resumen

    def __repr__(self) -> str:
        linea = "+" + "---" * self.tamano + "+"
        filas = [linea]
        for fila in self.celdas:
            celdas = " | ".join(
                "·" if celda == VACIO else ("●" if celda == NEGRO else "○")
                for celda in fila
            )
            filas.append(f"| {celdas} |")
        filas.append(linea)
        return "\n".join(filas)