import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
from tkinter import filedialog
import json
import webbrowser
import logging

logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)

try:
    def parse_log(log_line):
        # This function can be enhanced to handle the general log parsing
        # For now, it just returns the log as a dictionary
        try:
            timestamp, log_data_str = log_line.split(" ", 1)
            log_data = json.loads(log_data_str)
            log_data["timestamp"] = timestamp  # Adding the timestamp to the dictionary
            return log_data
        except (json.JSONDecodeError, ValueError):
            return None

    def extract_system_config(log_line):
        try:
            timestamp, log_data_str = log_line.split(" ", 1)
            log_data = json.loads(log_data_str)

            # Check if it's a system config log line
            if "windows" in log_data:

                # Convert memory from bytes to GB
                memory_in_bytes = log_data["mem"]["capacity"]
                memory_in_gb = memory_in_bytes / (1024 ** 3)

                # Process each hard drive detail
                all_hd_details = log_data["hdd"]
                formatted_hd_list = []

                for hd in all_hd_details:
                    hd_size_in_gb = hd["size"] / (1024 ** 3)
                    formatted_hd = f"Type: {hd['interface_type']}, Size: {hd_size_in_gb:.2f} GB, Status: {hd['status']}"
                    formatted_hd_list.append(formatted_hd)

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
            else:
                return None
        except (json.JSONDecodeError, ValueError, KeyError):
            return None

    def adjust_column_width(treeview):
        for col in treeview["columns"]:
            # Find the maximum width of the content in the column
            column_widths = [tkFont.Font().measure(col.title())]

            for item in treeview.get_children():
                bbox = treeview.bbox(item, col)
                if bbox:
                    column_widths.append(bbox[2])

            max_width = max(column_widths)
            treeview.column(col, width=max_width)

    def process_log_file(file_path):
        # Clear the treeview
        logs_tree.delete(*logs_tree.get_children())

        # Flag to track if the previous activity was 'Get Password'
        last_activity_was_get_password = False

        with open(file_path, 'r') as file:
            for log_line in file:
                system_config = extract_system_config(log_line)
                if system_config:
                    # Update the system configuration labels
                    for key, value in system_config.items():
                        config_labels[key].config(text=value)
                else:
                    # Parse other log data and update the treeview
                    log_data = parse_log(log_line)
                    if log_data:
                        timestamp = log_data.get("timestamp", "")
                        activity_name = log_data.get("activity_name", "").lower()  # Convert to lowercase

                        # If activity name is "Subprogram", search for filename in log data
                        if activity_name == "subprogram":
                            file_name_content = log_data.get("fileName", "")  # Assuming the key is "fileName"
                            if file_name_content:
                                activity_name += " (" + file_name_content + ")"

                        # Exclude logs with "START" and "END" activity names
                        if activity_name not in ["start", "end"]:
                            executed_branch = log_data.get("executed_branch", "")
                            output_result = log_data.get("output_result", "")
                            status = log_data.get("status", "")
                            error_message = log_data.get("error_message", "")

                            # Check if the last activity was "Get Password" and the current activity is one of the ones that show sensitive information
                            if last_activity_was_get_password and activity_name in ["input to browser", "assign value to variable"]:
                                output_result = "******"  # Mask the sensitive information

                            # Insert the values into the treeview
                            iid = logs_tree.insert("", "end", text=json.dumps(log_data), tags=('documentation',), values=(timestamp, activity_name, status, executed_branch, output_result, error_message))

                            adjust_column_width(logs_tree)

                            # Check for "error" status and update the background color if true
                            if status == "error":
                                logs_tree.item(iid, tags=('error',))

                        # Set the flag if the activity name is "Get Password", reset otherwise
                        last_activity_was_get_password = activity_name == "get password"

    def open_file():
        file_path = filedialog.askopenfilename(title="Select Log File", 
                                               filetypes=[("Robot Runner Logs", "robot_autolog_*.log"),
                                                          ("Studio Pro Logs", "autolog_*.log"),])
        if file_path:
            process_log_file(file_path)

    def open_documentation(event):
        # Load the documentation URLs from the JSON file each time the function is called
        with open("output.json", "r") as file:
            data = json.load(file)
            documentation_url = {k.lower(): v for k, v in data["activities"].items()}  # Convert keys to lowercase

        activity_name = event.widget.item(event.widget.selection())['values'][1].lower()  # Convert activity_name to lowercase

        # Case-insensitive check for "subprogram" in activity_name and reset to just "subprogram"
        if "subprogram" in activity_name:
            activity_name = "subprogram"

        if activity_name == "subprogram":
            item = event.widget.selection()[0]
            log_data = json.loads(event.widget.item(item, 'text'))  # Retrieve the JSON string and load it
            file_name_content = log_data.get("fileName", "")  # Assuming the key is "fileName"
            if file_name_content:
                activity_name += " (" + file_name_content + ")"

        webbrowser.open(documentation_url.get(activity_name, 'https://docs.example.com/default'))

    def open_help():
        # Create a new top-level window
        help_window = tk.Toplevel(root)
        #help_window.iconbitmap("faviconV2.ico")
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

        # Function to open the link when the label is clicked
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

        # Close button
        close_button = ttk.Button(help_window, text="Close", command=help_window.destroy)
        close_button.pack(pady=20)

    # Beginning of the GUI
    root = tk.Tk()
    #root.iconbitmap("faviconV2.ico")

    root.resizable(True, True)
    root.title("ElectroNeek Log Parser")

    # Grid configuration for root
    root.grid_rowconfigure(0, weight=0)  # Button frame
    root.grid_rowconfigure(1, weight=0)  # Separator 1
    root.grid_rowconfigure(2, weight=0)  # Config frame
    root.grid_rowconfigure(3, weight=0)  # Separator 2
    root.grid_rowconfigure(4, weight=1)  # Logs frame

    # Button frame with padding to align buttons with "Complete logs" tree
    button_frame = tk.Frame(root)
    button_frame.grid(row=0, column=0, sticky='w', padx=10, pady=10)
    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(1, weight=1)

    file_button = tk.Button(button_frame, text="Open File", command=open_file)  # Assuming the command is already defined
    file_button.grid(row=0, column=0, padx=5, pady=5)

    help_button = tk.Button(button_frame, text="Help", command=open_help)  # Assuming the command is already defined
    help_button.grid(row=0, column=1, padx=5, pady=5)

    separator1 = ttk.Separator(root, orient='horizontal')
    separator1.grid(row=1, column=0, sticky='ew', pady=(5, 5))

    # System Config Frame
    root.grid_columnconfigure(0, weight=1)

    # Set up the system configuration frame
    config_frame = tk.Frame(root, padx=10, pady=2)
    config_frame.grid(row=1, column=0, sticky='ew', pady=(2, 2))

    # To make the system configuration labels and values expandable
    config_frame.grid_columnconfigure(1, weight=1)

    # Example Label widgets inside the config_frame
    tk.Label(config_frame, text="Config Key:").grid(row=0, column=0, sticky='w')
    tk.Label(config_frame, text="Config Value", bg="lightgrey").grid(row=0, column=1, sticky='ew')


    separator2 = ttk.Separator(root, orient='horizontal')
    separator2.grid(row=3, column=0, sticky='ew', pady=(2, 5))


    config_label = tk.Label(config_frame, text="System Configuration", font=("Arial", 12))
    config_label.grid(row=0, column=0, sticky="w")
    config_label.config(font=("Arial", 12, "bold"))

    config_defaults = {
        "Windows Version": "N/A",
        "CPU Name": "N/A",
        "CPU Cores": "N/A",
        "Memory Ram": "N/A",
        "Hard Drive Details": "N/A",
        "Computer Manufacturer": "N/A",
        "Computer Model": "N/A"
    }

    config_labels = {}

    for index, key in enumerate(config_defaults, start=1):
        label = tk.Label(config_frame, text=f"{key}:", width=20, anchor="e")
        label.grid(row=index, column=0, padx=(0, 5), sticky="e")

        value_label = tk.Label(config_frame, text=config_defaults[key], anchor="w")
        value_label.grid(row=index, column=1, sticky="w", padx=5)

        config_labels[key] = value_label

    # Create Treeviews
    logs_frame = tk.Frame(root)
    logs_frame.grid(row=4, column=0, sticky='nsew')

    logs_frame.grid_rowconfigure(0, weight=1)
    logs_frame.grid_columnconfigure(0, weight=1)
    # Create a canvas
    logs_canvas = tk.Canvas(logs_frame)
    logs_canvas.grid(row=0, column=0, sticky='nsew')

    tree_frame = ttk.Frame(logs_canvas)
    logs_canvas.create_window((0,0), window=tree_frame, anchor="nw")

    # This function updates the canvas's scrollregion whenever the size of the frame inside it changes.
    def on_frame_configure(event):
        logs_canvas.configure(scrollregion=logs_canvas.bbox("all"))

    tree_frame.bind("<Configure>", on_frame_configure)
    logs_tree = ttk.Treeview(logs_frame, columns=("Time", "Activity Name", "Status", "Executed Branch", "Output Result", "Error Message"), show="headings")
    logs_tree.grid(row=0, column=0, sticky='nsew')
    v_scrollbar = ttk.Scrollbar(logs_frame, orient="vertical", command=logs_tree.yview)
    v_scrollbar.grid(row=0, column=1, sticky='ns')
    logs_tree.config(yscrollcommand=v_scrollbar.set)
    h_scrollbar = ttk.Scrollbar(logs_frame, orient="horizontal", command=logs_tree.xview)
    h_scrollbar.grid(row=1, column=0, sticky='ew')
    logs_tree.config(xscrollcommand=h_scrollbar.set)

    # Configure the canvas
    logs_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    logs_canvas.bind('<Configure>', lambda e: logs_canvas.configure(scrollregion=logs_canvas.bbox("all")))

    # Set up headings for 'Logs' Treeview
    logs_tree.heading("Time", text="Time")
    logs_tree.heading("Activity Name", text="Activity Name")
    logs_tree.heading("Status", text="Status")
    logs_tree.heading("Executed Branch", text="Executed Branch")
    logs_tree.heading("Output Result", text="Output Result")
    logs_tree.heading("Error Message", text="Error Message")
    logs_tree.tag_configure('error', background='red', foreground='white')

    # Dynamically set the width of the columns based on the title's width
    for col in logs_tree["columns"]:
        logs_tree.column(col, width=tkFont.Font().measure(col.title()), minwidth=50, stretch=tk.YES)

    root.grid_rowconfigure(2, weight=1)  # To make the logs_frame expand vertically
    root.grid_columnconfigure(0, weight=1)  # To make all columns in the main window expand horizontally

    config_frame.grid_rowconfigure(7, weight=1)  # To allow system config labels to take up space
    config_frame.grid_columnconfigure(1, weight=1)  # To make the system config values expand horizontally

    def format_json_for_display(data, indent=0):
        formatted_text = ""
        spaces = "  " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                formatted_text += f"{spaces}{key}:\n"
                formatted_text += format_json_for_display(value, indent + 1)
            elif isinstance(value, list):
                formatted_text += f"{spaces}{key}:\n"
                for item in value:
                    if isinstance(item, (dict, list)):
                        formatted_text += format_json_for_display(item, indent + 1)
                    else:
                        formatted_text += f"{spaces}  {item}\n"
            else:
                formatted_text += f"{spaces}{key}: {value}\n"

        return formatted_text

    def mask_password_from_treeview(current_item):
        """Mask password if previous item in treeview has a 'Get Password' activity."""

        # Get the previous item in the Treeview
        previous_item = logs_tree.prev(current_item)

        if not previous_item:
            # If there's no previous item, return the original log data
            return logs_tree.item(current_item, 'text')

        prev_log_data_str = logs_tree.item(previous_item, 'text')
        prev_log_data = json.loads(prev_log_data_str)
        prev_activity_name = prev_log_data.get("activity_name", "").lower()

        current_log_data_str = logs_tree.item(current_item, 'text')
        current_log_data = json.loads(current_log_data_str)
        current_activity_name = current_log_data.get("activity_name", "").lower()

        if prev_activity_name == "get password" and current_activity_name in ["input to browser", "assign value to variable"]:
            current_log_data["output_result"] = "******"
            return json.dumps(current_log_data)

        return current_log_data_str

    def display_log_detail(event):
        item = logs_tree.selection()[0]

        # Use the new masking function here
        masked_log_data_str = mask_password_from_treeview(item)

        # Load the JSON string into a dictionary
        log_data = json.loads(masked_log_data_str)

        # Format the JSON data for display using the new function
        formatted_log_data = format_json_for_display(log_data)

        # Create a new top-level window for details
        detail_window = tk.Toplevel(root)
        #detail_window.iconbitmap("faviconV2.ico")
        detail_window.title("Log Details")
        detail_window.minsize(500, 300)  # Minimum window size for better presentation

        # Define a font for the log details
        log_font = ('Courier', 10)

        # Create the Text widget and Scrollbar
        scrollbar = tk.Scrollbar(detail_window)
        scrollbar.pack(side='right', fill='y')

        log_text = tk.Text(detail_window, wrap='word', font=log_font, yscrollcommand=scrollbar.set)
        log_text.insert('1.0', formatted_log_data)
        log_text.pack(pady=10, padx=15, fill='both', expand=True)

        # Associate scrollbar with text widget
        scrollbar.config(command=log_text.yview)

        # Make the Text widget read-only
        log_text.config(state='disabled')


    def copy_log_to_clipboard():
        item = logs_tree.selection()[0]

        # Use the new masking function here
        masked_log_data_str = mask_password_from_treeview(item)

        # Convert the dictionary back to a string representation for copying
        log_str = json.dumps(json.loads(masked_log_data_str), indent=4)

        # Use the Tkinter clipboard to copy the log string
        root.clipboard_clear()
        root.clipboard_append(log_str)
        root.update()  # This line is necessary to finalize the clipboard action

    def show_context_menu(event):
        # Select the item under the cursor
        item = logs_tree.identify_row(event.y)
        if not item:
            # No item under the cursor, so don't show the context menu
            return

        logs_tree.selection_set(item)

        context_menu = tk.Menu(root, tearoff=0)
        context_menu.add_command(label="Log Details", command=lambda event=event: display_log_detail(event))
        context_menu.add_command(label="Activity Documentation", command=lambda: open_documentation(event))

        # Adding the new "Copy Log to Clipboard" command
        context_menu.add_command(label="Copy Log to Clipboard", command=copy_log_to_clipboard)

        context_menu.tk_popup(event.x_root, event.y_root)

    logs_tree.bind("<Button-3>", show_context_menu)  # Button-3 represents the right mouse button

except Exception as e:
    logging.exception("Exception occurred")

root.mainloop()