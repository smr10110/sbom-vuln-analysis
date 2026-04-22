import requests
import os
from datetime import datetime, timedelta

ORG = "pallets"  
MAX_REPOS = 10

repos_url = f"https://api.github.com/orgs/{ORG}/repos?per_page=100"
repos = requests.get(repos_url).json()

hace_un_mes = datetime.now() - timedelta(days=30)

os.makedirs("repos", exist_ok=True)

count = 0

for repo in repos:
    if count >= MAX_REPOS:
        break

    updated = datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")

    if updated > hace_un_mes:
        clone_url = repo["clone_url"]
        name = repo["name"]

        print(f"Clonando {name}...")
        os.system(f"git clone {clone_url} repos/{name}")
        count += 1