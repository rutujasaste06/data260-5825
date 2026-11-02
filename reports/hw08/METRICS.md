# METRICS.md - HW8 (SID4 5825)

SEED 5825, VERIFY_SEED 265825, PREFIX s5825, domain: Clinical trial listings.

## Failure table (before fix vs after fix)

| Failure scenario | Before fix | After fix |
|---|---|---|
| Duplicate delivery | Same correlation_id `ddb212a5-b506-410a-a16b-da238a05f255` replayed. Response #1 entity_id `8eca8d1b-b6c0-407c-a03f-0ebea33991e3`, Response #2 entity_id `92826e87-2dc1-4fb2-9bc0-bf0d7c294121`. "DIFFERENT entity_id each time -> NOT idempotent. A duplicate trial was created." | Same replay with correlation_id `de829fe1-3b6e-4500-a15d-ed709f9e89f2` returned entity_id `d21e877a-731b-4aa7-8042-9232803adf46` both times. Worker log: `DUPLICATE detected for correlation_id=de829fe1-... - returning cached response`, no new trial created. |
| Consumer killed mid-work | Offset committed immediately (before work) for correlation_id `9ab8f7b8-30e6-4af3-abb7-88c8222aa691`, then Writer killed during the LLM call. After restart, no `Received plan`: the message is lost. | Writer killed before the draft, restarted, same message `05038906-8b41-4514-bf2d-6418f0c6d409` redelivered and completed; `Offset committed ... now safe` printed only after the send. |
| Poison message | Worker crashed: `RuntimeError: Simulated processing crash (poison message test)`. Normal request #2 response: None; poison not on any dead-letter topic. | `GIVING UP after 4 attempts` - sent correlation_id `17f042b7-2f2a-4404-af7f-3dbbe7d0f4e5` to `s5825_dead_letter`; both normal requests succeeded. |
| Two partitions / two consumers | Run 1, no key: trial `28fd79e0` processed as [1, 2, 3, 4, 6, 5, 7], OUT OF ORDER. | Run 2, key = entity_id: all four trials IN ORDER, each on one partition and one Writer. |

Notes: "Before fix" for Consumer killed is a copy of the Writer that commits the offset immediately on receipt; "before fix" for Poison message is a copy of the worker without retry or dead-letter handling.

Raw data: `raw/ordering_nokey.csv`, `raw/ordering_nokey_log.jsonl`, `raw/ordering_key.csv`, `raw/ordering_key_log.jsonl`.
