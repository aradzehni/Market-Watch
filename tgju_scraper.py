import re
import os
import time
import pandas as pd
from bs4 import BeautifulSoup as bs
from io import StringIO
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Make pandas show all data (optional)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

# --- Function to scrape the latest page ---
def tgju_crawler_updater(url):
    """Grabs the latest page from a URL using requests."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request worked
        print(f"Scraped latest page for {url}")
        return [response.text]
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

# --- Function to change Persian words to English ---
def persian_to_english(text):
    """Turns Persian text into English (e.g., 'پایانی' to 'Close')."""
    persian_to_english_dict = {
        "پایانی": "Close",
        "کمترین": "Low",
        "بیشترین": "High",
        "بازگشایی": "Open",
        "تاریخ / میلادی": "Date",
        "/": "-"
    }
    return persian_to_english_dict.get(text, text) if isinstance(text, str) else text

# --- Function to process HTML into a table ---
def process_htmls(htmls, category):
    """Turns HTML data into a clean table for a category."""
    list_of_dfs = []
    for html in htmls:
        soup = bs(html, 'html.parser')
        table = soup.find_all("table")
        if not table:
            print(f"No table found in HTML for {category}")
            continue
        df = pd.read_html(StringIO(str(table)))[0]
        df.columns = [item.replace("؟", "") for item in df.columns]
        df_cleaned = df.drop(columns=["تاریخ / میلادی", "میزان تغییر", "درصد تغییر", "تاریخ / شمسی"], errors='ignore')
        df_cleaned.index = df["تاریخ / میلادی"]
        list_of_dfs.append(df_cleaned)
    
    if not list_of_dfs:
        return pd.DataFrame()  # Return empty table if nothing works
    
    category_output = pd.concat(list_of_dfs)
    category_output.columns = pd.MultiIndex.from_tuples([(category, item) for item in category_output.columns])
    category_output.rename_axis("Date", inplace=True)
    category_output.rename(index=persian_to_english, columns=persian_to_english, inplace=True)
    
    # Make dates look nice (e.g., "2023-10-01")
    new_index = pd.MultiIndex.from_tuples(
        [(pd.to_datetime(date_str).strftime("%Y-%m-%d"),) for date_str in category_output.index],
        names=category_output.index.names
    )
    category_output.index = new_index
    category_output = category_output[~category_output.index.duplicated(keep='first')]  # Keep newest data
    return category_output

# --- Function to scrape all pages ---
def tgju_crawler(link, max_retries=3):
    """Scrapes all pages from a URL using Selenium, tries up to 3 times with better error handling."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # No browser window
    chrome_options.add_argument("--disable-notifications")  # Disable pop-ups
    chrome_options.add_argument("--no-sandbox")  # Improve stability
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")  # Mimic a real browser

    driver = webdriver.Chrome(options=chrome_options)
    
    for attempt in range(max_retries):
        try:
            driver.get(link)
            time.sleep(2)
            driver.refresh()
            WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.CLASS_NAME, "paginate_button")))
            pagination_buttons = driver.find_elements(By.CLASS_NAME, "paginate_button")
            total_pages = int(pagination_buttons[-2].text)  # Last button before "Next"
            print(f"Total pages for {link}: {total_pages}")
            
            list_of_htmls = []
            for page_num in range(total_pages):
                WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                list_of_htmls.append(driver.page_source)
                print(f"Scraped page {page_num + 1}")
                
                next_button = WebDriverWait(driver, 50).until(EC.element_to_be_clickable((By.ID, "DataTables_Table_0_next")))
                if "disabled" in next_button.get_attribute("class"):
                    break
                
                # Scroll to the button to avoid overlap and click
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(2)
                driver.execute_script("window.scrollBy(0, -400);")
                time.sleep(2)  # Wait for scroll and ad adjustment
                action = ActionChains(driver)
                action.move_to_element(next_button).click().perform()
                
                time.sleep(2)  # Wait to avoid overwhelming the site
            
            driver.quit()
            return [True, list_of_htmls]
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {link}: {e}")
            time.sleep(5)  # Wait before retrying
    driver.quit()
    print(f"Failed to crawl {link} after {max_retries} tries")
    return [False, []]

