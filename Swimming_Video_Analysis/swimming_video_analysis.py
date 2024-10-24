import tkinter as tk
from tkinter import filedialog, Scale, Entry, Button, ttk, messagebox
import cv2 as cv
from PIL import Image, ImageTk, ImageDraw
import pandas as pd
from pandastable import Table, RowHeader, TableModel
import os
from os.path import join, basename
from pathlib import Path
import tkinter.font as font

# ------------------ CHANGELOG ------------------
#   09.10.2024 Dennis Rentsch: (v2)     Combined scripts swimming_tracks_processing and video_player into one GUI
#                                       Undo function currently not working
#   10.10.2024 Dennis Rentsch: (v2_1)   Adjusted GUI and added File Postprocessing script to the application
#                                       Changed GUI style for TrackProcessing from grid to pack
#   11.10.2024 Dennis Rentsch: (v2_2)   Identified problems for searching for track number if more than 75 tracks are found.
#                                       "*_track_raw.txt" files are now loaded correctly to find track numbers above 75.
#                                       removed .toggleIndex() in combine, delete and undo to keep the Tracks according to the combination


# ------------------ FileHandler Class ------------------

class FileHandler:
    def __init__(self, video_player, track_processor, status_label, root):
        self.video_player = video_player
        self.track_processor = track_processor
        self.status_label = status_label
        self.folder_path = None
        self.videos = []
        self.current_video_index = -1
        self.root = root

    def select_folder(self):
        # Prompt user to select a folder
        folder_selected = filedialog.askdirectory(title="Select Folder Containing Video and Data Files")
        if folder_selected:
            self.folder_path = folder_selected
            # Find all videos with the specified suffix
            self.videos = sorted([f for f in os.listdir(self.folder_path) if f.endswith('_labels_compressed.AVI')])
            total_videos = len(self.videos)
            if self.videos:
                self.current_video_index = 0
                self.load_current_video()
                self.update_status_label()
            else:
                messagebox.showwarning("No Videos Found", "No video files with '_labels_compressed.AVI' found in the selected folder.")
                self.status_label.config(text="No videos found in the selected folder.")

    def load_current_video(self):
        if 0 <= self.current_video_index < len(self.videos):
            video_file = self.videos[self.current_video_index]
            video_path = os.path.join(self.folder_path, video_file)
            # Derive basename by removing the suffix
            base_name = video_file.replace("_labels_compressed.AVI", "")
            # Define paths to associated data files
            track_file = os.path.join(self.folder_path, f"{base_name}_tracks.txt") # Stores major swimming analysis data from wrMTrack
            coords_file = os.path.join(self.folder_path, f"{base_name}_tracks_raw.txt") # Stores X-&Y-Coordinates of worms tracked by wrMTrck
            if os.path.exists(os.path.join(self.folder_path, f"{base_name}_tracks.txt.temp.xlsx")):
                temp_file = os.path.join(self.folder_path, f"{base_name}_tracks.txt.temp.xlsx")
            undo_file = os.path.join(self.folder_path, f"{base_name}_tracks.txt.temp_undo.xlsx")

            try:
                print(f"Loaded video: {video_file}")
                # Load DataFrames
                track_df = pd.read_csv(track_file, sep='\t', header=0)  # Data frame to find frame of which searched for worm track first appears

                # Load coordinate containing file into dataframe with track numbers above 75 by combining sections in the textfile
                with open(coords_file, 'r') as file:
                    lines = file.readlines()

                # Initialize variables for the combination process
                dataframes = []
                header = None
                current_data = []
                current_track_start = 1

                # Function to adjust row length to match header length
                def adjust_row_length(row, header_len):
                    if len(row) > header_len:
                        return row[:header_len]
                    elif len(row) < header_len:
                        return row + [''] * (header_len - len(row))
                    else:
                        return row

                # Loop over lines from the coords file
                for line in lines:
                    line = line.strip()

                    if not line:
                        continue

                    if line.startswith("Frame"):
                        header = line.split("\t")
                        continue

                    if line.startswith("Tracks"):
                        if current_data:
                            min_columns = min(len(header), len(max(current_data, key=len)))
                            df = pd.DataFrame([adjust_row_length(row, min_columns) for row in current_data], columns=header[:min_columns])
                            dataframes.append(df)
                            current_data = []

                        track_range = line.split(" ")[1:4:2]
                        track_start = int(track_range[0])
                        track_end = int(track_range[1])

                        adjusted_header = ["Frame"]
                        for i in range(track_start, track_end + 1):
                            adjusted_header.extend([f"X{i}", f"Y{i}", f"Flag{i}"])
                        header = adjusted_header
                        continue

                    current_data.append(line.split("\t"))

                if current_data:
                    min_columns = min(len(header), len(max(current_data, key=len)))
                    df = pd.DataFrame([adjust_row_length(row, min_columns) for row in current_data], columns=header[:min_columns])
                    dataframes.append(df)

                # Combine all DataFrames into one
                combined_df = dataframes[0]
                for df in dataframes[1:]:
                    combined_df = pd.merge(combined_df, df.drop(columns=["Frame"]), left_index=True, right_index=True)

                # Convert numeric columns to appropriate types
                combined_df = combined_df.apply(pd.to_numeric,
                                                errors='coerce')  # Convert all columns to numeric (floats/ints)
                combined_df = combined_df.fillna(0).astype(int)  # Fill NaNs with 0 and convert to integers

                # Store combined_df as coords_df
                coords_df = combined_df
                # print(coords_df)

                # coords_df = pd.read_csv(coords_file, sep='\t', header=0, skiprows=[1]) # Data frame to identify where worm appears in video (first frame derives from track_df)

                if os.path.exists(os.path.join(self.folder_path, f"{base_name}_tracks.txt.temp.xlsx")): # Data frame for combining and deleting tracks for future analysis
                    process_df = pd.read_excel(temp_file, index_col='Track')
                    print(f"Temporary file found: {temp_file}")
                else:
                    process_df = pd.read_csv(track_file, delimiter="\t").rename(columns={"Track ": "Track"}).set_index('Track')
                    print("No temporary file found. Loaded original track file")
                process_df.to_excel(undo_file)

                # Pass data to VideoPlayer and TrackProcessor
                self.video_player.set_video(video_path, track_df, coords_df)
                self.track_processor.set_track_data(track_df, coords_df, process_df, self.folder_path, base_name)
                self.update_status_label()
            except FileNotFoundError as fnf_error:
                messagebox.showerror("File Not Found", f"Required data files for {video_file} not found.\nError: {fnf_error}")
                print(f"Error loading data for {video_file}: {fnf_error}")
            except Exception as e:
                messagebox.showerror("File Loading Error", f"Error loading data for {video_file}:\n{e}")
                print(f"Error loading data for {video_file}: {e}")
        else:
            messagebox.showinfo("Completed", "All videos have been processed.")
            self.status_label.config(text="All videos have been processed.")

    def save_proceed(self):
        # Save current track data
        self.track_processor.save_file()
        # Move to the next video
        self.current_video_index += 1
        if self.current_video_index < len(self.videos):
            self.load_current_video()
            self.update_status_label()
        else:
            self.video_player.show_placeholder_at_end()
            messagebox.showinfo("Completed", "All videos have been processed.")
            self.status_label.config(text="All videos have been processed.")

    def save_exit(self):
        # Save current track data
        self.track_processor.save_file()
        self.root.destroy()

    def update_status_label(self):
        if self.videos:
            total_videos = len(self.videos)
            current = self.current_video_index + 1  # 1-based indexing for user-friendliness
            status_text = f"(Video {current} of {total_videos})"
            self.status_label.config(text=status_text, font=('Segoe UI', 10))
        else:
            self.status_label.config(text=" ")

