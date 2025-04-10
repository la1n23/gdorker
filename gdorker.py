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

banner = """
⠀⠀⣠⣶⣶⣦⣤⡄⠀⠀⠀⠀⠀⠀⠀⢠⣤⣤⣤⣀⣀⡀⠀⠀⠀⠀⣠⣤⣤⣤⣄⠀⠀⠀⣤⣤⣤⣤⣤⣀⡀⠀⠀⣀⣀⣤⡀⢠⣤⣤⣤⠀⣀⣀⣀⣤⣤⣤⣤⡄⠀⢠⣤⣤⣤⣤⣄⣀⠀⠀
⠀⣼⡟⠁⠀⠉⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⠉⠙⠻⣷⡄⠀⠀⣼⡿⠁⠀⠀⢻⡆⠀⠀⠘⣿⠀⠀⠈⢹⣷⠀⠀⠈⢿⡏⠀⣨⡿⠋⠀⠀⠈⣿⡏⠉⢉⠙⣿⡇⠀⠀⢻⡏⠀⠀⠉⣻⡇⠀
⠀⣿⡇⠀⢠⣦⣼⣷⣦⠄⠀⠀⠀⠀⠀⠀⢸⣧⠀⠀⠀⠸⣷⠀⠀⣿⠇⠀⠀⠀⠀⣿⠀⠀⠀⣿⡶⠶⣾⡟⠁⠀⠀⠀⢸⣀⣴⣿⡀⠀⠀⠀⠀⢸⣷⣶⣿⡇⠈⠀⠀⠀⠸⣷⠶⢶⣾⠟⠀⠀
⠀⢺⣇⠀⠀⠀⢹⣿⠀⠸⠿⠿⠾⠿⠗⠀⢘⣿⠀⠀⠀⢠⡿⠀⠀⣿⡆⠀⠀⠀⢠⡟⠀⠀⠀⢹⡁⠀⢸⣧⠀⠀⠀⠀⢸⠟⠁⠙⢷⡀⠀⠀⠀⢸⡇⠀⠙⠃⢠⣤⠀⠀⠀⣏⠀⠀⢻⣆⠀⠀
⠀⠈⠻⣷⣶⣴⣿⡿⠀⠀⠀⠀⠀⠀⠀⣤⣼⣿⣤⣠⣴⠿⠁⠀⠀⠘⠿⣦⣤⣤⠟⠀⠀⠀⢠⣿⣧⣄⢀⣿⣷⣤⠀⣠⣽⣄⡀⢀⣠⣷⣤⠀⣠⣿⣷⣤⣴⣴⣾⣿⠀⠀⢴⣿⣦⡀⣸⣿⣦⡄
                               
                               By La1n

"""

class Formatter:
    def __init__(self, options):
        self.options = options
        self.is_extended = any([self.options['code'], self.options['body']])
        pass
    def _title(self, title: str) -> str:
        return f"{Fore.MAGENTA}[{title}]"
    def _url(self, url: str) -> str:
        return f"{Fore.GREEN}[{url}]"
    def _code(self, code: int) -> str:
        color = Fore.WHITE
        if code >= 200 and code < 300:
            color = Fore.GREEN
        elif code >= 300 and code < 400:
            color = Fore.YELLOW
        elif code >= 400 and code < 600:
            color = Fore.RED
        return f"{color}[{code}]"
    def _body(self, html: str) -> str:
        soup = BeautifulSoup(html,'html.parser')
        body = soup.body.get_text() if soup.body else ""
        text = re.sub(r'[\s]+', " ", body).strip()[0:100]
        return f"{Fore.CYAN}[{text}]"

    def debug(self, info: str) -> str:
        return f"{Fore.LIGHTBLACK_EX}[DEBUG] {info}"
    def info(self, info: str) -> str:
        return f"{Fore.BLUE}[INFO] {info}"
    def error(self, error: str) -> str:
        return f"{Fore.RED}[ERROR] {error}"
    def _result(self, info: str) -> str:
        return f"{Fore.BLUE}[URL] {info}"
    def result(self, pieces: Dict[str, str]):
        output = [self._url(pieces["url"])]

        if self.options['code']:
            output.append(self._code(pieces["code"]))
        if self.options['title']:
            output.append(self._title(pieces['title']))
        if self.options['body']:
            output.append(self._body(pieces["body"]))
        return self._result(' '.join(output))


class Logger:
    def __init__(self, options: Dict[str, Any]) -> None:
        self.dest = options['dest']
        self.debug_enabled = options['debug']
        self.formatter = Formatter(options)
        if self.dest and isinstance(self.dest, str):
            self.dest = open(self.dest, 'a')

    def _write(self, line: str) -> None:
        print(line)

    def url(self, pieces: Dict[str, str]) -> None:
        line = self.formatter.result(pieces)
        self._write(line)
        if self.dest:
            print(line, file=self.dest)

    def info(self, info: str) -> None:
        line = self.formatter.info(info)
        self._write(line)

    def error(self, error: str) -> None:
        line = self.formatter.error(error)
        self._write(line)

    def debug(self, info: str) -> None:
        if not self.debug_enabled:
            return
        line = self.formatter.debug(info)
        self._write(line)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.dest:
            self.dest.close()


