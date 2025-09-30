import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Excuse Email Draft Tool",
    description="Generate professional excuse emails using Databricks Model Serving",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ExcuseRequest(BaseModel):
    category: str = Field(..., description="Category of excuse")
    tone: str = Field(..., description="Tone of the email")
    seriousness: int = Field(..., ge=1, le=5, description="Seriousness level 1-5")
    recipient_name: str = Field(..., description="Name of the recipient")
    sender_name: str = Field(..., description="Name of the sender")
    eta_when: str = Field(..., description="ETA or when information")

class ExcuseResponse(BaseModel):
    subject: str
    body: str
    success: bool
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Environment Configuration
DATABRICKS_API_TOKEN = os.getenv("DATABRICKS_API_TOKEN")
DATABRICKS_ENDPOINT_URL = os.getenv(
    "DATABRICKS_ENDPOINT_URL", 
    "https://dbc-32cf6ae7-cf82.staging.cloud.databricks.com/serving-endpoints/databricks-gpt-oss-120b/invocations"
)
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

# LLM Integration Functions
def create_excuse_prompt(request: ExcuseRequest) -> str:
    """Create a structured prompt for the LLM to generate excuse emails."""
    
    tone_descriptions = {
        "Sincere": "professional and apologetic",
        "Playful": "light-hearted and humorous",
        "Corporate": "formal and business-appropriate"
    }
    
    seriousness_descriptions = {
        1: "very casual and silly",
        2: "casual and light",
        3: "balanced and moderate",
        4: "serious and professional",
        5: "very serious and formal"
    }
    
    tone_desc = tone_descriptions.get(request.tone, "professional")
    seriousness_desc = seriousness_descriptions.get(request.seriousness, "moderate")
    
    prompt = f"""You are an expert at writing professional excuse emails. Generate a JSON response with a subject line and email body for the following scenario:

Category: {request.category}
Tone: {tone_desc}
Seriousness: {seriousness_desc}
Recipient: {request.recipient_name}
Sender: {request.sender_name}
ETA/When: {request.eta_when}

Requirements:
- Write in a {tone_desc} tone
- Make it {seriousness_desc} in nature
- Include appropriate greeting and sign-off
- Be specific about the timing (ETA/When)
- Keep it professional but match the requested tone
- Structure: greeting → apology/excuse → reason → next step → sign-off

You must respond with ONLY a valid JSON object in this exact format:
{{
    "subject": "Your subject line here",
    "body": "Dear {request.recipient_name},\\n\\n[Your email body here]\\n\\nBest regards,\\n{request.sender_name}"
}}

CRITICAL REQUIREMENTS:
- Return ONLY the JSON object
- No explanations, reasoning, or additional text
- No markdown formatting
- No code blocks
- Just the raw JSON object"""

    return prompt