# ------------------ VideoPlayer Class ------------------

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.vidFile = cv.VideoCapture("placeholder.jpg") # To load a placeholder image in the beginning
        self.cur_frame = 0
        self.imgtk = None
        self.zoom_level = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.base_scale = 0.33
        self.circle_coords = None  # Coordinates for the circle

        # DataFrames
        self.track_df = None
        self.coords_df = None

        # GUI Components
        title_frame = tk.Frame(root)
        title_frame.pack()

        self.img = Image.open("swim_tracks_ico.ico")
        self.img = self.img.resize((30, 30), Image.LANCZOS)
        self.icon_img = ImageTk.PhotoImage(self.img)
        # self.img = self.img.Image.resize((250, 250), Image.ANTIALIAS)
        self.icon = tk.Label(title_frame, image=self.icon_img)
        self.icon.pack(side=tk.LEFT)

        self.title_label = tk.Label(title_frame, text="Select folder to load video", font=('Segoe UI', 12))
        self.title_label.pack(side=tk.LEFT, pady=(10,0), anchor="center")



        # Removed "Load Video" button since FileHandler manages file loading

        main_frame = tk.Frame(root)
        main_frame.pack()

        zoom_frame = tk.Frame(main_frame)
        zoom_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.zoom_label = tk.Label(zoom_frame, text="Zoom")
        self.zoom_label.pack(pady=(60,0))

        self.zoom_slider = Scale(zoom_frame, orient='vertical', from_=0.33, to=2, resolution=0.1, command=self.on_zoom)
        self.zoom_slider.pack()
        self.zoom_slider.set(0.33)

        self.frame_label = tk.Label(zoom_frame, text="Frame")
        self.frame_label.place(x=0, y=620)

        video_frame = tk.Frame(main_frame)
        video_frame.pack(side=tk.LEFT)

        self.image_label = tk.Label(video_frame, width=800, height=600)
        self.image_label.pack()

        self.slider = Scale(video_frame, orient='horizontal', command=self.on_slider_move)
        self.slider.pack(fill=tk.X)

        control_frame = tk.Frame(root)
        control_frame.pack()

        self.frame_entry = Entry(control_frame)
        self.frame_entry.pack(side=tk.LEFT)

        self.jump_button = Button(control_frame, text="Jump to Frame", command=self.jump_to_frame)
        self.jump_button.pack(side=tk.LEFT, padx=10)

        # Input for finding number
        self.find_number_entry = Entry(control_frame)
        self.find_number_entry.pack(side=tk.LEFT)

        self.find_number_button = Button(control_frame, text="Find Number", command=self.find_number)
        self.find_number_button.pack(side=tk.LEFT, padx=10)

        # Bind events for pan
        self.image_label.bind("<ButtonPress-1>", self.start_pan)
        self.image_label.bind("<B1-Motion>", self.do_pan)

        # # Exit button
        # self.exit_button = tk.Button(root, text="Exit", command=root.quit)
        # self.exit_button.pack(side=tk.BOTTOM)

        # Bind resize event
        self.root.bind("<Configure>", self.on_resize)

    def set_video(self, video_path, track_df, coords_df):
        self.play_video(video_path)
        self.track_df = track_df
        self.coords_df = coords_df

    def play_video(self, filename):
        self.vidFile = cv.VideoCapture(filename)
        self.title_label.config(text=os.path.basename(filename))
        num_frames = int(self.vidFile.get(cv.CAP_PROP_FRAME_COUNT))
        self.slider.config(from_=0, to=num_frames - 1)
        self.update_frame()

    def show_placeholder_at_end(self):
        self.vidFile = cv.VideoCapture("placeholder.jpg")

    def find_number(self):
        if self.track_df is None or self.coords_df is None:
            messagebox.showwarning("Data Not Loaded", "Please load the video and associated data files first.")
            return

        try:
            # Get the number from the user
            number = int(self.find_number_entry.get())

            # Construct the column names dynamically for X and Y based on the user input
            x_column = f"X{number}"
            y_column = f"Y{number}"

            # Ensure that the columns for X and Y exist in the dataframe
            if x_column not in self.coords_df.columns or y_column not in self.coords_df.columns:
                messagebox.showerror("Track Not Found", f"Track {number} not found in the video and respective data.")
                return

            # Get the row corresponding to the input number from the track dataframe
            track_row = self.track_df.loc[self.track_df.index == number].squeeze()

            if not track_row.empty:
                # Retrieve the frame number from the track row
                frame_number = int(track_row['1stFrame'])

                # Get the corresponding row from the coords dataframe using the frame number
                coords_row = self.coords_df.loc[self.coords_df.index == frame_number].squeeze()

                # Fetch the coordinates for X and Y using the frame number and user input number
                x_coord = int(coords_row[x_column])
                y_coord = int(coords_row[y_column])

                # Set the circle coordinates BEFORE updating the frame
                self.circle_coords = (x_coord, y_coord)

                # Flag that we're doing a frame jump related to the find_number operation
                self.is_find_number_operation = True

                # Set the frame and force a single update
                self.cur_frame = frame_number
                self.slider.set(self.cur_frame)
                self.update_frame()

            else:
                messagebox.showerror("Frame Not Found", f"No frame data found for track {number}.")

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer for the track number.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def on_slider_move(self, value):
        self.cur_frame = int(value)
        self.vidFile.set(cv.CAP_PROP_POS_FRAMES, self.cur_frame)
        # Keep the circle coordinates intact if they exist (no reset to None)
        # We only reset the circle if it's a user-driven slider move, not frame jump via find_number
        if not hasattr(self, "is_find_number_operation") or not self.is_find_number_operation:
            self.circle_coords = None  # Reset only if not part of find_number

        # Update the frame
        self.update_frame()

        # Reset the flag after slider move
        if hasattr(self, "is_find_number_operation"):
            self.is_find_number_operation = False
        # self.circle_coords = None  # Remove the circle when manually moving
        # self.update_frame()

    def jump_to_frame(self):
        try:
            frame_number = int(self.frame_entry.get())
            if 0 <= frame_number <= self.slider.cget('to'):
                self.cur_frame = frame_number
                self.vidFile.set(cv.CAP_PROP_POS_FRAMES, self.cur_frame)
                self.slider.set(self.cur_frame)
                self.circle_coords = None
                self.update_frame()
            else:
                messagebox.showerror("Out of Range", "Frame number out of range.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer for the frame number.")

    def on_zoom(self, value):
        zoom_value = float(value)
        if zoom_value <= 1.0:
            # Adjust base_scale proportionally
            self.base_scale = 0.33 + (zoom_value - 0.33) * (1.0 - 0.33) / (1.0 - 0.33)
            self.zoom_level = 1.0
        else:
            self.base_scale = 1.0
            self.zoom_level = zoom_value
        self.update_frame()

    def start_pan(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def do_pan(self, event):
        self.pan_offset_x -= event.x - self.pan_start_x
        self.pan_offset_y -= event.y - self.pan_start_y
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.update_frame()

    def on_resize(self, event):
        if self.vidFile is not None:
            self.update_frame()

    def update_frame(self):
        if self.vidFile is None or not self.vidFile.isOpened():
            return

        self.vidFile.set(cv.CAP_PROP_POS_FRAMES, self.cur_frame)
        ret, frame = self.vidFile.read()
        if not ret:
            return

        img = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        img = Image.fromarray(img)

        # Scale the image based on the base scale
        new_width = int(img.width * self.base_scale)
        new_height = int(img.height * self.base_scale)
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Apply zoom
        width, height = img.size
        new_width = int(width * self.zoom_level)
        new_height = int(height * self.zoom_level)
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Apply pan
        try:
            img = img.crop(
                (self.pan_offset_x, self.pan_offset_y, self.pan_offset_x + width, self.pan_offset_y + height))
        except Exception as e:
            print(f"Error during cropping: {e}")
            return

        # If we have circle coordinates, adjust them for zoom and pan and draw the circle
        if self.circle_coords:
            draw = ImageDraw.Draw(img)
            x, y = self.circle_coords

            # Adjust coordinates based on zoom and pan
            adjusted_x = (x * self.base_scale * self.zoom_level) - self.pan_offset_x
            adjusted_y = (y * self.base_scale * self.zoom_level) - self.pan_offset_y

            circle_radius = 20  # Adjust the size of the circle as necessary
            draw.ellipse((adjusted_x - circle_radius, adjusted_y - circle_radius,
                          adjusted_x + circle_radius, adjusted_y + circle_radius),
                         outline='red', width=3)

        self.imgtk = ImageTk.PhotoImage(image=img)
        self.image_label.imgtk = self.imgtk  # Keep a reference to avoid garbage collection
        self.image_label.configure(image=self.imgtk)

        # Adjust the slider length to match the video width
        self.slider.config(length=self.image_label.winfo_width())

# ------------------ TrackProcessor Class ------------------

class TrackProcessor:
    def __init__(self, gui, video_player):
        self.gui = gui
        self.video_player = video_player  # Reference to VideoPlayer instance
        self.track_df = None
        self.coords_df = None
        self.process_df = None
        self.folder_path = None
        self.base_name = None
        self.setup_gui()

    def setup_gui(self):
        self.gui.pack_propagate(False)  # Prevent the frame from resizing to fit its content
        self.gui.config(width=600, height=550)  # Set the desired width and height

        myFont = font.Font(family='Cambria', size=10, weight="bold")
        fileFont = font.Font(size=9, weight="bold")

        # # Display current track basename
        # self.basename_label = tk.Label(self.gui, text="No track loaded", font=fileFont)
        # self.basename_label.pack(ipadx=90, padx=2, pady=10)

        # Horizontal separator
        ttk.Separator(self.gui, orient="horizontal").pack(fill='x', padx=15, pady=(0, 10))

        # Frame for the table
        self.f = tk.Frame(self.gui)
        self.f.pack(fill='both', expand=True)
        self.pt = Table(self.f, dataframe=pd.DataFrame())
        self.pt.show()

        # # Bind double-click event to the table
        # self.pt.bind("<Double-1>", self.on_double_click)

        # Bind double-click event on the row header (for index)
        self.pt.rowheader.bind("<Double-1>", self.on_index_double_click)

        # Horizontal separator
        ttk.Separator(self.gui, orient="horizontal").pack(fill='x', padx=15, pady=(10, 10))

        # Frame for undo button and track operations
        operations_frame = tk.Frame(self.gui)
        operations_frame.pack(fill='x', padx=5, pady=(5, 10))

        # Undo button
        self.undo_button = ttk.Button(operations_frame, text='↩ Undo', command=self.undo)
        self.undo_button.pack(side='left', padx=(5, 5), pady=(5, 5))

        # Frame for combine and delete sections
        track_operations_frame = tk.Frame(operations_frame)
        track_operations_frame.pack(side='left', fill='x', expand=True, padx=(5, 10))

        # Combine tracks section
        combine_frame = tk.Frame(track_operations_frame)
        combine_frame.pack(fill='x', pady=(0, 5))

        tk.Label(combine_frame, text="Combine tracks").pack(side='left', padx=(0, 5))
        self.entry_combine_tracks = tk.StringVar()
        combine_entry = tk.Entry(combine_frame, textvariable=self.entry_combine_tracks)
        combine_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(combine_frame, text="Combine", command=self.combine_tracks).pack(side='left', padx=(0, 5))

        combine_tracks_info = "Specify track numbers to be combined separated by commas.\nDo not use spaces after comma!\ne.g. '2,7,12,23,50'\nRepeat for next track until finished."
        combine_tracks_infobutton = tk.Button(combine_frame, text='i', font=myFont, bg='white', fg='blue', bd=0)
        create_tooltip(combine_tracks_infobutton, text=combine_tracks_info)
        combine_tracks_infobutton.pack(side='left', padx=5)

        # Delete tracks section
        delete_frame = tk.Frame(track_operations_frame)
        delete_frame.pack(fill='x', pady=(5, 0))

        tk.Label(delete_frame, text="Delete tracks     ").pack(side='left', padx=(0, 5))
        self.entry_delete_tracks = tk.StringVar()
        delete_entry = tk.Entry(delete_frame, textvariable=self.entry_delete_tracks)
        delete_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(delete_frame, text="Delete", command=self.delete_tracks).pack(side='left', padx=(0, 5))

        delete_tracks_info = "Specify track numbers to be deleted separated by commas.\nDo not use spaces after comma!\ne.g. '1,5,9,10,27'"
        delete_tracks_infobutton = tk.Button(delete_frame, text='i', font=myFont, bg='white', fg='blue', bd=0)
        create_tooltip(delete_tracks_infobutton, text=delete_tracks_info)
        delete_tracks_infobutton.pack(side='left', padx=5)

        # Horizontal separator
        ttk.Separator(self.gui, orient="horizontal").pack(fill='x')

    def set_track_data(self, track_df, coords_df, process_df, folder_path, base_name):
        self.track_df = track_df
        self.coords_df = coords_df
        self.process_df = process_df
        self.folder_path = folder_path
        self.base_name = base_name
        # Update the Table
        self.load_track_file_from_data(process_df)
        # # Update the basename label
        # self.basename_label.config(text=f"File: {base_name}")

    def load_track_file_from_data(self, process_df):
        # Update the pandastable with the new DataFrame
        relevant_columns = process_df[['#Frames', '1stFrame', 'time(s)', 'Bends', 'BBPS']] # display only columns relevant for combining tracks
        self.pt.updateModel(TableModel(relevant_columns))
        self.pt.redraw()
        RowHeader(table=self.pt).toggleIndex()
        self.pt.redraw()

    def combine_tracks(self):
        if self.process_df is None:
            messagebox.showwarning("No Track Data", "Please load a track first.")
            return

        try:
            track_list = list(map(int, self.entry_combine_tracks.get().split(",")))
            log_root = os.path.join(self.folder_path, "tracks_processed", f"{self.base_name}_log.txt")
            undo_file = os.path.join(self.folder_path, f"{self.base_name}_tracks.txt.temp_undo.xlsx")
            temp_file = os.path.join(self.folder_path, f"{self.base_name}_tracks.txt.temp.xlsx")

            # Ensure the 'tracks_processed' directory exists
            Path(os.path.dirname(log_root)).mkdir(parents=True, exist_ok=True)

            #Write to undo file
            self.process_df.to_excel(undo_file)
            # print(self.process_df)

            # Rename each track to the first track in the list
            for i in range(len(track_list)):
                self.process_df = self.process_df.rename(index={track_list[i]: track_list[0]})

            # Group by the new index and sum the values
            self.process_df = self.process_df.groupby('Track').sum()

            # Write temporary file in case anything crashes
            self.process_df.to_excel(temp_file)
            # Update the Table
            relevant_columns = self.process_df[['#Frames', '1stFrame', 'time(s)', 'Bends', 'BBPS']] # display only columns relevant for combining tracks
            self.pt.updateModel(TableModel(relevant_columns))
            self.pt.redraw()
            RowHeader(table=self.pt) # removed .toggleIndex() to keep the Tracks according to the combination
            self.pt.redraw()


            # Log the combination
            with open(log_root, "a") as log_file:
                log_file.write(f"Tracks {', '.join(map(str, track_list))} combined to Track {track_list[0]}!\n")
            self.entry_combine_tracks.set("")
            print(f"Tracks {', '.join(map(str, track_list))} combined successfully.")
            # messagebox.showinfo("Success", f"Tracks {', '.join(map(str, track_list))} combined successfully.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integers separated by commas (without spaces in between!).")
        # except Exception as e:
        #     messagebox.showerror("Error", f"Error combining tracks:\n{e}")

    def delete_tracks(self):
        if self.process_df is None:
            messagebox.showwarning("No Track Data", "Please load a track first.")
            return

        try:
            delete_list = list(map(int, self.entry_delete_tracks.get().split(",")))
            log_root = os.path.join(self.folder_path, "tracks_processed", f"{self.base_name}_log.txt")
            undo_file = os.path.join(self.folder_path, f"{self.base_name}_tracks.txt.temp_undo.xlsx")
            temp_file = os.path.join(self.folder_path, f"{self.base_name}_tracks.txt.temp.xlsx")

            # Ensure the 'tracks_processed' directory exists
            Path(os.path.dirname(log_root)).mkdir(parents=True, exist_ok=True)

            # Write to undo file
            self.process_df.to_excel(undo_file)
            # Delete track
            self.process_df = self.process_df.drop(delete_list)
            # Write to temporary file in case anything crashes
            self.process_df.to_excel(temp_file)

            # Update the Table
            # self.pt.updateModel(TableModel(self.process_df))
            relevant_columns = self.process_df[['#Frames', '1stFrame', 'time(s)', 'Bends',
                                                'BBPS']]  # display only columns relevant for combining tracks
            self.pt.updateModel(TableModel(relevant_columns))
            self.pt.redraw()
            RowHeader(table=self.pt) # removed .toggleIndex() to keep the Tracks according to the combination
            self.pt.redraw()

            # Log the deletion
            with open(log_root, "a") as log_file:
                log_file.write(f"Track(s) {', '.join(map(str, delete_list))} deleted!\n")
            self.entry_delete_tracks.set("")
            print(f"Track(s) {', '.join(map(str, delete_list))} deleted successfully.")
            # messagebox.showinfo("Success", f"Track(s) {', '.join(map(str, delete_list))} deleted successfully.")
        except KeyError as ke:
            messagebox.showerror("Deletion Error", f"One or more tracks not found:\n{ke}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integers separated by commas.")
        # except Exception as e:
        #     messagebox.showerror("Error", f"Error deleting tracks:\n{e}")

    def undo(self):
        if self.process_df is None:
            messagebox.showwarning("No Track Data", "Please load a track first.")
            return

        try:
            log_root = os.path.join(self.folder_path, "tracks_processed", f"{self.base_name}_log.txt")
            undo_file = os.path.join(self.folder_path, f"{self.base_name}_tracks.txt.temp_undo.xlsx")
            temp_file = os.path.join(self.folder_path, f"{self.base_name}_tracks.txt.temp.xlsx")

            # Load process_df from undo_file
            self.process_df = pd.read_excel(undo_file, index_col='Track')
            # Write to temporary file in case anything crashes
            self.process_df.to_excel(temp_file)

            # Update the Table
            # self.pt.updateModel(TableModel(self.process_df))
            relevant_columns = self.process_df[['#Frames', '1stFrame', 'time(s)', 'Bends',
                                                'BBPS']]  # display only columns relevant for combining tracks
            self.pt.updateModel(TableModel(relevant_columns))
            self.pt.redraw()
            RowHeader(table=self.pt) # removed .toggleIndex() to keep the Tracks according to the combination
            self.pt.redraw()
            # Log the deletion
            with open(log_root, "a") as log_file:
                log_file.write(f"Last step undone.\n")
            print(f"Last step undone.\n")

        except KeyError as ke:
            messagebox.showerror("Undo Error", f"Something went wrong reversing the last action:\n{ke}")

    def save_file(self):
        if self.process_df is None:
            messagebox.showwarning("No Track Data", "There is no track data to save.")
            return

        try:
            processed_root = os.path.join(self.folder_path, "tracks_processed")
            Path(processed_root).mkdir(parents=True, exist_ok=True)
            filename_tracks = self.base_name

            selected_columns = self.process_df[["#Frames", "time(s)", "Bends"]]
            # Compute additional metrics
            df2 = selected_columns.copy()
            df2['BBPS'] = self.process_df['Bends'].div(self.process_df['time(s)'], axis=0)
            df2['BBPM'] = df2['BBPS'] * 60
            df2['mean (BBPM)'] = df2['BBPM'].mean()
            df2['SEM'] = df2['BBPM'].sem()
            df2['n'] = len(df2['BBPM'])

            max_value = self.process_df['time(s)'].max()
            threshold_value = max_value * 0.5
            df3 = df2[df2['time(s)'] > threshold_value].copy()
            df3['mean (BBPM)'] = df3['BBPM'].mean()
            df3['SEM'] = df3['BBPM'].sem()
            df3['n'] = len(df3['BBPM'])

            # Save to Excel
            with pd.ExcelWriter(os.path.join(processed_root, f"{filename_tracks}_processed.xlsx")) as writer:
                df3.to_excel(writer, sheet_name='>50%_tracked_swimming_cycles')
                df2.to_excel(writer, sheet_name='all_swimming_cycles')
                self.process_df.to_excel(writer, sheet_name='all_data')

            messagebox.showinfo("Save Successful", f"Processed data saved to {processed_root}.")
            self.reset_gui()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integers separated by commas (without spaces in between!).")
        # except Exception as e:
        #     messagebox.showerror("Error", f"Error saving file:\n{e}")

    def reset_gui(self):
        self.entry_combine_tracks.set("")
        self.entry_delete_tracks.set("")
        self.track_df = None
        self.coords_df = None
        self.pt.updateModel(TableModel(pd.DataFrame()))
        self.pt.redraw()
        # self.basename_label.config(text="No track loaded")

    def save_proceed(self):
        self.save_file()
        # The FileHandler will call load_next_video, so no need to get_track_path here
        # This method should be connected via FileHandler's save_proceed

    def save_close(self):
        self.save_file()
        self.gui.master.destroy()

    def on_index_double_click(self, event):
        """Handle double-click event on the row index (header)."""
        # Get the row that was clicked
        row_clicked = self.pt.get_row_clicked(event)

        # Get the index value from the DataFrame
        index_value = self.pt.model.df.index[row_clicked]
        print(f"Searching for Track: {index_value}")

        # Pass the value to another method (or do something with it)
        self.pass_index_to_video_player(index_value)

    def pass_index_to_video_player(self, index_value):
        """Pass the index value to the VideoPlayer and trigger 'Find Number'."""
        # Set the index value in the find_number_entry of VideoPlayer
        self.video_player.find_number_entry.delete(0, tk.END)  # Clear the field
        self.video_player.find_number_entry.insert(0, int(index_value))  # Insert the index value

        # Trigger the find_number function in VideoPlayer
        self.video_player.find_number()

# ------------------ PostProcessing Class ------------------

class FilePostprocessing:
    def __init__(self, root):
        self.root = root
        self.data_root = None

        # Set up the GUI
        self.setup_gui()

    def setup_gui(self):
        """Create the GUI with a toggle button and a collapsible frame inside a bordered frame."""
        # self.root.title("File Postprocessing")

        myFont = font.Font(family='Cambria', size=10, weight="bold")

        # Create a bordered frame with a slightly darker background
        self.border_frame = ttk.Frame(self.root, padding=10, relief="solid", borderwidth=2)
        self.border_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # Set a slightly darker background color for the box
        self.border_frame.config(style="BorderedFrame.TFrame")

        # Create the toggle button, make it smaller, and align it to the top-left of the box
        self.toggle_button = tk.Button(
            self.border_frame, text="Open Postprocessing ▼", command=self.toggle_controls,
            font=('Segoe UI', 8), width=20, anchor='w'
        )
        self.toggle_button.pack(anchor='nw')

        self.postprocessing_info = """
Folder Structure for FilePostprocessing:

Instructions:
- Create an folder for the experiment (e.g. exp_day) with condition subfolders (cond1, cond2...) (e.g. strain a, strain b).
- Inside each condition, add line folders (line1, line2...) (e.g. dark, light, pulsed, ...).
- Important: Create or copy the "tracks_processed" into the subfolder of each line. This is necessary for the script to work.
- Place the processed track files (*_tracks_edited_processed.xlsx) inside the "tracks_processed" subfolder of each line.
- The results will be saved in the respective line folder as <line_name>_results.xlsx.

exp_day/
│
├── cond1/
│   ├── line1/
│   │   └── tracks_processed/
│   │        └── <data_files>
│   ├── line2/
│   │   └── tracks_processed/
│   │        └── <data_files>
│   └── line3/
│       └── tracks_processed/
│            └── <data_files>
│
├── cond2/
│   ├── line4/
│   │   └── tracks_processed/
│   │        └── <data_files>
│   ├── line5/
│   │   └── tracks_processed/
│   │        └── <data_files>
│   └── line6/
│       └── tracks_processed/
│            └── <data_files>
│
└── cond3/
    └── line7/
        └── tracks_processed/
             └── <data_files>
"""
        self.postprocessing_infobutton = tk.Button(self.border_frame, text='i', font=myFont, bg='white', fg='blue', bd=0)
        create_tooltip(self.postprocessing_infobutton, text=self.postprocessing_info)
        self.postprocessing_infobutton.pack(side='left', pady=17, padx=10)

        # Create a frame for the main controls (initially hidden)
        self.controls_frame = tk.Frame(self.border_frame, bg="#E6E6E6")  # A faintly darker grey for inner controls

        # Label to display the full selected folder path
        self.folder_label = tk.Label(self.controls_frame, text="No folder selected", wraplength=380, anchor="w",
                                     justify="left", bg="#E6E6E6")
        self.folder_label.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill='x')

        # Button to select the folder
        self.select_button = tk.Button(self.controls_frame, text="Select Folder", command=self.select_folder)
        self.select_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Button to process the data (disabled initially)
        self.process_button = tk.Button(self.controls_frame, text="Process Data", command=self.process_line_folders,
                                        state=tk.DISABLED)
        self.process_button.pack(side=tk.LEFT, padx=5, pady=5)

    def toggle_controls(self):
        """Toggle the visibility of the controls frame."""
        if self.controls_frame.winfo_ismapped():
            self.controls_frame.pack_forget()
            self.toggle_button.config(text="Open Postprocessing ▼")
        else:
            self.controls_frame.pack(pady=10, padx=10, fill='x')
            self.toggle_button.config(text="Close Postprocessing ▲")

    def select_folder(self):
        """Open a file dialog to select the data root folder and display its full path."""
        self.data_root = filedialog.askdirectory(title="Select Root Folder")
        if self.data_root:
            # Update the label with the full selected folder path
            self.folder_label.config(text=self.data_root)
            messagebox.showinfo("Folder Selected", f"Selected folder:\n{self.data_root}")
            # Enable the process button after selecting a folder
            self.process_button.config(state=tk.NORMAL)

    def process_line_folders(self):
        """Process each line folder within the condition folders."""
        if not self.data_root:
            messagebox.showerror("Error", "No folder selected.")
            return

        for rootdir, dirs, files in os.walk(self.data_root):
            for cond_folder in dirs:
                condition_path = join(rootdir, cond_folder)
                line_folders = self.find_subfolders(condition_path)

                for line_folder in line_folders:
                    tracks_processed_path = join(line_folder, "tracks_processed")
                    if os.path.exists(tracks_processed_path):
                        self.analyze_data(line_folder, tracks_processed_path)
                    # else:
                    #     print(f"Skipping {line_folder}: 'tracks_processed' folder not found.")

        messagebox.showinfo("Process Complete", "Data processing complete.")

    def find_subfolders(self, condition_path):
        """Find subfolders under a condition folder (e.g., line1, line2)."""
        subfolders = []
        for root, dirs, _ in os.walk(condition_path):
            for dir_name in dirs:
                subfolders.append(join(root, dir_name))
        return subfolders

    def analyze_data(self, line_folder, tracks_processed_path):
        """Analyze data inside a tracks_processed folder and write output to the line folder."""
        text_paths = []
        file_names = []

        # Collect files from tracks_processed
        for root, _, files in os.walk(tracks_processed_path):
            for file in files:
                if "_processed.xlsx" in file:
                    text_paths.append(join(root, file))
                    file_names.append(file[:-9])

        all_dfs = []
        wanted_columns = ['BBPM']

        # Process each file, extract desired columns, and rename them
        for text_path in text_paths:
            data = pd.read_excel(text_path, header=0)
            if wanted_columns:
                data = data[wanted_columns]
            data = data.rename(columns={"BBPM": basename(text_path)})
            all_dfs.append(data)

        if all_dfs:
            # Concatenate data from all files
            master_df = pd.concat(all_dfs, axis=1)

            # Output the results to the line folder
            output_file = join(line_folder, f"{basename(line_folder)}_results.xlsx")
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                master_df.to_excel(writer, sheet_name=basename(line_folder))

            print(f"Results written to: {output_file}")
        # else:
        #     print(f"No '_processed.xlsx' files found in {tracks_processed_path}")


