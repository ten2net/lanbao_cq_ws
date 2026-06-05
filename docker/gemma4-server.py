#!/usr/bin/env python3
"""
Gemma 4 12B OpenAI-compatible API server using Transformers native inference.
"""

import os
import sys
import json
import time
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

import torch
from transformers import (
    AutoProcessor,
    Gemma4ForConditionalGeneration,
    TextIteratorStreamer,
)
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
from threading import Thread

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "/root/.cache/huggingface/google/gemma-4-12B")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "32768"))
PORT = int(os.getenv("PORT", "8500"))

# Global model and processor
model = None
processor = None


def load_model():
    """Load Gemma 4 model and processor."""
    global model, processor

    print(f"Loading model from {MODEL_PATH}...")
    print(f"Device: {DEVICE}")

    processor = AutoProcessor.from_pretrained(MODEL_PATH)

    model = Gemma4ForConditionalGeneration.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="eager",  # Disable SDPA/FlashAttention to avoid compatibility issues
    )

    print(f"Model loaded. Memory used: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(f"Model type: {model.config.model_type}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield
    # Cleanup
    if model is not None:
        del model
    if processor is not None:
        del processor
    torch.cuda.empty_cache()


app = FastAPI(title="Gemma 4 API", lifespan=lifespan)


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "google/gemma-4-12B",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "google",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    messages = body.get("messages", [])
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 1024)
    temperature = body.get("temperature", 0.7)
    top_p = body.get("top_p", 0.9)

    # Convert messages to Gemma chat format
    chat_text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = processor(text=chat_text, return_tensors="pt").to(model.device)

    if stream:
        return StreamingResponse(
            generate_stream(inputs, max_tokens, temperature, top_p),
            media_type="text/event-stream",
        )
    else:
        return await generate_sync(inputs, max_tokens, temperature, top_p)


async def generate_sync(inputs, max_new_tokens: int, temperature: float, top_p: float):
    """Non-streaming generation."""
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=processor.tokenizer.pad_token_id or processor.tokenizer.eos_token_id,
        )

    response_text = processor.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "google/gemma-4-12B",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": inputs["input_ids"].shape[1],
            "completion_tokens": outputs.shape[1] - inputs["input_ids"].shape[1],
            "total_tokens": outputs.shape[1],
        },
    }


async def generate_stream(
    inputs, max_new_tokens: int, temperature: float, top_p: float
) -> AsyncGenerator[str, None]:
    """Streaming generation."""
    streamer = TextIteratorStreamer(
        processor.tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
        top_p=top_p,
        pad_token_id=processor.tokenizer.pad_token_id or processor.tokenizer.eos_token_id,
    )

    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    generated_id = f"chatcmpl-{int(time.time())}"
    created = int(time.time())

    for new_text in streamer:
        if new_text:
            chunk = {
                "id": generated_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": "google/gemma-4-12B",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": new_text},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"

    # Final chunk
    final_chunk = {
        "id": generated_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": "google/gemma-4-12B",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
