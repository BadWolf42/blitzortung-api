from typing import List, Optional, Union
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
EqIdField = Field(ge=0, description="Equipment id")


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class EqBoundaryModel(BaseModel):
    id: int = EqIdField
    north: float = Field(ge=-90, le=90, description="North latitude boundary")
    south: float = Field(ge=-90, le=90, description="South latitude boundary")
    est: float = Field(ge=-180, le=180, description="Est longitude boundary")
    west: float = Field(ge=-180, le=180, description="West longitude boundary")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                "id": 40,
                "north": 46.255608,
                "south": 45.344439,
                "est": 5.511808,
                "west": 4.239807
                },
            ]
        }
    }

# -----------------------------------------------------------------------------
class BoundaryModel(BaseModel):
    since: int = Field(ge=0, lt=9999999999, description="Last query timestamp")
    eqs: List[EqBoundaryModel] = Field(max_items=5, description="Equipments")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "since": 1694801111,
                    "eqs": [
                        {
                        "id": 40,
                        "north": 46.255608,
                        "south": 45.344439,
                        "est": 5.511808,
                        "west": 4.239807
                        }
                    ]
                }
            ]
        }
    }

# -----------------------------------------------------------------------------
class OldBoundaryModel(BaseModel):
    since: Union[float, int] = Field(
        ge=1000000000000000000,
        lt=9999999999999999999,
        description="Last query LONG timestamp"
    )
    eqs: List[EqBoundaryModel] = Field(max_items=5, description="Equipments")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "since": 1694801111000000000,
                    "eqs": [
                        {
                        "id": 40,
                        "north": 46.255608,
                        "south": 45.344439,
                        "est": 5.511808,
                        "west": 4.239807
                        }
                    ]
                }
            ]
        }
    }

# -----------------------------------------------------------------------------
class EqLLRModel(BaseModel):
    id: int = EqIdField
    lat: float = Field(ge=-90, le=90, description="Equipment latitude")
    lon: float = Field(ge=-180, le=180, description="Equipment longitude")
    rad: int = Field(ge=0, le=5000, description="Equipment radius (km)")

# -----------------------------------------------------------------------------
class LLRModel(BaseModel):
    since: int = Field(ge=0, lt=9999999999, description="Last query timestamp")
    eqs: List[EqLLRModel] = Field(max_items=5, description="Equipments")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "since": 1694801111,
                    "eqs": [
                        {
                        "id": 41,
                        "lat": 45.80878,
                        "lon": 4.872633,
                        "rad": 50
                        }
                    ]
                }
            ]
        }
    }

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class ImpactModel(BaseModel):
    time: int = Field(ge=0, description="Impact timestamp")
    lat: float = Field(ge=-90, le=90, description="Impact latitude")
    lon: float = Field(ge=-180, le=180, description="Impact longitude")
    distance: Optional[int] = Field(ge=0, description="Impact distance (m)")

# -----------------------------------------------------------------------------
class ResponseEqModel(BaseModel):
    id: int = EqIdField
    impacts: List[ImpactModel] = Field(description="List of impatcs for eq")

# -----------------------------------------------------------------------------
class ResponseModel(BaseModel):
    since: int = Field(ge=0, lt=9999999999, description="Very last impact")
    eqs: List[ResponseEqModel] = Field(max_items=5, description="Equipments")

