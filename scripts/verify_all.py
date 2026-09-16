#!/usr/bin/env python3
import os, sys, subprocess, urllib.request, json

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

def run(label, cmd):
    print(f"[CHECK] {label}")
    p=subprocess.run(cmd, text=True)
    if p.returncode != 0:
        print(f"[FAIL] {label} (exit {p.returncode})")
        return False
    print(f"[PASS] {label}")
    return True

ok=True
ok &= run("compileall", [sys.executable,"-m","compileall","-q","void","run.py","server.py"])
ok &= run("pytest", [sys.executable,"-m","pytest","-q"])
try:
    from void.config import Config
    from void.core import VoidCore
    from void.api import VoidAPI
    core=VoidCore()
    health=VoidAPI(core).health()
    assert health["status"] == "ok"
    assert "telegram" in health["interfaces"]
    print("[PASS] core/api smoke")
except Exception as e:
    print("[FAIL] core/api smoke:",e); ok=False
print("ALL CHECKS PASSED" if ok else "CHECKS FAILED")
sys.exit(0 if ok else 1)
