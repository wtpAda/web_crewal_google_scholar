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


'''Load data'''
file_path = '13_researcher_sample_input.xlsx'
output_filename = 'researcher_profiles_13_typical_v1.csv'

# Read the specific sheet
sheet_name = 'Data'
#input_df_5 = pd.read_excel(file_path, sheet_name=sheet_name, nrows = 5)
# Read the specific sheet and select the last 5 rows
input_df_5 = pd.read_excel(file_path, sheet_name=sheet_name)

processed_titles = set()

# Check if the output file exists and read its content
try:
    existing_data = pd.read_csv(output_filename)
    processed_titles.update(existing_data['name'].unique())
    #last_processed_title = existing_data['Original Paper Title'].iloc[-1] if not existing_data.empty else None
except FileNotFoundError:
    # If the file does not exist, initialize it with headers
    pd.DataFrame(columns=[
        'name', 'researcher_url', 'position', 'institution_href', 'institution',
        'personal_website', 'research_areas', 'Total Citations', 'h-index', 'i10-index', 'Annual Citation',
        'total access articles','Articles'
    ]).to_csv(output_filename, index=False)
    last_processed_title = None


#last_title_rows = input_df[input_df['Original Title'] == last_processed_title]

## Exclude existing data
input_df_5 = input_df_5[~input_df_5['name'].isin(processed_titles)]


'''Extract Author's profile page by name'''
def get_first_result_url_from_df(df, column_name):
    # Initialize the WebDriver (use your browser's WebDriver)
    driver = webdriver.Chrome()  # Replace with your WebDriver (e.g., webdriver.Firefox())
    # Base URL for Google Scholar
    base_url = "https://scholar.google.com/citations?view_op=search_authors&hl=en&oi=ao&mauthors="

    # List to store results
    results = []

    try:
        for index, row in df.iterrows():
            # Get the search query from the DataFrame's specified column
            search_query = row[column_name]
            print(f"Searching for: {search_query}")

            # Generate the search URL
            search_url = base_url + search_query.replace(" ", "+").replace(",", "%2C")

            # Open the generated URL
            driver.get(search_url)
            time.sleep(2)  # Allow the page to load

            try:
                # Find the first result container
                first_result = driver.find_element(By.CSS_SELECTOR, '.gs_ai_t h3.gs_ai_name a')

                # Get the href attribute of the first result
                first_result_url = first_result.get_attribute('href')
                print(f"Found URL: {first_result_url}")
            except Exception as e:
                print(f"No results found for {search_query}: {e}")
                first_result_url = None

            # Append the result to the list
            results.append({
                'name': search_query,
                'researcher_url': first_result_url
            })
    finally:
        # Close the WebDriver
        driver.quit()

    # Return the results as a DataFrame
    return pd.DataFrame(results)


# Get URLs for all names in the DataFrame
result_author_df = get_first_result_url_from_df(input_df_5, 'name')

'''Extract articles related information(brief)'''
# Function to press "Show more" button and ensure all articles are loaded
def load_all_articles(driver):
    while True:
        try:
            # Find the "Show more" button
            show_more_button = driver.find_element(By.ID, "gsc_bpf_more")

            # Check if the button is disabled
            if show_more_button.get_attribute("disabled") is not None:
                print("'Show more' button is disabled. All articles are loaded.")
                break

            # Click the button
            show_more_button.click()
            print("Clicked 'Show more' button.")

            # Wait for the next set of articles to load
            time.sleep(3)

        except NoSuchElementException:
            print("'Show more' button is no longer available.")
            break
        except ElementClickInterceptedException:
            print("'Show more' button click intercepted. Retrying...")
            time.sleep(2)


'''Extract Annual Citation Data'''
def extract_annual_citations(soup):
    citations = {}
    citation_container = soup.find('div', class_='gsc_md_hist_b')

    if citation_container:
        year_spans = citation_container.find_all('span', class_='gsc_g_t')
        years = [year.get_text(strip=True) for year in year_spans]

        citation_spans = citation_container.find_all('a', class_='gsc_g_a')
        counts = [cite.get_text(strip=True) for cite in citation_spans]

        for year, count in zip(years, counts):
            citations[year] = count

    return citations

'''Extract Public Access Articles'''
def extract_public_access_articles(soup):
    public_access_div = soup.find('div', class_='gsc_rsb_m')
    total_articles = None

    if public_access_div:
        available_articles_tag = public_access_div.find('div', class_='gsc_rsb_m_a')
        not_available_articles_tag = public_access_div.find('div', class_='gsc_rsb_m_na')

        available_articles = int(available_articles_tag.find('span').text.split()[0]) if available_articles_tag else 0
        not_available_articles = int(not_available_articles_tag.find('div').text.split()[0]) if not_available_articles_tag else 0

        total_articles = available_articles + not_available_articles

    return total_articles

