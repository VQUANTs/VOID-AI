import os
from void.api import make_server

if __name__ == "__main__":
    host = os.getenv("VOID_API_HOST", "127.0.0.1")
    port = int(os.getenv("VOID_API_PORT", "8787"))
    server = make_server(host, port)
    print(f"VOID API listening on http://{host}:{port}")
    server.serve_forever()
