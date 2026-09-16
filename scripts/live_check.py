#!/usr/bin/env python3
"""External integration smoke test. Never prints credential values."""
import os, sys, json, base64
import requests
from void.config import Config

OK=True

def check(name, fn):
    global OK
    try:
        result=fn()
        print(f"[PASS] {name}: {result}")
    except Exception as e:
        OK=False
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")

def router9():
    r=requests.get(Config.ROUTER_BASE_URL.rstrip('/')+'/models', headers=({"Authorization":"Bearer "+Config.ROUTER_API_KEY} if Config.ROUTER_API_KEY else {}), timeout=20)
    r.raise_for_status(); data=r.json(); models=data.get('data',[])
    if not models: raise RuntimeError('Router9 returned no models')
    model=Config.DEFAULT_MODEL if any(m.get('id')==Config.DEFAULT_MODEL for m in models) else models[0].get('id')
    payload={"model":model,"messages":[{"role":"user","content":"Reply exactly: VOID LIVE CHECK OK"}],"max_tokens":80,"stream":False}
    x=requests.post(Config.ROUTER_BASE_URL.rstrip('/')+'/chat/completions',json=payload,headers=({"Authorization":"Bearer "+Config.ROUTER_API_KEY} if Config.ROUTER_API_KEY else {}),timeout=90)
    x.raise_for_status(); j=x.json(); content=j.get('choices',[{}])[0].get('message',{}).get('content','')
    if not content: raise RuntimeError('Router9 returned no text')
    return f"{len(models)} models; model={j.get('model',model)}"

def telegram():
    r=requests.get('https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/getMe',timeout=20); r.raise_for_status(); j=r.json();
    if not j.get('ok'): raise RuntimeError(str(j))
    return f"bot={j['result'].get('username','unknown')}"

def jina():
    r=requests.get(Config.JINA_URL,params={'q':'Python programming language'},headers={'Authorization':'Bearer '+os.environ['JINA_API_KEY'],'Accept':'application/json'},timeout=30); r.raise_for_status(); j=r.json(); return f"results={len(j.get('data',[]))}"

def groq():
    h={'Authorization':'Bearer '+os.environ['GROQ_API_KEY']}; r=requests.get('https://api.groq.com/openai/v1/models',headers=h,timeout=20); r.raise_for_status(); ids=[m.get('id') for m in r.json().get('data',[])];
    if not ids: raise RuntimeError('Groq returned no models')
    model=Config.GROQ_MODEL if Config.GROQ_MODEL in ids else ids[0]
    x=requests.post(Config.GROQ_URL,json={'model':model,'messages':[{'role':'user','content':'Reply exactly: VOID GROQ CHECK OK'}],'max_tokens':80},headers={**h,'Content-Type':'application/json'},timeout=60); x.raise_for_status(); return f"model={x.json().get('model',model)}"

def gemini():
    h={'x-goog-api-key':os.environ['GEMINI_API_KEY']}; r=requests.get('https://generativelanguage.googleapis.com/v1beta/models',headers=h,timeout=20); r.raise_for_status(); models=r.json().get('models',[]); ids=[m.get('name','').split('/')[-1] for m in models];
    model=Config.GEMINI_MODEL if Config.GEMINI_MODEL in ids else next((x for x in ids if 'flash' in x.lower()), ids[0] if ids else None)
    if not model: raise RuntimeError('Gemini returned no models')
    x=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',json={'contents':[{'parts':[{'text':'Reply exactly: VOID GEMINI CHECK OK'}]}]},headers={**h,'Content-Type':'application/json'},timeout=60); x.raise_for_status(); return f"model={model}"

def hf():
    token=os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_API_KEY')
    if not token: raise RuntimeError('HF_TOKEN/HUGGINGFACE_API_KEY not set')
    r=requests.get('https://huggingface.co/api/whoami-v2',headers={'Authorization':'Bearer '+token},timeout=20); r.raise_for_status(); return 'token accepted'

check('Router9 -> model', router9)
if os.getenv('TELEGRAM_BOT_TOKEN'): check('Telegram', telegram)
if os.getenv('JINA_API_KEY'): check('Jina', jina)
if os.getenv('GROQ_API_KEY'): check('Groq', groq)
if os.getenv('GEMINI_API_KEY'): check('Gemini', gemini)
if os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_API_KEY'): check('Hugging Face', hf)
print('LIVE INTEGRATION CHECKS PASSED' if OK else 'LIVE INTEGRATION CHECKS FAILED')
sys.exit(0 if OK else 1)
