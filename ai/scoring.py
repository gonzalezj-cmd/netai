def calcular_score(data, anomalias, abuso):

    scores = []

    for u in data:

        rx = int(u.get("rx", 0))
        tx = int(u.get("tx", 0))

        score = 0
        total = rx + tx

        if total > 5_000_000_000:
            score += 2

        if tx > rx:
            score += 3

        if any(a["usuario"] == u["usuario"] for a in anomalias):
            score += 3

        if any(a["usuario"] == u["usuario"] for a in abuso):
            score += 4

        scores.append({
            "usuario": u["usuario"],
            "score": score
        })

    return scores