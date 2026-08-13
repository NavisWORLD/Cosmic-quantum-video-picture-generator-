"""Example renderer service for the COSMOS HTTP provider contract.

Run in a second terminal:
    uvicorn examples.provider_server:app --host 127.0.0.1 --port 9000

Then set:
    COSMOS_MEDIA_PROVIDER=http
    COSMOS_MEDIA_ENDPOINT=http://127.0.0.1:9000

This example reuses the procedural renderer only to demonstrate the protocol.
Replace the body of each route with ComfyUI, Diffusers, a render farm, or another
media backend without changing COSMOS core.
"""

from pathlib import Path
import tempfile

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cosmos_media.config import Settings
from cosmos_media.providers import ImageJob, ProceduralProvider, VideoJob

app = FastAPI(title="COSMOS Example Media Provider")
provider = ProceduralProvider(Settings())


class ImageRequest(BaseModel):
    prompt: str
    context: str = ""
    seed: int
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    state: list[float]


class VideoRequest(ImageRequest):
    fps: int = Field(gt=0)
    duration: float = Field(gt=0)
    continuity: dict = {}


@app.post("/generate/image")
def image(request: ImageRequest):
    path = Path(tempfile.gettempdir()) / f"cosmos-provider-{request.seed}.png"
    provider.generate_image(
        ImageJob(
            prompt=request.prompt,
            context=request.context,
            seed=request.seed,
            width=request.width,
            height=request.height,
            state=request.state,
            output=path,
        )
    )
    return FileResponse(path, media_type="image/png")


@app.post("/generate/video")
def video(request: VideoRequest):
    path = Path(tempfile.gettempdir()) / f"cosmos-provider-{request.seed}.mp4"
    provider.generate_video(
        VideoJob(
            prompt=request.prompt,
            context=request.context,
            seed=request.seed,
            width=request.width,
            height=request.height,
            fps=request.fps,
            duration=request.duration,
            state=request.state,
            output=path,
            continuity=request.continuity,
        )
    )
    return FileResponse(path, media_type="video/mp4")
