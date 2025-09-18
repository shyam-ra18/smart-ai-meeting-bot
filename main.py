from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
from typing import Dict, Any, List
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ENV variables
RECALL_API_KEY = os.getenv("RECALL_API_KEY")
RECALL_REGION = os.getenv("RECALL_REGION", "us-west-2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

app = FastAPI(title="Recall.ai Real-time Transcription Bot")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Store live transcripts in memory (use Redis/DB in production)
live_transcripts: Dict[str, List[Dict]] = {}
partial_transcripts: Dict[str, Dict] = {}  # Store partial results

class MeetingRequest(BaseModel):
    meeting_url: str
    bot_name: str = "Meeting Bot"
    join_at: str = ""
    recording_config: dict = {}

class TranscriptWebhookPayload(BaseModel):
    event: str
    data: Dict[str, Any]

@app.post("/start-bot")
async def start_bot(req: MeetingRequest):
    """
    Start a Recall.ai bot with real-time transcription using Deepgram.
    """
    url = f"https://{RECALL_REGION}.recall.ai/api/v1/bot"
    headers = {
        "Authorization": f"Token {RECALL_API_KEY}",
        "Content-Type": "application/json"
    }

    # Configure real-time transcription with Deepgram
    recording_config = {
        "transcript": {
            "provider": {
                "deepgram_streaming": {
                    "model": "nova-2",
                    "language": "en",
                    "punctuate": True,
                    "smart_format": True,
                    "interim_results": True,
                }
            }
        },
        "realtime_endpoints": [
            {
                "type": "webhook",
                "url": "https://ba0c7d1c7fb5.ngrok-free.app/api/webhook/recall/transcript",
                "events": ["transcript.data", "transcript.partial_data"]
            }
        ],
        # Optional: Configure additional recording settings
        "video_mixed_mp4": None,  # Disable video recording for faster processing
        "audio_mixed_raw": {
            "metadata": {"include_bot": False}
        }
    }

    # Merge with provided config if any
    if req.recording_config:
        recording_config.update(req.recording_config)

    payload = {
        "meeting_url": req.meeting_url,
        "bot_name": req.bot_name,
        "recording_config": recording_config
    }

    # Add join_at if provided
    if req.join_at:
        payload["join_at"] = req.join_at

    logger.info(f"Creating bot with payload: {json.dumps(payload, indent=2)}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 201:
            logger.error(f"Error creating bot: {resp.status_code} - {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        bot_data = resp.json()
        bot_id = bot_data.get("id")

        # Initialize transcript storage for this bot
        if bot_id:
            live_transcripts[bot_id] = []
            partial_transcripts[bot_id] = {}
            logger.info(f"Bot created successfully: {bot_id}")

        return bot_data

    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

@app.post("/api/webhook/recall/transcript")
async def handle_transcript_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle real-time transcript webhooks from Recall.ai.
    Process both partial and final transcript data from Deepgram.
    """
    try:
        payload = await request.json()
        event_type = payload.get("event")
        data = payload.get("data", {})

        logger.info(f"Received transcript webhook: {event_type}")

        # Extract relevant information
        bot_id = data.get("bot", {}).get("id")
        transcript_data = data.get("data", {})
        words = transcript_data.get("words", [])
        participant = transcript_data.get("participant", {})

        if not bot_id:
            logger.warning("No bot_id found in webhook payload")
            return {"status": "no_bot_id"}

        # Initialize storage if not exists
        if bot_id not in live_transcripts:
            live_transcripts[bot_id] = []
            partial_transcripts[bot_id] = {}

        # Process the transcript data
        background_tasks.add_task(process_transcript_data, event_type, bot_id, words, participant, transcript_data)

        return {"status": "received"}

    except Exception as e:
        logger.error(f"Transcript webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

async def process_transcript_data(event_type: str, bot_id: str, words: List[Dict], participant: Dict, transcript_data: Dict):
    """
    Process transcript data asynchronously to avoid blocking webhook responses.
    """
    try:
        # Extract text from words
        text_parts = [word.get("text", "") for word in words if word.get("text")]
        full_text = " ".join(text_parts).strip()

        if not full_text:
            return

        # Extract timestamps
        start_timestamp = words[0].get("start_timestamp", {}).get("relative", 0) if words else 0
        end_timestamp = words[-1].get("end_timestamp", {}).get("relative") if words else None

        transcript_segment = {
            "text": full_text,
            "speaker": participant.get("name") or f"Participant {participant.get('id', 'Unknown')}",
            "participant_id": participant.get("id"),
            "is_host": participant.get("is_host", False),
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "words": words,
            "is_partial": event_type == "transcript.partial_data",
            "timestamp": transcript_data.get("timestamp"),
            "event_type": event_type
        }

        if event_type == "transcript.partial_data":
            # Handle partial results - store temporarily
            participant_id = participant.get("id", "unknown")
            partial_transcripts[bot_id][participant_id] = transcript_segment
            logger.info(f"Partial transcript for bot {bot_id}: {full_text}")

        elif event_type == "transcript.data":
            # Handle final results - add to live transcript
            live_transcripts[bot_id].append(transcript_segment)

            # Remove corresponding partial result if exists
            participant_id = participant.get("id", "unknown")
            if participant_id in partial_transcripts[bot_id]:
                del partial_transcripts[bot_id][participant_id]

            logger.info(f"Final transcript for bot {bot_id}: {full_text}")

    except Exception as e:
        logger.error(f"Error processing transcript data: {str(e)}")

@app.get("/bot/{bot_id}/live-transcript")
async def get_live_transcript(bot_id: str, include_partial: bool = False):
    """
    Get the current live transcript segments for a bot.
    """
    if bot_id not in live_transcripts:
        return {"transcript": [], "message": "No live transcript available"}

    final_transcripts = live_transcripts[bot_id]
    result = {
        "transcript": final_transcripts,
        "total_segments": len(final_transcripts)
    }

    if include_partial:
        partials = list(partial_transcripts.get(bot_id, {}).values())
        result["partial_transcripts"] = partials
        result["total_partials"] = len(partials)

    return result

@app.get("/bot/{bot_id}/live-transcript/stream")
async def stream_live_transcript(bot_id: str):
    """
    Get a formatted stream of the live transcript with speaker labels.
    """
    if bot_id not in live_transcripts:
        return {"transcript": "", "message": "No live transcript available"}

    transcripts = live_transcripts[bot_id]

    # Format transcript with timestamps and speakers
    formatted_transcript = []
    for segment in transcripts:
        timestamp = segment.get("start_timestamp", 0)
        speaker = segment.get("speaker", "Unknown")
        text = segment.get("text", "")

        # Format timestamp as MM:SS
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"

        formatted_transcript.append(f"[{time_str}] {speaker}: {text}")

    return {
        "formatted_transcript": "\n".join(formatted_transcript),
        "raw_transcript": transcripts,
        "total_segments": len(transcripts)
    }

@app.get("/bot/{bot_id}/status")
async def get_bot_status(bot_id: str):
    """
    Get bot status from Recall.ai
    """
    url = f"https://{RECALL_REGION}.recall.ai/api/v1/bot/{bot_id}"
    headers = {"Authorization": f"Token {RECALL_API_KEY}"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        return resp.json()

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

@app.get("/bot/{bot_id}/summary")
async def summarize_meeting(bot_id: str):
    """
    Summarize meeting using live transcript data and OpenAI.
    """
    if bot_id not in live_transcripts or not live_transcripts[bot_id]:
        return {"summary": "No transcript available yet."}

    transcript_segments = live_transcripts[bot_id]

    # Combine transcript text with speaker labels
    transcript_text = "\n".join([
        f"{seg.get('speaker', 'Unknown')}: {seg.get('text', '')}"
        for seg in transcript_segments
        if seg.get('text', '').strip()
    ])

    if not transcript_text.strip():
        return {"summary": "No transcript text available."}

    try:
        # Use OpenAI to summarize
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following meeting transcript. Include key discussion points, decisions made, action items, and main participants. Format the summary in clear sections."
                },
                {"role": "user", "content": transcript_text}
            ],
            max_tokens=1000,
            temperature=0.3
        )

        summary = response.choices[0].message.content

        return {
            "summary": summary,
            "transcript_length": len(transcript_segments),
            "word_count": len(transcript_text.split()),
            "participants": list(set([seg.get('speaker', 'Unknown') for seg in transcript_segments]))
        }

    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@app.delete("/bot/{bot_id}")
async def stop_bot(bot_id: str):
    """
    Stop a Recall.ai bot and clean up transcript storage.
    """
    url = f"https://{RECALL_REGION}.recall.ai/api/v1/bot/{bot_id}"
    headers = {"Authorization": f"Token {RECALL_API_KEY}"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=headers)

        # Clean up transcript storage
        if bot_id in live_transcripts:
            del live_transcripts[bot_id]
        if bot_id in partial_transcripts:
            del partial_transcripts[bot_id]

        if resp.status_code not in [200, 204]:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        return {"message": f"Bot {bot_id} stopped successfully"}

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

@app.get("/bots/{bot_id}/transcript/export")
async def export_transcript(bot_id: str, format: str = "json"):
    """
    Export the transcript in various formats (json, txt, srt).
    """
    if bot_id not in live_transcripts:
        raise HTTPException(status_code=404, detail="Bot transcript not found")

    transcripts = live_transcripts[bot_id]

    if format == "txt":
        # Plain text format
        text_content = "\n".join([
            f"{seg.get('speaker', 'Unknown')}: {seg.get('text', '')}"
            for seg in transcripts
        ])
        return {"format": "txt", "content": text_content}

    elif format == "srt":
        # SRT subtitle format
        srt_content = []
        for i, seg in enumerate(transcripts, 1):
            start_time = seg.get('start_timestamp', 0)
            end_time = seg.get('end_timestamp', start_time + 5)  # Default 5 seconds if no end time

            start_srt = format_srt_time(start_time)
            end_srt = format_srt_time(end_time)

            srt_content.append(f"{i}\n{start_srt} --> {end_srt}\n{seg.get('text', '')}\n")

        return {"format": "srt", "content": "\n".join(srt_content)}

    else:  # Default to JSON
        return {"format": "json", "content": transcripts}

def format_srt_time(seconds: float) -> str:
    """Format seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

@app.get("/")
async def root():
    return {
        "message": "Recall.ai Real-time Transcription Service with Deepgram",
        "version": "2.0",
        "features": [
            "Real-time transcription with Deepgram",
            "Partial transcript support",
            "Live transcript streaming",
            "AI-powered meeting summaries",
            "Multiple export formats"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_bots": len(live_transcripts),
        "total_transcripts": sum(len(transcripts) for transcripts in live_transcripts.values())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)