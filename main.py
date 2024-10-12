import os
import random
import tempfile
from typing import List, Dict
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from openai import OpenAI
from openai import OpenAIError
import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ArticleRequest(BaseModel):
    article: str
    types: List[str]

def generate_question_and_answers(text: str) -> Dict[str, str]:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Create a question and provide a concise answer based on the following text:\n\n{text}"}
            ],
            max_tokens=150
        )
        generated_content = response.choices[0].message.content.strip().split('\n', 1)
        question = generated_content[0].strip()
        correct_answer = generated_content[1].strip()
        choices = generate_choices(question, correct_answer)
        return {
            "question": question,
            "correct_answer": correct_answer,
            "choices": choices
        }
    except OpenAIError as e:
        print(f"Error generating question and answers: {e}")
        return {
            "question": "An error occurred while generating the question.",
            "correct_answer": "Error",
            "choices": ["Error generating choices"]
        }

def generate_choices(question: str, correct_answer: str) -> List[str]:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Generate three incorrect but plausible answers for the following question and correct answer:\n\nQuestion: {question}\nCorrect Answer: {correct_answer}\n\nProvide only the three incorrect answers, separated by newlines."}
            ],
            max_tokens=100
        )
        incorrect_choices = response.choices[0].message.content.strip().split('\n')
        all_choices = incorrect_choices + [correct_answer]
        random.shuffle(all_choices)
        return all_choices
    except OpenAIError as e:
        print(f"Error generating choices: {e}")
        return [correct_answer, "Error generating choice", "Error generating choice", "Error generating choice"]

def generate_summarized_notes(text: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the following text into concise bullet points:\n\n{text}"}
            ],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        print(f"Error generating summarized notes: {e}")
        return "An error occurred while generating summarized notes."

def generate_story(text: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Create a short, engaging story that incorporates the key concepts from the following text:\n\n{text}"}
            ],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        print(f"Error generating story: {e}")
        return "An error occurred while generating the story."

def generate_image(text: str) -> str:
    try:
        response = client.images.generate(
            model="dall-e-2",
            prompt=text,
            size="512x512",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        print(f"Error generating image: {e}")
        return ""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "title": "Home"})

@app.get("/convert-notes", response_class=HTMLResponse)
async def convert_notes(request: Request):
    return templates.TemplateResponse("convert_notes.html", {"request": request, "title": "Convert Notes"})

@app.get("/output-selection", response_class=HTMLResponse)
async def output_selection(request: Request):
    return templates.TemplateResponse("output_selection.html", {"request": request, "title": "Output Selection"})

@app.post("/generate-content", response_class=JSONResponse)
async def generate_content(article_request: ArticleRequest):
    article = article_request.article
    types = article_request.types

    if not article or not types:
        raise HTTPException(status_code=400, detail="Article text and at least one type are required.")

    responses = {}

    if 'flashcards' in types:
        flashcard_content = generate_question_and_answers(article)
        responses['flashcard'] = {
            "question": flashcard_content["question"],
            "answer": flashcard_content["correct_answer"]
        }

    if 'quiz' in types:
        quiz_content = generate_question_and_answers(article)
        responses['quiz'] = {
            "question": quiz_content["question"],
            "correct_answer": quiz_content["correct_answer"],
            "choices": quiz_content["choices"]
        }

    if 'notes' in types:
        responses['notes'] = generate_summarized_notes(article)

    if 'story' in types:
        responses['story'] = generate_story(article)

    if 'images' in types:
        image_prompt = f"Create an educational image about: {article[:100]}"
        responses['image'] = generate_image(image_prompt)

    return responses

@app.post("/transcribe-audio")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(await audio.read())
            temp_audio_path = temp_audio.name

        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_audio_path) as source:
            audio_data = recognizer.record(source)
            transcription = recognizer.recognize_google(audio_data)

        os.unlink(temp_audio_path)

        return {"transcription": transcription}
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail="Error transcribing audio")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)