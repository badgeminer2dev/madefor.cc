import argparse
import logging
import sys
from difflib import SequenceMatcher
from typing import List

import dns.log
from dns.domains import domains


def write_diff(prefix: str, domain_list: List[str], start: int, end: int):
    for i in range(start, end):
        print(f"{prefix}{domain_list[i]}\33[0m")


def main(*, fetch_domains: bool = False) -> None:
    valid = True

    domain_list = list(domains.keys())
    sorted_domain_list = sorted(domain_list)

    # Ensure the list is sorted.
    if domain_list != sorted_domain_list:
        valid = False

        logging.error("Domain list is not sorted")

        matcher = SequenceMatcher(None, domain_list, sorted_domain_list)
        for tag, alo, ahi, blo, bhi in matcher.get_opcodes():
            if tag == "insert":
                write_diff("\033[32m +", sorted_domain_list, blo, bhi)
            elif tag == "delete":
                write_diff("\033[31m -", domain_list, alo, ahi)
            elif tag == "equal":
                write_diff("  ", domain_list, alo, ahi)
            elif tag == "replace":
                write_diff("\033[31m *", domain_list, alo, ahi)
                write_diff("\033[32m *", sorted_domain_list, blo, bhi)

    # Ensure CNAMEs are valid(ish). We only need to catch the common case of people using URLs instead of domains.
    for domain, info in domains.items():
        cname = info["cname"]
        if "/" in info["cname"]:
            valid = False

            logging.error(
                "Invalid CNAME '%s' for '%s'. This should be a domain name, not a URL",
                cname,
                domain,
            )

            cname = cname.removeprefix("https://").removeprefix("http://")
            if "/" in cname and (idx := cname.index("/")) and idx > 0:
                cname = cname[0:idx]

            if "/" not in cname:
                logging.info("Maybe try '%s' instead?", cname)

    if fetch_domains:
        for domain in domains.keys():
            url = f"https://{domain}.madefor.cc"
            from urllib.error import URLError
            from urllib.request import urlopen

            try:
                with urlopen(url, timeout=5) as h:
                    if h.getcode() != 200:
                        valid = False
                        logging.error("Got HTTP %s when requesting %s", url)

            except URLError as e:
                valid = False
                logging.error("Cannot request %s (%s)", url, str(e))

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    dns.log.configure()

    arg_spec = argparse.ArgumentParser()
    arg_spec.add_argument(
        "--fetch-domains", default=False, action="store_true", help="Fetch each domain and check it is still up."
    )
    args = arg_spec.parse_args()

    main(fetch_domains=args.fetch_domains)
