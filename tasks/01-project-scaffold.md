# Task 01: Project Scaffolding

- **Priority**: P0
- **Deps**: none (parallel with Task 00)
- **PRD**: NFR-5

## Objective

Create project structure, dependencies, and test infrastructure.

## Tests First

```python
# tests/test_scaffold.py

def test_pyproject_has_cartesia_line():
    """cartesia-line is a declared dependency."""
    import tomllib
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    assert any("cartesia-line" in d for d in deps)

def test_pyproject_has_firebase_admin():
    """firebase-admin is a declared dependency."""
    import tomllib
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    assert any("firebase-admin" in d for d in deps)

def test_pyproject_has_pytest():
    """pytest is a dev dependency."""
    import tomllib
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    # or check [tool.pytest] or [dependency-groups]
    assert any("pytest" in d for d in dev_deps)

def test_agents_package_importable():
    """agents package exists and is importable."""
    import agents

def test_tools_package_importable():
    """tools package exists and is importable."""
    import tools
```

## Implementation

### `pyproject.toml`
```toml
[project]
name = "answering-machine"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "cartesia-line>=0.2.2",
    "firebase-admin>=6.0.0",
    "loguru>=0.7.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
search = [
    "stagehand>=3.0.0",
    "google-genai>=1.26.0",
]
web = [
    "fastapi>=0.115.0",
    "uvicorn>=0.35.0",
]
```

### Directory structure
```
agents/__init__.py
agents/prompts.py        # Empty string constants (stubs)
tools/__init__.py
tests/__init__.py
tests/conftest.py        # Shared fixtures (db mock, metadata factory)
```

### `tests/conftest.py`
```python
import pytest

@pytest.fixture
def sample_metadata():
    """Factory for call metadata dicts."""
    def _make(
        family_id="smith_family",
        member_id="member_rose",
        member_name="Rose",
        member_role="grandparent",
        is_device_user=True,
        is_authorized=True,
        is_guest=False,
    ):
        return {
            "family_id": family_id,
            "member_id": member_id,
            "member_name": member_name,
            "member_role": member_role,
            "is_device_user": is_device_user,
            "is_authorized": is_authorized,
            "is_guest": is_guest,
        }
    return _make
```

## Notes

- Firestore async client should come from `firebase_admin.firestore_async` (see Task 02).

## Verification

```bash
uv sync
uv sync --extra dev
pytest tests/test_scaffold.py -v
```
