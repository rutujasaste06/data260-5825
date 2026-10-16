#Mongodb collection + DB side validation

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
db = client["s5825_doc"]

STATUSES = ["recruiting", "active", "completed", "withdrawn"]
PHASES = ["phase1", "phase2", "phase3", "phase4"]

VALIDATOR = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["trial_title", "status", "phase", "start_date", "created_at", "updated_at"],
    "properties": {
        "trial_title": {"bsonType": "string", "maxLength": 100},
        "description": {"bsonType": "string"},
        "status": {"enum": STATUSES},
        "phase": {"enum": PHASES},
        "start_date": {"bsonType": "date"},
        "created_at": {"bsonType": "date"},
        "updated_at": {"bsonType": "date"},
    }}}

def init_collection():
    try:
        db.create_collection("trials_docs", validator=VALIDATOR)
    except CollectionInvalid:
        db.command("collMod", "trials_docs", validator=VALIDATOR)
    return db["trials_docs"]

trials = init_collection()