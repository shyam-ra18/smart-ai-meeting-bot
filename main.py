from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# ENV variables
RECALL_API_KEY = os.getenv("RECALL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Recall.ai Zoom Meeting Bot")

class MeetingRequest(BaseModel):
    meeting_url: str
    bot_name: str = "Meeting Bot"
    join_at: str = ""
    recording_config: dict = {}

@app.post("/start-bot")
async def start_bot(req: MeetingRequest):
    """
    Start a Recall.ai bot to join a Zoom meeting.
    """
    url = "https://us-west-2.recall.ai/api/v1/bot/"
    headers = {
        "Authorization": f"Token {RECALL_API_KEY}",
         "accept": "application/json",
        "content-type": "application/json"
    }

    payload = {
        "meeting_url": req.meeting_url,
        "bot_name": req.bot_name,
        "join_at":req.join_at,
        "recording_config": req.recording_config
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code != 201:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()

@app.get("/bot/{bot_id}/transcript")
async def get_transcript(bot_id: str):
    """
    Fetch transcript from Recall.ai bot.
    """
    url = f"https://us-west-2.recall.ai/api/v1/transcript/{bot_id}/"
    headers = {"Authorization": f"Token {RECALL_API_KEY}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    transcript = resp.json()
    return {"transcript": transcript}

@app.get("/bot/{bot_id}/summary")
async def summarize_meeting(bot_id: str):
    """
    Fetch transcript and summarize using OpenAI GPT.
    """
    url = f"https://us-west-2.recall.ai/api/v1/bot/{bot_id}/transcript"
    headers = {"Authorization": f"Token {RECALL_API_KEY}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    transcript_data = resp.json()
    transcript_text = " ".join([seg["text"] for seg in transcript_data.get("segments", [])])

    if not transcript_text:
        return {"summary": "No transcript available yet."}

    # Summarize with OpenAI
    import openai
    openai.api_key = OPENAI_API_KEY

    summary = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the following meeting transcript."},
            {"role": "user", "content": transcript_text}
        ]
    )

    return {"summary": summary["choices"][0]["message"]["content"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
