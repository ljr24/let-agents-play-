"""Version boundaries. App version is deliberately separate from rule/data versions."""
APP_VERSION = "3.1.0"
MANIFEST_VERSION = 4
STREAM_VERSIONS = {
    "observation": 3,
    "action": 1,
    "event": 2,
    "checkpoint": 2,
    "model": 3,
    "result": 1,
}


def validate_manifest(manifest):
    version = manifest.get("schema_version", 1)
    if version not in (1, 2, 3, MANIFEST_VERSION):
        raise ValueError(f"Unsupported manifest schema: {version}")
    if version == MANIFEST_VERSION and manifest.get("stream_versions") != STREAM_VERSIONS:
        raise ValueError("Unsupported stream schema; an explicit reader migration is required")
    for field in ("config", "seed", "schedule", "versions"):
        if field not in manifest:
            raise ValueError(f"Missing manifest field: {field}")
    return manifest
