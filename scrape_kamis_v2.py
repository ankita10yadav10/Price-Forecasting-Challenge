"""
KAMIS Data Scraper V2
Improved scraper that properly handles pagination and downloads
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from io import StringIO

class KamisScraperV2:
    def __init__(self, base_url="https://kamis.kilimo.go.ke"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
    
    def inspect_page(self, product_id=1, per_page=3000, page=1):
        """
        Inspect a page to understand its structure
        """
        url = f"{self.base_url}/site/market"
        params = {
            'product': product_id,
            'per_page': per_page,
            'page': page
        }
        
        print(f"\n{'='*60}")
        print(f"Inspecting: {url}")
        print(f"Params: {params}")
        print(f"{'='*60}")
        
        response = self.session.get(url, params=params, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for download link
        download_links = soup.find_all('a', href=True)
        for link in download_links:
            if 'download' in link.get('href', '').lower() or 'export' in link.get('href', '').lower():
                print(f"Found download link: {link.get('href')}")
                print(f"Link text: {link.get_text(strip=True)}")
        
        # Check for pagination
        pagination = soup.find_all(['ul', 'div'], class_=re.compile('paginat', re.I))
        print(f"\nFound {len(pagination)} pagination elements")
        for pag in pagination:
            print(f"Pagination HTML: {pag}")
        
        # Look for page info
        page_info = soup.find_all(text=re.compile(r'page|showing|entries', re.I))
        for info in page_info[:5]:
            print(f"Page info: {info.strip()}")
        
        # Check table
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            print(f"\nTable found with {len(rows)} rows")
        
        return soup
    
    def try_download_endpoint(self, product_id=1, per_page=3000, page=1):
        """
        Try to find and use a download endpoint (CSV/Excel)
        """
        # Common download endpoint patterns
        endpoints = [
            f"{self.base_url}/site/market/download",
            f"{self.base_url}/site/market/export",
            f"{self.base_url}/site/export-market",
            f"{self.base_url}/site/market-export",
        ]
        
        params = {
            'product': product_id,
            'per_page': per_page,
            'page': page
        }
        
        for endpoint in endpoints:
            try:
                print(f"Trying endpoint: {endpoint}")
                response = self.session.get(endpoint, params=params, timeout=30)
                if response.status_code == 200:
                    # Check if it's CSV data
                    content_type = response.headers.get('content-type', '')
                    if 'csv' in content_type or 'text/csv' in content_type:
                        print(f"Found CSV endpoint! {endpoint}")
                        return response.text
                    # Try parsing as CSV anyway
                    try:
                        df = pd.read_csv(StringIO(response.text))
                        if not df.empty:
                            print(f"Successfully parsed CSV from {endpoint}")
                            return response.text
                    except:
                        pass
            except Exception as e:
                pass
        
        return None
    
    def get_page_with_offset(self, product_id=1, per_page=100, offset=0):
        """
        Try using offset instead of page number
        """
        url = f"{self.base_url}/site/market"
        params = {
            'product': product_id,
            'per_page': per_page,
            'offset': offset
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error with offset {offset}: {e}")
            return None
    
    def extract_all_page_links(self, soup):
        """
        Extract all pagination links from the page
        """
        page_links = []
        
        # Find pagination
        pagination = soup.find('ul', class_='pagination')
        if not pagination:
            # Try other pagination patterns
            pagination = soup.find('div', class_=re.compile('paginat', re.I))
        
        if pagination:
            links = pagination.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                # Extract page number from href
                match = re.search(r'page=(\d+)', href)
                if match:
                    page_num = int(match.group(1))
                    page_links.append((page_num, href))
                    print(f"Found page {page_num}: {href}")
        
        return sorted(page_links, key=lambda x: x[0])
    
    def get_page_by_url(self, url):
        """
        Fetch a page using full URL
        """
        try:
            if not url.startswith('http'):
                url = self.base_url + url
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_table_data(self, soup):
        """
        Extract table data from the page
        """
        data = []
        
        table = soup.find('table')
        if not table:
            return data
        
        # Extract headers
        headers = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Extract data rows
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells and len(cells) > 0:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        header = headers[i] if i < len(headers) else f"Column_{i+1}"
                        row_data[header] = cell.get_text(strip=True)
                    
                    if any(row_data.values()):
                        data.append(row_data)
        
        return data
    
    def scrape_all_pages_method1(self, product_id=1, per_page=3000):
        """
        Method 1: Use pagination links directly
        """
        print("\n" + "="*60)
        print("METHOD 1: Following pagination links")
        print("="*60)
        
        all_data = []
        
        # Get first page
        url = f"{self.base_url}/site/market"
        params = {'product': product_id, 'per_page': per_page}
        
        response = self.session.get(url, params=params, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract data from first page
        page_data = self.extract_table_data(soup)
        print(f"Page 1: {len(page_data)} rows")
        all_data.extend(page_data)
        
        # Get all page links
        page_links = self.extract_all_page_links(soup)
        print(f"Found {len(page_links)} page links")
        
        # Visit each page
        for page_num, page_url in page_links:
            if page_num == 1:  # Skip first page, already scraped
                continue
            
            print(f"\nFetching page {page_num}...")
            time.sleep(1)  # Be respectful
            
            soup = self.get_page_by_url(page_url)
            if soup:
                page_data = self.extract_table_data(soup)
                print(f"Page {page_num}: {len(page_data)} rows")
                
                # Check if data is unique (not duplicate)
                if page_data and all_data:
                    # Compare first row to check if it's different
                    if page_data[0] != all_data[-1]:
                        all_data.extend(page_data)
                    else:
                        print(f"  Warning: Page {page_num} appears to be duplicate")
                else:
                    all_data.extend(page_data)
        
        return pd.DataFrame(all_data) if all_data else pd.DataFrame()
    
    def scrape_all_pages_method2(self, product_id=1, per_page=100, max_pages=20):
        """
        Method 2: Use smaller per_page and iterate through pages
        """
        print("\n" + "="*60)
        print("METHOD 2: Iterating with smaller per_page")
        print("="*60)
        
        all_data = []
        
        for page in range(1, max_pages + 1):
            print(f"\nFetching page {page}...")
            
            url = f"{self.base_url}/site/market"
            params = {
                'product': product_id,
                'per_page': per_page,
                'page': page
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                page_data = self.extract_table_data(soup)
                
                if not page_data:
                    print(f"Page {page}: No data found, stopping")
                    break
                
                print(f"Page {page}: {len(page_data)} rows")
                
                # Check for duplicates
                if all_data and page_data:
                    if page_data[0] == all_data[-len(page_data)]:
                        print(f"Page {page}: Duplicate data detected, stopping")
                        break
                
                all_data.extend(page_data)
                time.sleep(1)
                
            except Exception as e:
                print(f"Error on page {page}: {e}")
                break
        
        return pd.DataFrame(all_data) if all_data else pd.DataFrame()


def main():
    scraper = KamisScraperV2()
    for product_id in range(2, 50):
        df1 = scraper.scrape_all_pages_method1(product_id=product_id, per_page=3000)
        if not df1.empty:
            print(f"\nMethod 1 Result: {len(df1)} total rows")
            print(f"Columns: {df1.columns.tolist()}")
            print(f"\nFirst few rows:\n{df1.head()}")
            print(f"\nLast few rows:\n{df1.tail()}")
            df1.to_csv(f"kamis_{product_id}.csv", index=False)
            print(f"\nSaved to kamis_{product_id}.csv")

if __name__ == "__main__":
    main()

