# Local private data

AI Core creates `faces.sqlite3` here when the face-embedding store is first used.
The database is ignored by Git.

It stores normalized face vectors, student IDs, display names, model identifiers,
and consent references. It deliberately does **not** store photographs. Treat the
database as biometric data anyway: encrypt the device, restrict file access, define
a deletion/retention policy, and enroll a child only after verified guardian consent.

Never copy the database into a Git commit, demo bundle, analytics system, or cloud
backup without explicit authorization.
