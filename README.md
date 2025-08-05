# Comprehensive Google Scholar Data Scraper

## Overview

This project provides a powerful, multi-stage Python solution for extracting comprehensive academic data from Google Scholar and general web searches. It's designed to build a rich dataset covering researcher profiles, detailed article information, and citation networks. The project is broken down into four sequential scripts, each performing a specific part of the data collection process.

## Project Workflow

The data collection process is designed to run in four sequential steps. Each script builds upon the output of the previous one:

1.  **`1_researcher_profile_extraction_v2.py`**:
    *   **Purpose**: Finds researcher profiles on Google Scholar and extracts their core details (position, institution, metrics) and a list of their publications.
    *   **Input**: `13_researcher_sample_input.xlsx` (list of researcher names).
    *   **Output**: `researcher_profiles_13_typical_v1_expand.csv` (researchers with their articles expanded on separate rows).

2.  **`2_google_articles_search.py`**:
    *   **Purpose**: Takes the articles found in Step 1 and visits each article's specific Google Scholar page to extract more detailed information (publication date, journal, abstract, total citations for the article).
    *   **Input**: `researcher_profiles_13_typical_v1_expand.csv` (from Step 1).
    *   **Output**: `paper_details_13_typical_v1.csv` (detailed article information).

3.  **`3_title_google_search.py`**:
    *   **Purpose**: Performs a *general Google search* for each article title (from Step 2) to find additional details like abstracts, direct article URLs, and "Cited by" links that might appear in broader web search results.
    *   **Input**: `paper_details_13_typical_v1.csv` (from Step 2).
    *   **Output**: `1by1_searched_paper_details_v2.csv` (enriched article details from general search).

4.  **`4_cited_articles_request.py`**:
    *   **Purpose**: Follows the "Cited by" links found in Step 3 to scrape lists of articles that cite the original papers, building a citation network.
    *   **Input**: `1by1_searched_paper_details_v2.csv` (from Step 3).
    *   **Output**: `cited_articles_with_original.csv` (list of citing articles).

## Key Features of the Project

*   **Comprehensive Data Collection**: Gathers a wide array of academic data, from researcher profiles to detailed article information and their citing papers.
*   **Modular Design**: Broken into distinct, sequential scripts for clarity, maintainability, and easier debugging.
*   **Dynamic Content Handling**: Utilizes Selenium for scripts that require browser interaction (e.g., clicking "Show more" buttons, handling JavaScript).
*   **Efficient Static Scraping**: Employs the `requests` library for faster data retrieval on pages that don't require browser rendering.
*   **Resume Capability**: Each script checks for existing output and skips already processed entries, allowing for interrupted runs to be resumed without loss of progress.
*   **Incremental Saving**: Data is saved in batches during execution, minimizing data loss in case of errors or interruptions.
*   **Flexible Output Formats**: Generates data in both CSV and Excel formats for easy analysis and integration with other tools.
*   **Polite Scraping**: Incorporates randomized delays between web requests to mimic human behavior and reduce the risk of being blocked by websites.

## Prerequisites

Before running any script, ensure you have the following installed:

*   **Python 3.x**: The programming language.
*   **Google Chrome Browser**: Required for scripts that use Selenium (Parts 1, 2, 3).
*   **ChromeDriver**: This executable allows Python to control your Chrome browser.
    *   **Download**: Get the version that *exactly matches* your Google Chrome browser version from [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads).
    *   **Placement**: Place the downloaded `chromedriver.exe` (or `chromedriver` on Mac/Linux) file in a directory that's included in your system's PATH. Alternatively, you can modify the `webdriver.Chrome()` line in each script to point directly to its location (e.g., `webdriver.Chrome('/path/to/chromedriver')`).

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/[Your-Username]/[Your-Repository-Name].git
    cd [Your-Repository-Name]
    ```
    (Replace `[Your-Username]` and `[Your-Repository-Name]` with your actual GitHub username and repository name.)
2.  **Install Python packages**: Open your command line or terminal in the project's root directory and run this command. It installs all necessary Python libraries for all scripts:
    ```bash
    pip install selenium beautifulsoup4 pandas openpyxl numpy requests
    ```

## How To Use The Project (Step-by-Step)

You must run the scripts in sequential order (1, then 2, then 3, then 4).

### Step 1: Extract Researcher Profiles

*   **Script**: `1_researcher_profile_extraction_v2.py`
*   **Input**: Create an Excel file named `13_researcher_sample_input.xlsx` with a sheet named `Data` and a column `name` containing researcher names.
    ```
    # Example: 13_researcher_sample_input.xlsx (Sheet: Data)
    name
    -----------------
    Researcher One
    Researcher Two
    ```
*   **Run**:
    ```bash
    python 1_researcher_profile_extraction_v2.py
    ```
*   **Output**: `researcher_profiles_13_typical_v1.csv`, `researcher_profiles_13_typical_v1.xlsx`, `researcher_profiles_13_typical_v1_expand.csv`, `researcher_profiles_13_typical_v1_expand.xlsx`. The `_expand.csv` file is the input for the next step.

### Step 2: Get Detailed Article Information

*   **Script**: `2_google_articles_search.py`
*   **Input**: This script automatically uses `researcher_profiles_13_typical_v1_expand.csv` (generated by Step 1). Ensure it's in the same directory.
*   **Run**:
    ```bash
    python 2_google_articles_search.py
    ```
*   **Output**: `paper_details_13_typical_v1.csv`, `paper_details_13_typical_v1.xlsx`. The `.csv` file is the input for the next step.

### Step 3: General Google Search for Article Details

*   **Script**: `3_title_google_search.py`
*   **Input**: This script automatically uses `paper_details_13_typical_v1.csv` (generated by Step 2). Ensure it's in the same directory.
*   **Run**:
    ```bash
    python 3_title_google_search.py
    ```
*   **Output**: `1by1_searched_paper_details_v2.csv`, `1by1_searched_paper_details_v2.xlsx`. The `.csv` file is the input for the final step.

### Step 4: Scrape Cited Articles

*   **Script**: `4_cited_articles_request.py`
*   **Input**: This script automatically uses `1by1_searched_paper_details_v2.csv` (generated by Step 3). Ensure it's in the same directory.
*   **Run**:
    ```bash
    python 4_cited_articles_request.py
    ```
*   **Output**: `cited_articles_with_original.csv`.

## Important Notes & Troubleshooting

*   **Sequential Execution**: Always run the scripts in the specified order (1 -> 2 -> 3 -> 4).
*   **Internet Connection**: A stable internet connection is required for all scripts.
*   **Google Scholar Terms of Service**: Be mindful of Google Scholar's (and Google's) terms of service regarding automated access. Excessive or very rapid requests might lead to temporary IP blocks. The scripts include random delays to mitigate this, but for very large datasets, further measures (like proxies) might be necessary.
*   **ChromeDriver Issues**: If a script fails to open a browser or gives an error related to ChromeDriver, ensure:
    *   Your ChromeDriver version exactly matches your Google Chrome browser version.
    *   `chromedriver.exe` (or `chromedriver`) is correctly placed in your system's PATH, or its full path is specified in the script.
*   **HTML Structure Changes**: Websites like Google Scholar can update their HTML structure. If a script stops working, the selectors used by BeautifulSoup (`find`, `find_all`, `class_`, `id`) might need to be updated to match the new structure.
*   **Input/Output File Names**: The scripts are hardcoded to look for specific input and output file names. Do not rename the intermediate output files if you plan to use them as input for the next step.



---
