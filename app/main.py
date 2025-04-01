import logging
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import os
from pathlib import Path

from google_drive_processor import GoogleDriveProcessor
from services.synthesizer import SynthesizedResponse

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("app")

# Create FastAPI app
app = FastAPI(
    title="Google Drive Document Processor",
    description="Process files from Google Drive and query them using natural language.",
    version="1.0.0",
)

# Initialize processor
processor = GoogleDriveProcessor()

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))

# Define API models
class QueryRequest(BaseModel):
    query: str
    limit: int = 5

class ProcessRequest(BaseModel):
    file_name: str

class ProcessResponse(BaseModel):
    success: bool
    message: str

# Set up the database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Setting up database tables and indexes...")
    processor.setup_database()
    logger.info("Database setup complete")

# Routes for API
@app.post("/api/process", response_model=ProcessResponse)
async def process_file_api(request: ProcessRequest):
    """Process a file from Google Drive via API."""
    try:
        success = processor.process_file(request.file_name)
        if success:
            return ProcessResponse(
                success=True,
                message=f"Successfully processed file: {request.file_name}"
            )
        else:
            return ProcessResponse(
                success=False,
                message=f"Failed to process file: {request.file_name}"
            )
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query", response_model=SynthesizedResponse)
async def query_documents_api(request: QueryRequest):
    """Query documents via API."""
    try:
        response = processor.search_documents(request.query, limit=request.limit)
        return response
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Routes for web UI
@app.get("/", response_class=HTMLResponse)
async def get_home_page(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "Google Drive Document Processor"}
    )

@app.post("/process", response_class=HTMLResponse)
async def process_file_web(request: Request, file_name: str = Form(...)):
    """Process a file from Google Drive via web UI."""
    try:
        success = processor.process_file(file_name)
        message = f"Successfully processed file: {file_name}" if success else f"Failed to process file: {file_name}"
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "title": "Google Drive Document Processor", "message": message, "success": success}
        )
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "title": "Google Drive Document Processor", "message": f"Error: {str(e)}", "success": False}
        )

@app.post("/query", response_class=HTMLResponse)
async def query_documents_web(request: Request, query: str = Form(...)):
    """Query documents via web UI."""
    try:
        response = processor.search_documents(query)
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request, 
                "title": "Google Drive Document Processor", 
                "query": query,
                "answer": response.answer,
                "thoughts": response.thought_process,
                "context_status": "Sufficient" if response.enough_context else "Insufficient"
            }
        )
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "title": "Google Drive Document Processor", "message": f"Error: {str(e)}", "success": False}
        )

def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()