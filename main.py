import json
import os
import asyncio
import aiohttp
from typing import List, Tuple, Optional
from dataclasses import dataclass

INPUT_FILE = "./plugin.json"
OUTPUT_FILE = "filtered_plugin.json"
TIMEOUT = 5  # seconds
CONCURRENCY = 10  # max concurrent requests


@dataclass
class Plugin:
    """
    Represents a plugin with a 'name' and 'url'.
    """
    name: str
    url: str
    version: str


async def is_url_valid(session: aiohttp.ClientSession, plugin: Plugin) -> tuple[bool, Plugin, Optional[str]]:
    """

    Returns:
        A tuple (is_valid: bool, plugin: Plugin, err: Optional[str]).
    """

    try:
        async with session.head(plugin.url, timeout=TIMEOUT, allow_redirects=True) as response:
            if 200 <= response.status < 300:
                return True, plugin, None
            return False, plugin, f"HTTP {response.status}"
    except Exception as e:
        return False, plugin, str(e)


async def main() -> None:
    """
    Filters the plugins in the input file and writes the result to an output file. 
    Concurrently checks URLs and saves valid plugins.
    """
    os.makedirs('./dist', exist_ok=True)

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)

    valid_plugins: List[Plugin] = []
    invalid_plugins: List[Tuple[str, str, str]] = []

    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        data = json.load(infile)
    # Perform URL validation concurrently
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        results = await asyncio.gather(
            *[is_url_valid(session, Plugin(**plugin_dict)) for plugin_dict in data.get("plugins", [])])

        for is_valid, plugin, reason in results:
            if is_valid:
                valid_plugins.append(plugin)
            else:
                invalid_plugins.append((plugin.name, plugin.url, reason))

    # Write valid plugins to output file

    with open(f'./dist/{OUTPUT_FILE}', "w", encoding="utf-8") as outfile:
        json.dump(
            {
                "desc": data.get("desc", ""),
                "plugins": [plugin.__dict__ for plugin in valid_plugins]
            },
            outfile,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n✅ Valid plugins: {len(valid_plugins)}")

    if invalid_plugins:
        print(f"❌ Invalid plugins: {len(invalid_plugins)}")
        print("List of invalid plugins:")
        for name, url, reason in invalid_plugins:
            print(f"- [{name}] {url} — {reason}")


if __name__ == "__main__":
    asyncio.run(main())
