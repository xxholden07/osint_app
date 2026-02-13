import json
import random
import time
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import instaloader
import requests
from bs4 import BeautifulSoup


class OSINTCore:
    def __init__(
        self,
        delay_range: tuple = (3, 7),
        user_agents: Optional[List[str]] = None,
        request_timeout: int = 15,
    ) -> None:
        self.delay_range = delay_range
        self.request_timeout = request_timeout
        self.user_agents = user_agents or [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]

    def _sleep_random(self) -> None:
        delay = random.uniform(self.delay_range[0], self.delay_range[1])
        time.sleep(delay)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _extract_ddg_url(self, href: str) -> str:
        if "duckduckgo.com/l/" not in href:
            return href
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
        return href

    def search_web(self, query: str, max_results: int = 20) -> List[str]:
        url = "https://duckduckgo.com/html/"
        params = {"q": query}
        self._sleep_random()
        response = requests.get(
            url,
            params=params,
            headers=self._get_headers(),
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results: List[str] = []
        for link in soup.select("a.result__a"):
            href = link.get("href")
            if not href:
                continue
            results.append(self._extract_ddg_url(href))
            if len(results) >= max_results:
                break
        return results

    def advanced_google_hacking(
        self, domain: str, dork_types: Optional[List[str]] = None, max_results: int = 20
    ) -> Dict[str, List[Dict[str, object]]]:
        dorks = {
            "Vazamento de Credenciais": 'site:{domain} filetype:xls OR filetype:xlsx "username" OR "password"',
            "Arquivos de Log e Backup": 'site:{domain} ext:log OR ext:bak OR ext:sql OR ext:txt "admin"',
            "Diretorios Expostos": 'site:{domain} intitle:"index of" "parent directory"',
            "Buckets de Nuvem": 'site:s3.amazonaws.com "{domain_token}"',
        }
        selected = dork_types or list(dorks.keys())
        results: List[Dict[str, object]] = []
        domain_token = domain.split(".")[0]
        for dork_type in selected:
            template = dorks.get(dork_type)
            if not template:
                continue
            query = template.format(domain=domain, domain_token=domain_token)
            urls = self.search_web(query, max_results=max_results)
            results.append({"type": dork_type, "query": query, "urls": urls})
        return {"domain": domain, "dorks": results}

    def image_dork(self, domain: str, max_results: int = 24) -> Dict[str, object]:
        query = 'site:{domain} (ext:jpg OR ext:png OR intitle:"index of" DCIM)'.format(
            domain=domain
        )
        urls = self.search_web(query, max_results=max_results)
        image_urls = [u for u in urls if u.lower().endswith((".jpg", ".jpeg", ".png"))]
        return {"domain": domain, "query": query, "urls": image_urls}

    def get_profile_metadata(self, username: str) -> Dict[str, object]:
        loader = instaloader.Instaloader()
        try:
            profile = instaloader.Profile.from_username(loader.context, username)
            return {
                "username": profile.username,
                "bio": profile.biography or "",
                "followers": profile.followers,
                "following": profile.followees,
                "id": profile.userid,
                "profile_pic_url": profile.profile_pic_url,
                "is_private": profile.is_private,
            }
        except Exception as exc:  # pragma: no cover - runtime dependent
            return {"username": username, "error": str(exc)}

    def private_sniffer(self, username: str, max_results: int = 20) -> Dict[str, object]:
        query = (
            'site:instagram.com "{username}" intext:"collab" OR intext:"tagged"'
        ).format(username=username)
        urls = self.search_web(query, max_results=max_results)
        return {"username": username, "query": query, "urls": urls}

    def monitor_followers(
        self, username: str, previous_followers: int
    ) -> Dict[str, object]:
        profile = self.get_profile_metadata(username)
        if "error" in profile:
            return {
                "username": username,
                "previous_followers": previous_followers,
                "status": "error",
                "error": profile["error"],
            }
        current = profile.get("followers", 0)
        delta = current - previous_followers
        return {
            "username": username,
            "previous_followers": previous_followers,
            "current_followers": current,
            "delta": delta,
            "status": "ok",
        }

    @staticmethod
    def to_json(data: Dict[str, object]) -> str:
        return json.dumps(data, ensure_ascii=True, indent=2)
