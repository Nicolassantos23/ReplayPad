#!/usr/bin/env python3
import os
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from server.api.replays import router as replays_router
from server.database import init_db, ReplayModel, get_session
from server.config import SERVER_CONFIG
from shared.logger import setup_logger

logger = setup_logger("replaypad-server")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ReplayPad — VPS Server",
        version="1.2.0",
        description="ReplayPad backend — upload, storage, and admin dashboard",
    )

    app.include_router(replays_router)

    # Health
    @app.get("/")
    async def root():
        return {"status": "online", "service": "ReplayPad Server"}

    # Admin dashboard
    @app.get("/admin", response_class=HTMLResponse)
    async def admin():
        html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ReplayPad — Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#e0e0e0;font-family:'Segoe UI',system-ui,sans-serif;padding:24px;max-width:1100px;margin:auto}
h1{font-size:1.3rem;font-weight:300;letter-spacing:4px;text-transform:uppercase;color:#00e676;margin-bottom:24px}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{text-align:left;padding:10px 12px;border-bottom:1px solid #333;color:#888;font-weight:500;text-transform:uppercase;font-size:.75rem;letter-spacing:1px}
td{padding:10px 12px;border-bottom:1px solid #1a1a2e}
tr:hover td{background:#111}
.id{color:#666;font-family:monospace;font-size:.8rem}
.btn{display:inline-block;padding:4px 12px;border-radius:4px;text-decoration:none;font-size:.8rem;margin-right:4px}
.btn.dl{border:1px solid #00e676;color:#00e676}
.btn.dl:hover{background:#00e676;color:#000}
.btn.del{border:1px solid #ff1744;color:#ff1744;cursor:pointer;background:transparent;font-family:inherit;font-size:.8rem;padding:4px 12px}
.btn.del:hover{background:#ff1744;color:#000}
.empty{text-align:center;padding:48px;color:#555}
.refresh{color:#666;font-size:.8rem;margin-bottom:16px}
.stats{display:flex;gap:24px;margin-bottom:20px;font-size:.85rem}
.stats div{background:#111;padding:12px 20px;border-radius:8px;border:1px solid #1a1a2e}
.stats strong{color:#00e676;font-weight:600}
</style>
</head>
<body>
<h1>ReplayPad — Admin</h1>
<div class="stats">
  <div>📦 Total: <strong id="total">0</strong></div>
  <div>📄 Página: <strong id="page">1</strong></div>
</div>
<div class="refresh">🔄 atualizando a cada 10s</div>
<table><thead><tr>
  <th>ID</th><th>Data</th><th>Duração</th><th>Arquivo</th><th>Tamanho</th><th>Ações</th>
</tr></thead><tbody id="tbody"></tbody></table>
<div id="empty" class="empty" style="display:none">Nenhum replay salvo ainda</div>
<script>
async function load(){
  try{
    const r=await fetch('/api/replays');
    const d=await r.json();
    document.getElementById('total').textContent=d.total;
    const tbody=document.getElementById('tbody');
    const empty=document.getElementById('empty');
    tbody.innerHTML='';
    if(!d.replays.length){empty.style.display='block';return}
    empty.style.display='none';
    d.replays.forEach(r=>{
      const size=(r.size/1024/1024).toFixed(1)+'MB';
      const date=new Date(r.created_at).toLocaleString('pt-BR');
      const dur=r.duration.toFixed(1)+'s';
      tbody.innerHTML+=`<tr>
        <td class="id">${r.id.slice(0,8)}</td>
        <td>${date}</td>
        <td>${dur}</td>
        <td>${r.filename}</td>
        <td>${size}</td>
        <td>
          <a class="btn dl" href="/api/replay/${r.id}" download>⬇ Baixar</a>
          <button class="btn del" onclick="del('${r.id}')">✕ Excluir</button>
        </td>
      </tr>`;
    });
  }catch(_){}
}
async function del(id){
  if(!confirm('Excluir replay?'))return;
  await fetch('/api/replay/'+id,{method:'DELETE'});
  load();
}
load();
setInterval(load,10000);
</script>
</body>
</html>"""
        return HTMLResponse(html)

    return app


def main():
    load_dotenv()

    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready")

    app = create_app()

    logger.info("─" * 45)
    logger.info(f"  ReplayPad v1.2 — VPS Server")
    logger.info(f"  Admin:   http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}/admin")
    logger.info(f"  Upload:  POST /api/upload")
    logger.info(f"  Replays: GET  /api/replays")
    logger.info(f"  Storage: {SERVER_CONFIG['storage_path']}")
    logger.info("─" * 45)

    uvicorn.run(
        app,
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
        log_level="info",
    )


if __name__ == "__main__":
    main()
