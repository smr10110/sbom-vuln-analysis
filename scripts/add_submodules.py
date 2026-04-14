import json
import shutil
import subprocess
import sys
from pathlib import Path


def _run_git_command(args, cwd, error_msg):
    """Helper to run git commands, returns True on success."""
    try:
        subprocess.run(args, check=True, cwd=cwd, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{error_msg}: {e}")
        return False
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?")
        sys.exit(1)


def sync_repos():
    """
    Reads data/repos.json and clones each repository into data/repos/.
    Repos already cloned are skipped. Repos no longer in repos.json are removed.
    """
    repo_root = Path(__file__).resolve().parents[1]
    repos_file = repo_root / "data" / "repos.json"

    if not repos_file.exists():
        print(f"Error: Repositories file not found at {repos_file}")
        sys.exit(1)

    with open(repos_file, "r") as f:
        repos_data = json.load(f)

    desired_paths = {repo["path"] for repo in repos_data.get("repositories", []) if repo.get("path")}
    repos_dir = repo_root / "data" / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)

    # Remove directories no longer in repos.json
    for existing in repos_dir.iterdir():
        rel_path = str(existing.relative_to(repo_root)).replace("\\", "/")
        if rel_path not in desired_paths:
            print(f"Removing {rel_path} (not in repos.json)...")
            shutil.rmtree(existing)
            print(f"[OK] Removed {rel_path}")

    # Clone repos from repos.json
    for repo in repos_data.get("repositories", []):
        url = repo.get("url")
        path = repo.get("path")
        ref = repo.get("ref")

        if not url or not path:
            print(f"Skipping invalid entry: {repo}")
            continue

        dest = repo_root / path

        if dest.exists() and any(dest.iterdir()):
            print(f"Already cloned: {path}")
        else:
            print(f"Cloning {url} -> {path}...")
            dest.mkdir(parents=True, exist_ok=True)
            if not _run_git_command(
                ["git", "clone", "--depth=1", url, str(dest)],
                repo_root,
                f"Failed to clone {url}",
            ):
                continue
            print(f"[OK] Cloned {path}")

        # Checkout specific ref if provided
        if ref and dest.exists():
            print(f"Checking out {ref} in {path}...")
            if _run_git_command(
                ["git", "checkout", ref],
                dest,
                f"Failed to checkout {ref} in {path}",
            ):
                print(f"[OK] Checked out {ref}")

    print("\n[OK] Repository sync complete!")


if __name__ == "__main__":
    sync_repos()
