from Recording import Recording
from Selenium import Selenium
import logging
import os
from datetime import datetime
import time
import threading


class Main:
    def __init__(self, recording_duration):
        # Initialize the main class with recording duration and other parameters
        self.recording_duration = recording_duration  # Duration for the video recording
        self.min_video_duration = 120  # Minimum duration of video to be recorded (in seconds)
        self.setup_logging()  # Set up logging configuration
        self.driver = None  # Placeholder for Selenium WebDriver instance
        self.recording_thread = None  # Thread for recording video
        self.should_stop = False  # Flag to stop recording
        self.target_fps = 30  # Target frames per second for the recording
        self.recording = Recording(recording_duration)  # Initialize Recording object
        self.selenium = Selenium(recording_duration)  # Initialize Selenium automation object

        # Log the initial setup information
        logging.info("Starting New Recording Session")
        logging.info(f"Recording duration set to: {self.recording_duration} seconds")
        logging.info(f"Minimum video duration set to: {self.min_video_duration} seconds")

    def setup_logging(self):
        # Set up logging configuration: create log files and log the session start.
        if not os.path.exists('logs'):  # Check if 'logs' directory exists
            os.makedirs('logs')  # Create 'logs' directory if not exists

        # Create a timestamped log file name
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file = f'logs/youtube_recorder_{timestamp}.log'

        # Configure logging to output to both console and file
        logging.basicConfig(
            level=logging.INFO,  # Set log level to INFO
            format='%(asctime)s - %(levelname)s - %(message)s',  # Set log message format
            handlers=[
                logging.FileHandler(log_file),  # Log to the file
                logging.StreamHandler()  # Also log to console
            ]
        )

        # Log the session start information
        logging.info("=== Starting New Recording Session ===")
        logging.info(f"Recording duration set to: {self.recording_duration} seconds")
        logging.info(f"Minimum video duration set to: {self.min_video_duration} seconds")

    def run(self):
        try:
            logging.info("Starting...")

            # Check if there is an active internet connection
            if not self.selenium.check_internet_connection():
                logging.error("No internet connection detected.")  # Log error if no connection
                logging.info("Waiting for 15 seconds before shutting down...")
                time.sleep(15)  # Wait for 15 seconds before rechecking the connection
                if not self.selenium.check_internet_connection():
                    logging.error("Exiting due to lack of internet connection.")  # Exit if no connection
                    return
                logging.info("Internet connection detected. Resuming...")  # If internet is back, continue

            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self.recording.record_screen)
            self.recording_thread.start()  # Begin recording in the background
            logging.info("Recording thread started")

            try:
                # Run Selenium automation to find and play a YouTube video
                self.selenium.run()
            finally:
                # Ensure that the browser is closed after the Selenium task
                if self.driver:
                    logging.info("Closing browser")
                    self.driver.quit()  # Quit the WebDriver
                    self.driver = None  # Reset WebDriver reference

            # Wait for the recording to finish
            logging.info("Waiting for recording to complete")
            self.recording_thread.join()  # Wait for the recording thread to finish
            logging.info("Recording thread completed")

        finally:
            # Log session completion
            logging.info("C'est fini.")


if __name__ == "__main__":
    # Initialize and run the main program with a 70-second recording duration
    main = Main(recording_duration=70)
    main.run()