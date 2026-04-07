def formatear_bytes(bytes):
    gb = bytes / (1024**3)
    mb = bytes / (1024**2)

    if gb >= 1:
        return f"{gb:.2f} GB"
    return f"{mb:.2f} MB"