import os
import sys
import json
import traceback
import math
import io
import time
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import google.generativeai as genai
from sqlalchemy.orm import Session

from dotenv import load_dotenv
load_dotenv()

import database, models, auth

# Create DB tables
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- AUTH ROUTES ----------------- #
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    identifier: str
    password: str

@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(database.get_db)):
    if not user.username or len(user.username.strip()) == 0:
        raise HTTPException(status_code=400, detail="Invalid username.")
        
    username_clean = user.username.strip().lower()
    email_clean = user.email.strip().lower()
    
    if not email_clean.endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Only Gmail addresses are allowed.")
        
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password does not meet requirements.")

    db_user_email = db.query(models.User).filter(models.User.email == email_clean).first()
    if db_user_email:
        raise HTTPException(status_code=409, detail="Email already exists.")
        
    db_user_name = db.query(models.User).filter(models.User.username == username_clean).first()
    if db_user_name:
        raise HTTPException(status_code=409, detail="Username already exists.")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=username_clean, email=email_clean, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = auth.create_access_token(data={"sub": str(new_user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}}

@app.post("/api/auth/login")
def login(user: UserLogin, db: Session = Depends(database.get_db)):
    identifier_clean = user.identifier.strip().lower()
    
    db_user = db.query(models.User).filter(
        (models.User.email == identifier_clean) | (models.User.username == identifier_clean)
    ).first()
    
    if not db_user or not auth.verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")
        
    access_token = auth.create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": db_user.id, "username": db_user.username, "email": db_user.email}}

@app.get("/api/auth/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}

# ----------------- DATASET ROUTES ----------------- #
@app.post("/api/upload")
async def upload_dataset(
    file: UploadFile = File(...), 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        content = await file.read()
        
        if not content or len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty.")
            
        if len(content) > 50 * 1024 * 1024: # 50 MB limit
            raise HTTPException(status_code=413, detail="File is too large. Maximum size is 50MB.")
            
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            elif file.filename.endswith('.xlsx'):
                df = pd.read_excel(io.BytesIO(content))
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")
        except Exception as read_e:
            raise HTTPException(status_code=422, detail="Malformed file. Could not parse dataset.")
            
        # Serialize back to parquet for efficient storage
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer)
        parquet_bytes = parquet_buffer.getvalue()
        
        # Profile data
        ds = models.Dataset(
            user_id=current_user.id,
            name=file.filename,
            original_filename=file.filename,
            file_type="csv" if file.filename.endswith('.csv') else "xlsx",
            row_count=len(df),
            column_count=len(df.columns),
            file_data=parquet_bytes
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)
        
        sensitive_keywords = ['email', 'password', 'token', 'phone', 'mobile', 'address', 'name', 'aadhaar', 'pan', 'credit_card', 'secret']
        
        # Create columns
        for col in df.columns:
            col_type = str(df[col].dtype)
            missing = int(df[col].isna().sum())
            unique = int(df[col].nunique())
            
            ds_col = models.DatasetColumn(
                dataset_id=ds.id,
                column_name=str(col),
                data_type=col_type,
                missing_count=missing,
                unique_count=unique,
                nullable=(missing > 0)
            )
            db.add(ds_col)
            
        db.commit()
        
        return {"id": ds.id, "filename": ds.name, "rows": ds.row_count, "columns": ds.column_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/datasets")
def list_datasets(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    datasets = db.query(models.Dataset).filter(models.Dataset.user_id == current_user.id).all()
    
    result = []
    for ds in datasets:
        cols = db.query(models.DatasetColumn).filter(models.DatasetColumn.dataset_id == ds.id).all()
        
        columns_info = {}
        for c in cols:
            columns_info[c.column_name] = {
                "type": c.data_type,
                "missing": c.missing_count,
                "unique": c.unique_count
            }
            
        result.append({
            "id": ds.id,
            "filename": ds.name,
            "profile": {
                "rows": ds.row_count,
                "columns": ds.column_count,
                "columns_info": columns_info
            }
        })
    return result

@app.get("/api/datasets/{id}")
def get_dataset(id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    ds = db.query(models.Dataset).filter(
        models.Dataset.id == id,
        models.Dataset.user_id == current_user.id
    ).first()
    
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied.")
        
    cols = db.query(models.DatasetColumn).filter(models.DatasetColumn.dataset_id == ds.id).all()
    
    columns_info = {}
    for c in cols:
        columns_info[c.column_name] = {
            "type": c.data_type,
            "missing": c.missing_count,
            "unique": c.unique_count
        }
        
    return {
        "id": ds.id,
        "filename": ds.name,
        "profile": {
            "rows": ds.row_count,
            "columns": ds.column_count,
            "columns_info": columns_info
        }
    }

# ----------------- AI & ANALYSIS ROUTES ----------------- #
class QuestionRequest(BaseModel):
    question: str
    dataset_ids: List[int]

@app.post("/api/ask")
def ask_question(
    req: QuestionRequest, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not req.question:
        raise HTTPException(status_code=400, detail="No question provided")
    if not req.dataset_ids:
        raise HTTPException(status_code=400, detail="No datasets selected")
    if len(req.dataset_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum of 5 datasets can be analyzed at once.")
        
    # Load requested datasets and verify ownership
    datasets = {}
    schemas = {}
    
    sensitive_keywords = ['email', 'password', 'token', 'phone', 'mobile', 'address', 'customer_name', 'aadhaar', 'pan', 'credit_card', 'secret']
    
    for ds_id in req.dataset_ids:
        ds = db.query(models.Dataset).filter(models.Dataset.id == ds_id, models.Dataset.user_id == current_user.id).first()
        if not ds:
            raise HTTPException(status_code=403, detail=f"Dataset {ds_id} not found or access denied")
            
        # Load df
        df = pd.read_parquet(io.BytesIO(ds.file_data))
        datasets[ds.name] = df
        
        # Build schema for AI (without sensitive data)
        cols = db.query(models.DatasetColumn).filter(models.DatasetColumn.dataset_id == ds.id).all()
        col_schemas = {}
        for c in cols:
            is_sensitive = any(kw in c.column_name.lower() for kw in sensitive_keywords)
            if not is_sensitive:
                col_schemas[c.column_name] = {
                    "type": c.data_type,
                    "missing": c.missing_count
                }
                
        schemas[ds.name] = {
            "rows": ds.row_count,
            "columns": col_schemas
        }
            
    # Setup Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemma-4-26b-a4b-it", generation_config={"response_mime_type": "application/json"})
    
    prompt = f"""
    You are an expert Data Analyst. Your goal is to answer the user's question using the provided datasets.
    
    User Question: {req.question}
    
    Available Datasets and Schemas:
    {json.dumps(schemas, indent=2)}
    
    Instructions:
    1. Determine if the question can be reliably answered using ONLY the provided datasets. If the data is missing or doesn't support forecasting/prediction (e.g. asking for 2035 revenue when only past data is present), set answerable to false. Do NOT invent numbers.
    2. If answerable, generate Python code using pandas to compute the exact answer.
    3. The code will be executed in an environment where datasets are available in a dictionary called `datasets`.
       Example: `sales = datasets['sales.csv']`
    4. The python code must assign the final result to a variable named `result`.
    5. The final `result` MUST be a single JSON serializable value (string, number, list, or simple dict), not a DataFrame or Series. Use `.to_dict()`, `.tolist()`, `.item()`. Do not return raw DataFrames.
    6. Ensure the code is safe (no arbitrary OS operations). DO NOT include any `import` statements. pandas and numpy are already available as `pd` and `np`.
    
    IMPORTANT: Output ONLY valid JSON. Do not include any explanations, reasoning, markdown formatting, or text outside of the JSON block. Your entire response must be parseable by json.loads().
    
    Output JSON schema:
    {{
      "answerable": boolean,
      "confidence": float,
      "reason": "String explaining why it's answerable or not",
      "required_datasets": ["list", "of", "filenames"],
      "required_columns": ["list", "of", "columns"],
      "python_code": "Python code block as a string, no imports, ending with `result = ...` (only if answerable=true, else null)",
      "visualization": "string (e.g. 'bar', 'line', 'pie', or null)"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Try to find ```json ... ``` blocks
        import re
        blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if blocks:
            json_text = blocks[-1]
        else:
            # find first { and last }
            # Since LLM might output LaTeX like \text{quantity}, find '{' followed by '"answerable"' or similar.
            import re
            json_match = re.search(r'\{\s*"answerable".*\}', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                start = text.rfind('{')
                end = text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_text = text[start:end+1]
                else:
                    json_text = text
                    
        ai_plan = json.loads(json_text)
    except Exception as e:
        # Internally, we can log the exact error. For the user, return a clean message.
        print(f"AI Generation Error: {str(e)}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"Raw response: {response.text}")
        raise HTTPException(status_code=500, detail="An error occurred while generating the analysis plan.")
        
    # Save History placeholder
    history = models.AnalysisHistory(
        user_id=current_user.id,
        question=req.question,
        dataset_ids=json.dumps(req.dataset_ids),
        status="started"
    )
    db.add(history)
    db.commit()
    db.refresh(history)
        
    if not ai_plan.get("answerable"):
        history.status = "refused"
        history.answer = json.dumps({"reason": ai_plan.get("reason", "Question cannot be answered with current data.")})
        db.commit()
        return {
            "status": "refused",
            "reason": ai_plan.get("reason", "Question cannot be answered with current data."),
            "evidence": ai_plan
        }
        
    code = ai_plan.get("python_code")
    if not code:
        history.status = "error"
        history.answer = "No code generated by AI."
        db.commit()
        return {
            "status": "error",
            "message": "No code generated by AI.",
            "evidence": ai_plan
        }

    # Validate and clean code
    unsafe_keywords = ["os.", "subprocess", "sys.", "open(", "eval(", "exec(", "import os", "import sys", "import subprocess", "__import__", "socket", "requests", "urllib", "__"]
    if any(kw in code for kw in unsafe_keywords):
        history.status = "error"
        history.answer = "Unsafe code generated."
        db.commit()
        return {
            "status": "error",
            "message": "Unsafe code generated.",
            "evidence": ai_plan
        }

    # Execute code
    local_env = {
        "datasets": datasets,
        "pd": pd,
        "np": np
    }
    
    try:
        start_time = time.time()
        exec(code, local_env)
        result = local_env.get("result")
        exec_time = time.time() - start_time
        
        # Convert pandas types to native python for serialization
        if isinstance(result, (np.integer, np.floating)):
            result = result.item()
        elif isinstance(result, pd.Series):
            result = result.to_dict()
        elif isinstance(result, np.ndarray):
            result = result.tolist()
            
        history.status = "success"
        history.answer = json.dumps(result)
        history.generated_code = code
        history.execution_time_ms = round(exec_time * 1000, 2)
        db.commit()
            
        return {
            "status": "success",
            "result": result,
            "execution_time_ms": round(exec_time * 1000, 2),
            "evidence": ai_plan,
            "code": code
        }
    except Exception as e:
        history.status = "execution_error"
        history.answer = str(e)
        history.generated_code = code
        db.commit()
        
        return {
            "status": "execution_error",
            "error": "Error executing the generated code.",
            "evidence": ai_plan,
            "code": code
        }

@app.get("/api/history")
def get_history(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    history = db.query(models.AnalysisHistory).filter(models.AnalysisHistory.user_id == current_user.id).order_by(models.AnalysisHistory.created_at.desc()).limit(10).all()
    return [{
        "id": h.id,
        "question": h.question,
        "status": h.status,
        "created_at": h.created_at
    } for h in history]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
