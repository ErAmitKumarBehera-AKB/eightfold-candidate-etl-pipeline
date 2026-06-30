from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import json
from src.pipeline import Pipeline

app = FastAPI(title="Candidate Data Transformer")

os.makedirs("web", exist_ok=True)

app.mount("/static", StaticFiles(directory="web"), name="static")

class RunPipelineRequest(BaseModel):
    config: dict

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("web/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/run")
async def run_pipeline(request: RunPipelineRequest):
    try:
        with open("mock_data/temp_config.json", "w", encoding="utf-8") as f:
            json.dump(request.config, f)
            
        pipeline = Pipeline(data_dir="mock_data", config_path="mock_data/temp_config.json")
        result = pipeline.run()
        
        if os.path.exists("mock_data/temp_config.json"):
            os.remove("mock_data/temp_config.json")
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/api/config")
async def get_default_config():
    try:
        with open("mock_data/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

@app.get("/api/inputs")
async def get_inputs():
    inputs = {}
    for filename in os.listdir("mock_data"):
        if filename.endswith(".json") and filename != "config.json" and filename != "temp_config.json":
            with open(os.path.join("mock_data", filename), "r", encoding="utf-8") as f:
                inputs[filename] = json.load(f)
        elif filename.endswith(".csv"):
            with open(os.path.join("mock_data", filename), "r", encoding="utf-8") as f:
                inputs[filename] = f.read()
    return inputs
