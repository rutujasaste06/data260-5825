# Domain Schema- Clinical Trial Listings

## Entity Fields

| Field | Type | Description |
|-------|------|-------------|
| Trial Title | Text (required) | Primary field — full name of the clinical trial |
| NCT Number | Text (required) | Secondary field — unique trial registry ID (format: NCT + 8 digits) |
| Submitter Email | Email (required) | Email of the person submitting the entry |
| Trial Description | Textarea (required) | Summary of the trial's purpose and methodology (must exceed 25 characters) |
| Trial Phase | Dropdown (required) | Category field, one of four fixed phase values |
| Terms Agreement | Checkbox (required) | Confirmation that the submitter agrees to terms and conditions |

## Category Values — Trial Phase

- Phase I
- Phase II
- Phase III
- Phase IV