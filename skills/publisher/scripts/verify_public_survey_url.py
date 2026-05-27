#!/usr/bin/env python3
"""
Verify that a published survey URL returns browser-openable HTML instead of
attachment-style download behavior.
"""

from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()

    request = Request(args.url, method="HEAD")
    with urlopen(request) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        content_type = headers.get("content-type", "")
        disposition = headers.get("content-disposition", "")
        result = {
            "url": args.url,
            "status": response.status,
            "contentType": content_type,
            "contentDisposition": disposition,
            "isHtml": "text/html" in content_type.lower(),
            "isAttachment": "attachment" in disposition.lower(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
