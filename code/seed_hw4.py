import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from sqlalchemy import text
from database import Base, SessionLocal, db_session_basede26
import models

SEED = 5825
N_TRIALS = 5000
N_SITES = 200

rng = random.Random(SEED)

DRUGS = ["Metformin", "Aspirin", "Atorvastatin", "Semaglutide", "Insulin", "Lisinopril",
         "Sitagliptin", "Empagliflozin", "Losartan", "Vildagliptin"]
CONDITIONS = ["Type 2 Diabetes", "Hypertension", "High Cholesterol", "Heart Failure",
              "Obesity", "Kidney Disease", "Stroke Prevention"]
CITIES = ["San Jose", "Boston", "Chicago", "Houston", "Seattle", "Denver", "Atlanta", "Miami"]
HOSPITALS = ["General Hospital", "University Medical Center", "Research Institute", "Community Clinic"]

Base.metadata.create_all(bind=db_session_basede26)
db = SessionLocal()

# start clean so the same SEED always gives the same data
db.execute(text("DELETE FROM trial_sites"))
db.execute(text("DELETE FROM trials"))
db.execute(text("ALTER TABLE trials AUTO_INCREMENT = 1"))
db.commit()

trials = []
for i in range(N_TRIALS):
    title = f"{rng.choice(DRUGS)} for {rng.choice(CONDITIONS)} #{i + 1}"
    trials.append(models.Trial(trial_title=title, nct_number=f"NCT{10000000 + i}"))
db.add_all(trials)
db.commit()

ids = [t.id for t in trials] # get all 5000 real trial id numbers
chosen = rng.sample(ids, N_SITES)  # randomly pick 200 of those ids
sites = [
    models.TrialSite(
        trial_id=tid,        # this actually writes the real number in
        site_name=f"{rng.choice(CITIES)} {rng.choice(HOSPITALS)}",
        city=rng.choice(CITIES),
    )
    for tid in chosen
]
db.add_all(sites)
db.commit()

print("trials:", db.query(models.Trial).count())
print("trial_sites:", db.query(models.TrialSite).count())
db.close()
