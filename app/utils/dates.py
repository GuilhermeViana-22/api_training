DAY_NAMES = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}


def day_name(day_of_week: int) -> str:
    return DAY_NAMES.get(day_of_week, "Desconhecido")
