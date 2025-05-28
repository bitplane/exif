#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def fetch_all_galleries():
    """Fetch all gallery links from dpreview sample galleries page"""
    galleries = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        await page.goto('https://m.dpreview.com/sample-galleries?category=all&sort=chronologically', wait_until='domcontentloaded')
        
        # Wait for the gallery list to load
        await page.wait_for_selector('.articleList', timeout=30000)
        
        # Keep scrolling to load all galleries (lazy loading)
        last_count = 0
        while True:
            # Get current gallery count
            gallery_elements = await page.query_selector_all('.articleList article')
            current_count = len(gallery_elements)
            
            # If no new galleries loaded, we're done
            if current_count == last_count:
                break
            
            last_count = current_count
            
            # Scroll to bottom to trigger lazy loading
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Wait a bit for new content to load
            await page.wait_for_timeout(2000)
        
        # Extract all gallery links and titles
        galleries = await page.evaluate('''
            () => {
                const articles = document.querySelectorAll('.articleList article');
                return Array.from(articles).map(article => {
                    const link = article.querySelector('a');
                    const title = article.querySelector('h4');
                    if (link && title) {
                        return {
                            url: link.href,
                            title: title.textContent.trim()
                        };
                    }
                    return null;
                }).filter(item => item !== null);
            }
        ''')
        
        await browser.close()
        
    return galleries

async def main():
    galleries = await fetch_all_galleries()
    
    # Output in TSV format: url<tab>title
    for gallery in galleries:
        print(f"{gallery['url']}\t{gallery['title']}")

if __name__ == "__main__":
    asyncio.run(main())