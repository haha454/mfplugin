import json
import os
import asyncio
import aiohttp
from typing import List, Tuple, Optional
from dataclasses import dataclass

INPUT_FILE = "./plugin.json"
OUTPUT_FILE = "output/filtered_plugin.json"
TIMEOUT = 5  # seconds
CONCURRENCY = 10  # max concurrent requests

@dataclass
class Plugin:
    """
    Represents a plugin with a 'name' and 'url'.
    """
    name: str
    url: str

async def is_url_valid(session: aiohttp.ClientSession, plugin: Plugin) -> tuple[bool, Plugin, Optional[str]]:
    """
    Check if the URL in the plugin is valid (returns a 2xx HTTP status).
    
    Args:
        session: aiohttp session to perform requests.
        plugin: A Plugin object with a 'url' and possibly a 'name'.
        
    Returns:
        A tuple (is_valid: bool, plugin: Plugin, reason: Optional[str]).
    """

    if not url:
        return False, plugin, "Missing URL field"

    try:
        async with session.head(plugin.url, timeout=TIMEOUT, allow_redirects=True) as response:
            if 200 <= response.status < 300:
                return True, plugin, None
            return False, plugin, f"HTTP {response.status}"
    except Exception as e:
        return False, plugin, str(e)

async def filter_plugins_async() -> None:
    """
    Filters the plugins in the input file and writes the result to an output file. 
    Concurrently checks URLs and saves valid plugins.
    """
    os.makedirs("output", exist_ok=True)

    # Load plugins from the input JSON file
    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        data = json.load(infile)
    plugins: List[Plugin] = [Plugin(**plugin) for plugin in data.get("plugins", [])]

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)

    valid_plugins: List[Plugin] = []
    invalid_plugins: List[Tuple[str, str, str]] = []

    # Perform URL validation concurrently
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [is_url_valid(session, plugin) for plugin in plugins]
        results = await asyncio.gather(*tasks)

        for is_valid, plugin, reason in results:
            if is_valid:
                valid_plugins.append(plugin)
            else:
                name = plugin.name or "unknown"
                url = plugin.url or "no-url"
                invalid_plugins.append((name, url, reason))

    # Write valid plugins to output file
    filtered_data = {
        "desc": data.get("desc", ""),
        "plugins": [plugin.__dict__ for plugin in valid_plugins]
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        json.dump(filtered_data, outfile, indent=2, ensure_ascii=False)

    # Print invalid plugin details to stdout
    print(f"\n✅ Valid plugins: {len(valid_plugins)}")
    print(f"❌ Invalid plugins: {len(invalid_plugins)}\n")

    if invalid_plugins:
        print("List of invalid plugins:")
        for name, url, reason in invalid_plugins:
            print(f"- [{name}] {url} — {reason}")

def main() -> None:
    """
    Entry point of the script, runs the filtering process asynchronously.
    """
    asyncio.run(filter_plugins_async())

if __name__ == "__main__":
    main()

