from typing import Optional, List, Literal
from pydantic import BaseModel, Field, validator


# Collection: property
class Property(BaseModel):
    owner_name: str
    owner_email: Optional[str] = None
    address: str
    city: str
    state: str
    zip_code: str
    property_type: Literal["single_family", "multi_family", "condo", "townhome", "land"] = "single_family"
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None

    asking_price: float = Field(..., ge=0)
    arv: Optional[float] = Field(None, ge=0, description="After Repair Value")
    repair_cost: Optional[float] = Field(0, ge=0)

    notes: Optional[str] = None


# Collection: buyer
class Buyer(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    target_states: Optional[List[str]] = None
    min_budget: Optional[float] = Field(0, ge=0)
    max_budget: Optional[float] = Field(None, ge=0)
    property_types: Optional[List[str]] = None


# Collection: deal
class Deal(BaseModel):
    property_id: str
    status: Literal["submitted", "matched", "reviewed", "closed"] = "submitted"
    rank: Literal["A", "B", "C", "D"] = "D"
    analysis: dict = {}
    matched_buyer_ids: List[str] = []
    jv_opt_in: bool = False
    profit_split_percentage: Optional[float] = Field(0.0, ge=0, le=100)
    contract_url: Optional[str] = None


class DealReview(BaseModel):
    approve: bool = True
    notes: Optional[str] = None


class CloseDealRequest(BaseModel):
    sale_price: float = Field(..., ge=0)
    jv_opt_in: bool = False
    profit_split_percentage: Optional[float] = Field(0.0, ge=0, le=100)


# Utility schemas
class MatchResponse(BaseModel):
    deal_id: str
    matched_buyers: List[dict]
    rank: str
    analysis: dict
