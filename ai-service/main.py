from fastapi import Form
from fastapi.responses import RedirectResponse

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"
from database import init_db
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os
import face_recognition
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, UploadFile, File

app = FastAPI()
init_db()
templates = Jinja2Templates(directory="templates")

# ----------------------------
# FOLDER SETUP
# ----------------------------

KNOWN_FACES_DIR = "known_faces"

if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)

# ----------------------------
# LOAD KNOWN FACES
# ----------------------------

known_encodings = []
known_names = []


def load_known_faces():
    known_encodings.clear()
    known_names.clear()

    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            image_path = os.path.join(KNOWN_FACES_DIR, filename)

            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)

            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(os.path.splitext(filename)[0])


# ----------------------------
# ATTENDANCE FUNCTION
# ----------------------------

import sqlite3
from datetime import datetime

def mark_attendance(name):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    today_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    cursor.execute("""
        SELECT * FROM attendance 
        WHERE name = ? AND date = ?
    """, (name, today_date))

    record = cursor.fetchone()

    if record:
        conn.close()
        return "Already Marked Today"

    cursor.execute("""
        INSERT INTO attendance (name, date, time)
        VALUES (?, ?, ?)
    """, (name, today_date, current_time))

    conn.commit()
    conn.close()

    return "Attendance Marked Successfully"


# ----------------------------
# RECOGNIZE API
# ----------------------------

@app.post("/recognize", response_class=HTMLResponse)
async def recognize_face(request: Request, file: UploadFile = File(...)):
    load_known_faces()

    temp_file = f"temp_{file.filename}"

    with open(temp_file, "wb") as buffer:
        buffer.write(await file.read())

    image = face_recognition.load_image_file(temp_file)
    unknown_encodings = face_recognition.face_encodings(image)

    os.remove(temp_file)

    if len(unknown_encodings) == 0:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": "❌ No face detected"
        })

    unknown_encoding = unknown_encodings[0]

    results = face_recognition.compare_faces(
        known_encodings,
        unknown_encoding
    )

    if True in results:
        match_index = results.index(True)
        matched_name = known_names[match_index]
        status = mark_attendance(matched_name)

        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": f"✅ {matched_name} - {status}"
        })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": "❌ Unknown Face"
    })


# ----------------------------
# HOME ROUTE
# ----------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



    import sqlite3

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name, date, time FROM attendance ORDER BY id DESC")
    records = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = date('now')")
    total_today = cursor.fetchone()[0]

    conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "records": records,
        "total_today": total_today
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=303)
        return response
    return {"message": "Invalid Credentials"}


    from fastapi import Form
from fastapi.responses import JSONResponse

# Ensure known_faces folder exists
if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register_student")
async def register_student(name: str = Form(...), file: UploadFile = File(...)):
    file_path = os.path.join(KNOWN_FACES_DIR, f"{name}.jpg")

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Update known faces immediately
    load_known_faces()

    return JSONResponse({"message": f"✅ Student '{name}' registered successfully!"})