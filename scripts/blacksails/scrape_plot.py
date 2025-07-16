import requests
from bs4 import BeautifulSoup
import json


def int_to_roman(num):
    """Converts an integer to a Roman numeral for URL generation."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num


def scrape_episode_data(episode_numeral):
    """
    Scrapes the synopsis, quotes, and trivia for a single episode.
    """
    url = f"https://black-sails.fandom.com/wiki/{episode_numeral}."
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", class_="mw-parser-output")

    if not content:
        print(f"Could not find main content for Episode {episode_numeral}")
        return None

    episode_data = {"synopsis": "", "memorable_quotes": [], "trivia": []}

    # --- Extract Synopsis ---
    synopsis_header = content.find("span", id="Synopsis")
    if synopsis_header:
        # Iterate through siblings until the next h2 tag is found
        for sibling in synopsis_header.find_parent("h2").find_next_siblings():
            if sibling.name == "h2":
                break
            if sibling.name == "p":
                episode_data["synopsis"] += sibling.get_text(strip=True) + "\n\n"

    # --- Extract Memorable Quotes ---
    quotes_header = content.find("span", id="Memorable_Quotes")
    if quotes_header:
        for sibling in quotes_header.find_parent("h2").find_next_siblings():
            if sibling.name == "h2":
                break
            if sibling.name == "dl":  # Quotes are in <dl> tags
                quote = sibling.get_text(strip=True, separator="\n").strip()
                episode_data["memorable_quotes"].append(quote)

    # --- Extract Trivia ---
    trivia_header = content.find("span", id="Trivia")
    if trivia_header:
        # The trivia is usually in the first <ul> after the header
        ul_tag = trivia_header.find_parent("h2").find_next_sibling("ul")
        if ul_tag:
            for li in ul_tag.find_all(
                "li", recursive=False
            ):  # Get only top-level list items
                episode_data["trivia"].append(li.get_text(strip=True))

    return episode_data


def main():
    """
    Main function to scrape all 38 episodes and print the combined data.
    """
    all_episodes_data = {}
    print("Starting Black Sails wiki scrape...")

    for i in range(1, 39):
        episode_numeral = int_to_roman(i)
        print(f"Scraping data for Episode {episode_numeral}...")
        data = scrape_episode_data(episode_numeral)
        if data:
            all_episodes_data[episode_numeral] = data

    print("\nScraping complete.")

    # Save to a file
    file_path = "black_sails_lore.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(all_episodes_data, f, indent=2, ensure_ascii=False)

    print(f"All episode data saved to {file_path}")

    # You can also print it to the console if you prefer
    # print("\n--- Compiled Data ---")
    # print(json.dumps(all_episodes_data, indent=2))


if __name__ == "__main__":
    main()
