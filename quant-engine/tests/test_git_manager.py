import pytest
import os
import git
from pathlib import Path
from src.qa.git_manager import GitManager

@pytest.fixture
def tmp_git_repo(tmp_path):
    """Fixture to create a temporary git repository with an initial commit."""
    repo = git.Repo.init(tmp_path)
    
    # Configure git author
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test Medic")
        cw.set_value("user", "email", "medic@example.com")
        
    test_file = tmp_path / "test_file.py"
    test_file.write_text("print('Hello World')")
    
    repo.index.add(["test_file.py"])
    repo.index.commit("Initial commit")
    
    # Create 'main' branch (git init usually creates 'master' or 'main')
    if 'main' not in [head.name for head in repo.heads]:
        if 'master' in [head.name for head in repo.heads]:
            repo.heads.master.rename('main')
        else:
            new_branch = repo.create_head('main')
            new_branch.checkout()
    
    return tmp_path

def test_git_manager_create_branch(tmp_git_repo):
    """Test creating a new branch via GitManager."""
    manager = GitManager(str(tmp_git_repo))
    branch_name = "medic/fix-test"
    
    manager.create_branch(branch_name)
    
    repo = git.Repo(tmp_git_repo)
    assert repo.active_branch.name == branch_name

def test_git_manager_commit_file(tmp_git_repo):
    """Test committing a modified file via GitManager."""
    manager = GitManager(str(tmp_git_repo))
    branch_name = "medic/fix-commit-test"
    manager.create_branch(branch_name)
    
    # Modify the file
    test_file = tmp_git_repo / "test_file.py"
    test_file.write_text("print('Hello Medic')")
    
    commit_hash = manager.commit_file(str(test_file), "[AUTO-MEDIC] Modified test file")
    
    repo = git.Repo(tmp_git_repo)
    assert commit_hash == repo.head.commit.hexsha
    assert repo.head.commit.message == "[AUTO-MEDIC] Modified test file"

def test_git_manager_restore_main(tmp_git_repo):
    """Test checking out the main branch."""
    manager = GitManager(str(tmp_git_repo))
    branch_name = "medic/fix-restore-test"
    manager.create_branch(branch_name)
    
    repo = git.Repo(tmp_git_repo)
    assert repo.active_branch.name == branch_name
    
    manager.restore_main()
    
    assert repo.active_branch.name == "main"
