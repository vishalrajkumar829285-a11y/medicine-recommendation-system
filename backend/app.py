"""CareCompass API — educational health insights, never a diagnosis or prescription."""
from datetime import datetime, timezone
from io import BytesIO
import base64, hashlib, hmac, os, secrets, sqlite3
from pathlib import Path
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from recommendation import assess
DB_PATH=Path(__file__).with_name("carecompass.db"); TOKENS={}; security=HTTPBearer(); app=FastAPI(title="CareCompass API",version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://medicine-recommendation-system-woad.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
def connection():
 db=sqlite3.connect(DB_PATH);db.row_factory=sqlite3.Row;return db
@app.on_event("startup")
def startup():
 with connection() as db: db.executescript("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,input_json TEXT NOT NULL,output_json TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));")
def hash_password(password,salt=None):
 salt=salt or os.urandom(16);return base64.b64encode(salt+hashlib.pbkdf2_hmac("sha256",password.encode(),salt,210000)).decode()
def verify_password(password,stored):
 raw=base64.b64decode(stored.encode());return hmac.compare_digest(hash_password(password,raw[:16]),stored)
def current_user(credentials:HTTPAuthorizationCredentials=Depends(security)):
 user_id=TOKENS.get(credentials.credentials)
 if not user_id: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Please sign in.")
 return user_id
class AuthRequest(BaseModel):
 name:str=Field(default="",max_length=80);email:str=Field(min_length=5,max_length=254);password:str=Field(min_length=8,max_length=128)
class AssessmentRequest(BaseModel):
 age:int=Field(ge=1,le=120);gender:str="Prefer not to say";weight:float|None=Field(default=None,ge=1,le=350);height:float|None=Field(default=None,ge=30,le=260);blood_pressure:str|None=Field(default=None,max_length=30);sugar_level:float|None=Field(default=None,ge=0,le=1000);symptoms:list[str]=Field(min_length=1,max_length=20);medical_history:str=Field(default="",max_length=1000);allergies:str=Field(default="",max_length=1000)
def user_response(user,token): return {"token":token,"user":{"id":user["id"],"name":user["name"],"email":user["email"]}}
@app.get("/health")
def health(): return {"status":"ok","message":"Educational use only; not medical advice."}
@app.post("/auth/register",status_code=201)
def register(payload:AuthRequest):
 email=payload.email.strip().lower()
 if not payload.name.strip(): raise HTTPException(422,"Name is required.")
 try:
  with connection() as db:
   cur=db.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(payload.name.strip(),email,hash_password(payload.password),datetime.now(timezone.utc).isoformat()));user=db.execute("SELECT * FROM users WHERE id=?",(cur.lastrowid,)).fetchone()
 except sqlite3.IntegrityError as exc: raise HTTPException(409,"An account with this email already exists.") from exc
 token=secrets.token_urlsafe(32);TOKENS[token]=user["id"];return user_response(user,token)
@app.post("/auth/login")
def login(payload:AuthRequest):
 with connection() as db:user=db.execute("SELECT * FROM users WHERE email=?",(payload.email.strip().lower(),)).fetchone()
 if not user or not verify_password(payload.password,user["password_hash"]):raise HTTPException(401,"Incorrect email or password.")
 token=secrets.token_urlsafe(32);TOKENS[token]=user["id"];return user_response(user,token)
@app.post("/assess")
def create_assessment(payload:AssessmentRequest,user_id:int=Depends(current_user)):
 import json
 output=assess(payload.model_dump());report={"id":str(uuid4()),"created_at":datetime.now(timezone.utc).isoformat(),"input":payload.model_dump(),**output}
 with connection() as db:db.execute("INSERT INTO reports VALUES(?,?,?,?,?)",(report["id"],user_id,report["created_at"],json.dumps(report["input"]),json.dumps(output)))
 return report
@app.get("/history")
def history(user_id:int=Depends(current_user)):
 import json
 with connection() as db:rows=db.execute("SELECT id,created_at,output_json FROM reports WHERE user_id=? ORDER BY created_at DESC",(user_id,)).fetchall()
 return [{"id":r["id"],"created_at":r["created_at"],**{k:json.loads(r["output_json"])[k] for k in("prediction","confidence","emergency")}} for r in rows]
@app.get("/dashboard")
def dashboard(user_id:int=Depends(current_user)):
 import json
 with connection() as db:rows=db.execute("SELECT output_json FROM reports WHERE user_id=? ORDER BY created_at DESC",(user_id,)).fetchall()
 reports=[json.loads(r["output_json"]) for r in rows];return {"total_assessments":len(reports),"urgent_flags":sum(r["emergency"] for r in reports),"latest_pattern":reports[0]["prediction"] if reports else None}
@app.get("/reports/{report_id}")
def report_detail(report_id:str,user_id:int=Depends(current_user)):
 import json
 with connection() as db:row=db.execute("SELECT created_at,input_json,output_json FROM reports WHERE id=? AND user_id=?",(report_id,user_id)).fetchone()
 if not row:raise HTTPException(404,"Report not found")
 return {"id":report_id,"created_at":row["created_at"],"input":json.loads(row["input_json"]),**json.loads(row["output_json"])}
@app.get("/reports/{report_id}/download")
def download_report(report_id:str,user_id:int=Depends(current_user)):
 import json
 with connection() as db:row=db.execute("SELECT created_at,input_json,output_json FROM reports WHERE id=? AND user_id=?",(report_id,user_id)).fetchone()
 if not row:raise HTTPException(404,"Report not found")
 result,intake=json.loads(row["output_json"]),json.loads(row["input_json"])
 try:
  from reportlab.lib.pagesizes import letter
  from reportlab.pdfgen import canvas
 except ImportError as exc:raise HTTPException(503,"Install reportlab to enable PDF downloads") from exc
 buffer=BytesIO();pdf=canvas.Canvas(buffer,pagesize=letter);lines=["CareCompass Educational Health Summary","This is not a diagnosis, prescription, or substitute for a clinician.",f"Generated: {row['created_at'][:19]} UTC",f"Possible pattern: {result['prediction']}",f"Educational confidence indicator: {result['confidence']}%","Symptoms: "+", ".join(intake["symptoms"]),"Next step: "+result["specialist"]];y=740
 for line in lines:pdf.drawString(48,y,line[:110]);y-=28
 pdf.save();buffer.seek(0);return StreamingResponse(buffer,media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=carecompass-report.pdf"})
