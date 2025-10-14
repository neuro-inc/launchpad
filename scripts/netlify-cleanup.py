#!/usr/bin/env python3
"""
Netlify domain alias management script.
This script adds or removes domain aliases from a Netlify site.

Environment variables required:
- NETLIFY_TOKEN: Netlify API token
- NETLIFY_SITE_ID: Netlify site ID
"""

import argparse
import logging
import os
import sys

import requests


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

NETLIFY_API_BASE = "https://api.netlify.com/api/v1"


def get_site_info(site_id: str, token: str) -> dict:
    """Fetch site information from Netlify API."""
    url = f"{NETLIFY_API_BASE}/sites/{site_id}"
    headers = {"Authorization": f"Bearer {token}"}

    logger.info(f"Fetching site info for site {site_id}")

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    site_data = response.json()
    logger.info(f"SITE INFO: {site_data}")
    return site_data


def update_domain_aliases(site_id: str, token: str, new_aliases: list[str]) -> dict:
    """Update the domain aliases for a Netlify site."""
    url = f"{NETLIFY_API_BASE}/sites/{site_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"domain_aliases": new_aliases}

    logger.info("Updating domain aliases...")

    response = requests.patch(url, headers=headers, json=payload)
    response.raise_for_status()

    result = response.json()
    logger.info("Updated domain aliases.")
    logger.info(f"Resulting site data: {result}")
    return result


def add_domain(site_id: str, token: str, domain_alias: str) -> int:
    """Add a domain alias to a Netlify site."""
    site_info = get_site_info(site_id, token)
    current_aliases = site_info.get("domain_aliases", [])

    logger.info(f"Current domains: {current_aliases}")

    if domain_alias in current_aliases:
        logger.info(f"Domain alias '{domain_alias}' already exists")
        return 0

    new_aliases = current_aliases + [domain_alias]
    logger.info(f"Adding domain alias '{domain_alias}'")
    logger.info(f"New domain list: {new_aliases}")

    update_domain_aliases(site_id, token, new_aliases)
    return 0


def delete_domain(site_id: str, token: str, domain_alias: str) -> int:
    """Remove a domain alias from a Netlify site."""
    site_info = get_site_info(site_id, token)
    current_aliases = site_info.get("domain_aliases", [])

    logger.info(f"Current domains: {current_aliases}")

    if domain_alias not in current_aliases:
        logger.info(f"Domain alias '{domain_alias}' does not exist")
        return 0

    new_aliases = [alias for alias in current_aliases if alias != domain_alias]
    logger.info(f"Removing domain alias '{domain_alias}'")
    logger.info(f"New domain list: {new_aliases}")

    update_domain_aliases(site_id, token, new_aliases)
    return 0


def main() -> int:
    """Entry point"""
    parser = argparse.ArgumentParser(
        description="Manage Netlify domain aliases",
    )
    parser.add_argument(
        "action",
        choices=["add", "delete"],
        help="Action to perform: add or delete domain alias",
    )
    parser.add_argument(
        "--site-id",
        required=True,
        help="Netlify site ID",
    )
    parser.add_argument(
        "--domain-alias",
        required=True,
        help="Domain alias to add or remove",
    )

    args = parser.parse_args()

    # Check for required environment variable
    token = os.environ.get("NETLIFY_TOKEN")
    if not token:
        logger.error("Error: NETLIFY_TOKEN environment variable is not set")
        return 1

    try:
        if args.action == "add":
            return add_domain(args.site_id, token, args.domain_alias)
        else:  # delete
            return delete_domain(args.site_id, token, args.domain_alias)
    except requests.RequestException as e:
        logger.error(f"Failed to modify domain alias: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
