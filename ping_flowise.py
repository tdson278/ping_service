#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import subprocess, platform, re
from datetime import datetime

app = FastAPI(title="PingService", version="1.0")

class PingRequest(BaseModel):
    target: str = Field(..., description="IPv4/IPv6 address hoặc hostname")
    count: int = Field(4, description="Số gói tin ping (default = 4)")
    confirm: bool = Field(False, description="Phải đặt True để cho phép ping")

def run_ping(target: str, count: int = 4):
    system = platform.system().lower()

    if system == "windows":
        cmd = ["ping", "-n", str(count), target]
    else:  # Linux / macOS
        cmd = ["ping", "-c", str(count), target]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Ping timeout")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Ping failed: {result.stderr.strip()}")

    return result.stdout

def parse_ping_output(output: str):
    stats = {"packet_loss": None, "avg_rtt_ms": None}

    # Detect packet loss
    m_loss = re.search(r"(\d+)%\s*loss", output)
    if not m_loss:
        m_loss = re.search(r"(\d+(\.\d+)?)% packet loss", output)
    if m_loss:
        stats["packet_loss"] = float(m_loss.group(1))

    # Detect average RTT
    m_rtt = re.search(r"Average = (\d+)ms", output)  # Windows
    if not m_rtt:
        m_rtt = re.search(r"= [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+ ms", output)  # Linux/macOS
    if m_rtt:
        stats["avg_rtt_ms"] = float(m_rtt.group(1))

    return stats

@app.post("/ping")
def ping_host(req: PingRequest):
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Phải đặt confirm=true để chạy ping")

    started = datetime.utcnow().isoformat() + "Z"
    raw_output = run_ping(req.target, req.count)
    stats = parse_ping_output(raw_output)

    return {
        "target": req.target,
        "count": req.count,
        "started_at": started,
        "raw_output": raw_output,
        "stats": stats
    }

@app.get("/health")
def health():
    return {"status": "ok", "ping_available": True}
