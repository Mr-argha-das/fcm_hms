BASE_URL = "https://wecarehhcs.in"

def with_domain(path):
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{BASE_URL}{path}"