from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import openpyxl
import random
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
import unicodedata
import re

"""load input data"""
file_path = 'paper_details.csv'
output_filename = '1by1_searched_paper_details_v2.csv'

# Read input and output data
input_df = pd.read_csv(file_path)
processed_titles = set()

# Check if the output file exists and read its content
try:
    existing_data = pd.read_csv(output_filename)
    processed_titles.update(existing_data['Matched Title'].unique())
    #last_processed_title = existing_data['Original Paper Title'].iloc[-1] if not existing_data.empty else None
except FileNotFoundError:
    # If the file does not exist, initialize it with headers
    pd.DataFrame(columns=[
        'Matched Title','URL','Abstract','Cited Articles URL','Authors with URLs','Original Title','Original URL'
    ]).to_csv(output_filename, index=False)
    last_processed_title = None


#last_title_rows = input_df[input_df['Original Title'] == last_processed_title]

## Exclude existing data
input_df = input_df[~input_df['title'].isin(processed_titles)]


# Function to replace problematic characters with ASCII equivalents and remove surrounding quotes
def normalize_text(text):
    # Normalize Unicode (NFKD) and replace special characters with standard ones
    text = unicodedata.normalize('NFKD', text)
    text = text.replace("’", "'")  # Replace right single quote with ASCII apostrophe
    text = text.replace("“", '"').replace("”", '"')  # Replace smart quotes with ASCII quotes
    text = text.replace("–", "-")  # Replace en dash with hyphen
    text = ' '.join(text.split())  # Remove extra spaces

    # Remove any enclosing quotes (single or double)
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    elif text.startswith("'") and text.endswith("'"):
        text = text[1:-1]

    return text