class Dorker:
    per_page = 10

    def __init__(self, logger: Logger, api_key: str, cse_id: str) -> None:
        self.logger = logger
        self.api_key = api_key
        self.cse_id = cse_id
        self.offset: int = 0
        self.is_limit_reached = False
        self.client = lambda q, cx, start, num: build("customsearch", "v1", developerKey=self.api_key).cse().list(q=q, cx=cx, start=start, num=num).execute()

    @property
    def _page(self) -> int:
        return self.offset // self.per_page + 1

    def _search(self, query: str, start: int = 0) -> List[Dict[str, Any]]:
        try:
            res = self.client(query, self.cse_id, start, self.per_page)
            items = res.get('items')
            return items
        except Exception as e:
            try:
                self.logger.debug(e)
                error_content = json.loads(e.content)
                #print(json.dumps(error_content, indent=4))
                if error_content['error']['status'] == 'RESOURCE_EXHAUSTED':
                    self.logger.info("Resource limit reached. Please try again in 24h")
                    self.is_limit_reached = True
                else:
                    self.logger.error(e.content)
            except json.JSONDecodeError:
                self.logger.error(e.content)
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
            self.logger.url(pieces)

    def query_results(self, query: str, offset: int | None) -> None:
        if offset is None:
            offset = 0
        self.offset: int = offset
        self.query = query
        while not self.is_limit_reached:
            self.logger.info(f"Page {self._page}")
            results = self._search(query, start=self.offset)
            self._print_results(results)
            if not results:
                break
            self.offset = self.offset + self.per_page
            time.sleep(1)

class Session():
    """
    todo: save data inside session class and pass it google search
    """
    def __init__(self, file):
        self.file = file

    def load(self):
        with open(self.file, "r") as f:
            j = json.loads(f.read())
            return j

    def clean(self):
        os.remove(self.file)

    def save(self, api_key, cse_id, file_or_query, logger: Logger, gs: Dorker):
        session = {
            'api_key': api_key,
            'cse_id': cse_id,
            'file_or_query': file_or_query,
            'options': logger.formatter.options,
            'current_query': gs.query,
            'offset': gs.offset
        }
        j = json.dumps(session, indent=2)
        with open(self.file, 'w') as f:
            f.write(j)    

def handle_exit_signal(session, api_key, cse_id, file_or_query, logger: Logger, gs: Dorker) -> NoReturn:
    logger.info("Interrupted by user, saving session...")
    session.save(api_key, cse_id, file_or_query, logger, gs)
    exit(0)

def load_queries(file_or_query: str) -> list[str]:
    try:
        with open(file_or_query, 'r') as f:
            queries = f.readlines()
            unique = list(set(queries))
            return queries
    except Exception as e:
        return [file_or_query]


def main(api_key: str, cse_id: str, file_or_query: str, resume: bool, session, options) -> None:
    """
    todo: take api keys form config file
    todo: async requests
    """
    current_query = None
    offset = None
    session = Session(session)
    if resume:
        data = session.load()
        api_key = data['api_key']
        cse_id = data['cse_id']
        file_or_query = data['file_or_query']
        options = data['options']
        offset = data['offset']
        current_query = data['current_query']

    logger = Logger(options)
    google_search = Dorker(logger, api_key, cse_id)

    queries = load_queries(file_or_query)
    if current_query:
        index = next((i for i, q in enumerate(queries) if q == current_query), len(queries))
        queries = queries[index:]

    signal.signal(signal.SIGINT, lambda signum, frame: handle_exit_signal(session, api_key, cse_id, file_or_query, logger, google_search))
    for query in queries:
        logger.info(f"Query: {query}")
        google_search.query_results(query, offset)
        if google_search.is_limit_reached:
            session.save(api_key, cse_id, file_or_query, logger, google_search)
            exit(1)
    session.clean()

if __name__ == "__main__":
    print(banner)
    parser = argparse.ArgumentParser(
        description="""
G-Dorker - Google Custom Search Engine Dorking Tool

A tool for performing Google dorks using Custom Search Engine API.
Allows saving results to file and extracting additional information from URLs.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ./gdorker.py -q "site:example.com" -k YOUR_API_KEY -x YOUR_CSE_ID
    ./gdorker.py -q "inurl:admin" -k YOUR_API_KEY -x YOUR_CSE_ID -t -c -b
    ./gdorker.py -q "filetype:pdf" -k YOUR_API_KEY -x YOUR_CSE_ID -f results.txt -b
    ./gdorker.py -q ./bb_dorks.txt -k YOUR_API_KEY -x YOUR_CSE_ID -f results.txt -b
    ./gdorker.py -q ./bb_dorks.txt -k YOUR_API_KEY -x YOUR_CSE_ID -f results.txt --session ./g_dorker_session_1744260850.json
""")

    required = parser.add_argument_group('Required arguments')
    required.add_argument(
        "-q", "--query",
        help="Search query (Google dork string) or path to file with queries"
    )
    required.add_argument(
        "-k", "--api-key",
        help="Google Custom Search API key"
    )
    required.add_argument(
        "-x", "--cx",
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
    output.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Debug output"
    )
    output.add_argument(
        "-s", "--session",
        help="Resume from"
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
    options = {
        'title': args.title,
        'body': args.body,
        'code': args.code,
        'dest': args.file,
        'debug': args.debug
    }
    if args.debug:
        print(dir(Fore))

    session = args.session
    resume = bool(session)
    if not session:
        session = f"g_dorker_session_{int(time.time())}.json"
    main(args.api_key, args.cx, args.query, resume, session, options)
