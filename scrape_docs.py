import asyncio
import json
from playwright.async_api import async_playwright
from pathlib import Path


async def scrape_ticktick_docs_complete():
    """Complete scrape of TickTick API docs with expansion of all interactive elements."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        print("Navigating to TickTick Developer docs...")
        await page.goto(
            "https://developer.ticktick.com/docs/index.html#/openapi",
            wait_until="networkidle",
        )
        await page.wait_for_timeout(5000)

        print("Expanding all interactive elements...")

        # Click all expandable/collapsible elements
        clicked_count = 0
        for _ in range(5):  # Multiple rounds to catch nested elements
            expandable = await page.query_selector_all("""
                .opblock-summary, 
                .expand, 
                .collapse, 
                [class*="toggle"], 
                [class*="expand"],
                details,
                summary,
                button[class*="tab"],
                .tab,
                [role="tab"]
            """)

            for elem in expandable:
                try:
                    await elem.click()
                    clicked_count += 1
                    await asyncio.sleep(0.1)
                except:
                    pass

            await page.wait_for_timeout(500)

        print(f"Clicked {clicked_count} interactive elements")

        # Now thorough scrolling
        print("Thoroughly scrolling to load all content...")

        # Get initial measurements
        initial_height = await page.evaluate("document.body.scrollHeight")
        initial_text = await page.evaluate("document.body.innerText")
        print(f"Initial: height={initial_height}px, text={len(initial_text)} chars")

        # Scroll down in small increments
        scroll_position = 0
        scroll_step = 500
        max_scrolls = 200

        for i in range(max_scrolls):
            scroll_position += scroll_step
            await page.evaluate(f"window.scrollTo(0, {scroll_position})")
            await asyncio.sleep(0.3)

            current_height = await page.evaluate("document.body.scrollHeight")
            current_text = await page.evaluate("document.body.innerText")

            if i % 20 == 0:
                print(
                    f"  Scroll {i}: pos={scroll_position}, height={current_height}, text={len(current_text)}"
                )

            # Try clicking any new elements that appeared
            new_elements = await page.query_selector_all("""
                .opblock-summary:not([class*="is-open"]),
                .expand:not([class*="expanded"]),
                details:not([open])
            """)
            for elem in new_elements[:10]:  # Limit to avoid timeout
                try:
                    await elem.click()
                    await asyncio.sleep(0.1)
                except:
                    pass

            # Stop if we've scrolled past the content
            if scroll_position > current_height + 1000:
                print(f"  Reached end of content at scroll position {scroll_position}")
                break

        # Final measurements
        final_height = await page.evaluate("document.body.scrollHeight")
        final_text = await page.evaluate("document.body.innerText")
        print(f"\nFinal: height={final_height}px, text={len(final_text)} chars")
        print(f"Height change: {final_height - initial_height}px")
        print(f"Text change: {len(final_text) - len(initial_text)} chars")

        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)

        # Extract full content
        print("\nExtracting complete content...")

        content = await page.evaluate("""
            () => {
                const article = document.querySelector('article') || 
                               document.querySelector('.markdown-section') || 
                               document.querySelector('main') || 
                               document.body;
                
                // Get all text
                const text = article.innerText;
                
                // Get structured data
                const data = {
                    headings: Array.from(article.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(h => ({
                        level: h.tagName,
                        text: h.innerText.trim()
                    })),
                    
                    tables: Array.from(article.querySelectorAll('table')).map(table => ({
                        headers: Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim()),
                        rows: Array.from(table.querySelectorAll('tbody tr')).map(tr =>
                            Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim())
                        ).filter(row => row.length > 0)
                    })),
                    
                    codeBlocks: Array.from(article.querySelectorAll('pre, code')).map(block => ({
                        tag: block.tagName,
                        class: block.className,
                        content: block.innerText
                    })),
                    
                    endpoints: Array.from(article.querySelectorAll('*')).filter(el => 
                        el.innerText && (el.innerText.includes('GET /open/') || 
                        el.innerText.includes('POST /open/') ||
                        el.innerText.includes('PUT /open/') ||
                        el.innerText.includes('DELETE /open/'))
                    ).map(el => el.innerText.trim().split('\\n')[0]),
                    
                    links: Array.from(article.querySelectorAll('a[href]')).map(a => ({
                        text: a.innerText.trim(),
                        href: a.href
                    }))
                };
                
                return { text, data };
            }
        """)

        # Save plain text
        with open(docs_dir / "ticktick_api_docs.txt", "w", encoding="utf-8") as f:
            f.write(content["text"])

        # Save HTML
        html_content = await page.content()
        with open(docs_dir / "ticktick_api_docs.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        # Save structured JSON
        with open(docs_dir / "ticktick_api_docs.json", "w", encoding="utf-8") as f:
            json.dump(content["data"], f, indent=2)

        # Save markdown
        md_content = "# TickTick Open API Documentation\n\n"
        md_content += f"**Source:** https://developer.ticktick.com/docs#/openapi\n\n"
        md_content += "---\n\n"
        md_content += content["text"]

        with open(docs_dir / "ticktick_api_docs.md", "w", encoding="utf-8") as f:
            f.write(md_content)

        # Take screenshot
        await page.screenshot(
            path=str(docs_dir / "ticktick_docs_screenshot.png"), full_page=True
        )

        await browser.close()

        print("\nDone! Files saved:")
        for f in sorted(docs_dir.glob("ticktick_api_docs*")):
            size = f.stat().st_size
            if size > 1024 * 1024:
                print(f"  - {f.name} ({size / 1024 / 1024:.1f} MB)")
            elif size > 1024:
                print(f"  - {f.name} ({size / 1024:.1f} KB)")
            else:
                print(f"  - {f.name} ({size} bytes)")

        return content


if __name__ == "__main__":
    content = asyncio.run(scrape_ticktick_docs_complete())
    print(f"\nTotal text extracted: {len(content['text'])} characters")
    print(f"Headings: {len(content['data']['headings'])}")
    print(f"Tables: {len(content['data']['tables'])}")
    print(f"Code blocks: {len(content['data']['codeBlocks'])}")
    print(f"Endpoints found: {len(content['data']['endpoints'])}")
