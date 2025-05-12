import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# Load input data
file_path = '1by1_searched_paper_details.csv'
output_file = 'cited_articles_with_original.csv'

# Read input and output data
input_df = pd.read_csv(file_path)
processed_titles = set()

# Check if the output file exists and read its content
try:
    existing_data = pd.read_csv(output_file)
    processed_titles.update(existing_data['Original Paper Title'].unique())
except FileNotFoundError:
    # If the file does not exist, initialize it with headers
    pd.DataFrame(columns=[
        'Original Paper Title', 'Original Paper URL', 'Original Cited Page URL',
        'Cited Article Title', 'Cited Article URL', 'Next Cited Articles URL'
    ]).to_csv(output_file, index=False)

# Exclude existing data
input_df = input_df[~input_df['Original Title'].isin(processed_titles)]
input_df = input_df[input_df['Cited Articles URL'].notnull()]


# Function to scrape cited articles for a given URL using requests
def scrape_cited_articles(row):
    try:
        cited_url = row['Cited Articles URL']
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(cited_url, headers=headers)
        time.sleep(random.uniform(2, 5))  # Avoid making requests too quickly
        soup = BeautifulSoup(response.text, 'html.parser')

        all_articles = []  # To store all articles from multiple pages
        visited_pages = set()  # Track visited pages to avoid loops

        # Extract all page links once
        navigation_div = soup.find('div', id='gs_nml')
        if not navigation_div:
            print("No navigation bar found. Proceeding with only the current page.")
            page_links = []
        else:
            page_links = navigation_div.find_all('a', class_='gs_nma')
            page_links = [f"https://scholar.google.com{link['href']}" for link in page_links]

        # Add the first page link (current page) at the beginning
        page_links.insert(0, cited_url)

        # Process each page link
        for page_link in page_links:
            if page_link in visited_pages:
                print(f"Already visited {page_link}. Skipping.")
                continue

            visited_pages.add(page_link)
            print(f"Processing page: {page_link}")

            response = requests.get(page_link, headers=headers)
            time.sleep(random.uniform(2, 5))  # Avoid making requests too quickly
            soup = BeautifulSoup(response.text, 'html.parser')

            # Scrape articles on the current page
            results = soup.find_all('div', class_=['gs_r gs_or gs_scl', 'gs_r gs_or gs_scl gs_fmar'])
            for result in results:
                try:
                    # Extract title and URL
                    title_tag = result.find('h3', class_='gs_rt')
                    title, url = None, None
                    if title_tag:
                        title_html = str(title_tag)
                        title = BeautifulSoup(title_html, 'html.parser').get_text(separator=" ", strip=True)
                        url = title_tag.find('a')['href'] if title_tag.find('a') else None

                    # Extract cited articles URL
                    cited_by_tag = result.find('a', text=lambda x: x and (
                            x.startswith('Cited by') or x.startswith('被引用次数')))
                    cited_articles_url = (
                        f"https://scholar.google.com{cited_by_tag['href']}"
                        if cited_by_tag
                        else None
                    )

                    # Append the cited article data along with the original paper details
                    all_articles.append({
                        'Original Paper Title': row['Original Title'],
                        'Original Paper URL': row['URL'],
                        'Original Cited Page URL': row['Cited Articles URL'],
                        'Cited Article Title': title,
                        'Cited Article URL': url,
                        'Next Cited Articles URL': cited_articles_url
                    })
                except Exception as e:
                    print(f"Error processing a result: {e}")
                    continue

        return all_articles

    except Exception as e:
        print(f"Error scraping cited articles for URL: {row['Cited Articles URL']} - {e}")
        return []


# Initialize a list to store all scraped data
batch_size = 1
all_cited_articles = []

try:
    # Loop through each row in the original DataFrame
    for index, row in input_df.iterrows():
        print(f"Scraping cited articles for: {row['Original Title']}")
        articles = scrape_cited_articles(row)
        all_cited_articles.extend(articles)  # Add to the main list

        # Save data in batches
        if len(all_cited_articles) >= batch_size:
            print(f"Saving batch of {len(all_cited_articles)} articles...")
            pd.DataFrame(all_cited_articles).to_csv(output_file, mode='a', header=False, index=False)
            all_cited_articles = []  # Reset the batch list

    # Save any remaining data after the loop
    if all_cited_articles:
        print(f"Saving final batch of {len(all_cited_articles)} articles...")
        pd.DataFrame(all_cited_articles).to_csv(output_file, mode='a', header=False, index=False)

except Exception as e:
    print(f"An error occurred: {e}")
