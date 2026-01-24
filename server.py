
import asyncio
import logging
import os
import subprocess
import threading
import queue
from typing import List, Optional

from fastapi import FastAPI, WebSocket, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

# Initialize FastAPI app
app = FastAPI(title="Bidding Scraper UI")

# Allow CORS (useful for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for the running process
class ProcessManager:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.output_queue = queue.Queue()
        self.is_running = False

    def start_process(self, command: List[str]):
        with self.lock:
            if self.is_running:
                raise Exception("A scan is already running")
            
            self.is_running = True
            # Use line buffering
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            # Start a thread to read output
            threading.Thread(target=self._read_output, daemon=True).start()

    def _read_output(self):
        try:
            if not self.process:
                return
                
            for line in iter(self.process.stdout.readline, ''):
                self.output_queue.put(line)
                
            self.process.stdout.close()
            self.process.wait()
        except Exception as e:
            self.output_queue.put(f"Error reading output: {e}\n")
        finally:
            with self.lock:
                self.is_running = False
            self.output_queue.put("[Process Completed]\n")

    def kill_process(self):
        with self.lock:
            if self.process and self.is_running:
                self.process.terminate()
                self.is_running = False

process_manager = ProcessManager()

# Models
class SearchRequest(BaseModel):
    keywords: str
    search_type: str = "fulltext"
    pinmu: str = "all"
    category: str = "all"
    bid_type: str = "all"
    time_type: str = "1week"
    max_pages: int = 3
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# Database helper
def get_db_connection():
    db_path = os.path.join("data", "gp.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# API Endpoints

@app.post("/api/search")
async def start_search(req: SearchRequest):
    try:
        # Construct command
        cmd = ["python", "main.py", "bxsearch"]
        
        # Handle keywords (comma separated)
        kw_list = [k.strip() for k in req.keywords.split(",") if k.strip()]
        if not kw_list:
             return JSONResponse(status_code=400, content={"error": "Keywords required"})
        
        cmd.extend(["--kw"] + kw_list)
        cmd.extend(["--search-type", req.search_type])
        cmd.extend(["--pinmu", req.pinmu])
        cmd.extend(["--category", req.category])
        cmd.extend(["--bid-type", req.bid_type])
        cmd.extend(["--time", req.time_type])
        cmd.extend(["--max-pages", str(req.max_pages)])
        
        if req.time_type == "custom":
            if req.start_date:
                cmd.extend(["--start-date", req.start_date])
            if req.end_date:
                cmd.extend(["--end-date", req.end_date])
        
        process_manager.start_process(cmd)
        return {"status": "started", "command": " ".join(cmd)}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/api/stop")
async def stop_search():
    process_manager.kill_process()
    return {"status": "stopped"}

@app.get("/api/status")
async def get_status():
    return {"is_running": process_manager.is_running}

@app.websocket("/api/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Non-blocking get from queue
            try:
                # Flush all available lines
                lines = []
                while True:
                    line = process_manager.output_queue.get_nowait()
                    lines.append(line)
            except queue.Empty:
                pass
            
            if lines:
                await websocket.send_text("".join(lines))
            
            await asyncio.sleep(0.1)
    except Exception:
        pass

@app.get("/api/stats")
async def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM announcements")
        total_announcements = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM business_cards")
        total_cards = cursor.fetchone()[0]
        
        # Top 5 companies
        cursor.execute("""
            SELECT company, COUNT(*) as count 
            FROM business_cards 
            GROUP BY company 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_companies = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total_announcements": total_announcements,
            "total_cards": total_cards,
            "top_companies": top_companies
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/api/announcements")
async def get_announcements(limit: int = 50, offset: int = 0):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, url, publish_date, source 
            FROM announcements 
            ORDER BY publish_date DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/api/cards")
async def get_cards(limit: int = 50, offset: int = 0, q: str = ""):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if q:
            search = f"%{q}%"
            cursor.execute("""
                SELECT * FROM business_cards 
                WHERE company LIKE ? OR contact_name LIKE ?
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (search, search, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM business_cards 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

# Mount static files - MUST BE LAST
app.mount("/", StaticFiles(directory="web", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Ensure data dir exists
    if not os.path.exists("data"):
        os.makedirs("data")
        
    print("Starting server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