async def call_databricks_llm(prompt: str) -> Dict[str, Any]:
    """Call the Databricks Model Serving endpoint."""
    
    if not DATABRICKS_API_TOKEN:
        raise HTTPException(
            status_code=500, 
            detail="DATABRICKS_API_TOKEN not configured"
        )
    
    headers = {
        "Authorization": f"Bearer {DATABRICKS_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DATABRICKS_ENDPOINT_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail="LLM service error")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

def parse_llm_response(response: Dict[str, Any]) -> ExcuseResponse:
    """Parse the LLM response and extract subject and body with robust error handling."""
    
    try:
        logger.info(f"Raw LLM response type: {type(response)}")
        logger.info(f"Raw LLM response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        # Try to extract content from different response formats
        content = None
        
        if "choices" in response and len(response["choices"]) > 0:
            # OpenAI-style format
            content = response["choices"][0].get("message", {}).get("content", "")
            logger.info("Using OpenAI-style format")
        elif "predictions" in response and len(response["predictions"]) > 0:
            # Databricks-style format
            candidates = response["predictions"][0].get("candidates", [])
            if candidates and len(candidates) > 0:
                content = candidates[0].get("content", "")
            logger.info("Using Databricks-style format")
        elif "content" in response:
            # Direct content format
            content = response["content"]
            logger.info("Using direct content format")
        else:
            # Fallback: try to find any text content
            content = str(response)
            logger.info("Using fallback string conversion")
        
        # Handle case where content might be a list
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
            logger.info("Converted list content to string")
        
        logger.info(f"Content type: {type(content)}")
        logger.info(f"Content preview: {str(content)[:500]}...")
        
        if not content:
            logger.error("No content found in response")
            return ExcuseResponse(
                subject="Error",
                body="No content found in LLM response",
                success=False,
                error="No content found in LLM response"
            )
        
        # ROBUST PARSING: Try multiple approaches
        import re
        
        # Approach 1: Look for JSON in 'text' field
        if isinstance(content, str):
            # Pattern 1: 'text': '{...}'
            text_patterns = [
                r"'text':\s*'(\{.*?\})'",
                r'"text":\s*"(\{.*?\})"',
                r"'text':\s*\"(\{.*?\})\"",
                r'"text":\s*\'(\{.*?)\''
            ]
            
            for pattern in text_patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    logger.info(f"Found JSON with pattern {pattern}: {json_str[:100]}...")
                    
                    # Clean up escaped characters
                    json_str = json_str.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
                    
                    try:
                        parsed = json.loads(json_str)
                        if "subject" in parsed and "body" in parsed:
                            # Clean up the body text to remove any remaining escaped characters
                            clean_body = parsed["body"].replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
                            logger.info(f"Successfully parsed JSON: subject='{parsed['subject']}'")
                            return ExcuseResponse(
                                subject=parsed["subject"],
                                body=clean_body,
                                success=True
                            )
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error with pattern {pattern}: {e}")
                        continue
        
        # Approach 2: Look for any JSON object with subject and body
        json_patterns = [
            r'\{[^{}]*"subject"[^{}]*"body"[^{}]*\}',
            r'\{.*?"subject".*?"body".*?\}',
            r'\{[^}]*"subject"[^}]*"body"[^}]*\}'
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                json_str = match.group(0)
                logger.info(f"Found JSON with general pattern: {json_str[:100]}...")
                
                try:
                    parsed = json.loads(json_str)
                    if "subject" in parsed and "body" in parsed:
                        # Clean up the body text to remove any remaining escaped characters
                        clean_body = parsed["body"].replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
                        logger.info(f"Successfully parsed general JSON: subject='{parsed['subject']}'")
                        return ExcuseResponse(
                            subject=parsed["subject"],
                            body=clean_body,
                            success=True
                        )
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error with general pattern: {e}")
                    continue
        
        # Approach 3: Try to parse the entire content as JSON
        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict) and "subject" in parsed and "body" in parsed:
                # Clean up the body text to remove any remaining escaped characters
                clean_body = parsed["body"].replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
                logger.info(f"Successfully parsed entire content as JSON: subject='{parsed['subject']}'")
                return ExcuseResponse(
                    subject=parsed["subject"],
                    body=clean_body,
                    success=True
                )
        except json.JSONDecodeError:
            pass
        
        # Approach 4: Extract subject and body from text patterns
        subject_match = re.search(r'"subject":\s*"([^"]+)"', content)
        body_match = re.search(r'"body":\s*"([^"]+)"', content)
        
        if subject_match and body_match:
            subject = subject_match.group(1)
            body = body_match.group(1).replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
            logger.info(f"Extracted subject and body from text patterns: subject='{subject}'")
            return ExcuseResponse(
                subject=subject,
                body=body,
                success=True
            )
        
        # If all approaches fail, return error with detailed info
        logger.error("All parsing approaches failed")
        logger.error(f"Full content: {content}")
        return ExcuseResponse(
            subject="Error",
            body="Failed to parse LLM response",
            success=False,
            error=f"Could not extract email from LLM response. Content: {str(content)[:200]}..."
        )
        
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM response: {str(e)}")
        import traceback
        traceback.print_exc()
        return ExcuseResponse(
            subject="Error",
            body=f"Failed to generate email: {str(e)}",
            success=False,
            error=str(e)
        )

# API Endpoints
@app.post("/api/generate-excuse", response_model=ExcuseResponse)
async def generate_excuse(request: ExcuseRequest):
    """Generate an excuse email using the LLM."""
    try:
        logger.info(f"Generating excuse for: {request.category} - {request.tone}")
        
        # Create prompt
        prompt = create_excuse_prompt(request)
        
        # Call LLM
        llm_response = await call_databricks_llm(prompt)
        
        # Parse response
        result = parse_llm_response(llm_response)
        
        logger.info(f"Generated excuse successfully: {result.success}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_excuse: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

@app.get("/healthz")
async def healthz():
    """Kubernetes-style health check."""
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    """Readiness check."""
    return {"status": "ready"}

@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {"message": "pong"}

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    return "# HELP excuse_generator_requests_total Total number of excuse generation requests\n# TYPE excuse_generator_requests_total counter\nexcuse_generator_requests_total 0"

@app.get("/debug")
async def debug():
    """Debug endpoint for environment information."""
    return {
        "environment": {
            "has_databricks_token": bool(DATABRICKS_API_TOKEN),
            "databricks_endpoint": DATABRICKS_ENDPOINT_URL,
            "port": PORT,
            "host": HOST
        },
        "paths": {
            "current_dir": str(Path.cwd()),
            "app_dir": str(Path(__file__).parent),
            "public_dir": str(Path(__file__).parent.parent / "public")
        }
    }

# Static file serving
def get_public_file_path(filename: str) -> Optional[Path]:
    """Get the path to a public file, trying multiple locations."""
    possible_paths = [
        Path(__file__).parent.parent / "public" / filename,
        Path.cwd() / "public" / filename,
        Path.cwd() / filename,
        Path("/app/public") / filename,
        Path("/app") / filename
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found {filename} at: {path}")
            return path
    
    logger.warning(f"Could not find {filename} in any of the expected locations")
    return None

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the React frontend."""
    index_path = get_public_file_path("index.html")
    
    if not index_path:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Excuse Email Draft Tool</title>
        </head>
        <body>
            <h1>Frontend not found</h1>
            <p>The React frontend could not be loaded. Please check the deployment.</p>
        </body>
        </html>
        """, status_code=404)
    
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    except Exception as e:
        logger.error(f"Error reading index.html: {str(e)}")
        return HTMLResponse(f"Error loading frontend: {str(e)}", status_code=500)

# Serve static files
@app.get("/static/{filename}")
async def serve_static(filename: str):
    """Serve static files."""
    file_path = get_public_file_path(filename)
    if file_path and file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
