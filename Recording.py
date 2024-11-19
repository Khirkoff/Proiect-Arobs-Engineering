import logging
import threading
import numpy as np
import mss
import cv2
import os
import soundcard as sc
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor
import warnings
from moviepy.editor import ImageSequenceClip, AudioFileClip
import time

class Recording:

    def __init__(self, recording_duration):
        # Initialize with the specified recording duration
        self.recording_duration = recording_duration

    def record_screen(self):
        OUTPUT_FOLDER = "Recording"  # Output folder for the recording

        # Log the setup of screen recording
        logging.info("Initializing screen recording setup.")

        # Prevent audio recorder warning spam
        warnings.filterwarnings("ignore")

        # Event to stop recording when hotkey is pressed
        stop_recording = threading.Event()

        # Create the output folder if it doesn't exist
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
            logging.info(f"Created output folder at {OUTPUT_FOLDER}")

        # Setup for screen capture using mss (multi-screen screenshot library)
        sct = mss.mss()
        screen = sct.monitors[1]  # Set the screen to record from (e.g., primary monitor)
        frames = []  # List to store captured frames
        logging.debug(f"Screen dimensions set to {screen}.")

        # Synchronization variables for audio and video recording
        sync_event = threading.Event()
        audio_delay = 1.5  # Audio delay compensation to sync video and audio

        # Function to save each frame to disk
        def save_frame(i, frame, frames_dir):
            frame_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
            cv2.imwrite(frame_path, frame)  # Save the frame as an image
            logging.debug(f"Saved frame {i} to {frame_path}")

        # Function to record audio in chunks and save it to a file
        def record_audio(output_file=os.path.join(OUTPUT_FOLDER, "audio.mp3"), record_sec=self.recording_duration,
                         sample_rate=44100):
            data = []  # List to store audio data chunks

            # Use soundcard library to record audio from the default microphone
            with sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True).recorder(
                    samplerate=sample_rate) as mic:
                sync_event.set()  # Signal that audio recording is ready to start

                chunk_duration = 0.05  # 50ms chunks for better sync with video
                chunk_samples = int(sample_rate * chunk_duration)
                num_chunks = int(record_sec / chunk_duration)

                for _ in range(num_chunks):
                    if stop_recording.is_set():
                        logging.warning("Audio recording stopped early due to stop signal.")
                        break
                    chunk = mic.record(numframes=chunk_samples)  # Record a chunk of audio
                    data.append(chunk[:, 0])  # Append the chunk to the data list

            # Process the recorded audio (concatenate chunks and pad if needed)
            full_data = np.concatenate(data)
            target_samples = int(record_sec * sample_rate)

            if len(full_data) > target_samples:
                full_data = full_data[:target_samples]  # Trim excess audio
            elif len(full_data) < target_samples:
                full_data = np.pad(full_data, (0, target_samples - len(full_data)))  # Pad audio if too short

            # Save the processed audio to file
            sf.write(file=output_file, data=full_data, samplerate=sample_rate)
            logging.info(f"Audio recording saved to {output_file}")

            # Calculate and log the RMS and dB level of the audio
            rms = np.sqrt(np.mean(np.square(full_data)))
            db_level = 20 * np.log10(rms) if rms > 0 else -float('inf')
            logging.info(f"Average sound level: {db_level:.2f} dB")

            # Write the dB level to a file

            db_file = os.path.join(os.getcwd(), "Average_dB.txt")
            with open(db_file, 'w') as f:
                f.write(f"Average Sound Level: {db_level:.2f} dB\n")
            logging.info(f"Average sound level saved to: {db_file}")

        # Start audio recording in a separate thread
        audio_thread = threading.Thread(target=record_audio,
                                        args=(os.path.join(OUTPUT_FOLDER, "audio.mp3"), self.recording_duration))
        logging.info(f"Starting audio recording for {self.recording_duration} seconds.")
        audio_thread.start()

        # Wait for audio to be ready to start
        sync_event.wait()

        # Add a small delay before starting video recording for sync
        time.sleep(audio_delay)

        # Start recording the screen
        start_time = time.perf_counter()  # High precision timer for accurate time tracking
        frame_count = 0
        target_fps = 30  # Target frame rate for video recording
        logging.info("Screen recording started.")

        try:
            while time.perf_counter() - start_time < self.recording_duration:
                if stop_recording.is_set():
                    logging.warning("Screen recording stopped early due to stop signal.")
                    break

                frame_start = time.perf_counter()  # Timer for frame capture

                target_frame_time = frame_count * (1.0 / target_fps)
                current_time = time.perf_counter() - start_time

                if current_time >= target_frame_time:
                    # Capture a frame from the screen
                    img = sct.grab(screen)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # Convert to BGR format
                    frames.append(frame)  # Add frame to the frames list
                    frame_count += 1
                    logging.debug(f"Captured frame {frame_count}")

                # Ensure the frame rate stays close to the target FPS
                elapsed = time.perf_counter() - frame_start
                if elapsed < 1.0 / target_fps:
                    time.sleep(1.0 / target_fps - elapsed)

        except KeyboardInterrupt:
            logging.error("Screen recording interrupted by user.")
            stop_recording.set()

        # Wait for the audio recording thread to finish
        audio_thread.join()
        logging.info("Audio recording thread joined.")

        # Calculate the actual frames per second during the recording
        elapsed_time = time.perf_counter() - start_time
        actual_fps = len(frames) / elapsed_time
        logging.info(f"Actual FPS during recording: {actual_fps:.2f}")

        # Save captured frames to disk
        frames_dir = os.path.join(OUTPUT_FOLDER, "frames")
        if not os.path.exists(frames_dir):
            os.makedirs(frames_dir)
            logging.info(f"Created frames directory at {frames_dir}")

        # Use ThreadPoolExecutor to save frames concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(save_frame, i, frame, frames_dir)
                       for i, frame in enumerate(frames)]
            for future in futures:
                future.result()  # Wait for each frame to be saved

        # Combine video and audio into a final output file
        try:
            current_time_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
            output_video_file = os.path.join(OUTPUT_FOLDER, f"Recording_{current_time_str}.mp4")
            logging.info("Assembling video with MoviePy...")

            # Create video clip from frames and sync with audio
            video_clip = ImageSequenceClip(frames_dir, fps=actual_fps)
            audio_clip = AudioFileClip(os.path.join(OUTPUT_FOLDER, "audio.mp3"))
            sync_offset = 4  # Delay the audio to sync with video
            audio_clip = audio_clip.set_start(sync_offset)
            final_duration = min(video_clip.duration, audio_clip.duration - sync_offset)
            video_clip = video_clip.set_duration(final_duration)
            final_clip = video_clip.set_audio(audio_clip)

            # Write the final video to file
            final_clip.write_videofile(
                output_video_file,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=os.path.join(OUTPUT_FOLDER, "temp-audio.m4a"),
                remove_temp=True,
                threads=4,
                preset='ultrafast'
            )

            video_clip.close()
            audio_clip.close()
            final_clip.close()
            os.remove(os.path.join(OUTPUT_FOLDER, "audio.mp3"))
            logging.info(f"Recording saved as {output_video_file}")

        except Exception as e:
            logging.error(f"An error occurred while combining video and audio: {str(e)}")

        finally:
            # Clean up: remove frames directory and temporary files
            if os.path.exists(frames_dir):
                for file in os.listdir(frames_dir):
                    try:
                        os.remove(os.path.join(frames_dir, file))
                    except Exception as e:
                        logging.warning(f"Error removing frame file: {str(e)}")
                try:
                    os.rmdir(frames_dir)
                except Exception as e:
                    logging.warning(f"Error removing frames directory: {str(e)}")

            frames.clear()  # Clear frames list to free memory
            logging.info(f"Total process time: {time.perf_counter() - start_time}")
