#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

async def get_image(gallery_url, output_filepath):
    """Download the first/top image from the gallery to specified file"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Run headless for automation
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        try:
            # Convert www URLs to m. URLs if needed
            if gallery_url.startswith('https://www.dpreview.com'):
                gallery_url = gallery_url.replace('https://www.', 'https://m.')
            
            await page.goto(gallery_url, wait_until='domcontentloaded')
            
            # Wait for page to load
            await page.wait_for_timeout(3000)
            
            # Try to wait for PhotoSwipe gallery image to appear
            try:
                await page.wait_for_selector('img.pswp__img', timeout=5000)
            except:
                # If PhotoSwipe doesn't load, continue with fallback
                pass
            
            # Find the first image with class pswp__img (PhotoSwipe gallery image)
            # If not found, fall back to finding large images
            image_url = await page.evaluate('''
                () => {
                    // First try to find PhotoSwipe gallery image
                    const pswpImg = document.querySelector('img.pswp__img');
                    if (pswpImg && pswpImg.src) {
                        return pswpImg.src;
                    }
                    
                    // Fallback: find all images
                    const images = Array.from(document.querySelectorAll('img'));
                    
                    // Filter for large images that are likely gallery images
                    for (const img of images) {
                        // Skip if image is not loaded
                        if (!img.complete || !img.src) continue;
                        
                        // Get computed dimensions
                        const rect = img.getBoundingClientRect();
                        const width = rect.width;
                        const height = rect.height;
                        
                        // Look for reasonably sized images (not thumbnails)
                        if (width >= 400 && height >= 300) {
                            return img.src;
                        }
                    }
                    
                    return null;
                }
            ''')
            
            if not image_url:
                print(f"Error: No suitable gallery image found", file=sys.stderr)
                return False
                
            # Download using page context to maintain session
            response = await page.context.request.get(image_url)
            if response.ok:
                # Ensure parent directory exists
                output_path = Path(output_filepath)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(await response.body())
                return True
            else:
                print(f"Error: Failed to download image (status: {response.status})", file=sys.stderr)
                return False
                
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return False
        finally:
            await browser.close()

async def main():
    if len(sys.argv) != 3:
        print("Usage: download_sample.py <gallery_url> <output_file>", file=sys.stderr)
        sys.exit(1)
    
    gallery_url = sys.argv[1]
    output_file = sys.argv[2]
    
    success = await get_image(gallery_url, output_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())