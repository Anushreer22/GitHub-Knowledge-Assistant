
import argparse
import os
import time
import requests

from dotenv import load_dotenv
from .common import DATA, write

load_dotenv()

def search_repositories(language, per_page):
    api = os.getenv(
        "GITHUB_API_URL",
        "https://api.github.com"
    ).rstrip("/")

    token = os.getenv("GITHUB_TOKEN", "").strip()

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Removed invalid license:* qualifier.
    query = (
        f"language:{language} "
        "stars:>=5 "
        "archived:false "
        "fork:false"
    )

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(per_page, 100)
    }

    response = requests.get(
        f"{api}/search/repositories",
        headers=headers,
        params=params,
        timeout=30
    )

    if not response.ok:
        print("GitHub API status:", response.status_code)
        print("GitHub API response:", response.text[:1500])
        response.raise_for_status()

    return response.json().get("items", [])


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--per-language",
        type=int,
        default=10
    )

    args = parser.parse_args()

    records = []
    seen = set()

    languages = ["Python", "Java"]

    for language in languages:

        print(f"\nSearching {language} repositories...")

        try:
            repositories = search_repositories(
                language,
                args.per_language
            )

        except requests.RequestException as error:
            print(f"[ERROR] {language}: {error}")
            continue

        for repo in repositories:

            full_name = repo["full_name"]

            if full_name.lower() in seen:
                continue

            seen.add(full_name.lower())

            # Keep only repositories with licence metadata.
            # Human licence review is still required.
            licence = repo.get("license")

            if not licence:
                print(f"[SKIP] No detected licence: {full_name}")
                continue

            record = {
                "repo_id": full_name.replace("/", "__"),
                "full_name": full_name,
                "html_url": repo["html_url"],
                "clone_url": repo["clone_url"],
                "default_branch": repo.get("default_branch"),
                "language": repo.get("language"),
                "stars": repo.get("stargazers_count"),
                "license_spdx_id": licence.get("spdx_id"),
                "license_name": licence.get("name"),
                "licence_review_status": "needs_human_review",
                "collection_source": "github_search_api"
            }

            records.append(record)

            print(
                f"[ADDED] {full_name} | "
                f"{record['language']} | "
                f"{record['license_name']}"
            )

        time.sleep(2)

    output = DATA / "metadata" / "repositories.jsonl"

    write(output, records)

    print("\n--------------------------------")
    print("REPOSITORY COLLECTION COMPLETE")
    print("--------------------------------")
    print("Total repositories:", len(records))
    print("Output:", output)


if __name__ == "__main__":
    main()
