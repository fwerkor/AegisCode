from aegiscode.memory import JsonMemoryStore

def test_memory_retrieves_by_token_and_tag(tmp_path):
    store = JsonMemoryStore(tmp_path / "memory.json")
    store.add("Project uses pytest for validators", ["python", "testing"])
    store.add("Release through Docker image", ["distribution"])
    found = store.search("python testing", limit=1)
    assert found[0].text.startswith("Project uses pytest")
