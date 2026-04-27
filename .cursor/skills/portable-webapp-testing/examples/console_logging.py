from pathlib import Path
import os

from playwright.sync_api import sync_playwright


url = "http://localhost:5173"
output_dir = Path(os.environ.get("OUTPUT_DIR", "./test-results"))
output_dir.mkdir(parents=True, exist_ok=True)
console_logs: list[str] = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    def handle_console_message(msg):
        line = f"[{msg.type}] {msg.text}"
        console_logs.append(line)
        print(f"Console: {line}")

    page.on("console", handle_console_message)
    page.goto(url)
    page.wait_for_load_state("networkidle")

    # Trigger logs caused by interaction when a matching control exists.
    if page.get_by_text("Dashboard").count() > 0:
        page.get_by_text("Dashboard").first.click()

    page.wait_for_timeout(1000)
    browser.close()

log_path = output_dir / "console.log"
log_path.write_text("\n".join(console_logs), encoding="utf-8")

print(f"\nCaptured {len(console_logs)} console messages")
print(f"Logs saved to: {log_path}")
