# TGJU Data Scraper
This script grabs financial data from TGJU and saves it in Excel files.

## What You Need
- Python 3 (like the toy’s batteries)
- Chrome browser and chromedriver (get it from [here](https://chromedriver.chromium.org/downloads), match your Chrome version)
- **Install these tools: pip install selenium pandas beautifulsoup4 requests**

## Setup
1. Make these folders (or the script will make them):
 - `HTML Dataframes`
 - `HTML Dataframes - Latest Page`
 - `TGJU Database`
 - `Output Dataframes`
2. Put `TGJU-DATA.txt` in the same place as the script.
3. Add `chromedriver` to your PATH (ask a ChatGPT if stuck!).

## What happens
It’ll scrape data, update files, and add a 50-day average!

## Notes
- If it breaks, check your internet or TGJU-DATA.txt.
- Be nice to the website—don’t run it too much!