# ------------------ ToolTip Class ------------------

class ToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None

    def showtip(self, text):
        if self.tipwindow or not text:
            return

        # Get the widget position and size
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() + 27

        # Create tooltip window
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)

        # Create and pack the label in the tooltip
        label = tk.Label(tw, text=text, justify="left",
                         background="#ffffe0", relief="solid", borderwidth=1,
                         font=("tahoma", "10", "normal"))
        label.pack(ipadx=1)

        # Update the window to get the correct width and height
        tw.update_idletasks()  # Ensure the geometry is calculated after packing

        # Get the parent window dimensions
        parent = self.widget.winfo_toplevel()  # Get the parent window
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Calculate tooltip width and height
        tooltip_width = label.winfo_reqwidth()
        tooltip_height = label.winfo_reqheight()

        # Adjust x position if it exceeds the parent window width
        if x + tooltip_width > parent_x + parent_width:
            x = parent_x + parent_width - tooltip_width - 10  # 10 pixels padding from the right

        # Adjust y position if it exceeds the parent window height
        if y + tooltip_height > parent_y + parent_height:
            y = parent_y + parent_height - tooltip_height - 10  # 10 pixels padding from the bottom

        # Set the position of the tooltip
        tw.wm_geometry(f"+{x}+{y}")

    def hidetip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
        self.tipwindow = None

