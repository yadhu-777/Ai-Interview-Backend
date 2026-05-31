from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from dotenv import load_dotenv
import os
import shutil
from openai import OpenAI
from pypdf import PdfReader
import mammoth
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
from fastapi.responses import StreamingResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
load_dotenv()
import base64



api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



async def extract_text(file: UploadFile):
    content = await file.read()

  
    file.file.seek(0)

    
    if file.content_type == "text/plain":
        return content.decode("utf-8")

    
    if file.content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join([page.extract_text() or "" for page in reader.pages])

  
    if file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        result = mammoth.extract_raw_text(io.BytesIO(content))
        return result.value

    raise Exception("Unsupported file type")

class ResumeRequest(BaseModel):
    text: str


@app.post("/pasteResume")
async def paste_resume(req: ResumeRequest):
    try:
        text = req.text[:4000]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert resume writer."},
                {"role": "user", "content": f"""
Rewrite this resume using the existing content, while enhancing clarity, structure, and impact. Add relevant improvements to make it more professional, ATS-friendly, and appealing to recruiters.

RULES:
- NO markdown
- Use UPPERCASE headings
- Use "-" for bullet points
- Clean spacing
- ATS-friendly format

Resume:
{text}
"""}
            ]
        )

        improved = response.choices[0].message.content

      
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer)

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="Title",
            fontSize=16,
            leading=18,
            spaceAfter=10,
            alignment=1,
            fontName="Helvetica-Bold"
        )

        heading_style = ParagraphStyle(
            name="Heading",
            fontSize=13,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
            fontName="Helvetica-Bold"
        )

        normal_style = styles["Normal"]

        elements = []

        for i, line in enumerate(improved.split("\n")):
            line = line.strip()

            if not line:
                elements.append(Spacer(1, 8))
                continue

           
            if i == 0:
                elements.append(Paragraph(line, title_style))

          
            elif line.isupper() and len(line) < 40:
                elements.append(Paragraph(line, heading_style))

           
            elif line.startswith("-"):
                elements.append(Paragraph(f"• {line[1:].strip()}", normal_style))

            else:
                elements.append(Paragraph(line, normal_style))

        doc.build(elements)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=AI_Resume.pdf"
            },
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/uploadRes")
async def upload_resume(file: UploadFile = File(...)):
    try:
     
        text = await extract_text(file) 

       
        response = client.chat.completions.create(
            model="gpt-4o-mini",
          messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume writer."
                },
                {
                    "role": "user",
                    "content": f"""
Rewrite this resume professionally while enhancing clarity, structure, and impact. Add relevant improvements to make it more professional, ATS-friendly, and appealing to recruiters.

RULES:
- NO markdown (**, ---, #, [])
- Use UPPERCASE headings
- Use "-" for bullet points
- Clean spacing
- ATS-friendly format
Resume:
{text}
"""
                }
            ]
        )

        improved = response.choices[0].message.content
        if not improved or improved.strip() == "":
             raise Exception("Empty AI response")

       


        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer)

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="Title",
            fontSize=16,
            leading=18,
            spaceAfter=10,
            alignment=1,
            fontName="Helvetica-Bold"
        )

        heading_style = ParagraphStyle(
            name="Heading",
            fontSize=13,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
            fontName="Helvetica-Bold"
        )

        normal_style = styles["Normal"]

        elements = []

        for i, line in enumerate(improved.split("\n")):
            line = line.strip()

            if not line:
                elements.append(Spacer(1, 8))
                continue

            if i == 0:
                elements.append(Paragraph(line, title_style))

            elif line.isupper() and len(line) < 40:
                elements.append(Paragraph(line, heading_style))

            elif line.startswith("-"):
                elements.append(Paragraph(f"• {line[1:]}", normal_style))

            else:
                elements.append(Paragraph(line, normal_style))

        doc.build(elements)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=AI_Resume.pdf"
            },
        )

    except Exception as e:
        return {"error": str(e)}

@app.post("/upload")
async def analyze_resume(file: UploadFile = File(...)):
    try:
        text = await extract_text(file)   
        text = text[:12000]

        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"""
Analyze this resume:

{text}

Return:
-Summary
-Skills
-Projects
-Strengths
-Weaknesses
-changes
-Score out of 100
"""
        )

        return {"result": response.output[0].content[0].text}

    except Exception as e:
        return {"error": str(e)}
from pydantic import BaseModel

class AskRequest(BaseModel):
    answer: str
    domainText: str 


@app.post("/ask")
async def ask(payload: AskRequest):
    try:
      
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""
You are a professional interviewer.
Ask SHORT and clear questions (max 1-2 lines).
Domain: {payload.domainText}
"""
                },
                {"role": "user", "content": payload.answer}
            ]
        )

        reply = chat.choices[0].message.content

       
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=reply
        )

        audio_base64 = base64.b64encode(speech.content).decode("utf-8")

        return {
            "reply": reply,
            "audio": audio_base64
        }

    except Exception as e:
        return {"error": str(e)}



class QuickPrepRequest(BaseModel):
    text: str
@app.post("/QuickPrep")
async def quick_prep(payload: QuickPrepRequest):
    try:
        text = payload.text
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"Prepare interview questions for {text}"}
            ]
        )
        return {"msg": chat.choices[0].message.content}
    except Exception as e:
        return {"msg": str(e)}