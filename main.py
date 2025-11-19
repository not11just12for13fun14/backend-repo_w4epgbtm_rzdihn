from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

from schemas import Property, Buyer, Deal, DealReview, CloseDealRequest, MatchResponse
from database import create_document, get_documents

app = FastAPI(title="QuickFlip API", version="0.1.0")

# CORS for local dev and modal previews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "QuickFlip API"}


def analyze_deal(property: Property) -> Dict[str, Any]:
    # Simple analysis: compute MAO (Max Allowable Offer) and discount from ARV
    arv = property.arv or 0
    repair = property.repair_cost or 0
    asking = property.asking_price

    # 70% rule baseline
    mao = max(0.0, 0.70 * arv - repair)
    spread = max(0.0, mao - asking)
    discount_pct = (1 - asking / arv) * 100 if arv else 0

    # Rank by spread and discount
    if spread >= 30000 and discount_pct >= 25:
        rank = "A"
    elif spread >= 15000 and discount_pct >= 20:
        rank = "B"
    elif spread >= 5000 and discount_pct >= 10:
        rank = "C"
    else:
        rank = "D"

    return {
        "arv": arv,
        "repair_cost": repair,
        "asking_price": asking,
        "max_allowable_offer": round(mao, 2),
        "projected_spread": round(spread, 2),
        "discount_pct": round(discount_pct, 2),
        "rank": rank,
    }


def match_buyers(property: Property, buyers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for b in buyers:
        budget_ok = True
        if b.get("min_budget") is not None and property.asking_price < b["min_budget"]:
            budget_ok = False
        if b.get("max_budget") is not None and property.asking_price > b["max_budget"]:
            budget_ok = False

        loc_ok = False
        target_states = b.get("target_states") or []
        if property.state and (property.state == b.get("state") or property.state in target_states):
            loc_ok = True

        type_ok = True
        ptypes = b.get("property_types")
        if ptypes:
            type_ok = property.property_type in ptypes

        if budget_ok and (loc_ok or not target_states) and type_ok:
            matches.append({
                "buyer_id": str(b.get("_id")),
                "name": b.get("name"),
                "email": b.get("email"),
                "score": 1 + (0.5 if loc_ok else 0) + (0.5 if type_ok else 0)
            })
    # sort by score desc
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test")
async def test_db():
    # quick check the database connectivity by listing collections
    try:
        buyers = await get_documents("buyer", {}, 1)
        return {"ok": True, "buyers_sample": buyers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/buyers", response_model=dict)
async def register_buyer(buyer: Buyer):
    buyer_id = await create_document("buyer", buyer.dict())
    return {"buyer_id": buyer_id}


@app.post("/properties", response_model=MatchResponse)
async def submit_property(property: Property):
    # Analyze
    analysis = analyze_deal(property)
    # Persist property
    prop_id = await create_document("property", property.dict())

    # Find matching buyers
    buyers = await get_documents("buyer", {}, limit=200)
    matches = match_buyers(property, buyers)

    # Create deal doc
    deal = Deal(
        property_id=prop_id,
        status="matched" if matches else "submitted",
        rank=analysis["rank"],
        analysis=analysis,
        matched_buyer_ids=[m["buyer_id"] for m in matches],
    )
    deal_id = await create_document("deal", deal.dict())

    return MatchResponse(
        deal_id=deal_id,
        matched_buyers=matches,
        rank=analysis["rank"],
        analysis=analysis,
    )


@app.post("/deals/{deal_id}/review", response_model=dict)
async def review_deal(deal_id: str, review: DealReview):
    # For demo: just echo status update result
    status = "reviewed" if review.approve else "submitted"
    return {"deal_id": deal_id, "status": status, "notes": review.notes}


@app.post("/deals/{deal_id}/close", response_model=dict)
async def close_deal(deal_id: str, req: CloseDealRequest):
    # Placeholder for JV/contract generation
    jv = None
    if req.jv_opt_in and req.profit_split_percentage:
        jv = {
            "split": req.profit_split_percentage,
            "our_share": round(req.sale_price * (req.profit_split_percentage / 100.0), 2)
        }
    return {"deal_id": deal_id, "status": "closed", "sale_price": req.sale_price, "jv": jv}
