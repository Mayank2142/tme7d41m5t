# Versioned Source Ingestion and Dataset Releases

Adopted during Phase 2 on 29 October 2026.

Preserve the original Elexon JSON response bytes, source query, receipt time, byte count, and SHA-256. A portable gzip/JSON archive carries those bytes as base64, source attribution, and scope. Its checksums detect accidental alteration; they are not a source signature. Trust begins with the fixed official HTTPS endpoints and the reviewed archive/manifest.

Normalization is strict about required timestamps and integer types. It preserves null/negative values with explicit quality reasons and retains conflicting source-key variants. Normalized version IDs include the parser version and validation reason. The quality manifest fingerprints the complete normalized ID set, preventing a silently changed parse from colliding with an older release identity.

Raw batch membership and parsed release membership are separate. Each release freezes both its raw batch IDs and its exact parsed forecast/actual IDs. Re-parsing the same raw bytes can add versions without changing old releases. PostgreSQL triggers reject updates/deletes on source facts and release evidence; the active pointer and ingestion-run status are separately mutable.

Publication uses an advisory transaction lock and one database transaction for the accepted release and pointer. A transport-complete archive can still have incomplete analytical coverage. Strict publication rejects that candidate while retaining the previous active release; an explicit partial override is named in the manifest. Failed imports are recorded, and raw archives remain available for investigation.

PostgreSQL JSONB, foreign keys, typed UTC timestamps, immutable triggers, and the migration behavior are tested against real PostgreSQL. SQLite is not used as a substitute. The local Windows engine came from the official PostgreSQL-linked EDB portable distribution because Docker's Linux engine was unavailable. Container execution and external Vercel PostgreSQL remain separate deployment checks.
