import math

# Lista de coordenadas aproximadas das principais cidades e pontos de interesse do Chernarus
# Fonte: Central DayZ / Wiki
CHERNARUS_POI = [
    {"name": "Chernogorsk", "x": 6700, "z": 2400},
    {"name": "Elektrozavodsk", "x": 10400, "z": 2200},
    {"name": "Berezino", "x": 12100, "z": 9300},
    {"name": "Svetloyarsk", "x": 13900, "z": 13200},
    {"name": "Novodmitrovsk", "x": 11500, "z": 14500},
    {"name": "Severograd", "x": 7700, "z": 11700},
    {"name": "Vybor", "x": 3800, "z": 8900},
    {"name": "Stary Sobor", "x": 6000, "z": 7700},
    {"name": "Novy Sobor", "x": 7100, "z": 7600},
    {"name": "Zelenogorsk", "x": 2700, "z": 5200},
    {"name": "NWAF (Aeroporto Norte)", "x": 4600, "z": 10300},
    {"name": "Tisy (Base Militar)", "x": 1700, "z": 14000},
    {"name": "Pavlovo", "x": 1600, "z": 3800},
    {"name": "Balota", "x": 4400, "z": 2300},
    {"name": "Kamensk", "x": 7700, "z": 14600},
    {"name": "Gorka", "x": 9500, "z": 8800},
    {"name": "Grishino", "x": 5900, "z": 10300},
    {"name": "Pusta", "x": 7000, "z": 3900},
    {"name": "Mogilevka", "x": 7500, "z": 5100},
    {"name": "Staroye", "x": 10100, "z": 5400},
    {"name": "Guglovo", "x": 8400, "z": 6600},
    {"name": "Shakhovka", "x": 9600, "z": 6500},
    {"name": "Kabanino", "x": 5300, "z": 8600},
    {"name": "Pogorevka", "x": 4400, "z": 7000},
    {"name": "Rogovo", "x": 4800, "z": 7800},
    {"name": "Nadezhdino", "x": 6200, "z": 4300},
    {"name": "Bor", "x": 3300, "z": 3900},
    {"name": "Tulga", "x": 12800, "z": 4400},
    {"name": "Kamyshovo", "x": 12000, "z": 3500},
    {"name": "Kamenka", "x": 1800, "z": 2200},
    {"name": "Zaprudnoe", "x": 4000, "z": 11700},
]


def get_nearest_location(coords_str):
    """
    Traduz uma string de coordenadas 'X Y Z' ou 'X Z' para a localização mais próxima.
    Exemplo: '2906 0 9736' -> 'Próximo a Vybor'
    """
    try:
        parts = coords_str.replace(",", "").split()
        if len(parts) < 2:
            return "Local Desconhecido"

        x = float(parts[0])
        z = float(parts[2]) if len(parts) == 3 else float(parts[1])

        min_dist = float("inf")
        nearest_city = "Área Remota"

        for poi in CHERNARUS_POI:
            dist = math.sqrt((x - poi["x"]) ** 2 + (z - poi["z"]) ** 2)
            if dist < min_dist:
                min_dist = dist
                nearest_city = poi["name"]

        if min_dist < 500:
            return f"Em {nearest_city}"
        elif min_dist < 1500:
            return f"Próximo a {nearest_city}"
        else:
            return f"Na região de {nearest_city}"

    except:
        return "Coordenadas Inválidas"
