"""Consolidate metadata from ANSTO .asc scan files into a single Excel table.

Walks an experiment folder recursively, parses every ``.asc`` file for scan
metadata (scan time, positioner/detector column descriptions, Extra PV values),
rejects ``scanH`` dtacq-array files, and handles XRpad multi-acquisition files
by offsetting the scan time by the per-frame acquisition time. The combined
table is written to ``<output_path>/<output_excel_name>.xlsx``, sorted by scan
time.

Edit the ``# Input section`` constants below before running. No beamline
hardware required -- operates on saved ``.asc`` files.
"""

import time

start_time = time.time()  # Start timer

import os
import pandas as pd
from datetime import datetime, timedelta
from scidata.io_utils import filter_files, format_windows_path
from pathlib import Path
import mmap

# To do
# Modify scan_time for asc files with multiple acquisitions (XRpad data only) taking account into the acquisition time in between scans

# Input section for processing user data
epn = "XXXXXa"  # experiment (proposal) number
input_path_parentfolder = r"path/to/userarchive"
input_path = os.path.join(input_path_parentfolder, epn)
output_path = r"path/to/output"
output_excel_name = "Metadata_" + epn

# Input section for processing local data
# input_path = r"path/to/local/1D"
# output_path = input_path

ftype_filter = (".asc")
fn_filter_cond = ""

# Don't change anything down here
input_path = format_windows_path(input_path)
output_path = format_windows_path(output_path)
df = pd.DataFrame()

print("-------------------------")
print("Searching for all subfolders")
fpath = Path(input_path)
all_folders_path = [str(f) for f in fpath.glob("**/")]  # glob("**/") includes parent and all subfolders
for folder_path in all_folders_path:
    print(f"-- {folder_path}")
    
print("-------------------------")
print("Start processing")
print("-------------------------")
for folder_path in all_folders_path:
    print(f"Current path: {folder_path}")
    asc_path_list = filter_files(folder_path, ftype_filter, fn_filter_cond)

    # Remove asc file that contain Scan H.
    print(f"-- Filtering ASC files with dtacq array data: Rejecting scanH ASC files")
    asc_path_list = [
        path for path in asc_path_list
        if not any(
            scan_str in line
            for line in open(path, "r")
            for scan_str in ("SR10BM01SSCAN5:scanH", "SR10BM01SSCAN4:scanH")
        )
    ]

    print(f"-- Metadata extraction begins")
    if len(asc_path_list) == 0:
        print((f"** No ASC files to extract **"))
    for asc_path in asc_path_list:
        metadata_dict = {} # Initialise an empty dictionary
        with open(asc_path, "r") as file:
            lines = file.readlines()
            
            # Initialize flags
            col_val_start_index = None
            skip_positioner_data_in_col_val_counter = 0
            extra_pv_lines = []
            col_des_lines = [] # col_des stands for column description
            col_val_line = [] # col_val stands for column value
            
            # Read the input file
            for index, line in enumerate(lines):

                # Extract Extra PV
                if "# Extra PV "  in line:
                    extra_pv_lines.append(line)
                
                # Extract Column Descriptions
                if "-D Detector  "  in line:
                    col_des_lines.append(line)
                
                # Extract Scan Time
                if "# Scan time" in line:
                    scan_time = line
                
                # Identify the starting for 2-D Scan Values    
                if line.strip().endswith("-D Scan Values"):
                    col_val_start_index = index + 1
                
                # Identify if a Positioner is in Column Descriptions, to skip this row during metadata extraction
                if "-D Positioner " in line:
                    skip_positioner_data_in_col_val_counter += 1
                    
            # Extract all lines after the "# 2-D Scan Values" line
            if col_val_start_index is not None:
                col_val_lines = lines[col_val_start_index:]
            else:
                print("Line with '# 2-D Scan Values' not found.")
                   
            col_des_lines_extracted = []
            for i, col_des_line in enumerate(col_des_lines):
                # String parsing 
                col_des_line_split = col_des_line.split(", ")
                col_des_line_split0_split = col_des_line_split[0].split()
                pv = col_des_line_split0_split[-1]
                pv_description = col_des_line_split[-2].strip()
                pv_unit = col_des_line_split[-1].strip()
                col_des = pv + ", " + pv_description + ", " + pv_unit
                col_des_lines_extracted.append(str(col_des))
                                                   
            for k, col_val_line in enumerate(col_val_lines):
                print(f"[+] Processing {asc_path}")
                
                asc_name = os.path.basename(asc_path).replace(".asc", "")
                if len(col_val_lines) > 1: # Only for XRpad data, define filename based on the number of rows of col_val_lines. Append index if there are multiple rows
                    output_fname = asc_name + "_" + str(k+1)                    
                else:
                    output_fname = asc_name.replace(".asc", "")
                
                scan_time_title = "Scan Time"
                scan_time_value = scan_time.strip().split(" = ")[-1] # Extract date and time
                dt_obj = datetime.strptime(scan_time_value, "%b %d, %Y %H:%M:%S.%f") # Convert to datetime object, the time delta make sure col_val_lines are sorted in the correct increasing time order.
                metadata_dict[scan_time_title] = dt_obj
                
                fpath_title = "File Path"
                fpath_entry = folder_path
                metadata_dict[fpath_title] = fpath_entry
                
                fname_title = "File Name"
                fname_entry = output_fname
                metadata_dict[fname_title] = fname_entry

                for l, col_des_line in enumerate(col_des_lines_extracted):
                    col_val = float(col_val_line.split()[l+1+skip_positioner_data_in_col_val_counter])
                    metadata_dict[col_des_line] = col_val
                
                for extra_pv_line in extra_pv_lines:
                    # String parsing
                    extra_pv_line_split = extra_pv_line.split(",")
                    pv = extra_pv_line_split[0].split()[-1]
                    pv_description = extra_pv_line_split[1].strip()
                    pv_unit = extra_pv_line_split[-1].strip()
                    
                    extra_pv = pv + ", " + pv_description + ", " + pv_unit
                    extra_pv_value = float(extra_pv_line_split[-2].strip().strip('"'))

                    metadata_dict[extra_pv] = extra_pv_value
                
                if len(col_val_lines) > 1: # The time delta extracted from xrpad acquisition time make sure col_val_lines are sorted in the correct increasing time order with the correct length of time.
                    delay_time = metadata_dict["SR10BM01XRPAD01:cam1:AcquireTime_RBV, , "]
                    metadata_dict[scan_time_title] = dt_obj + timedelta(seconds=k*delay_time)
                    
                series = pd.Series(metadata_dict)
                df = pd.concat([df, series.to_frame().T], ignore_index=True)
    print(f"-- Metadata extraction ends")

# Save to an Excel file
os.makedirs(output_path, exist_ok=True) # Create the folder if it doesn't exist
output_fpath = output_path + "\\" + output_excel_name + ".xlsx"

if not df.empty:
    df.sort_values(by=scan_time_title, ascending=True, inplace=True) # Sort the df by scan time.
    df.to_excel(output_fpath, index=False)  # 'index=False' removes the default index
else:
    print(f"There's no asc file in the folder {input_path}")

print("-------------------------")
print("Finish processing")
print("-------------------------")

end_time = time.time()  # End timer
elapsed_time = end_time - start_time
print(f"Code execution time: {elapsed_time:.2f} seconds")
