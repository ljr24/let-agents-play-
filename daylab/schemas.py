"""Version boundaries. App version is deliberately separate from rule/data versions."""
APP_VERSION = "2.0.0"
MANIFEST_VERSION = 2
STREAM_VERSIONS = {
    "observation": 1,
    "action": 1,
    "event": 1,
    "checkpoint": 1,
    "model": 1,
    "result": 1,
}


def validate_manifest(manifest):
    version = manifest.get("schema_version", 1)
    if version not in (1, MANIFEST_VERSION):
        raise ValueError(f"Unsupported manifest schema: {version}")
    if version == 2 and manifest.get("stream_versions") != STREAM_VERSIONS:
        raise ValueError("Unsupported stream schema; an explicit reader migration is required")
    for field in ("config", "seed", "schedule", "versions"):
        if field not in manifest:
            raise ValueError(f"Missing manifest field: {field}")
    return manifest
