import pytest
from pathlib import Path
from maestro.orch.validator_tools import ValidatorTools, ToolResult


class TestValidatorTools:
    """Tests für ValidatorTools."""
    
    @pytest.fixture
    def sample_repo(self, tmp_path):
        """Erstelle ein Sample-Repo für Tests."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "src").mkdir()
        (repo / "tests").mkdir()
        
        (repo / "src" / "main.py").write_text("""
def main():
    print("Hello")

class MyClass:
    def method(self):
        pass
""")
        (repo / "src" / "utils.py").write_text("def helper(): pass")
        (repo / "tests" / "test_main.py").write_text("def test_main(): pass")
        (repo / "README.md").write_text("# Project")
        
        return repo
    
    def test_list_files_all(self, sample_repo):
        """Test list_files ohne Pattern."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("list_files")
        
        assert result.success
        assert result.data["count"] == 4
        assert "README.md" in result.data["files"]
    
    def test_list_files_pattern(self, sample_repo):
        """Test list_files mit Pattern."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("list_files", pattern="src/**/*.py")
        
        assert result.success
        assert result.data["count"] == 2
        assert all("src/" in f for f in result.data["files"])
    
    def test_read_file_success(self, sample_repo):
        """Test read_file existierende Datei."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("read_file", path="src/main.py")
        
        assert result.success
        assert "def main()" in result.data["content"]
        assert result.data["total_lines"] > 0
    
    def test_read_file_not_found(self, sample_repo):
        """Test read_file nicht existierende Datei."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("read_file", path="nonexistent.py")
        
        assert not result.success
        assert "not found" in result.error.lower()
    
    def test_read_file_offset_limit(self, sample_repo):
        """Test read_file mit offset und limit."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("read_file", path="src/main.py", offset=0, limit=2)
        
        assert result.success
        lines = result.data["content"].split("\n")
        assert len(lines) <= 2
    
    def test_grep_repo(self, sample_repo):
        """Test grep_repo."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("grep_repo", query="def main")
        
        assert result.success
        assert result.data["count"] >= 1
        assert any("main.py" in m["file"] for m in result.data["matches"])
    
    def test_check_symbol_found(self, sample_repo):
        """Test check_symbol - Symbol existiert."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("check_symbol", symbol="main", language="py")
        
        assert result.success
        assert result.data["found"] is True
        assert len(result.data["locations"]) > 0
    
    def test_check_symbol_not_found(self, sample_repo):
        """Test check_symbol - Symbol existiert nicht."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("check_symbol", symbol="nonexistent", language="py")
        
        assert result.success
        assert result.data["found"] is False
    
    def test_path_traversal_protection(self, sample_repo):
        """Test Path Traversal Schutz."""
        tools = ValidatorTools(sample_repo)
        
        # Versuch auf Parent-Verzeichnis zuzugreifen
        result = tools.execute("read_file", path="../etc/passwd")
        
        assert not result.success
    
    def test_get_repo_structure(self, sample_repo):
        """Test get_repo_structure."""
        tools = ValidatorTools(sample_repo)
        result = tools.execute("get_repo_structure", max_depth=2)
        
        assert result.success
        assert result.data["structure"]["name"] == "repo"
        assert "children" in result.data["structure"]
    
    def test_tool_history(self, sample_repo):
        """Test dass Tool-Calls geloggt werden."""
        tools = ValidatorTools(sample_repo)
        
        tools.execute("list_files")
        tools.execute("read_file", path="README.md")
        
        history = tools.get_history()
        assert len(history) == 2
        assert history[0]["tool"] == "list_files"
