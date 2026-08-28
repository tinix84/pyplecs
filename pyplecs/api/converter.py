"""REST adapter for offline Circuit Model conversion."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..converter import parse_plecs, plecs_to_ltspice, plecs_to_spice

router = APIRouter(tags=["converter"])


class ConversionRequest(BaseModel):
    plecs_file: str
    format: Literal["cir", "asc"] = "cir"


class ConversionResponse(BaseModel):
    filename: str
    content: str


@router.post("/convert", response_model=ConversionResponse)
async def convert_plecs(request: ConversionRequest) -> ConversionResponse:
    """Convert one local ``.plecs`` schematic without starting PLECS."""
    try:
        circuit = parse_plecs(request.plecs_file)
        if request.format == "cir":
            content = plecs_to_spice(circuit)
        else:
            content = plecs_to_ltspice(circuit)
        return ConversionResponse(
            filename=f"{Path(request.plecs_file).stem}.{request.format}",
            content=content,
        )
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
