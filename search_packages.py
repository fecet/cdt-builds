#!/usr/bin/env python3
"""
Search for packages in AlmaLinux/CentOS repositories.

This utility allows searching for packages across different distributions and repositories
used by the CDT builds system.
"""

import requests
import xml.etree.ElementTree as ET
import gzip
import re
import argparse
from urllib.parse import urljoin

# Repository configurations matching rpm.py
REPO_CONFIGS = {
    "centos7": {
        "base_url": "https://vault.centos.org/7.9.2009/os/{architecture}/",
        "repos": ["os"],
        "repodata_path": "repodata/repomd.xml",
    },
    "alma8": {
        "base_url": "https://vault.almalinux.org/8.9/{repo}/{architecture}/os/",
        "repos": ["BaseOS", "AppStream", "PowerTools"],
        "repodata_path": "repodata/repomd.xml",
    },
    "alma9": {
        "base_url": "https://vault.almalinux.org/9.4/{repo}/{architecture}/os/",
        "repos": ["BaseOS", "AppStream", "CRB", "devel"],
        "repodata_path": "repodata/repomd.xml",
    },
}


def search_packages_in_repo(repomd_url, search_term, repo_name):
    """Search for packages containing the search term in a repository"""
    print(f"Searching in {repo_name}: {repomd_url}")

    try:
        # Get repomd.xml
        response = requests.get(repomd_url, timeout=30)
        if response.status_code != 200:
            print(f"  Failed to fetch repomd.xml (HTTP {response.status_code})")
            return []

        # Remove namespace
        xmlstring = re.sub(rb'\sxmlns="[^"]+"', b"", response.content, count=1)
        repomd = ET.fromstring(xmlstring)

        # Find primary.xml.gz
        for child in repomd.findall("*[@type='primary']"):
            location = child.findall("location")[0].attrib["href"]
            primary_url = urljoin(
                repomd_url.replace("/repodata/repomd.xml", "/"), location
            )

            print(f"  Fetching package data...")
            primary_response = requests.get(primary_url, timeout=60)
            if primary_response.status_code != 200:
                continue

            # Decompress and parse
            primary_data = gzip.decompress(primary_response.content)
            primary_xmlstring = re.sub(rb'\sxmlns="[^"]+"', b"", primary_data, count=1)
            primary_root = ET.fromstring(primary_xmlstring)

            packages = []
            for package in primary_root.findall("package"):
                name = package.find("name").text
                if search_term.lower() in name.lower():
                    arch = package.find("arch").text
                    version = package.find("version").attrib["ver"]
                    release = package.find("version").attrib["rel"]
                    packages.append(
                        {
                            "name": name,
                            "version": version,
                            "release": release,
                            "arch": arch,
                            "full_name": f"{name}-{version}-{release}.{arch}",
                        }
                    )

            return packages

        print(f"  No primary.xml found in repository")
        return []

    except Exception as e:
        print(f"  Error: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Search for packages in AlmaLinux/CentOS repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python search_packages.py shadow-utils --distro alma9
  python search_packages.py glibc --distro centos7 --architecture aarch64
  python search_packages.py --search-term kernel --distro alma8 --repo BaseOS
        """,
    )

    parser.add_argument(
        "search_term", nargs="?", help="Package name or partial name to search for"
    )
    parser.add_argument("--search-term", help="Alternative way to specify search term")
    parser.add_argument(
        "--distro",
        choices=["centos7", "alma8", "alma9"],
        default="alma9",
        help="Distribution to search in (default: alma9)",
    )
    parser.add_argument(
        "--architecture",
        default="x86_64",
        help="Architecture to search for (default: x86_64)",
    )
    parser.add_argument(
        "--repo",
        help="Specific repository to search in (if not specified, searches all repos for the distro)",
    )
    parser.add_argument(
        "--exact", action="store_true", help="Only show exact package name matches"
    )

    args = parser.parse_args()

    # Determine search term
    search_term = args.search_term or args.search_term
    if not search_term:
        parser.error("Search term is required")

    distro = args.distro
    architecture = args.architecture

    if distro not in REPO_CONFIGS:
        print(f"Unsupported distro: {distro}")
        return 1

    config = REPO_CONFIGS[distro]
    repos_to_search = [args.repo] if args.repo else config["repos"]

    all_packages = []

    for repo in repos_to_search:
        if distro == "centos7":
            repomd_url = f"{config['base_url'].format(architecture=architecture)}{config['repodata_path']}"
        else:
            repomd_url = f"{config['base_url'].format(repo=repo, architecture=architecture)}{config['repodata_path']}"

        packages = search_packages_in_repo(repomd_url, search_term, f"{distro}/{repo}")

        if packages:
            print(f"  Found {len(packages)} packages:")
            for pkg in packages:
                if args.exact and pkg["name"] != search_term:
                    continue
                print(f"    {pkg['full_name']}")
            all_packages.extend([(pkg, repo) for pkg in packages])
        else:
            print(f"  No packages found")
        print()

    print("=" * 60)
    print(f"SUMMARY: {len(all_packages)} packages found containing '{search_term}'")
    print("=" * 60)

    if args.exact:
        all_packages = [
            (pkg, repo) for pkg, repo in all_packages if pkg["name"] == search_term
        ]

    for pkg, repo in all_packages:
        print(f"{pkg['full_name']} (from {repo})")

    return 0


if __name__ == "__main__":
    exit(main())

