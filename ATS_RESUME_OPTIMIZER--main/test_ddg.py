try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS  # legacy package name
import sys

try:
    with DDGS() as ddgs:
        results = list(ddgs.text("python programming", max_results=2))
        print(f"Success: {results}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
