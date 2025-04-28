import os, socket, requests, json, time

CONSUL = os.getenv("CONSUL_HTTP_ADDR", "http://consul:8500")
SESSION = requests.Session()

def _addr_port(default_port: int):
    """Return container’s IP and the externally exposed port."""
    ip   = socket.gethostbyname(socket.gethostname())
    port = int(os.getenv("SERVICE_PORT", default_port))
    return ip, port

def register(service_name: str, default_port: int, health_path: str = "/health"):
    ip, port = _addr_port(default_port)
    sid = f"{service_name}-{ip}-{port}"
    payload = {
        "ID": sid,
        "Name": service_name,
        "Address": ip,
        "Port": port,
        "Check": {
            "HTTP": f"http://{ip}:{port}{health_path}",
            "Interval": "10s",
            "DeregisterCriticalServiceAfter": "60s"
        }
    }
    SESSION.put(f"{CONSUL}/v1/agent/service/register", data=json.dumps(payload))
    print(f"[CONSUL] registered {sid} → {ip}:{port}", flush=True)

def instances(service_name: str) -> list[str]:
    """Return list of 'http://ip:port' for passing checks."""
    r = SESSION.get(f"{CONSUL}/v1/health/service/{service_name}?passing=true")
    r.raise_for_status()
    return [f"http://{s['Service']['Address']}:{s['Service']['Port']}"
            for s in r.json()]

def kv(key: str, default: str = None) -> str:
    r = SESSION.get(f"{CONSUL}/v1/kv/{key}?raw=true")
    if r.status_code == 200:
        return r.text
    if default is not None:
        return default
    raise KeyError(f"Key {key!r} not found in Consul")
