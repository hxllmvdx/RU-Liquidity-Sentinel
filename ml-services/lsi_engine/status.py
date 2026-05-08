def resolve_status(lsi):
    if lsi < 35:
        return "green"
    if lsi < 65:
        return "yellow"
    return "red"
