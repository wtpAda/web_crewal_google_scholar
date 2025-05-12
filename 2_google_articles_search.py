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

"""load input data"""
file_path = 'researcher_profiles_13_typical_v1_expand.csv'
output_filename = 'paper_details_13_typical_v1.csv'
input_df_50 = pd.read_csv(file_path)



# Select 50 random rows for test
#input_df_50 = result_professor_info_df.sample(n=50, random_state=42)

processed_titles = set()

# Check if the output file exists and read its content
try:
    existing_data = pd.read_csv(output_filename)
    processed_titles.update(existing_data['title'].unique())
    #last_processed_title = existing_data['Original Paper Title'].iloc[-1] if not existing_data.empty else None
except FileNotFoundError:
    # If the file does not exist, initialize it with headers
    pd.DataFrame(columns=[
        'title','paper url','Authors','Pubilcation_date','Book','Pages','Description','Total Citations','Annual Citations'
    ]).to_csv(output_filename, index=False)
    last_processed_title = None


#last_title_rows = input_df[input_df['Original Title'] == last_processed_title]

## Exclude existing data
input_df_50 = input_df_50[~input_df_50['Title'].isin(processed_titles)]


'''Extract Paper details'''
# Configure Selenium WebDriver
options = webdriver.ChromeOptions()
options.page_load_strategy = 'normal'
driver = webdriver.Chrome(options=options)

# Define batch size
batch_size = 10  # Adjust the batch size as needed

# Initialize data storage
data = []

# Split the DataFrame into batches
batches = [input_df_50[i:i + batch_size] for i in range(0, len(input_df_50), batch_size)]



# Process each batch
for batch_number, batch in enumerate(batches, start=1):
    print(f"Processing Batch {batch_number}/{len(batches)}...")
    batch_data = []
    for index, row in batch.iterrows():
        paper_url = row['URL']
        title = row['Title']
        print(f"Processing URL: {paper_url}...")
        try:
            # Navigate to the URL
            driver.get(paper_url)
            driver.implicitly_wait(10)
            time.sleep(random.uniform(5, 8))

            # Extract HTML source
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Initialize storage for the current paper
            paper_data = {'title': title, 'paper url': paper_url}

            # Extract Authors (Multilingual)
            authors_div = soup.find('div', class_='gsc_oci_field', string=lambda s: s in ['Authors', 'Autoren', 'Inventors'])
            if authors_div:
                paper_data['Authors'] = authors_div.find_next_sibling('div', class_='gsc_oci_value').get_text(strip=True)

            # Extract Publication Date
            try:
                fields = soup.find_all('div', class_='gs_scl')  # Locate all "gs_scl" sections
                publication_date = None
                for field in fields:
                    field_label = field.find('div', class_='gsc_oci_field')
                    if field_label and field_label.get_text(strip=True) in ['Publication date', 'Publikationsdatum']:
                        value = field.find('div', class_='gsc_oci_value')
                        publication_date = value.get_text(strip=True) if value else None
                        break
            except Exception as e:
                print(f"Error extracting Publication Date: {e}")
                publication_date = None
            paper_data['Pubilcation_date'] = publication_date

            # Extract Book (Multilingual)
            book_div = soup.find('div', class_='gsc_oci_field', string=lambda s: s in ['Book', 'Zeitschrift', 'Journal', 'Source'])
            if book_div:
                paper_data['Book'] = book_div.find_next_sibling('div', class_='gsc_oci_value').get_text(strip=True)

            # Extract Pages (Multilingual)
            pages_div = soup.find('div', class_='gsc_oci_field', string=lambda s: s in ['Pages', 'Seiten'])
            if pages_div:
                paper_data['Pages'] = pages_div.find_next_sibling('div', class_='gsc_oci_value').get_text(strip=True)

            # Extract Description
            try:
                fields = soup.find_all('div', class_='gs_scl')  # Locate all "gs_scl" sections
                description = None
                for field in fields:
                    field_label = field.find('div', class_='gsc_oci_field')
                    if field_label and field_label.get_text(strip=True) in ['Description', 'Beschreibung']:
                        value = field.find('div', id='gsc_oci_descr')
                        description = value.get_text(strip=True) if value else None
                        break
            except Exception as e:
                print(f"Error extracting Description: {e}")
                description = None
            paper_data['Description'] = description

            # Extract Total Citations (Multilingual)
            total_citations_div = soup.find('div', class_='gsc_oci_field', string=lambda s: s in ['Total citations', 'Zitate insgesamt'])
            if total_citations_div:
                total_citations = total_citations_div.find_next('a')
                if total_citations:
                    total_citations_text = total_citations.get_text(strip=True)
                    paper_data['Total Citations'] = total_citations_text.replace('Cited by ', '').replace('Zitiert von: ', '')

            # Extract Annual Citations
            years_elements = soup.find_all('span', class_='gsc_oci_g_t')
            citation_elements = soup.find_all('a', class_='gsc_oci_g_a')

            years = [year.get_text(strip=True) for year in years_elements]
            citations = [int(citation.find('span', class_='gsc_oci_g_al').get_text(strip=True)) for citation in citation_elements]
            paper_data['Annual Citations'] = dict(zip(years, citations))

            # Append paper data to the batch data list
            batch_data.append(paper_data)

        except Exception as e:
            print(f"Error processing URL {paper_url}: {e}")
            continue

    # Add batch data to the main data list
    data.extend(batch_data)

    # Convert the accumulated data to a DataFrame
    accumulated_df = pd.DataFrame(data)

    # Save the accumulated data to a CSV file (incrementally overwrite)
    accumulated_df.to_csv(output_filename, index=False)
    print(f"Batch {batch_number} saved to {output_filename}")

