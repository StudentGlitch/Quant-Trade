import os
import git
from loguru import logger
from pathlib import Path

class GitManager:
    """GitPython wrapper for automated branching and committing."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        try:
            self.repo = git.Repo(self.repo_path)
            logger.info(f"GitManager initialized for repo at {self.repo_path}")
        except git.InvalidGitRepositoryError:
            logger.error(f"Invalid Git repository at {self.repo_path}")
            raise

    def create_branch(self, branch_name: str):
        """Checkout main and create a new branch."""
        try:
            # Ensure we are on main and up to date
            self.restore_main()
            
            # Create and checkout new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            logger.info(f"Created and checked out branch: {branch_name}")
        except Exception as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            raise

    def commit_file(self, file_path: str, message: str) -> str:
        """Add and commit a specific file."""
        try:
            # Absolute path to relative path for git
            rel_path = os.path.relpath(file_path, self.repo_path)
            self.repo.index.add([rel_path])
            commit = self.repo.index.commit(message)
            logger.info(f"Committed changes to {rel_path} with message: {message}")
            return commit.hexsha
        except Exception as e:
            logger.error(f"Failed to commit file {file_path}: {e}")
            raise

    def restore_main(self):
        """Checkout the main branch and pull changes."""
        try:
            # Attempt 'main', fallback to 'master'
            main_branch = 'main'
            if 'main' not in self.repo.heads:
                if 'master' in self.repo.heads:
                    main_branch = 'master'
                else:
                    raise Exception("Neither 'main' nor 'master' branch found.")

            self.repo.heads[main_branch].checkout()
            # self.repo.remotes.origin.pull() # Uncomment in production if remote exists
            logger.info(f"Restored to {main_branch} branch.")
        except Exception as e:
            logger.error(f"Failed to restore main: {e}")
            raise
