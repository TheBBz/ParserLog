import json
import threading
import io
import logging
import webbrowser
import os
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, StringVar
import tkinter.font as tkFont
from collections import deque
import logging
import traceback
import tkinter.messagebox as messagebox

logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class LogProcessor:
    def __init__(self, root):
        logging.info("Initializing LogProcessor")
        self.root = root
        self.setup_ui() 

        try:
            self.treeview_data = deque()  # Update here
            self.processing_thread = None
            self.config_labels = {}
            self.processed_data = []
            self.full_log_data = {}
            self.logs_tree = self.setup_ui()
            self.current_offset = 0  # Track the current offset in the logs
            self.chunk_size = 1000  # Define how many entries to load at once
            self.treeview_loaded = True
            self.progress_bar.grid_remove()  # This hides the progress bar
            self.activity_filter = ''
            self.error_filter = 'Any'
        except Exception as e:
            logging.error(f"An error occurred during initialization of LogProcessor: {e}\n{traceback.format_exc()}")
            return None
        
    def validate_file_format(self, file_path):
        """
        Check if the provided file has the correct format.
        The expected format is a series of lines with a timestamp followed by JSON data.
        """
        try:
            # Open the file and read the first few lines to check the format
            with io.BufferedReader(io.FileIO(file_path, 'r')) as file:
                for _ in range(10):  # Read up to first 10 lines for the sake of checking
                    line = file.readline().decode('utf-8', errors='replace').strip()
                    if not line:  # Skip empty lines if any
                        continue
                    
                    # Attempt to split the line into a timestamp and JSON data
                    if " " in line:
                        timestamp, json_data_str = line.split(" ", 1)
                        # Attempt to parse the JSON data string
                        json.loads(json_data_str)
                    else:
                        raise ValueError("Line does not match expected format.")
            # The above will raise an error if the format is incorrect
            return True
        except (IOError, ValueError, json.JSONDecodeError) as e:
            logging.error(f"File validation error: {e}")
            return False
        
    def setup_ui(self):
        logging.info("Setting up UI components")
        try:
            self.root.resizable(True, True)
            self.root.title("ElectroNeek Log Parser")
            # Grid configuration for root
            self.root.grid_rowconfigure(0, weight=0)  # Button frame
            self.root.grid_rowconfigure(1, weight=0)  # Separator 1
            self.root.grid_rowconfigure(2, weight=0)  # Config frame
            self.root.grid_rowconfigure(3, weight=0)  # Progress bar
            self.root.grid_rowconfigure(4, weight=0)  # Separator 2
            self.root.grid_rowconfigure(5, weight=1)  # Logs frame
            self.root.grid_rowconfigure(6, weight=1)  # Logs frame
            # Button frame with padding to align buttons with "Complete logs" tree
            self.button_frame = tk.Frame(self.root)
            self.button_frame.grid(row=0, column=0, sticky='w', padx=10, pady=10)
            self.button_frame.grid_columnconfigure(0, weight=1)
            self.button_frame.grid_columnconfigure(1, weight=1)
            self.file_button = tk.Button(self.button_frame, text="Open File", command=self.open_file)  # Assuming the command is already defined
            self.file_button.grid(row=0, column=0, padx=5, pady=5)
            self.help_button = tk.Button(self.button_frame, text="Help", command=self.open_help)  # Assuming the command is already defined
            self.help_button.grid(row=0, column=1, padx=5, pady=5)
            self.separator1 = ttk.Separator(self.root, orient='horizontal')
            self.separator1.grid(row=1, column=0, sticky='ew', pady=(5, 5))
            # System Config Frame
            self.root.grid_columnconfigure(0, weight=1)
            # Set up the system configuration frame
            self.config_frame = tk.Frame(self.root, padx=10, pady=2)
            self.config_frame.grid(row=2, column=0, sticky='ew', pady=(2, 2))
            # To make the system configuration labels and values expandable
            self.config_frame.grid_columnconfigure(1, weight=1)
            # Example Label widgets inside the config_frame
            tk.Label(self.config_frame, text="Config Key:").grid(row=0, column=0, sticky='w')
            tk.Label(self.config_frame, text="Config Value", bg="lightgrey").grid(row=0, column=1, sticky='ew')
            self.progress_var = tk.DoubleVar()
            self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, length=400)
            self.progress_bar.grid(row=3, column=0, pady=(5, 5), padx=(10, 10))
            self.filter_frame = tk.Frame(self.root, padx=10, pady=2)
            self.filter_frame.grid(row=5, column=0, sticky='ew', pady=(2, 2))  # Placing it below the logs_frame
            tk.Label(self.filter_frame, text="Filter by Activity Name:").grid(row=0, column=0, sticky='w')
            self.activity_filter_combobox = ttk.Combobox(self.filter_frame, values=self.load_activities_from_json())
            self.activity_filter_combobox.grid(row=0, column=1, sticky='ew')
        
            tk.Label(self.filter_frame, text="Filter by Error:").grid(row=1, column=0, sticky='w')
            self.error_filter_var = tk.StringVar(value="Any")
            self.error_filter_menu = tk.OptionMenu(self.filter_frame, self.error_filter_var, "Any", "Yes", "No")
            self.error_filter_menu.grid(row=1, column=1, sticky='ew')
            self.filter_button = tk.Button(self.filter_frame, text="Apply Filter", command=self.apply_filter)
            self.filter_button.grid(row=0, column=2, rowspan=2, padx=5, pady=5)
            self.remove_filter_button = tk.Button(self.filter_frame, text="Remove Filter", command=self.remove_filter)
            self.remove_filter_button.grid(row=0, column=3, rowspan=2, padx=5, pady=5)
                    
            self.separator2 = ttk.Separator(self.root, orient='horizontal')
            self.separator2.grid(row=4, column=0, sticky='ew', pady=(2, 5))
            
            self.config_label = tk.Label(self.config_frame, text="System Configuration", font=("Arial", 12))
            self.config_label.grid(row=0, column=0, sticky="w")
            self.config_label.config(font=("Arial", 12, "bold"))
            self.config_defaults = {
                "Windows Version": "N/A",
                "CPU Name": "N/A",
                "CPU Cores": "N/A",
                "Memory Ram": "N/A",
                "Hard Drive Details": "N/A",
                "Computer Manufacturer": "N/A",
                "Computer Model": "N/A"
            }
            self.config_labels = {}
            for index, key in enumerate(self.config_defaults, start=1):
                label = tk.Label(self.config_frame, text=f"{key}:", width=20, anchor="e")
                label.grid(row=index, column=0, padx=(0, 5), sticky="e")
                value_label = tk.Label(self.config_frame, text=self.config_defaults[key], anchor="w")
                value_label.grid(row=index, column=1, sticky="w", padx=5)
                self.config_labels[key] = value_label
            

                        # Create Treeviews
            self.logs_frame = tk.Frame(self.root)
            self.logs_frame.grid(row=6, column=0, sticky='nsew')
            self.logs_frame.grid_rowconfigure(0, weight=1)
            self.logs_frame.grid_columnconfigure(0, weight=1)


            # Create a canvas
            self.logs_canvas = tk.Canvas(self.logs_frame)
            self.logs_canvas.grid(row=0, column=0, sticky='nsew')


            self.tree_frame = ttk.Frame(self.logs_canvas)
            self.logs_canvas.create_window((0,0), window=self.tree_frame, anchor="nw")
            # This function updates the canvas's scrollregion whenever the size of the frame inside it changes.

            self.logs_canvas.configure(scrollregion=self.logs_canvas.bbox("all"))
            self.tree_frame.bind("<Configure>", self.on_frame_configure)
        
            self.logs_tree = ttk.Treeview(self.logs_frame, columns=("Time", "Activity Name", "Status", "Executed Branch", "Output Result", "Error Message"), show="headings")
            self.logs_tree.grid(row=0, column=0, sticky='nsew')
            self.logs_tree.bind('<MouseWheel>', self.on_scroll)  # Add this line here

            self.v_scrollbar = ttk.Scrollbar(self.logs_frame, orient="vertical", command=self.logs_tree.yview)
            self.v_scrollbar.grid(row=0, column=1, sticky='ns')
            self.logs_tree.config(yscrollcommand=self.v_scrollbar.set)
            self.h_scrollbar = ttk.Scrollbar(self.logs_frame, orient="horizontal", command=self.logs_tree.xview)
            self.h_scrollbar.grid(row=1, column=0, sticky='ew')
            self.logs_tree.config(xscrollcommand=self.h_scrollbar.set)
            # Configure the canvas
            self.logs_canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
            self.logs_canvas.bind('<Configure>', lambda e: self.logs_canvas.configure(scrollregion=self.logs_canvas.bbox("all")))
            # Set up headings for 'Logs' Treeview
            self.logs_tree.heading("Time", text="Time")
            self.logs_tree.heading("Activity Name", text="Activity Name")
            self.logs_tree.heading("Status", text="Status")
            self.logs_tree.heading("Executed Branch", text="Executed Branch")
            self.logs_tree.heading("Output Result", text="Output Result")
            self.logs_tree.heading("Error Message", text="Error Message")
            self.logs_tree.tag_configure('error', background='red', foreground='white')
            # Dynamically set the width of the columns based on the title's width

            for col in self.logs_tree["columns"]:
                self.logs_tree.column(col, width=tkFont.Font().measure(col.title()), minwidth=50, stretch=tk.YES)
            self.root.grid_rowconfigure(2, weight=1)  # To make the logs_frame expand vertically
            self.root.grid_columnconfigure(0, weight=1)  # To make all columns in the main window expand horizontally
            self.config_frame.grid_rowconfigure(7, weight=1)  # To allow system config labels to take up space
            self.config_frame.grid_columnconfigure(1, weight=1)  # To make the system config values expand horizontally
            self.logs_tree.bind("<Button-3>", self.show_context_menu)  # Button-3 represents the right mouse button
        except Exception as e:
            logging.error(f"An error occurred during UI setup: {e}\n{traceback.format_exc()}")
        return self.logs_tree       

    def load_activities_from_json(self):
        with open("output.json", "r") as file:
            data = json.load(file)
        activities = [activity.lower() for activity in data.get("activities", {})]
        return activities
    
    def apply_filter(self):
        # Grab the filter criteria
        activity_filter = self.activity_filter_combobox.get().lower()
        error_filter = self.error_filter_var.get()
        # Store the filter criteria as instance variables so they can be accessed in populate_treeview
        self.activity_filter = activity_filter
        self.error_filter = error_filter
        # Re-populate the treeview with the current filter criteria
        self.populate_treeview(0)


    def on_frame_configure(self, event):
        logging.debug("Frame reconfigured. Updating canvas scrollregion.")
        self.logs_canvas.configure(scrollregion=self.logs_canvas.bbox("all"))

    def parse_log(self, timestamp, log_data):
  
        log_data["timestamp"] = timestamp  # Adding the timestamp to the dictionary
        return log_data
    
    def remove_filter(self):
        # Function to remove the applied filter
        self.activity_filter_combobox.set('')  # Clear the activity name filter
        self.error_filter_var.set('Any')  # Reset the error filter to 'Any'
        self.apply_filter()  # Re-apply the filter, which will now show all data

    def process_parsed_data(self, parsed_log_data):    

       # Assuming the parsed_log_data contains keys 'Activity Name', 'Status', 'Executed Branch', 'Output Result', and 'Error Message'
        try:
            activity_name = parsed_log_data.get('activity_name', 'N/A')
            status = parsed_log_data.get('status', 'N/A')
            executed_branch = parsed_log_data.get('executed_branch', 'N/A')
            output_result = parsed_log_data.get('output_result', 'N/A')
            error_message = parsed_log_data.get('error_message', 'N/A')
            timestamp = parsed_log_data.get('timestamp', 'N/A')
            
            unique_id = str(uuid.uuid4())

            # Store the full parsed data in the dictionary using the unique ID as the key
            self.full_log_data[unique_id] = parsed_log_data


            # Populate a dictionary with the parsed data
            treeview_log_entry = {
                "UUID": unique_id,
                "Time": timestamp,
                "Activity Name": activity_name,
                "Status": status,
                "Executed Branch": executed_branch,
                "Output Result": output_result,
                "Error Message": error_message
            }
            
            # Append the dictionary to treeview_data
            self.treeview_data.append(treeview_log_entry)
        except Exception as e:
            logging.error(f"Error processing parsed data: {e}\n{traceback.format_exc()}")   

    def populate_treeview(self, start_index):
        logging.debug("Populating the treeview with the parsed information.")

        # Clear the treeview before populating
        if start_index == 0:
            self.logs_tree.delete(*self.logs_tree.get_children())

        end_index = start_index + self.chunk_size
        try:
            end_index = start_index + self.chunk_size

            for log_entry in list(self.treeview_data)[start_index:end_index]:
                unique_id = log_entry["UUID"]
                timestamp = log_entry.get("Time", "")
                activity_name = log_entry.get("Activity Name", "").lower()

                executed_branch = log_entry.get("Executed Branch", "")
                output_result = log_entry.get("Output Result", "")
                status = log_entry.get("Status", "")
                error_message = log_entry.get("Error Message", "")
                # Filtering logic
                
                if self.activity_filter and self.activity_filter not in activity_name:
                    continue  # Skip this log entry if it doesn't match the activity name filter
                if self.error_filter == "Yes" and status != "error":
                    continue  # Skip this log entry if error filter is "Yes" and status is not "error"
                if self.error_filter == "No" and status == "error":
                    continue  

                # Insert the values into the treeview
                iid = self.logs_tree.insert("", "end", text=json.dumps(log_entry), tags=(unique_id, 'documentation'),
                                            values=(timestamp, activity_name, status, executed_branch, output_result,
                                                    error_message))
                # Check for "error" status within the loop and update background color
                if status == "error":
                    current_tags = self.logs_tree.item(iid, 'tags')
                    new_tags = current_tags + ('error',)
                    self.logs_tree.item(iid, tags=new_tags)

            self.adjust_column_width()
            self.update_progress_after_chunk(end_index)

        except Exception as e:
            logging.error(f"Error populating treeview: {e}\n{traceback.format_exc()}")

    def process_log_file(self, file_path):
        try:
            total_size = os.path.getsize(file_path)
            processed_size = 0
            chunks = []  # Initialize a list to store decoded chunks

            with io.BufferedReader(io.FileIO(file_path, 'r')) as file:
                while True:
                    chunk = file.read(8192)
                    if not chunk:
                        break  # Exit the loop if we've reached the end of the file
                    processed_size += len(chunk)

                    # Append the decoded chunk to the chunks list
                    chunks.append(chunk.decode('utf-8', errors='replace'))

            # Join the chunks to form the buffer
            buffer = ''.join(chunks)

            # Now, process the buffer
            lines = buffer.split('\n')
            for log_line in lines:
                if " " in log_line:
                    timestamp, log_data_str = log_line.split(" ", 1)
                else:
                    continue  # Skip to the next line
                try:
                    log_data = json.loads(log_data_str)
                except json.JSONDecodeError:
                    print(f"Could not decode JSON: {log_data_str}")
                    continue  # Skip to the next line
                system_config = self.extract_system_config(timestamp, log_data)
                if system_config:
                    for key, value in system_config.items():
                        self.config_labels[key].config(text=value)
                else:
                    parsed_log_data = self.parse_log(timestamp, log_data)
                    if parsed_log_data:
                        self.process_parsed_data(parsed_log_data)

                self.update_progress(processed_size, total_size)


            #self.populate_treeview(0)


        except Exception as e:
            logging.error(f"Error procesing the log file: {e}\n{traceback.format_exc()}")


    def update_progress_after_chunk(self, end_index):
        # Assuming total_size is the total number of log entries
        total_size = len(self.full_log_data)
        processed_size = end_index
    
        if processed_size > total_size:
            processed_size = total_size
    
        progress = (processed_size / total_size) * 100
        self.progress_var.set(progress)

    def start_processing(self, file_path):
        self.treeview_loaded = False
        self.progress_var.set(0)
        self.processing_thread = threading.Thread(target=self.process_log_file, args=(file_path,))
        self.processing_thread.start()
        self.root.after(100, self.check_thread)


    def update_progress(self, processed_size, total_size):
        progress = (processed_size / total_size) * 70  # Change 100 to 50
        self.progress_var.set(progress)
    

    def extract_system_config(self, timestamp, log_data):
        try:
            if "windows" in log_data:
                memory_in_bytes = log_data["mem"]["capacity"]
                memory_in_gb = memory_in_bytes / (1024 ** 3)
                all_hd_details = log_data["hdd"]
                formatted_hd_list = [
                    f"Type: {hd['interface_type']}, Size: {hd['size'] / (1024 ** 3):.2f} GB, Status: {hd['status']}"
                    for hd in all_hd_details
                ]
                formatted_hd_details = '\n'.join(formatted_hd_list)
                system_config = {
                    "Windows Version": log_data["windows"]["version"],
                    "CPU Name": log_data["cpu"]["name"],
                    "CPU Cores": log_data["cpu"]["number_of_cores"],
                    "Memory Ram": f"{memory_in_gb:.2f} GB",
                    "Hard Drive Details": formatted_hd_details,
                    "Computer Manufacturer": log_data["computer"]["manufacturer"],
                    "Computer Model": log_data["computer"]["model"]
                }
                return system_config
        except (KeyError, TypeError):
            return None
        
    def adjust_column_width(self):
        for col in self.logs_tree["columns"]:
            self.logs_tree.column(col, width=tkFont.Font().measure(col.title()), minwidth=50, stretch=tk.YES)

    
    def open_file(self):
        if not self.treeview_loaded:  # Check the flag before proceeding
            return

        file_path = filedialog.askopenfilename(title="Select Log File", 
                                               filetypes=[("Robot Runner Logs", "robot_autolog_*.log"),
                                                          ("Studio Pro Logs", "autolog_*.log"),])
        if file_path:
            if not self.validate_file_format(file_path):
                messagebox.showerror("Invalid File Format", "The selected file is not valid.")
                return

            # If we get here, the file is valid
            self.logs_tree.delete(*self.logs_tree.get_children())
            self.treeview_loaded = False 
            self.file_button.config(state="disabled")  # Disable the Open File button
            self.progress_bar.grid()  # Show the progress bar
            self.processing_thread = threading.Thread(target=self.process_log_file, args=(file_path,))
            self.processing_thread.start()
            self.root.after(100, self.check_thread)

    def check_thread(self):
        if self.processing_thread.is_alive():
            self.root.after(100, self.check_thread)
        else:
            self.file_button.config(state="normal")
            self.populate_treeview(0)
            self.progress_bar.grid_remove()  # Hide the progress bar
            self.treeview_loaded = True 
            self.root.update_idletasks()


    def open_documentation(self, event):
        try:
            with io.BufferedReader(io.FileIO("output.json", 'r')) as file:
                buffer = file.read().decode('utf-8')
                data = json.loads(buffer)
                self.documentation_url = {k.lower(): v for k, v in data["activities"].items()}  # Convert keys to lowercase

            activity_name = event.widget.item(event.widget.selection())['values'][1].lower()  # Convert activity_name to lowercase

            if "subprogram" in activity_name:
                activity_name = "subprogram"

            if activity_name == "subprogram":
                item = event.widget.selection()[0]
                log_data = json.loads(event.widget.item(item, 'text'))  # Retrieve the JSON string and load it
                file_name_content = log_data.get("fileName", "")  # Assuming the key is "fileName"
                if file_name_content:
                    activity_name += " (" + file_name_content + ")"

            webbrowser.open(self.documentation_url.get(activity_name, 'https://docs.example.com/default'))
        except Exception as e:
            logging.exception("Exception occurred in open_documentation")

    def open_help(self):
        if not self.treeview_loaded:
            return
        # Create a new top-level window
        help_window = tk.Toplevel(self.root)  # Modified this line to use self.root
        # Disable maximize and minimize buttons
        help_window.resizable(False, False)
        # Title and size
        help_window.title("Help")
        help_window.geometry("700x300")  # Adjusted size to fit content
        # Font settings
        font_setting = ('Arial', 10)
        title_font = ('Arial', 12, 'bold')
        # Top separator
        ttk.Separator(help_window).pack(fill=tk.X, pady=5)
        # Title
        title = "How to Enable and Parse Automatic Logs:"
        title_label = tk.Label(help_window, text=title, font=title_font, anchor="w", justify=tk.LEFT)
        title_label.pack(pady=5, padx=10, anchor="w")
        # Description
        description = ("Automatic logs provide detailed insights into the system details of the machine where the "
                       "workflow executed, as well as a complete trail of the workflow from start to finish. "
                       "These logs are structured with a timestamp followed by JSON data detailing each activity in the workflow.")
        desc_label = tk.Label(help_window, text=description, wraplength=650, font=font_setting, anchor="w", justify=tk.LEFT)
        desc_label.pack(pady=10, padx=10, anchor="w")

        def open_link(link):
            webbrowser.open(link)

        # Link for Robot Runner
        rr_text = "How to enable automatic logs on Bot Runner: "
        rr_label = tk.Label(help_window, text=rr_text, font=title_font, anchor="w")
        rr_label.pack(pady=5, padx=10, anchor="w")
        link1 = "https://docs.electroneek.com/page/how-tos-bot-runner#logging"
        link_label1 = tk.Label(help_window, text="Link", cursor="hand2", fg="blue", underline=1, font=font_setting)
        link_label1.pack(pady=5, padx=10, anchor="w")
        link_label1.bind("<Button-1>", lambda e: open_link(link1))

        # Link for Studio Pro
        studio_pro_text = "How to enable automatic logs on Studio Pro: "
        studio_pro_label = tk.Label(help_window, text=studio_pro_text, font=title_font, anchor="w")
        studio_pro_label.pack(pady=5, padx=10, anchor="w")
        link2 = "https://docs.electroneek.com/page/how-tos-studio-pro#logging"
        link_label2 = tk.Label(help_window, text="Link", cursor="hand2", fg="blue", underline=1, font=font_setting)
        link_label2.pack(pady=5, padx=10, anchor="w")
        link_label2.bind("<Button-1>", lambda e: open_link(link2))

        # Bottom separator
        ttk.Separator(help_window).pack(fill=tk.X, pady=5)
        version_label = tk.Label(help_window, text="Version: 1.1", anchor="w", font=font_setting)
        version_label.pack(pady=5, padx=10, anchor="w")

    def format_json_for_display(self, data):
        formatted_text = json.dumps(data, indent=4)  # Utilize json.dumps for formatting
        return formatted_text

    def display_log_detail(self, event=None):
        selected_item = self.logs_tree.selection()[0]
        tags = self.logs_tree.item(selected_item, "tags")
        unique_id = [tag for tag in tags if tag not in ['documentation', 'error']][0]  # Assuming UID is the only other tag
        log_data = self.full_log_data[unique_id]

        # Format the log_data for display
        formatted_log_data = self.format_json_for_display(log_data)



        detail_window = tk.Toplevel(self.root)

        detail_window.title("Log Details")
        detail_window.minsize(500, 300)  # Minimum window size for better presentation
        # Define a font for the log details
        log_font = ('Courier', 10)
        # Create the Text widget and Scrollbar
        scrollbar = tk.Scrollbar(detail_window)
        scrollbar.pack(side='right', fill='y')
        log_text = tk.Text(detail_window, wrap='word', font=log_font, yscrollcommand=scrollbar.set)
        log_text.insert('1.0', formatted_log_data)  # Use formatted_log_data here
        log_text.pack(pady=10, padx=15, fill='both', expand=True)
        # Associate scrollbar with text widget
        scrollbar.config(command=log_text.yview)
        # Make the Text widget read-only
        log_text.config(state='disabled')


    def copy_log_to_clipboard(self):
        selected_item = self.logs_tree.selection()[0]  # Get the selected treeview item
        uid = self.logs_tree.item(selected_item, "tags")[0]  # Get the UID from the tags of the selected item

        # Fetch the full log data using the UID
        log_data = self.full_log_data[uid]

        # Convert the dictionary back to a string representation for copying
        log_str = json.dumps(log_data, indent=4)

        # Use the Tkinter clipboard to copy the log string
        self.root.clipboard_clear()
        self.root.clipboard_append(log_str)
        self.root.update()  # This line is necessary to finalize the clipboard action


    def show_context_menu(self, event):
        if not self.treeview_loaded:
            return
        item = self.logs_tree.identify_row(event.y)
        if not item:
            return
        self.logs_tree.selection_set(item)
        # Get the values from the selected item
        selected_values = self.logs_tree.item(item, "values")
    
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Log Details", command=lambda event=event: self.display_log_detail(event))
        context_menu.add_command(label="Activity Documentation", command=lambda: self.open_documentation(event))
        context_menu.add_command(label="Copy Log to Clipboard", command=self.copy_log_to_clipboard)
    
        # Check if the selected item has an 'Output Result' to copy
        if len(selected_values) > 4:  # Check if 'Output Result' index exists
            output_result = selected_values[4]  # Assuming 'Output Result' is at index 4
            context_menu.add_command(label="Copy Output Result to Clipboard", 
                                     command=lambda: self.copy_to_clipboard(output_result))
    
        context_menu.tk_popup(event.x_root, event.y_root)
    def copy_to_clipboard(self, text):

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks() 

    def on_scroll(self, event):
        if not self.treeview_loaded:  # Prevent further loading while Treeview is still loading previous data
            return

        # Check if the Treeview is at the bottom
        if self.logs_tree.yview()[1] == 1.0 and self.current_offset < len(self.treeview_data):
            self.current_offset += self.chunk_size
            #self.populate_treeview(self.current_offset)


if __name__ == "__main__":
    root = tk.Tk()
    processor = LogProcessor(root)
    root.mainloop()