def create_tooltip(widget, text):
    toolTip = ToolTip(widget)
    widget.bind('<Enter>', lambda event: toolTip.showtip(text))
    widget.bind('<Leave>', lambda event: toolTip.hidetip())

# ------------------ Main Function ------------------

def main():
    root = tk.Tk()
    root.geometry("1450x720")  # Adjust the window size to fit both sections and top frame
    root.title("Swimming Video Analysis")
    root.iconbitmap('swim_tracks_ico.ico')

    # # Top frame for Select Folder, Save & Proceed buttons and status indicator
    # top_frame = tk.Frame(root)
    # top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

    # Create frames for each section
    left_frame = tk.Frame(root, width=850, height=600)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

    right_frame = tk.Frame(root, width=400, height=600)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)

    # Initialize VideoPlayer in left_frame
    video_player = VideoPlayer(left_frame)

    # Top frame inside right frame (for Select Folder, Save & Proceed buttons, and status)
    top_frame = tk.Frame(right_frame, height=100)  # Reduce the height for this section
    top_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=10)

    # Status label inside top_frame
    status_label = tk.Label(top_frame, text=" ", font=("Helvetica", 12))
    status_label.pack(side=tk.RIGHT, padx=10)

    # Initialize TrackProcessor in the middle part of the right frame
    track_processor_frame = tk.Frame(right_frame, height=400)  # Give it a fixed height
    track_processor_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=25)  # Don't expand beyond its height
    track_processor = TrackProcessor(track_processor_frame, video_player)

    # Initialize space between TrackProcessor and FilePostprocessing

    # separator_space = tk.Frame(right_frame, height=50)
    # separator_space.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

    # Initialize FilePostprocessing in the lower part of the right frame
    file_postprocessing_frame = tk.Frame(right_frame, height=200)  # Give it the rest of the space
    file_postprocessing_frame.pack(fill=tk.BOTH, expand=False, padx=25)
    file_postprocessing = FilePostprocessing(file_postprocessing_frame)

    # Initialize FileHandler
    file_handler = FileHandler(video_player, track_processor, status_label, root)

    # Add Select Folder and Save & Proceed buttons inside the top_frame
    select_folder_button = tk.Button(top_frame, text="Select Folder", command=file_handler.select_folder)
    select_folder_button.pack(side=tk.LEFT, padx=10)

    save_proceed_button = tk.Button(top_frame, text="Save & Proceed", command=file_handler.save_proceed)
    save_proceed_button.pack(side=tk.LEFT, padx=10)

    save_exit_button = tk.Button(top_frame, text="Save & Exit",bg='#ff6666', relief='groove', command=file_handler.save_exit)
    save_exit_button.pack(side=tk.LEFT, padx=10)

    root.mainloop()


if __name__ == "__main__":
    main()
