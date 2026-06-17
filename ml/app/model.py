from .pipeline.run import process

async def predict(text: str, session_id: str) -> dict:
    return await process(text, session_id)
