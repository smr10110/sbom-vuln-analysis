import os

repos_path = "repos"
sbom_path = "sboms"

os.makedirs(sbom_path, exist_ok=True)

for repo in os.listdir(repos_path):
    full_path = os.path.join(repos_path, repo)
    output = os.path.join(sbom_path, f"{repo}.json")

    print(f"Generando SBOM de {repo}...")
    os.system(f"syft {full_path} -o json > {output}")