

import hashlib
import json
import os
from datetime import date

import requests

API_URL = "https://clinicaltrials.gov/api/v2/studies"
CONDITION = "Type 2 Diabetes"
PAGE_SIZE = 55

# Where things get saved -- adjust if your repo layout differs
OUTPUT_DIR = os.path.join("data", "corpus")
SOURCES_MD_PATH = os.path.join("reports", "hw03", "SOURCES.md")
MANIFEST_PATH = os.path.join("reports", "hw03", "CORPUS_MANIFEST.json")


def fetch_studies():
    #Pull raw study records from the ClinicalTrials.gov v2 API
    params = {
        "query.cond": CONDITION,
        "pageSize": PAGE_SIZE,
        "fields": ",".join([
            "NCTId",
            "BriefTitle",
            "OfficialTitle",
            "OverallStatus",
            "Phase",
            "Condition",
            "BriefSummary",
            "DetailedDescription",
            "EligibilityCriteria",
            "LeadSponsorName",
        ]),
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("studies", [])


def study_to_text(study):
    """Turn one API study record into a readable plain-text document."""
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    desc = protocol.get("descriptionModule", {})
    elig = protocol.get("eligibilityModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    conditions = protocol.get("conditionsModule", {}).get("conditions", [])

    nct_id = ident.get("nctId", "UNKNOWN")
    lines = [
        f"NCT ID: {nct_id}",
        f"Brief Title: {ident.get('briefTitle', '')}",
        f"Official Title: {ident.get('officialTitle', '')}",
        f"Status: {status.get('overallStatus', '')}",
        f"Phase: {', '.join(design.get('phases', []) or [])}",
        f"Conditions: {', '.join(conditions)}",
        f"Sponsor: {sponsor.get('name', '')}",
        "",
        "Brief Summary:",
        desc.get("briefSummary", "").strip(),
        "",
        "Detailed Description:",
        desc.get("detailedDescription", "").strip(),
        "",
        "Eligibility Criteria:",
        elig.get("eligibilityCriteria", "").strip(),
    ]
    return nct_id, "\n".join(lines)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SOURCES_MD_PATH), exist_ok=True)

    studies = fetch_studies()
    print(f"Fetched {len(studies)} studies from ClinicalTrials.gov")

    today = date.today().isoformat()
    sources_lines = [
        "# SOURCES.md",
        "",
        f"Domain: Clinical Trial Listings (DOMAIN_ID 1) — condition: {CONDITION}",
        f"Access date: {today}",
        f"Retrieved via: ClinicalTrials.gov public API v2 ({API_URL})",
        "",
        "| NCT ID | Local filename | Source URL |",
        "|---|---|---|",
    ]
    manifest_entries = []
    total_bytes = 0

    for study in studies:
        nct_id, text = study_to_text(study)
        filename = f"{nct_id}.txt"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        file_bytes = os.path.getsize(filepath)
        total_bytes += file_bytes

        with open(filepath, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()

        source_url = f"https://clinicaltrials.gov/study/{nct_id}"
        sources_lines.append(f"| {nct_id} | {filename} | {source_url} |")
        manifest_entries.append({
            "nct_id": nct_id,
            "filename": filename,
            "byte_size": file_bytes,
            "sha256": sha256,
            "source_url": source_url,
            "access_date": today,
        })

    with open(SOURCES_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(sources_lines) + "\n")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "domain": "Clinical Trial Listings",
            "condition_searched": CONDITION,
            "access_date": today,
            "total_files": len(manifest_entries),
            "total_bytes": total_bytes,
            "files": manifest_entries,
        }, f, indent=2)

    print(f"Saved {len(manifest_entries)} files to {OUTPUT_DIR}/")
    print(f"Total corpus size: {total_bytes / 1024:.1f} KB "
          f"({'OK, above 200KB minimum' if total_bytes >= 200_000 else 'WARNING: below 200KB minimum, consider widening the query'})")
    print(f"Wrote {SOURCES_MD_PATH}")
    print(f"Wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()