# Function to extract text from HTML while handling inline tags like <b>, <i>, etc.
def extract_text_with_inline_tags(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return normalize_text(soup.get_text(separator=""))

def search_google_scholar_details(title_query):
    try:
        # Open Google Scholar
        driver.get('https://scholar.google.com')
        driver.implicitly_wait(10)

        # Find the search box and enter the title query
        search_box = driver.find_element(By.NAME, 'q')
        search_box.clear()
        search_box.send_keys(title_query)
        time.sleep(random.uniform(2, 4))
        search_box.send_keys(Keys.RETURN)
        time.sleep(random.uniform(5, 7))  # Wait for results to load

        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        results = soup.find_all('div',
                                class_=['gs_r gs_or gs_scl', 'gs_r gs_or gs_scl gs_fmar'])  # All search result divs

        matched_title = None
        matched_url = None
        abstract_text = None
        cited_articles_url = None
        authors_with_urls = {}

        if results:
            for result in results:
                try:
                    # Extract title HTML and process inline tags
                    title_tag = result.find('h3', class_='gs_rt')
                    if title_tag:
                        title_html = str(title_tag)  # Get the raw HTML
                        extracted_title = normalize_text(extract_text_with_inline_tags(title_html))
                        # Remove unwanted prefixes like [CITATION], [C], etc.
                        extracted_title = re.sub(r'\[.*?\]', '', extracted_title).strip()

                        extracted_title = ' '.join(extracted_title.split())
                        title_query = ' '.join(title_query.split())

                    # Compare the extracted title with the query
                    if normalize_text(extracted_title.lower()) == normalize_text(title_query.lower()):
                        matched_title = extracted_title
                        matched_url = title_tag.find('a')['href'] if title_tag.find('a') else None
                        #Extract Abstract

                        try:
                            # First attempt to get abstract from `gsh_csp`
                            gsh_sp_element = result.find('div', class_='gsh_csp')
                            if gsh_sp_element:
                                abstract_text = gsh_sp_element.text.strip()
                            else:
                                # Try to get abstract from `gs_rs`
                                abstract_div = result.find('div', class_='gs_rs')
                                if abstract_div:
                                    abstract_text = abstract_div.get_text(separator=" ").strip()
                                else:
                                    # Handle complex abstract structure in `gs_fma_snp`
                                    abstract_container = result.find('div', class_='gs_fma_snp')
                                    if abstract_container:
                                        abstract_text = ' '.join(
                                            [div.text.strip() for div in
                                             abstract_container.find_all('div', class_='gsh_csp') if div.text.strip()]
                                        )
                                    else:
                                        # Handle abstract from `gs_rs gs_fma_s`
                                        abstract_special = result.find('div', class_='gs_rs gs_fma_s')
                                        if abstract_special:
                                            # Extract and handle <br> tags within the text
                                            abstract_text = abstract_special.get_text(separator=" ").replace('\xa0',
                                                                                                             ' ').strip()
                                        else:
                                            # Handle nested structures with <br> tags explicitly in `gs_fma_snp`
                                            abstract_nested = result.find('div', class_='gs_fma_snp')
                                            if abstract_nested:
                                                abstract_text = ' '.join(
                                                    [
                                                        part.strip().replace('\xa0', ' ')
                                                        for part in
                                                        abstract_nested.get_text(separator=" ").split('<br>')
                                                        if part.strip()
                                                    ]
                                                )
                        except Exception:
                            pass

                        # Extract cited articles URL
                        cited_by_tag = result.find('a', text= lambda x: x and (x.startswith('Cited by') or x.startswith('被引用次数')))
                        cited_articles_url = (
                            f"https://scholar.google.com{cited_by_tag['href']}"
                            if cited_by_tag
                            else None
                        )

                        # Extract authors and their URLs
                        authors_tag = result.find('div', class_=['gs_a', 'gs_fmaa'])
                        if authors_tag:
                            authors_links = authors_tag.find_all('a')
                            for author_link in authors_links:
                                author_name = author_link.get_text(strip=True)
                                author_url = f"https://scholar.google.com{author_link['href']}" if author_link.has_attr('href') else None
                                authors_with_urls[author_name] = author_url

                        break  # Exit loop if an exact match is found

                except Exception as e:
                    print(f"Error processing a result: {e}")
                    continue

            # If no exact match is found but there's only one result, treat it as matched
            if not matched_title and len(results) == 1:
                single_result = results[0]
                try:
                    title_tag = single_result.find('h3', class_='gs_rt')
                    if title_tag:
                        matched_title = title_tag.get_text(strip=True)
                        matched_url = title_tag.find('a')['href'] if title_tag.find('a') else None

                        # Try to extract the abstract
                        try:
                            # First attempt to get abstract from `gsh_csp`
                            gsh_sp_element = result.find('div', class_='gsh_csp')
                            if gsh_sp_element:
                                abstract_text = gsh_sp_element.text.strip()
                            else:
                                # Try to get abstract from `gs_rs`
                                abstract_div = result.find('div', class_='gs_rs')
                                if abstract_div:
                                    abstract_text = abstract_div.get_text(separator=" ").strip()
                                else:
                                    # Handle complex abstract structure
                                    abstract_container = result.find('div', class_='gs_fma_snp')
                                    if abstract_container:
                                        abstract_text = ' '.join(
                                            [div.text.strip() for div in abstract_container.find_all('div') if
                                             div.text.strip()]
                                        )
                        except Exception:
                            pass

                    # Extract cited articles URL
                    cited_by_tag = single_result.find('a', text=lambda x: x and (x.startswith('Cited by') or x.startswith('被引用次数')))
                    cited_articles_url = (
                        f"https://scholar.google.com{cited_by_tag['href']}"
                        if cited_by_tag
                        else None
                    )

                    # Extract authors and their URLs
                    authors_tag = single_result.find('div', class_=['gs_a', 'gs_fmaa'])
                    if authors_tag:
                        authors_links = authors_tag.find_all('a')
                        for author_link in authors_links:
                            author_name = author_link.get_text(strip=True)
                            author_url = f"https://scholar.google.com{author_link['href']}" if author_link.has_attr('href') else None
                            authors_with_urls[author_name] = author_url
                except Exception as e:
                    print(f"Error processing single result: {e}")

        # Return matched data
        return {
            'Matched Title': matched_title,
            'URL': matched_url,
            'Abstract': abstract_text,
            'Cited Articles URL': cited_articles_url,
            'Authors with URLs': authors_with_urls,
        }

    except Exception as e:
        print(f"Error during search for '{title_query}': {e}")
        return {
            'Matched Title': None,
            'URL': None,
            'Abstract': None,
            'Cited Articles URL': None,
            'Authors with URLs': {},
        }


# Configure Selenium WebDriver
options = webdriver.ChromeOptions()
options.page_load_strategy = 'normal'
driver = webdriver.Chrome(options=options)

# Initialize storage for new rows
batch_size = 10
detailed_data = []


# Process each title in the DataFrame
for index, row in input_df.iterrows():
    title_query = row['title']
    print(f"Processing: {title_query}...")
    result = search_google_scholar_details(title_query)

    # Add the original title and URL to the result
    result['Original Title'] = row['title']
    result['Original URL'] = row['paper url']

    # If no match, keep only the original title and URL
    if not result['Matched Title']:
        result['Abstract'] = None
    detailed_data.append(result)

    # Save data in batches
    if len(detailed_data) >= batch_size:
        print(f"Saving batch of {len(detailed_data)} records...")
        pd.DataFrame(detailed_data).to_csv(output_filename, mode='a', header=False, index=False)
        detailed_data = []  # Reset batch list

# Save any remaining data after processing all rows
if detailed_data:
    print(f"Saving final batch of {len(detailed_data)} records...")
    pd.DataFrame(detailed_data).to_csv(output_filename, mode='a', header=False, index=False)



