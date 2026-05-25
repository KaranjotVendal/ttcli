from bs4 import BeautifulSoup
from pathlib import Path
import json
import re


def extract_api_structure():
    html_path = Path("docs/ticktick_api_docs.html")

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup.find("main") or soup.find("body")

    structure = {
        "title": "TickTick Open API Documentation",
        "source": "https://developer.ticktick.com/docs#/openapi",
        "sections": [],
    }

    current_section = None
    current_group = None
    current_endpoint = None

    for elem in article.find_all(["h2", "h3", "h4", "h5", "pre", "table", "p"]):
        if elem.name == "h2":
            current_section = {
                "type": "section",
                "title": elem.get_text(strip=True),
                "content": [],
            }
            structure["sections"].append(current_section)
            current_group = None
            current_endpoint = None

        elif elem.name == "h3" and current_section:
            current_group = {
                "type": "endpoint_group",
                "title": elem.get_text(strip=True),
                "endpoints": [],
            }
            current_section["content"].append(current_group)
            current_endpoint = None

        elif elem.name == "h4" and current_group:
            current_endpoint = {
                "type": "endpoint",
                "title": elem.get_text(strip=True),
                "method": None,
                "path": None,
                "parameters": [],
                "responses": [],
                "examples": [],
            }
            current_group["endpoints"].append(current_endpoint)

        elif elem.name == "pre" and current_endpoint:
            code = elem.find("code")
            if code:
                text = code.get_text(strip=True)
                # Check if it's an HTTP method + path
                match = re.match(r"(GET|POST|PUT|DELETE|PATCH)\s+(.+)", text)
                if match:
                    current_endpoint["method"] = match.group(1)
                    current_endpoint["path"] = match.group(2).strip()
                elif text.startswith("http") or text.startswith("{"):
                    current_endpoint["examples"].append(text)

        elif elem.name == "table" and current_endpoint:
            # Determine if it's parameters or responses
            prev_heading = elem.find_previous(["h5", "h6"])
            if prev_heading:
                heading_text = prev_heading.get_text(strip=True).lower()

                if "parameter" in heading_text:
                    # Parse parameters table
                    thead = elem.find("thead")
                    tbody = elem.find("tbody")
                    if thead and tbody:
                        headers = [
                            th.get_text(strip=True) for th in thead.find_all("th")
                        ]
                        for tr in tbody.find_all("tr"):
                            cells = [
                                td.get_text(strip=True) for td in tr.find_all("td")
                            ]
                            if cells:
                                param = {}
                                for i, header in enumerate(headers):
                                    if i < len(cells):
                                        param[header.lower()] = cells[i]
                                if param:
                                    current_endpoint["parameters"].append(param)

                elif "response" in heading_text:
                    # Parse responses table
                    thead = elem.find("thead")
                    tbody = elem.find("tbody")
                    if thead and tbody:
                        headers = [
                            th.get_text(strip=True) for th in thead.find_all("th")
                        ]
                        for tr in tbody.find_all("tr"):
                            cells = [
                                td.get_text(strip=True) for td in tr.find_all("td")
                            ]
                            if cells:
                                response = {}
                                for i, header in enumerate(headers):
                                    if i < len(cells):
                                        response[header.lower()] = cells[i]
                                if response:
                                    current_endpoint["responses"].append(response)

    # Save JSON
    with open("docs/ticktick_api_docs.json", "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2)

    print(f"JSON structure saved with {len(structure['sections'])} sections")

    # Count endpoints
    endpoint_count = 0
    for section in structure["sections"]:
        for item in section.get("content", []):
            if item.get("type") == "endpoint_group":
                endpoint_count += len(item.get("endpoints", []))

    print(f"Total endpoints: {endpoint_count}")

    return structure


if __name__ == "__main__":
    extract_api_structure()
