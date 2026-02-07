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
    assert any("pytest" in d for d in dev_deps)

def test_agents_package_importable():
    """agents package exists and is importable."""
    import agents

def test_tools_package_importable():
    """tools package exists and is importable."""
    import tools
