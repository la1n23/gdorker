#!/usr/bin/env python
import argparse
import json
import os
import time
import signal
from typing import Dict, List, Optional, Any, NoReturn
from googleapiclient.discovery import build
from colorama import init, Fore
import sys
import requests
from bs4 import BeautifulSoup
import re

init(autoreset=True)

class Logger:
    def __init__(self, options: Dict[str, Any]) -> None:
        self.has_title = options.get('title', False)
        self.has_code = options.get('code', False)
        self.has_body = options.get('body', False)
        self.dest = options.get('dest', False)
        self.is_extended = any([self.has_code, self.has_body])
        if self.dest and isinstance(self.dest, str):
            self.dest = open(self.dest, 'a')

    def f_title(self, title: str) -> str:
        return f"{Fore.MAGENTA}[{title}]"
    def f_url(self, url: str) -> str:
        return f"{Fore.GREEN}[{url}]"
    def f_code(self, code: int) -> str:
        color = Fore.WHITE
        if code >= 200 and code < 300:
            color = Fore.GREEN
        elif code >= 300 and code < 400:
            color = Fore.YELLOW
        elif code >= 400 and code < 600:
            color = Fore.RED
        return f"{color}[{code}]"
    def f_body(self, html: str) -> str:
        soup = BeautifulSoup(html,'html.parser')
        body = soup.body.get_text() if soup.body else ""
        text = re.sub(r'[\s]+', " ", body).strip()[0:100]
        return f"{Fore.CYAN}[{text}]"

    def f_result(self, info: str) -> str:
        return f"{Fore.BLUE}[URL] {info}"
    def f_info(self, info: str) -> str:
        return f"{Fore.BLUE}[INFO] {info}"
    def f_error(self, error: str) -> str:
        return f"{Fore.RED}[ERROR] {error}"

    def _build_result(self, pieces: Dict[str, str]):
        output = [self.f_url(pieces["url"])]

        if self.has_code:
            output.append(self.f_code(pieces["code"]))
        if self.has_title:
            output.append(self.f_title(pieces['title']))
        if self.has_body:
            output.append(self.f_body(pieces["body"]))
        return ' '.join(output)

    def write(self, line: str) -> None:
        print(line)

    def log_url(self, pieces: Dict[str, str]) -> None:
        result = self._build_result(pieces)
        line = self.f_info(result)
        self.write(line)
        if self.dest:
            print(line, file=self.dest)

    def log_info(self, info: str) -> None:
        line = self.f_info(info)
        self.write(line)

    def log_error(self, error: str) -> None:
        line = self.f_error(error)
        self.write(line)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.dest:
            self.dest.close()


class GoogleSearch:
    per_page = 10

    def __init__(self, logger: Logger, api_key: str, cse_id: str) -> None:
        self.logger = logger
        self.api_key = api_key
        self.cse_id = cse_id
        self.offset: int = 1
        self.is_limit_reached = False

    @property
    def _page(self) -> int:
        return self.offset // self.per_page + 1

    def _google_search(self, query: str, start: int = 0) -> List[Dict[str, Any]]:
        service = build("customsearch", "v1", developerKey=self.api_key)
        try:
            res = service.cse().list(q=query, cx=self.cse_id, start=start, num=self.per_page).execute()
            items = res.get('items')
            return items
        except Exception as e:
            try:
                error_content = json.loads(e.content)
                #print(json.dumps(error_content, indent=4))
                if error_content['error']['status'] == 'RESOURCE_EXHAUSTED':
                    self.logger.log_info("Resource limit reached. Please try again in 24h")
                    self.is_limit_reached = True
                else:
                    self.logger.log_error(e.content)
            except json.JSONDecodeError:
                self.logger.log_error(e.content)
            return []

    def _print_results(self, results: list):
        for item in results:
            url = item['link']
            pieces = {
                "url": url,
                "title": item['title']
            }
            if self.logger.is_extended:
                res = requests.get(url)
                pieces = {
                    **pieces,
                    "code": res.status_code,
                    "body": res.text
                }
            self.logger.log_url(pieces)

    def query_results(self, query: str) -> None:
        self.offset: int = 1
        start: int = self.offset
        while not self.is_limit_reached:
            self.logger.log_info(f"Page {self._page}")
            results = self._google_search(query, start=start)
            self._print_results(results)
            if not results:
                break
            self.offset = start + self.per_page
            start += self.per_page
            time.sleep(1)

def handle_exit_signal(google_search: GoogleSearch, logger: Logger, signum: int, frame: Any) -> NoReturn:
    logger.log_info("Interrupted by user, saving session...")
    #google_search.save_session()  # TODO
    exit(0)

def load_queries(file_or_query: str) -> list[str]:
    try:
        with open(file_or_query, 'r') as f:
            queries = f.readlines()
            return queries
    except Exception as e:
        return [file_or_query]

