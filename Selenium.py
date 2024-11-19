from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
import time
import random
import socket

class Selenium:
    def __init__(self, recording_duration):
        self.recording_duration = recording_duration
        self.min_video_duration = 120
        self.long_videos = []

        # Initialize WebDriver for Firefox and WebDriverWait for waiting conditions
        self.driver = webdriver.Firefox()
        self.wait = WebDriverWait(self.driver, 5)
        logging.info("WebDriver initialized successfully")

    def check_internet_connection(self, host="8.8.8.8", port=53, timeout=3):
        # Check if the system has an active internet connection.
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except Exception as e:
            logging.error(f"Internet connection check failed: {str(e)}")
            return False

    def handle_cookie(self):
        # Handle cookie consent popup
        try:
            logging.info("Looking for cookie consent popup")
            # Wait for the cookie consent button to be clickable and accept it
            cookie_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Accept')]"))
            )
            cookie_button.click()
            logging.info("Cookie consent accepted")
            time.sleep(2)
        except TimeoutException:
            # If no cookie popup appears, log the absence of it
            logging.info("No cookie consent popup found")

    def scroll_page(self, scroll_count=3):
        # Scroll the page to load more content.
        for _ in range(scroll_count):
            self.driver.execute_script("window.scrollBy(0, 1000)")
            time.sleep(1)

    def find_video(self):
        #Find videos on the page, filter them by duration, and add long ones to the list.
        logging.info("Searching for videos")
        # Locate video elements based on the specified XPath
        videos = self.driver.find_elements(
            By.XPATH,
            "//ytd-video-renderer[.//span[@class='style-scope ytd-thumbnail-overlay-time-status-renderer']]"
        )
        logging.info(f"Found {len(videos)} total videos")

        for index, video in enumerate(videos, 1):
            try:
                # Get the duration of each video and parse it into seconds
                duration_element = video.find_element(
                    By.XPATH,
                    ".//span[@class='style-scope ytd-thumbnail-overlay-time-status-renderer']"
                )
                duration = duration_element.get_attribute("textContent").strip()
                title = video.find_element(By.ID, "video-title").get_attribute("title")

                # Parse duration (e.g., "3:15" or "1:05:30")
                time_parts = duration.split(':')
                total_seconds = 0
                if len(time_parts) == 2:
                    minutes, seconds = map(int, time_parts)
                    total_seconds = minutes * 60 + seconds
                elif len(time_parts) == 3:
                    hours, minutes, seconds = map(int, time_parts)
                    total_seconds = hours * 3600 + minutes * 60 + seconds

                logging.info(f"Video {index}: '{title}' - Duration: {duration}")

                if total_seconds > self.min_video_duration:
                    # If the video is longer than the minimum duration, add it to the list
                    video_link = video.find_element(By.ID, "video-title")
                    self.long_videos.append((video_link, duration, title))
                    logging.info(f"Added to long videos list")
                else:
                    logging.info("Video too short, skipping")

            except Exception as e:
                # Log any errors encountered during the process
                logging.warning(f"Error processing video {index}: {str(e)}")
                continue

        if not self.long_videos:
            # If no videos are long enough, raise an error
            logging.error("No suitable videos found")
            raise ValueError("No suitable videos found")

    def select_video(self):
        # Select a random long video from the list and navigate to it.
        random_video, duration, title = random.choice(self.long_videos)
        logging.info(f"Selected video: '{title}' - Duration: {duration}")

        video_url = random_video.get_attribute('href')
        if not video_url:
            logging.error("Failed to get video URL")
            raise ValueError("Failed to get video URL")

        if not video_url.startswith('http'):
            video_url = f"https://www.youtube.com{video_url}"

        logging.info(f"Navigating to video: {video_url}")
        self.driver.get(video_url)
        time.sleep(5)

    def start_playback(self):
        # Click video player thumbnail to start playback
        try:
            logging.info("Attempting to start video playback")
            # Try to click the video player thumbnail to start playback
            player = self.driver.find_element(By.CLASS_NAME, "ytp-cued-thumbnail-overlay")
            player.click()
            logging.info("Video playback started")
        except Exception:
            # If the video starts automatically, log it
            logging.info("Video may have started automatically")

    def handle_ads(self):
        # Handle ads by skipping them when possible
        while True:
            try:
                # Detect if an ad is playing by looking for the ad overlay element
                ad = self.driver.find_element(By.XPATH, "//div[contains(@class, 'ytp-ad-player-overlay')]")
                if ad:
                    logging.info("Advertisement detected")
                    try:
                        # Wait for the skip button to be present and click it
                        skip_button = WebDriverWait(self.driver, 2).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[1]/div[2]/div/div/ytd-player/div/div/div[6]/div/div[3]/div/button/div")))
                        time.sleep(5)
                        skip_button.click()
                        logging.info("Advertisement skipped")
                    except Exception:
                        # If the ad is unskippable, wait before continuing
                        logging.info("Unskippable advertisement, waiting")
                        time.sleep(6)
            except Exception:
                logging.info("No advertisements detected")
                break

    def run(self):
        try:
            logging.info("Navigating to YouTube music videos search")
            # Go to YouTube search page for official music videos
            self.driver.get("https://www.youtube.com/results?search_query=official+music+video&sp=EgIYAQ%253D%253D")
            self.handle_cookie()
            self.scroll_page()
            self.find_video()
            self.select_video()
            self.start_playback()
            self.handle_ads()
            logging.info("Playing video...")
            time.sleep(self.recording_duration)
        except Exception as e:
            # Log any errors encountered during the automation
            logging.error(f"Error during YouTube automation: {str(e)}")
        finally:
            # Quit the driver after the process is complete
            self.driver.quit()
            logging.info("WebDriver closed")
