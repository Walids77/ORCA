"""ORCA ingestion — the doorman + the per-type file processors.

A file enters through `router.detect_file_type` / `router.route`, which decides
what kind of file it is and hands it to the right specialist (excel / pdf / image).
"""
