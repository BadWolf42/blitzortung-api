from typing import List, Optional, Union
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
class QueryEqModel(BaseModel):
    id: int = Field(ge=0, description="Equipment id")
    lat: float = Field(ge=-90, le=90, description="Equipment latitude")
    lon: float = Field(ge=-180, le=180, description="Equipment longitude")
    rad: int = Field(ge=0, le=1100, description="Equipment radius (km)")

class QueryModel(BaseModel):
    since: int = Field(ge=0, lt=9999999999, description="Last query timestamp")
    eqs: List[QueryEqModel] = Field(max_items=5, description="Equipments")
    model_config = {
        "json_schema_extra":{"examples":[{
            "since": 1694801111,
            "eqs": [{"id": 41, "lat": 45.80878, "lon": 4.872633, "rad": 50}]
        }]}
    }

# -----------------------------------------------------------------------------
class ImpactModel(BaseModel):
    time: int = Field(ge=0, description="Impact timestamp")
    lat: float = Field(ge=-90, le=90, description="Impact latitude")
    lon: float = Field(ge=-180, le=180, description="Impact longitude")
    distance: Optional[int] = Field(ge=0, description="Impact distance (m)")

# -----------------------------------------------------------------------------
class ResponseEqModel(BaseModel):
    id: int = Field(ge=0, description="Equipment id")
    impacts: List[ImpactModel] = Field(description="List of impatcs for eq")

class ResponseModel(BaseModel):
    since: int = Field(ge=0, lt=9999999999, description="Very last impact")
    eqs: List[ResponseEqModel] = Field(max_items=5, description="Equipments")
