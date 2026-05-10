import pytest
from unittest.mock import patch, MagicMock

# Mock git module globally before imports
import sys
mock_git = MagicMock()
sys.modules['git'] = mock_git

from src.execution.autonomous_dev_agent import AutonomousDevAgent

def test_autonomous_dev_branching_logic():
    """
    Test the core validation logic of the autonomous dev agent.
    If simulated S_new is 3.5 and S_base is 2.0 (improvement > 5%),
    it should trigger git branching and commit logic.
    """
    mock_repo = MagicMock()
    mock_git_manager = MagicMock()
    
    with patch("src.execution.autonomous_dev_agent.GitManager", return_value=mock_git_manager):
        agent = AutonomousDevAgent(repo=mock_repo, workspace_root="/mock/workspace")
        
        # We patch the random simulation to force the specific S_new
        import random
        with pytest.MonkeyPatch.context() as m:
            # random.uniform generates the multiplier for S_base
            # S_new = 2.0 * multiplier. To get 3.5, multiplier = 1.75
            m.setattr(random, "uniform", lambda a, b: 1.75)
            
            # We also need to patch os.path.exists and open to avoid actual file system errors in test
            import builtins
            m.setattr("os.path.join", lambda *args: "/mock/file.py")
            
            # Mock the open function
            mock_file = MagicMock()
            mock_open = MagicMock(return_value=mock_file)
            mock_file.__enter__.return_value.write = MagicMock()
            m.setattr(builtins, "open", mock_open)
            
            # Run the feature evolution
            success = agent.evolve_feature("test_feature_xyz", "Find arbitrage")
            
            # Assertions
            assert success is True
            
            # Ensure git branch was created
            assert mock_git_manager.create_branch.called
            branch_call_args = mock_git_manager.create_branch.call_args[0][0]
            assert branch_call_args.startswith("feat/ai-auto-dev-")
            
            # Ensure file was committed
            assert mock_git_manager.commit_file.called
            
            # Ensure DB log was created
            assert mock_repo.con.execute.called
            
            # Ensure it restored to main
            assert mock_git_manager.restore_main.called