# --- Main function to run everything ---
def update_tgju_data():
    """Runs the whole process to scrape and update TGJU data."""
    # Make sure folders exist
    for folder in ["HTML Dataframes", "HTML Dataframes - Latest Page", "TGJU Database", "Output Dataframes"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")

    # Define categories and their URLs directly in the code
    links_dict = {
        "price_dollar_rl (قیمت دلار آزاد)": "https://www.tgju.org/profile/price_dollar_rl/history",
        "mesghal (مثقال طلا)": "https://www.tgju.org/profile/mesghal/history",
        "hobab_ab_shode_mesghal (حباب آب شده)": "https://www.tgju.org/profile/gold_17_transfer/history",
        "mesghal_bedone_hobab (مثقال بدون حباب)": "https://www.tgju.org/profile/gold_17/history",
        "gold_18 (طلای 18 عیار / 750)": "https://www.tgju.org/profile/geram18/history",
        "gold_24 (طلای ۲۴ عیار)": "https://www.tgju.org/profile/geram24/history",
        "gold_740 (طلای 18 عیار / 740)": "https://www.tgju.org/profile/gold_740k/history",
        "ab_shode_kamtar_az_K (آبشده کمتر از کیلو)": "https://www.tgju.org/profile/gold_world_futures/history",
        "price_aed (قیمت درهم)": "https://www.tgju.org/profile/price_aed/history",
        "seke_baharazadi (قیمت سکه بهار آزادی)": "https://www.tgju.org/profile/sekeb/history",
        "seke_nim (قیمت نیم سکه)": "https://www.tgju.org/profile/nim/history",
        "seke_emami (قیمت سکه امامی)": "https://www.tgju.org/profile/sekee/history",
        "seke_rob (قیمت ربع سکه)": "https://www.tgju.org/profile/rob/history",
        "nima_sell_usd (نرخ فروش دلار نیما)": "https://www.tgju.org/profile/nima_sell_usd/history",
        "nima_buy_usd (نرخ خرید دلار نیما)": "https://www.tgju.org/profile/nima_buy_usd/history",
        "price_cny (قیمت یوان چین)": "https://www.tgju.org/profile/price_cny/history"
    }
    categories = list(links_dict.keys())
    

    # Find categories not in the database yet
    database_dir = "TGJU Database"
    existing_categories = [f.split()[1].split('.')[0] for f in os.listdir(database_dir) if f.startswith("database")]
    not_in_DB = [ctg for ctg in categories if ctg not in existing_categories]
    
    # Scrape all pages for new categories
    for ctg in not_in_DB:
        print(f"Scraping all pages for {ctg}")
        successful, crawled_HTMLS = tgju_crawler(links_dict[ctg])
        if successful:
            df = process_htmls(crawled_HTMLS, ctg)
            df.to_excel(f"{database_dir}/database {ctg}.xlsx")
            print(f"Saved new data for {ctg}")
        else:
            print(f"Couldn’t scrape {ctg}")
    
    # Update all categories with the latest page
    for ctg in categories:
        print(f"Scraping latest page for {ctg}")
        crawled_HTMLS = tgju_crawler_updater(links_dict[ctg])
        if crawled_HTMLS:
            new_df = process_htmls(crawled_HTMLS, ctg)
            try:
                old_df = pd.read_excel(f"{database_dir}/database {ctg}.xlsx", header=[0,1], index_col=[0])
                combined_df = pd.concat([new_df, old_df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='first')]  # Keep newest data
                combined_df.to_excel(f"{database_dir}/database {ctg}.xlsx")
                print(f"Updated data for {ctg}")
            except FileNotFoundError:
                new_df.to_excel(f"{database_dir}/database {ctg}.xlsx")
                print(f"No old data for {ctg}, saved new data")
    
    # Add 50-day average and save final file
    output_dfs = []
    for ctg in categories:
        df = pd.read_excel(f"{database_dir}/database {ctg}.xlsx", header=[0,1], index_col=[0])
        ma_df = df[(ctg, 'Close')].sort_index().rolling(window=50).mean().to_frame(name=(ctg, '50-day MA'))
        ma_df = ma_df.dropna()  # Remove empty averages
        combined_df = pd.concat([df, ma_df], axis=1)
        output_dfs.append(combined_df)
    pd.concat(output_dfs, axis=1).to_excel('Output Dataframes/df1.xlsx')
    print("All done! Saved final file with 50-day averages.")

# --- Run the script ---
if __name__ == "__main__":
    update_tgju_data()
