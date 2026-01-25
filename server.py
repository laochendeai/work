
import asyncio
import logging
import os
import subprocess
import threading
import queue
from typing import List, Optional

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from storage import Database

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    Database()
    yield
    # Clean up (if needed)

# Initialize FastAPI app
app = FastAPI(title="Bidding Scraper UI", lifespan=lifespan)

# Allow CORS (useful for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        import sys
        cmd = [sys.executable, "main.py", "bxsearch"]
        
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
        
        # Top 5 companies by project count (number of announcements)
        cursor.execute("""
            SELECT bc.company, COUNT(DISTINCT bcm.announcement_id) as count 
            FROM business_cards bc
            JOIN business_card_mentions bcm ON bcm.business_card_id = bc.id
            GROUP BY bc.company 
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
async def get_announcements(limit: int = 50, offset: int = 0, q: str = "", province: str = ""):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause
        where_parts = []
        params = []
        
        if q:
            where_parts.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        
        if province:
            # 按省份筛选（从标题或内容中匹配）
            where_parts.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{province}%", f"%{province}%"])
        
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        # Get total count
        count_sql = f"SELECT COUNT(*) FROM announcements WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # Get data
        data_sql = f"""
            SELECT id, title, url, publish_date, source 
            FROM announcements 
            WHERE {where_clause}
            ORDER BY publish_date DESC 
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_sql, params + [limit, offset])
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [dict(row) for row in cursor.fetchall()]
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/api/announcements/{item_id}")
async def get_announcement_detail(item_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM announcements WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Not found"})
        return dict(row)
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
        
        # 基础查询条件
        where_clause = ""
        params = []
        if q:
            search = f"%{q}%"
            where_clause = "WHERE bc.company LIKE ? OR bc.contact_name LIKE ?"
            params = [search, search]
        
        # 获取总数
        count_sql = f"""
            SELECT COUNT(DISTINCT bc.id) 
            FROM business_cards bc
            {where_clause}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        data_sql = f"""
            SELECT 
                bc.id, bc.company, bc.contact_name, 
                bc.phones_json, bc.emails_json,
                bc.created_at, bc.updated_at,
                COUNT(DISTINCT bcm.announcement_id) AS projects_count
            FROM business_cards bc
            LEFT JOIN business_card_mentions bcm ON bcm.business_card_id = bc.id
            {where_clause}
            GROUP BY bc.id
            ORDER BY bc.updated_at DESC 
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_sql, params + [limit, offset])
        
        import json
        results = []
        for row in cursor.fetchall():
            card = dict(row)
            # Parse JSON fields
            try:
                phones_list = json.loads(card.get('phones_json') or '[]')
                card['phones'] = ', '.join(phones_list) if phones_list else ''
            except:
                card['phones'] = ''
            try:
                emails_list = json.loads(card.get('emails_json') or '[]')
                card['emails'] = ', '.join(emails_list) if emails_list else ''
            except:
                card['emails'] = ''
            results.append(card)
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": results
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/api/cards/{card_id}/mentions")
async def get_card_mentions(card_id: int):
    try:
        conn = get_db_connection()
        # We need to use the Database class method, but here we are using raw connection in get_db_connection helper.
        # However, the previous code in server.py mainly uses raw sql. 
        # But wait, `Database()` in `lifespan` just inits the table.
        # The `get_db_connection` returns a raw sqlite3 connection.
        # It's better to use the `Database` class if possible, or just write the SQL here.
        # Since I just added the SQL to Database class, I should probably use it or copy the SQL.
        # `server.py` seems to use `get_db_connection` and raw SQL for other endpoints.
        # To match the style (and avoid instantiating Database class which might have overhead or different locking),
        # I will replicate the SQL here as commonly done in this file.
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                a.id, a.title, a.url, a.source, a.publish_date, 
                bcm.role
            FROM business_card_mentions bcm
            JOIN announcements a ON bcm.announcement_id = a.id
            WHERE bcm.business_card_id = ?
            ORDER BY a.publish_date DESC
        """, (card_id,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

# ========== Keyword Management ==========
KEYWORDS_FILE = os.path.join("data", "saved_keywords.json")

class KeywordsRequest(BaseModel):
    keywords: List[str]
    filename: Optional[str] = None

@app.get("/api/keywords")
async def get_keywords():
    try:
        if os.path.exists(KEYWORDS_FILE):
            import json
            with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        return {"keywords": [], "filename": None}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/keywords")
async def save_keywords(req: KeywordsRequest):
    try:
        import json
        # Ensure data directory exists
        os.makedirs(os.path.dirname(KEYWORDS_FILE), exist_ok=True)
        
        data = {
            "keywords": req.keywords,
            "filename": req.filename
        }
        with open(KEYWORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {"status": "saved", "count": len(req.keywords)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ========== Card Export ==========
@app.get("/api/cards/export")
async def export_cards(q: str = ""):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if q:
            search = f"%{q}%"
            cursor.execute("""
                SELECT 
                    bc.id, bc.company, bc.contact_name, 
                    bc.phones_json, bc.emails_json,
                    bc.created_at, bc.updated_at,
                    COUNT(DISTINCT bcm.announcement_id) AS projects_count
                FROM business_cards bc
                LEFT JOIN business_card_mentions bcm ON bcm.business_card_id = bc.id
                WHERE bc.company LIKE ? OR bc.contact_name LIKE ?
                GROUP BY bc.id
                ORDER BY bc.company, bc.contact_name
            """, (search, search))
        else:
            cursor.execute("""
                SELECT 
                    bc.id, bc.company, bc.contact_name, 
                    bc.phones_json, bc.emails_json,
                    bc.created_at, bc.updated_at,
                    COUNT(DISTINCT bcm.announcement_id) AS projects_count
                FROM business_cards bc
                LEFT JOIN business_card_mentions bcm ON bcm.business_card_id = bc.id
                GROUP BY bc.id
                ORDER BY bc.company, bc.contact_name
            """)
        
        import json
        rows = []
        for row in cursor.fetchall():
            card = dict(row)
            try:
                phones = json.loads(card.get('phones_json') or '[]')
                card['phones'] = ', '.join(phones)
            except:
                card['phones'] = ''
            try:
                emails = json.loads(card.get('emails_json') or '[]')
                card['emails'] = ', '.join(emails)
            except:
                card['emails'] = ''
            rows.append(card)
        
        conn.close()
        
        # Generate Excel file
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        except ImportError:
            return JSONResponse(status_code=500, content={"error": "openpyxl not installed. Run: pip install openpyxl"})
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "名片库"
        
        # Header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Headers
        headers = ["公司名称", "联系人", "电话", "邮箱", "关联项目数", "创建时间", "更新时间"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Data rows
        for row_idx, card in enumerate(rows, 2):
            ws.cell(row=row_idx, column=1, value=card.get('company', ''))
            ws.cell(row=row_idx, column=2, value=card.get('contact_name', ''))
            ws.cell(row=row_idx, column=3, value=card.get('phones', ''))
            ws.cell(row=row_idx, column=4, value=card.get('emails', ''))
            ws.cell(row=row_idx, column=5, value=card.get('projects_count', 0))
            ws.cell(row=row_idx, column=6, value=card.get('created_at', ''))
            ws.cell(row=row_idx, column=7, value=card.get('updated_at', ''))
            
            for col in range(1, 8):
                ws.cell(row=row_idx, column=col).border = thin_border
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 30
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 20
        
        # Save to bytes
        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        from datetime import datetime
        filename = f"business_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# Mount static files - MUST BE LAST
app.mount("/", StaticFiles(directory="web", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Ensure data dir exists
    if not os.path.exists("data"):
        os.makedirs("data")
        
    print("Starting server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
