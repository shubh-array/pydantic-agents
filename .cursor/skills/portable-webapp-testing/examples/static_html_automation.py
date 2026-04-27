from pathlib import Path
import os

from playwright.sync_api import sync_playwright


output_dir = Path(os.environ.get("OUTPUT_DIR", "./test-results"))
output_dir.mkdir(parents=True, exist_ok=True)

html_file_path = Path("path/to/your/file.html").resolve()
file_url = html_file_path.as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    page.goto(file_url)
    page.screenshot(path=str(output_dir / "static_page.png"), full_page=True)

    page.click("text=Click Me")
    page.fill("#name", "John Doe")
    page.fill("#email", "john@example.com")
    page.click('button[type="submit"]')
    page.wait_for_timeout(500)

    page.screenshot(path=str(output_dir / "after_submit.png"), full_page=True)
    browser.close()

print(f"Static HTML automation completed. Outputs saved to {output_dir}")
