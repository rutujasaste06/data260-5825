#CRUD handlers

from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError
from db import trials
from schemas import TrialIn, TrialOut, TrialUpdate

router = APIRouter(prefix="/trials-doc", tags=["trials-doc"])

def now():
    return datetime.now(timezone.utc)

def oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Invalid id format")

def to_out(d):
    d["id"] = str(d.pop("_id"))
    return d

@router.post("", response_model=TrialOut, status_code=201)
def create(payload: TrialIn):
    doc = payload.model_dump(mode="python")
    doc["status"] = payload.status.value
    doc["phase"] = payload.phase.value
    doc["created_at"] = doc["updated_at"] = now()
    try:
        doc["_id"] = trials.insert_one(doc).inserted_id
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    return to_out(doc)

@router.get("", response_model=list[TrialOut])
def list_all():
    return [to_out(d) for d in trials.find().sort("created_at", -1)]

@router.get("/{trial_id}", response_model=TrialOut)
def get_one(trial_id: str):
    d = trials.find_one({"_id": oid(trial_id)})
    if not d:
        raise HTTPException(status_code=404, detail="Trial not found")
    return to_out(d)

@router.put("/{trial_id}", response_model=TrialOut)
def update(trial_id: str, payload: TrialUpdate):
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "status" in changes:
        changes["status"] = changes["status"].value
    if "phase" in changes:
        changes["phase"] = changes["phase"].value
    changes["updated_at"] = now()
    d = trials.find_one_and_update({"_id": oid(trial_id)}, {"$set": changes},
                                   return_document=True)
    if not d:
        raise HTTPException(status_code=404, detail="Trial not found")
    return to_out(d)

@router.delete("/{trial_id}")
def delete(trial_id: str):
    r = trials.delete_one({"_id": oid(trial_id)})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trial not found")
    return {"deleted": trial_id}