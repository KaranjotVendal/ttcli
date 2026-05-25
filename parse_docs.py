from bs4 import BeautifulSoup
from pathlib import Path
import re


def parse_ticktick_docs():
    html_path = Path("docs/ticktick_api_docs.html")

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # Find the main article content
    article = (
        soup.find("article")
        or soup.find(class_="markdown-section")
        or soup.find("main")
    )
    if not article:
        print("Could not find article element, using body")
        article = soup.find("body")

    def process_table(table):
        """Convert HTML table to markdown table."""
        rows = []

        # Header
        thead = table.find("thead")
        if thead:
            headers = []
            for th in thead.find_all("th"):
                headers.append(th.get_text(strip=True))
            if headers:
                rows.append("| " + " | ".join(headers) + " |")
                rows.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Body
        tbody = table.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                cells = []
                for td in tr.find_all("td"):
                    # Process the cell content to preserve inline formatting
                    cell_text = process_element(td, level=0)
                    # Clean up excessive whitespace
                    cell_text = " ".join(cell_text.split())
                    cells.append(cell_text)
                if cells:
                    rows.append("| " + " | ".join(cells) + " |")

        if rows:
            return "\n" + "\n".join(rows) + "\n\n"
        return ""

    def process_element(elem, level=0):
        """Recursively process HTML elements."""
        if elem.name is None:
            # Text node
            text = str(elem)
            return text

        if elem.name in ["script", "style", "nav", "aside"]:
            return ""

        # Handle table directly
        if elem.name == "table":
            return process_table(elem)

        # Process children first
        children_text = []
        for child in elem.children:
            child_result = process_element(child, level + 1)
            if child_result is not None:
                children_text.append(child_result)

        content = "".join(children_text)
        # For block-level elements, strip leading/trailing whitespace
        # For inline elements, preserve whitespace
        if elem.name in [
            "p",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "td",
            "th",
        ]:
            content = content.strip()

        if elem.name == "h1":
            return f"\n# {content}\n\n"
        elif elem.name == "h2":
            return f"\n## {content}\n\n"
        elif elem.name == "h3":
            return f"\n### {content}\n\n"
        elif elem.name == "h4":
            return f"\n#### {content}\n\n"
        elif elem.name == "h5":
            return f"\n##### {content}\n\n"
        elif elem.name == "h6":
            return f"\n###### {content}\n\n"
        elif elem.name == "p":
            return f"{content}\n\n"
        elif elem.name == "pre":
            # Code block
            code = elem.find("code")
            if code:
                lang = (
                    code.get("class", [""])[0]
                    .replace("lang-", "")
                    .replace("language-", "")
                    if code.get("class")
                    else ""
                )
                code_text = code.get_text()
                return f"\n```{lang}\n{code_text}\n```\n\n"
            else:
                return f"\n```\n{content}\n```\n\n"
        elif elem.name == "code":
            # Inline code - wrap with spaces to prevent word merging
            if content:
                return f" `{content}` "
            return ""
        elif elem.name == "a":
            href = elem.get("href", "")
            if href.startswith("http") or href.startswith("#"):
                return f" [{content}]({href}) "
            return f" {content} "
        elif elem.name == "strong" or elem.name == "b":
            return f" **{content}** "
        elif elem.name == "em" or elem.name == "i":
            return f" *{content}* "
        elif elem.name == "br":
            return "\n"
        elif elem.name == "ul":
            items = []
            for li in elem.find_all("li", recursive=False):
                li_text = process_element(li, level).strip()
                if li_text:
                    items.append(f"- {li_text}")
            return "\n".join(items) + "\n\n" if items else ""
        elif elem.name == "ol":
            items = []
            for i, li in enumerate(elem.find_all("li", recursive=False), 1):
                li_text = process_element(li, level).strip()
                if li_text:
                    items.append(f"{i}. {li_text}")
            return "\n".join(items) + "\n\n" if items else ""
        elif elem.name == "li":
            return content
        elif elem.name == "div":
            return content
        elif elem.name == "span":
            return content
        else:
            return content

    # Process the article
    result = process_element(article)

    # Clean up the markdown
    result = re.sub(r"\n{3,}", "\n\n", result)  # Remove excessive newlines
    result = result.strip()

    # Fix excessive spaces
    result = re.sub(r" +", " ", result)  # Multiple spaces to single space
    result = re.sub(r" \n", "\n", result)  # Remove spaces before newlines
    result = re.sub(r"\n ", "\n", result)  # Remove spaces after newlines

    # Fix spacing around inline elements (be careful not to break markdown syntax)
    result = re.sub(r"(?<=[a-zA-Z.,;:!?])\[(?!\s)", " [", result)  # Space before link

    # Remove anchor-only links (links that just point to anchors on the same page)
    result = re.sub(r"\[([^\]]+)\]\(#/[^)]+\)", r"\1", result)

    # Add header
    md_content = f"""# TickTick Open API Documentation

**Source:** https://developer.ticktick.com/docs#/openapi

---

{result}
"""

    # Save markdown
    with open("docs/ticktick_api_docs.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    # Generate plain text version
    txt_content = re.sub(r"#{1,6}\s+", "", md_content)  # Remove markdown headings
    txt_content = re.sub(r"\*\*", "", txt_content)  # Remove bold
    txt_content = re.sub(r"\*", "", txt_content)  # Remove italic
    txt_content = re.sub(r"`", "", txt_content)  # Remove code backticks
    txt_content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", txt_content)  # Remove links
    txt_content = re.sub(r"```\w*\n", "\n", txt_content)  # Remove code block starts
    txt_content = re.sub(r"```\n", "\n", txt_content)  # Remove code block ends
    txt_content = re.sub(r"\|", " | ", txt_content)  # Add spacing to table cells
    txt_content = re.sub(r"---", "-", txt_content)  # Simplify separators
    txt_content = re.sub(r"\n{3,}", "\n\n", txt_content)
    txt_content = txt_content.strip()

    with open("docs/ticktick_api_docs.txt", "w", encoding="utf-8") as f:
        f.write(txt_content)

    print(f"Markdown saved: {len(md_content)} chars")
    print(f"Text saved: {len(txt_content)} chars")


if __name__ == "__main__":
    parse_ticktick_docs()