def main(api_key: str, cse_id: str, file_or_query: str, f_options) -> None:
    logger = Logger(f_options)
    google_search = GoogleSearch(logger, api_key, cse_id)

    signal.signal(signal.SIGINT, lambda signum, frame: handle_exit_signal(google_search, logger, signum, frame))
    queries = load_queries(file_or_query)
    for query in queries:
        logger.log_info(f"Query: {query}")
        google_search.query_results(query)
        if google_search.is_limit_reached:
            break

if __name__ == "__main__":
    sys.stderr.write("""
⠀⠀⣠⣶⣶⣦⣤⡄⠀⠀⠀⠀⠀⠀⠀⢠⣤⣤⣤⣀⣀⡀⠀⠀⠀⠀⣠⣤⣤⣤⣄⠀⠀⠀⣤⣤⣤⣤⣤⣀⡀⠀⠀⣀⣀⣤⡀⢠⣤⣤⣤⠀⣀⣀⣀⣤⣤⣤⣤⡄⠀⢠⣤⣤⣤⣤⣄⣀⠀⠀
⠀⣼⡟⠁⠀⠉⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⠉⠙⠻⣷⡄⠀⠀⣼⡿⠁⠀⠀⢻⡆⠀⠀⠘⣿⠀⠀⠈⢹⣷⠀⠀⠈⢿⡏⠀⣨⡿⠋⠀⠀⠈⣿⡏⠉⢉⠙⣿⡇⠀⠀⢻⡏⠀⠀⠉⣻⡇⠀
⠀⣿⡇⠀⢠⣦⣼⣷⣦⠄⠀⠀⠀⠀⠀⠀⢸⣧⠀⠀⠀⠸⣷⠀⠀⣿⠇⠀⠀⠀⠀⣿⠀⠀⠀⣿⡶⠶⣾⡟⠁⠀⠀⠀⢸⣀⣴⣿⡀⠀⠀⠀⠀⢸⣷⣶⣿⡇⠈⠀⠀⠀⠸⣷⠶⢶⣾⠟⠀⠀
⠀⢺⣇⠀⠀⠀⢹⣿⠀⠸⠿⠿⠾⠿⠗⠀⢘⣿⠀⠀⠀⢠⡿⠀⠀⣿⡆⠀⠀⠀⢠⡟⠀⠀⠀⢹⡁⠀⢸⣧⠀⠀⠀⠀⢸⠟⠁⠙⢷⡀⠀⠀⠀⢸⡇⠀⠙⠃⢠⣤⠀⠀⠀⣏⠀⠀⢻⣆⠀⠀
⠀⠈⠻⣷⣶⣴⣿⡿⠀⠀⠀⠀⠀⠀⠀⣤⣼⣿⣤⣠⣴⠿⠁⠀⠀⠘⠿⣦⣤⣤⠟⠀⠀⠀⢠⣿⣧⣄⢀⣿⣷⣤⠀⣠⣽⣄⡀⢀⣠⣷⣤⠀⣠⣿⣷⣤⣴⣴⣾⣿⠀⠀⢴⣿⣦⡀⣸⣿⣦⡄
                               
                               By La1n

""")
    parser = argparse.ArgumentParser(
        description="""
G-Dorker - Google Custom Search Engine Dorking Tool

A tool for performing Google dorks using Custom Search Engine API.
Allows saving results to file and extracting additional information from URLs.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ./g-dorker.py -q "site:example.com" -k YOUR_API_KEY -x YOUR_CSE_ID
    ./g-dorker.py -q "inurl:admin" -k YOUR_API_KEY -x YOUR_CSE_ID -t -c -b
    ./g-dorker.py -q "filetype:pdf" -k YOUR_API_KEY -x YOUR_CSE_ID -f results.txt -b
""")

    required = parser.add_argument_group('Required arguments')
    required.add_argument(
        "-q", "--query",
        required=True,
        help="Search query (Google dork string) or path to file with queries"
    )
    required.add_argument(
        "-k", "--api-key",
        required=True,
        help="Google Custom Search API key"
    )
    required.add_argument(
        "-x", "--cx",
        required=True,
        help="Google Custom Search Engine ID"
    )

    output = parser.add_argument_group('Output options')
    output.add_argument(
        "-f", "--file",
        help="Save results to file"
    )
    output.add_argument(
        "-t", "--title",
        action="store_true",
        help="Include page title"
    )

    content = parser.add_argument_group('Options that trigger additional request for each URL')
    content.add_argument(
        "-c", "--code",
        action="store_true",
        help="Include HTTP status codes"
    )
    content.add_argument(
        "-b", "--body",
        action="store_true",
        help="Include first 100 chars of page body"
    )

    args = parser.parse_args()
    f_options = {
        'title': args.title,
        'body': args.body,
        'code': args.code,
        'dest': args.file,
    }
    main(args.api_key, args.cx, args.query, f_options)