# Main scraping loop for researchers
def scrape_researcher_data(result_df, output_filename):
    # Configure Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.page_load_strategy = 'normal'
    driver = webdriver.Chrome(options=options)

    # Initialize data storage
    data = []
    batch_size = 1

    # Loop through each researcher URL
    for index, row in result_df.iterrows():
        researcher_url = row['researcher_url']
        name = row['name']
        print(f"Processing URL: {researcher_url}...")
        try:
            # Navigate to the researcher's profile URL
            driver.get(researcher_url)
            driver.implicitly_wait(10)
            time.sleep(random.uniform(5, 8))

            # Load all articles by pressing "Show more"
            load_all_articles(driver)

            # Extract HTML source
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Extract Position and Institution
            position_institution_div = soup.find('div', class_='gsc_prf_il')
            position, institution_href, institution = None, None, None
            if position_institution_div:
                # Extract full text and split by commas
                full_text = position_institution_div.get_text(strip=True)
                text_parts = [part.strip() for part in full_text.split(",")]

                # Keywords for identifying position and institution
                position_keywords = ["professor", "prof", "director", "head"]
                institution_keywords = ["institute", "university", "school", "college", "campus"]

                # Search for position and institution
                for part in text_parts:
                    lower_part = part.lower()
                    if any(keyword in lower_part for keyword in position_keywords):
                        position = part
                    elif any(keyword in lower_part for keyword in institution_keywords):
                        institution = part

                # Extract institution href if available
                institution_tag = position_institution_div.find('a', class_='gsc_prf_ila')
                if institution_tag:
                    institution_href = f"https://scholar.google.com{institution_tag['href']}"
                    if not institution:
                        institution = institution_tag.get_text(strip=True)

            # Extract Personal Website
            personal_website = None
            personal_website_div = soup.find('div', id='gsc_prf_ivh')
            if personal_website_div:
                personal_website_tag = personal_website_div.find('a', rel='nofollow')
                if personal_website_tag:
                    personal_website = personal_website_tag['href']

            # Extract Research Areas
            research_areas_div = soup.find('div', id='gsc_prf_int')
            research_areas = []
            if research_areas_div:
                research_areas_tags = research_areas_div.find_all('a', class_='gsc_prf_inta')
                research_areas = [area.get_text(strip=True) for area in research_areas_tags]

            # Extract Metrics from Citation Table
            metrics_table = soup.find('table', id='gsc_rsb_st')
            total_citations, h_index, i10_index = None, None, None
            if metrics_table:
                rows = metrics_table.find('tbody').find_all('tr')
                for row in rows:
                    metric_name = row.find('td', class_='gsc_rsb_sc1').get_text(strip=True)
                    all_value = row.find_all('td', class_='gsc_rsb_std')[0].get_text(strip=True)
                    if metric_name == "Citations":
                        total_citations = all_value
                    elif metric_name == "h-index":
                        h_index = all_value
                    elif metric_name == "i10-index":
                        i10_index = all_value

            # Extract Additional Data
            annual_citations = extract_annual_citations(soup)
            public_access_articles = extract_public_access_articles(soup)

            # Extract Articles
            articles = []
            article_elements = soup.find_all('tr', class_='gsc_a_tr')

            for article_element in article_elements:
                try:
                    article_title = article_element.find('a', class_='gsc_a_at').text
                    article_year = article_element.find('td', class_='gsc_a_y').find('span', class_='gsc_a_h').get_text(
                        strip=True)
                    article_tag = article_element.find('a', class_='gsc_a_at')  # Locate the <a> tag
                    article_url = f"https://scholar.google.com{article_tag.get('href')}" if article_tag else None
                    articles.append({'Title': article_title, 'Year': article_year, 'URL': article_url})
                except Exception as e:
                    print(f"Error extracting article: {e}")

            # Append data
            data.append({
                'name': name,
                'researcher_url': researcher_url,
                'position': position,
                'institution_href': institution_href,
                'institution': institution,
                'personal_website': personal_website,
                'research_areas': ", ".join(research_areas),
                'Total Citations': total_citations,
                'h-index': h_index,
                'i10-index': i10_index,
                'Annual Citation': annual_citations,
                'total access articles': public_access_articles,
                'Articles': articles
            })

            # Save data in batches
            if len(data) >= batch_size:
                print(f"Saving batch of {len(data)} records...")
                pd.DataFrame(data).to_csv(output_filename, mode='a', header=False, index=False)
                data = []  # Reset the batch list

        except Exception as e:
            print(f"Error processing URL {researcher_url}: {e}")
            continue

    # Save any remaining data
    if data:
        print(f"Saving final batch of {len(data)} records...")
        pd.DataFrame(data).to_csv(output_filename, mode='a', header=False, index=False)

    # Close the WebDriver
    driver.quit()

scrape_researcher_data(result_author_df, output_filename)

output_filename_excel = 'researcher_profiles_13_typical_v1.xlsx'
df = pd.read_csv(output_filename)
df.to_excel(output_filename_excel)

# Scrape researcher data
#df_professor_info = scrape_researcher_data(result_author_df)

# Save the results to a CSV file
#df_professor_info.to_csv('researcher_profiles.csv', index=False)

# Save the results to a CSV file
#df_professor_info.to_csv('researcher_profiles.csv', index=False)
# 假设 df_professor_info 是已经存在的数据框
df_professor_info = pd.read_csv(output_filename) # 如果数据来自CSV文件，可以使用这行代码读取
df_professor_info['Articles']=df_professor_info['Articles'] .apply(eval)

# Step 1: Explode the articles column
df_professor_info = df_professor_info.explode('Articles')
df_expanded = df_professor_info['Articles'].apply(pd.Series)
df_professor_info = pd.concat([df_professor_info, df_expanded], axis=1)
df_professor_info = df_professor_info.drop(columns=['Articles'])
print(df_professor_info)
#
#
# # Step 2: Normalize the articles dictionary into separate columns
# articles_df = pd.json_normalize(df_professor_info['Articles'])
#
# # Step 3: Merge back with the Researcher column
# result_df = df_professor_info.drop(columns=['Articles']).reset_index(drop=True)
# result_professor_info_df = pd.concat([result_df, articles_df], axis=1)
#
# # Save the results to a CSV file
df_professor_info.to_csv('researcher_profiles_13_typical_v1_expand.csv', index=False)
df_professor_info.to_excel('researcher_profiles_13_typical_v1_expand.xlsx', index=False)






