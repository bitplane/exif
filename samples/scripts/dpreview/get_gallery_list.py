#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def fetch_all_galleries():
    """Fetch all gallery links from dpreview sample galleries page"""
    galleries = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Run in headless mode
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        await page.goto('https://m.dpreview.com/sample-galleries?category=all&sort=chronologically', wait_until='domcontentloaded')
        
        # Try to dismiss GDPR popup if present
        try:
            # Look for common GDPR popup dismiss buttons
            await page.wait_for_selector('[data-testid="accept-all"], .accept-all, .gdpr-accept, .cookie-accept', timeout=3000)
            await page.click('[data-testid="accept-all"], .accept-all, .gdpr-accept, .cookie-accept')
            await page.wait_for_timeout(1000)
        except:
            # No popup or couldn't find dismiss button, continue
            pass
        
        # Wait for the gallery table to load
        await page.wait_for_selector('tr.gallery', timeout=10000)
        
        # Extract gallery rows from the table
        galleries = await page.evaluate('''
            () => {
                const rows = document.querySelectorAll('tr.gallery');
                if (rows.length === 0) {
                    throw new Error('No tr.gallery elements found on page');
                }
                
                return Array.from(rows).map(row => {
                    const link = row.querySelector('td.title a');
                    if (!link) {
                        throw new Error('No link found in gallery row');
                    }
                    
                    return {
                        url: link.href,
                        title: link.textContent.trim()
                    };
                });
            }
        ''')
        
        await browser.close()
        
    return galleries

async def main():
    try:
        galleries = await fetch_all_galleries()
        
        if not galleries:
            print("Error: No galleries found", file=sys.stderr)
            return 1
        
        # Output in TSV format: url<tab>title
        for gallery in galleries:
            print(f"{gallery['url']}\t{gallery['title']}")
        
        print(f"Found {len(galleries)} galleries", file=sys.stderr)
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)