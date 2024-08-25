# DIEGO OLIVEIRA BOMFIM
import os
import logging
import re
import time
from RPA.Browser.Selenium import Selenium
from RPA.Excel.Files import Files
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime


class Config:
    """
    Configuration class for setting up constants used across the scraper.
    """
    SEARCH_URL = "https://www.latimes.com/"
    DATE_STR = datetime.now().strftime("%Y%m%d")
    OUTPUT_DIR = os.path.join(os.getcwd(), 'output')  # Output directory
    LOG_FILE = os.path.join(OUTPUT_DIR, 'scraper.log')

# Ensure output directory exists
if not os.path.exists(Config.OUTPUT_DIR):
    os.makedirs(Config.OUTPUT_DIR)

# Setup logging
logging.basicConfig(
    filename=Config.LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('news_scraper')

# Set the logging level of external libraries to WARNING or ERROR
logging.getLogger('RPA.Browser.Selenium').setLevel(logging.WARNING)
logging.getLogger('RPA.Excel.Files').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class NewsScraper:
    """
    A scraper class to extract news articles from the LA Times website based on a search phrase.
    """

    def __init__(self, search_phrase):
        """
        Initializes the NewsScraper instance with a search phrase.

        Args:
            search_phrase (str): The phrase to search for on the LA Times website.
        """
        self.browser = Selenium()
        self.search_phrase = search_phrase

    def open_site(self):
        """
        Opens the LA Times website using Selenium browser.

        Raises:
            Exception: If the website cannot be opened.
        """
        logger.info(f"Opening site: {Config.SEARCH_URL}")
        try:
            self.browser.open_available_browser(Config.SEARCH_URL)
            logger.info("Site opened successfully.")
        except Exception as e:
            logger.error(f"Failed to open site: {e}")
            raise

    def search_news(self):
        """
        Performs a search on the LA Times website using the provided search phrase.

        Raises:
            Exception: If the search operation fails.
        """
        logger.info(f"Searching for news with phrase: '{self.search_phrase}'")
        try:
            self.browser.click_element("css:button[data-element='search-button']") #The search button element.
            self.browser.input_text("css:input[data-element='search-form-input']", self.search_phrase) # The search input field.
            self.browser.press_keys("css:input[data-element='search-form-input']", "ENTER") # Prssing ENTER to search.
            logger.info("Search completed successfully.")
            self.progress_indicator(2, 3)
        except Exception as e:
            logger.error(f"Error during search: {e}")
            raise

    def extract_news(self):
        """
        Extracts the latest new article from the search results and saves it to an Excel file.

        Raises:
            Exception: If extraction of news details fails.
        """
        logger.info("Extracting the newest news article.")
        try:
            # Extract article details
            first_item = self.browser.find_element("css:ul.search-results-module-results-menu > li:first-child")
            image_url = self.browser.get_element_attribute("css:img.image", "src")
            title = self.browser.get_text("css:h3.promo-title a.link")
            description = self.browser.get_text("css:p.promo-description")
            date = self.browser.get_text("css:p.promo-timestamp")

            image_filename = self.download_image(image_url)
            count_search_phrases = title.lower().count(self.search_phrase.lower()) + description.lower().count(self.search_phrase.lower())
            contains_money = self.check_for_money(title, description)

            article = {
                "Title": title,
                "Date": date,
                "Description": description,
                "Image Filename": image_filename,
                "Count of Search Phrases": count_search_phrases,
                "Contains Money": contains_money
            }

            logger.info("Article extracted successfully.")
            self.save_to_excel([article])
            self.progress_indicator(3, 3)
        except Exception as e:
            logger.error(f"Error during extraction: {e}")
            raise

    def download_image(self, url):
        """
        Downloads the image from the provided URL using Selenium.

        Args:
            url (str): The URL of the image to download.

        Returns:
            str or None: The filename of the downloaded image, or None if download fails.
        """
        logger.info(f"Attempting to download image from URL: {url}")
        try:
            if url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if 'url' in query_params:
                    actual_image_url = unquote(query_params['url'][0])
                    self.browser.go_to(actual_image_url)
                    image_name = actual_image_url.split("/")[-1]
                    image_path = os.path.join(Config.OUTPUT_DIR, image_name)
                    self.browser.screenshot(filename=image_path) #Since using requests is out of the table, a good solution I discovered was using the screenshot method. 
                    logger.info(f"Image downloaded successfully: {image_name}")
                    return image_name
                else:
                    logger.warning("No valid 'url' parameter found in image URL.")
                    return None
            else:
                logger.warning("No URL provided for image download.")
                return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    def check_for_money(self, title, description):
        """
        Checks if the provided text contains any amount of money.

        Args:
            title (str): The title text to check.
            description (str): The description text to check.

        Returns:
            bool: True if any amount of money is found, False otherwise.
        """
        logger.info("Checking for monetary values in the article.")
        money_patterns = [r"\$\d[\d,]*\.?\d{0,2}", r"\d+ dollars", r"\d+ USD"]
        text = f"{title} {description}"
        for pattern in money_patterns:
            if re.search(pattern, text):
                logger.info("Monetary value found in the article.")
                return True
        logger.info("No monetary values found in the article.")
        return False

    def save_to_excel(self, articles):
        """
        Saves the extracted artcle data to an Excel file.

        Args:
            articles (list): A list of dictionaries containing article data.
        """
        logger.info("Saving article data to Excel file.")
        try:
            excel = Files()
            file_path = os.path.join(Config.OUTPUT_DIR, 'news_data.xlsx')
            excel.create_workbook(file_path)
            excel.append_rows_to_worksheet([list(articles[0].keys())])  # Header row
            for article in articles:
                excel.append_rows_to_worksheet([list(article.values())])
            excel.save_workbook()
            excel.close_workbook()
            logger.info(f"Data saved successfully to {file_path}")
            self.progress_indicator(3, 3)
        except Exception as e:
            logger.error(f"Error saving data to Excel: {e}")
            raise

    def run(self):
        """
        Executes the complete scraping process: opening the site, searching, extracting, and saving data into the excel file.
        """
        logger.info("Starting the news scraping process...")
        try:
            self.progress_indicator(1, 3)
            self.open_site()
            self.search_news()
            self.extract_news()
            logger.info("News scraping process completed successfully.")
        except Exception as e:
            logger.error(f"An error occurred during the scraping process: {e}")
        finally:
            self.browser.close_browser()
            logger.info("Browser closed.")

    def progress_indicator(self, step, total):
        """
        Displays and logs the progress of the scraping process.

        Args:
            step (int): The current step number.
            total (int): The total number of steps in the process.
        """
        progress_message = f"Progress: {step}/{total} steps completed."
        logger.info(progress_message)
        print(progress_message)
        time.sleep(1)


if __name__ == "__main__":
    search_phrase = "ship" 
    scraper = NewsScraper(search_phrase)
    scraper.run()
