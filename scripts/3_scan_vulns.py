import os

sbom_path = "sboms"
vuln_path = "vulns"

os.makedirs(vuln_path, exist_ok=True)

for sbom in os.listdir(sbom_path):
    input_file = os.path.join(sbom_path, sbom)
    output_file = os.path.join(vuln_path, sbom)

    print(f"Escaneando {sbom}...")
    os.system(f"grype sbom:{input_file} -o json > {output_file}")