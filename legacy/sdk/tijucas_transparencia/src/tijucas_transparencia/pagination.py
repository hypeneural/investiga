from __future__ import annotations
from typing import Callable, Dict, Any, List
import time

def collect_paginated(fetch_page: Callable[[int], Dict[str, Any]]) -> List[Dict[str, Any]]:
    first_page = fetch_page(1)
    items = list(first_page["items"])
    total_pages = int(first_page.get("total_pages") or 1)

    for page in range(2, total_pages + 1):
        time.sleep(1.5)  # Respeita o limite de 1 requisição por segundo da API
        page_data = fetch_page(page)
        items.extend(page_data["items"])

    return items
