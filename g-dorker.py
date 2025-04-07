import argparse
import json
import os
import time
import signal
from googleapiclient.discovery import build
from colorama import init, Fore

init(autoreset=True)

class GoogleSearch:
    def __init__(self, api_key, cse_id, output_file, limit=100, session_file='session.json'):
        self.api_key = api_key
        self.cse_id = cse_id
        self.limit = limit
        self.requests_today = 0
        self.session_file = session_file
        self.offset = 1
        self.output_file = output_file

    def google_search(self, query, start=0, num=10):
        service = build("customsearch", "v1", developerKey=self.api_key)
        try:
            res = service.cse().list(q=query, cx=self.cse_id, start=start, num=num).execute()
            return res.get('items', [])
        except Exception as e:
            print(e)
            return []

    def check_limit(self):
        if self.requests_today >= self.limit:
            print(f"{Fore.BLUE}[INFO] Rate limit reached for today. Saving session to {self.session_file}...")
            self.save_session()
            return False
        return True

    def save_session(self):
        session_data = {
            'requests_today': self.requests_today,
            'offset': self.offset,
            'timestamp': time.time()
        }
        with open(self.session_file, 'w') as f:
            json.dump(session_data, f)

    def load_session(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
                self.requests_today = session_data.get('requests_today', 0)
                self.offset = session_data.get('offset', 1)
                timestamp = session_data.get('timestamp', 0)
                if time.time() - timestamp > 86400 or self.requests_today < self.limit:
                    print(f"{Fore.RED}[INFO] Continue from saved session")
                    return True
                else:
                    print(f"{Fore.RED}[INFO] Cannot resume. Less than 24 hours since the last session and rate limit not reached.")
                    return False
        return True

    def print_results(self, results, show_title):
        with open(self.output_file, "a") as f:
            if not results:
                print(f"{Fore.RED}[INFO] No more results found.")
                return False
            for result in results:
                url = result['link']
                output = f"{Fore.BLUE}[URL] {Fore.GREEN}[{url}]"
                if show_title:
                    output = f"{Fore.BLUE}[URL] {Fore.GREEN}[{url}] {Fore.MAGENTA}[{result['title']}]"
                print(output)
                print(output, file=f)
            return True

    def query_results(self, query, show_title):
        start = self.offset
        while self.check_limit():
            print(f"{Fore.BLUE}[INFO] Offset {self.offset}")
            results = self.google_search(query, start=start)
            if not self.print_results(results, show_title):
                break
            self.requests_today += 1
            self.offset = start + 10
            start += 10
            time.sleep(1)
        print(f"{Fore.BLUE}[INFO] Total requests made today: {self.requests_today}")

def handle_exit_signal(google_search, signum, frame):
    print(f"{Fore.RED}[INFO] Interrupted by user (Ctrl+C). Saving session...")
    google_search.save_session()
    exit(0)

def main(api_key, cse_id, query, limit, show_title, file):
    google_search = GoogleSearch(api_key, cse_id, file, limit)
    if google_search.load_session():
        signal.signal(signal.SIGINT, lambda signum, frame: handle_exit_signal(google_search, signum, frame))
        google_search.query_results(query, show_title)
    else:
        print(f"{Fore.RED}[INFO] Session is too recent or rate limit not reached. Exiting.")

if __name__ == "__main__":
    print("""
⠀⠀⣠⣶⣶⣦⣤⡄⠀⠀⠀⠀⠀⠀⠀⢠⣤⣤⣤⣀⣀⡀⠀⠀⠀⠀⣠⣤⣤⣤⣄⠀⠀⠀⣤⣤⣤⣤⣤⣀⡀⠀⠀⣀⣀⣤⡀⢠⣤⣤⣤⠀⣀⣀⣀⣤⣤⣤⣤⡄⠀⢠⣤⣤⣤⣤⣄⣀⠀⠀
⠀⣼⡟⠁⠀⠉⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⠉⠙⠻⣷⡄⠀⠀⣼⡿⠁⠀⠀⢻⡆⠀⠀⠘⣿⠀⠀⠈⢹⣷⠀⠀⠈⢿⡏⠀⣨⡿⠋⠀⠀⠈⣿⡏⠉⢉⠙⣿⡇⠀⠀⢻⡏⠀⠀⠉⣻⡇⠀
⠀⣿⡇⠀⢠⣦⣼⣷⣦⠄⠀⠀⠀⠀⠀⠀⢸⣧⠀⠀⠀⠸⣷⠀⠀⣿⠇⠀⠀⠀⠀⣿⠀⠀⠀⣿⡶⠶⣾⡟⠁⠀⠀⠀⢸⣀⣴⣿⡀⠀⠀⠀⠀⢸⣷⣶⣿⡇⠈⠀⠀⠀⠸⣷⠶⢶⣾⠟⠀⠀
⠀⢺⣇⠀⠀⠀⢹⣿⠀⠸⠿⠿⠾⠿⠗⠀⢘⣿⠀⠀⠀⢠⡿⠀⠀⣿⡆⠀⠀⠀⢠⡟⠀⠀⠀⢹⡁⠀⢸⣧⠀⠀⠀⠀⢸⠟⠁⠙⢷⡀⠀⠀⠀⢸⡇⠀⠙⠃⢠⣤⠀⠀⠀⣏⠀⠀⢻⣆⠀⠀
⠀⠈⠻⣷⣶⣴⣿⡿⠀⠀⠀⠀⠀⠀⠀⣤⣼⣿⣤⣠⣴⠿⠁⠀⠀⠘⠿⣦⣤⣤⠟⠀⠀⠀⢠⣿⣧⣄⢀⣿⣷⣤⠀⣠⣽⣄⡀⢀⣠⣷⣤⠀⣠⣿⣷⣤⣴⣴⣾⣿⠀⠀⢴⣿⣦⡀⣸⣿⣦⡄
""")
    parser = argparse.ArgumentParser(description="g-dorker")
    parser.add_argument("-q", "--query", required=True, help="Search query")
    parser.add_argument("-k", "--api-key", required=True, help="API key for Google Custom Search")
    parser.add_argument("-x", "--cx", required=True, help="Custom Search Engine ID")
    parser.add_argument("-t", "--title", action="store_true", help="Print page title after the URL")
    parser.add_argument("-r", "--limit", type=int, default=100, help="Daily limit of API requests (default: 100)")
    parser.add_argument("-f", "--file", default="output.txt", help="Output file")
    #parser.add_argument("-u", "--unique", type=bool, help="Unique")


    args = parser.parse_args()
    main(args.api_key, args.cx, args.query, args.limit, args.title, args.file)
