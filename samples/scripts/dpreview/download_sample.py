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
            
            print(f"Opening gallery: {gallery_url}", file=sys.stderr)
            await page.goto(gallery_url, wait_until='domcontentloaded')
            
            # Wait for page to load
            await page.wait_for_timeout(3000)
            
            # Click on the first image div to open the viewer
            try:
                await page.wait_for_selector('div.image', timeout=5000)
                await page.click('div.image')
                await page.wait_for_timeout(2000)
            except:
                print(f"Error: Could not find or click first image div", file=sys.stderr)
                return False
            
            # Extract all image URLs from the EXIF table
            image_urls = await page.evaluate('''
                () => {
                    const exifTable = document.querySelector('table.exif');
                    if (!exifTable) {
                        return null;
                    }
                    
                    // Find the "Original:" row
                    const originalRow = Array.from(exifTable.querySelectorAll('tr.item')).find(row => {
                        const label = row.querySelector('td.label');
                        return label && label.textContent.trim() === 'Original:';
                    });
                    
                    if (!originalRow) {
                        return null;
                    }
                    
                    const links = originalRow.querySelectorAll('a[href]');
                    const files = [];
                    
                    links.forEach(link => {
                        const href = link.href;
                        const text = link.textContent.trim();
                        
                        // Extract file extension from URL or text
                        let extension = '';
                        if (href.includes('.jpg')) extension = 'jpg';
                        else if (href.includes('.jpeg')) extension = 'jpeg';  
                        else if (href.includes('.png')) extension = 'png';
                        else if (href.includes('.cr3')) extension = 'cr3';
                        else if (href.includes('.nef')) extension = 'nef';
                        else if (href.includes('.arw')) extension = 'arw';
                        else if (href.includes('.dng')) extension = 'dng';
                        else if (text.toLowerCase().includes('jpeg')) extension = 'jpeg';
                        else if (text.toLowerCase().includes('png')) extension = 'png';
                        else if (text.toLowerCase().includes('raw')) extension = 'raw';
                        
                        if (extension) {
                            files.push({
                                url: href,
                                extension: extension,
                                text: text,
                                isRaw: ['cr3', 'nef', 'arw', 'dng', 'raw'].includes(extension)
                            });
                        }
                    });
                    
                    return files;
                }
            ''')
            
            if not image_urls or len(image_urls) == 0:
                print(f"Error: No image URLs found in EXIF table", file=sys.stderr)
                return False
            
            # Priority order: PNG > JPEG > RAW formats
            def get_priority(file_info):
                if file_info['extension'] == 'png':
                    return 1
                elif file_info['extension'] in ['jpg', 'jpeg']:
                    return 2
                elif file_info['isRaw']:
                    return 3
                else:
                    return 4
            
            # Sort by priority and pick the best one
            best_file = min(image_urls, key=get_priority)
            image_url = best_file['url']
            file_type = best_file['extension'].upper()
            
            print(f"Downloading {file_type} image from: {image_url}", file=sys.stderr)
                
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
        print("Usage: download_sample.py <output_file> <gallery_url>", file=sys.stderr)
        sys.exit(1)
    
    output_file = sys.argv[1]
    gallery_url = sys.argv[2]
    
    success = await get_image(gallery_url, output_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())