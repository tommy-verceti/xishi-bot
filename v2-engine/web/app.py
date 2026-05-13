"""FastAPI developer dashboard.

Phase 6: Web panel for monitoring conversations, users, and bot state.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from config import CONFIG
from db.database import get_db
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="西施 Bot V2 - Developer Panel")

HTML_INDEX = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>西施 Bot V2</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font:14px/1.5 system-ui,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:24px}
h1{color:#e8a0bf;margin-bottom:8px}
h2{color:#c4a0e8;margin:16px 0 8px}
.card{background:#16213e;border-radius:8px;padding:16px;margin:8px 0}
table{width:100%;border-collapse:collapse}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #333}
th{color:#a0c4e8}
.nav{display:flex;gap:12px;margin:16px 0}
.nav a{background:#16213e;padding:8px 16px;border-radius:6px;text-decoration:none}
.nav a:hover{background:#0f3460}
.stat{display:inline-block;background:#16213e;border-radius:8px;padding:16px;margin:8px;min-width:120px;text-align:center}
.stat .num{font-size:28px;font-weight:bold;color:#e8a0bf}
.stat .label{font-size:12px;color:#888;margin-top:4px}
</style>
</head>
<body>
<h1>西施 Bot - V2 Developer Panel</h1>
<div class="nav">
<a href="/">概览</a><a href="/api/users">用户</a>
<a href="/api/stats">统计</a><a href="/api/health">健康检查</a>
</div>
<div><div class="stat"><div class="num" id="users">-</div><div class="label">总用户</div></div>
<div class="stat"><div class="num" id="msgs">-</div><div class="label">总消息</div></div>
<div class="stat"><div class="num" id="active">-</div><div class="label">今日活跃</div></div></div>
<h2>最近用户</h2><div id="users-list">加载中...</div>
<h2>API</h2>
<div class="card">
<p>GET /api/users - 用户列表</p>
<p>GET /api/users/{id} - 用户详情(含记忆/情绪)</p>
<p>GET /api/conversations?user_id=X - 对话记录</p>
<p>GET /api/stickers - 表情包库</p>
<p>GET /api/stats - 统计数据</p>
<p>GET /api/health - 健康检查</p>
</div>
<script>
fetch('/api/stats').then(r=>r.json()).then(d=>{
 document.getElementById('users').textContent=d.total_users||0;
 document.getElementById('msgs').textContent=d.total_messages||0;
 document.getElementById('active').textContent=d.active_today||0;
});
fetch('/api/users').then(r=>r.json()).then(users=>{
 var h='<table><tr><th>QQ</th><th>称呼</th><th>最后活跃</th><th>消息数</th></tr>';
 users.slice(0,10).forEach(u=>{
 h+='<tr><td>'+u.qq_id+'</td><td>'+(u.preferred_name||u.nickname||'-')+'</td><td>'+(u.last_seen||'-')+'</td><td>'+u.total_messages+'</td></tr>';
 });
 h+='</table>';
 document.getElementById('users-list').innerHTML=h;
});
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return HTML_INDEX


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok", "version": "2.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/stats")
async def stats() -> dict[str, Any]:
    db = await get_db()
    try:
        u = await db.execute_fetchall("SELECT COUNT(*) as c FROM users")
        m = await db.execute_fetchall("SELECT COUNT(*) as c FROM messages")
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        a = await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM users WHERE last_seen >= ?", (today,)
        )
        return {
            "total_users": u[0]["c"],
            "total_messages": m[0]["c"],
            "active_today": a[0]["c"],
        }
    finally:
        await db.close()


@app.get("/api/users")
async def list_users() -> list[dict[str, Any]]:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, qq_id, nickname, preferred_name, last_seen, total_messages "
            "FROM users ORDER BY last_seen DESC LIMIT 50"
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


@app.get("/api/users/{user_id}")
async def user_detail(user_id: int) -> dict[str, Any]:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        if not rows:
            return {"error": "not found"}
        user = dict(rows[0])
        facts = await db.execute_fetchall(
            "SELECT * FROM memory_facts WHERE user_id = ?", (user_id,)
        )
        em = await db.execute_fetchall(
            "SELECT * FROM emotions WHERE user_id = ?", (user_id,)
        )
        user["facts"] = [dict(f) for f in facts]
        user["emotion"] = dict(em[0]) if em else None
        return user
    finally:
        await db.close()


@app.get("/api/conversations")
async def conversations(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
) -> dict[str, Any]:
    db = await get_db()
    try:
        offset = (page - 1) * limit
        rows = await db.execute_fetchall(
            "SELECT * FROM messages WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        )
        total = await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM messages WHERE user_id = ?", (user_id,)
        )
        return {
            "messages": [dict(r) for r in reversed(rows)],
            "total": total[0]["c"],
            "page": page, "limit": limit,
        }
    finally:
        await db.close()


@app.get("/api/stickers")
async def list_stickers() -> list[dict[str, Any]]:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM stickers ORDER BY usage_count DESC"
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


def start_web() -> None:
    import uvicorn
    uvicorn.run(app, host=CONFIG.web_host, port=CONFIG.web_port, log_level="info")
