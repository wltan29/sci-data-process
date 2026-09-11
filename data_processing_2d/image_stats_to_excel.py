"""Summarise a folder of detector TIFFs into a multi-sheet Excel workbook.

For each 16-bit TIFF matching the name filter, computes mean intensity and
saturated-pixel count, reads creation/modification timestamps, and parses gain
and exposure time from the file name. Results are routed into separate sheets
(offset reference / offset / data / all) selected by ``process_type`` and
sorted by acquisition time.

Edit the ``# Define data processing parameter here`` block below. No beamline
hardware required.
"""

import os
import pandas as pd
from PIL import Image
import numpy as np
from datetime import datetime
from scidata.io_utils import filter_files, format_windows_path

# Define data processing parameter here
#-------------------------------------------------------------------------------------------------------

# File paths and excel name definition
input_path = r"path/to/tif_folder"
output_path = r"path/to/output"
excel_name = r"Summary.xlsx"

# User selection for the type of images to process
process_type = "offset"  # Options: 'offset_ref', 'offset', 'data', 'all_separate_sheet', 'all_in_a_sheet'

# file type and image_name filter
ftype_filter = (".tif")
fn_filter_cond = "offset_check_"  # Set your image_name filter here (e.g., '1002'). Use empty string if processing all images in the folder.

# Define saturated threshold once globally
# The value of saturated pixel of data image is 65535, the value of saturated pixel in offset image is 65534
# The comparator is >=, so use 65535 if finding saturated pixels in data image.
intensity_threshold = 65535

#-------------------------------------------------------------------------------------------------------

# Functions definition
def image_processing(image_path):
    img = Image.open(image_path)
    if img.mode != 'I;16':
        print(f"Image {image_path} is not a 16-bit unsigned integer pixels TIFF. The image mode is {img.mode}")
    
    # Calculate average intensity
    img_array = np.array(img, dtype=np.uint16)
    avg_intensity = img_array.mean() if img_array.size > 0 else 0  # Avoid division by zero   
    
    # Count the number of pixels greater than intensity_threshold
    saturated_pixel = np.sum(img_array >= intensity_threshold)

    return avg_intensity, saturated_pixel

def extract_gain_and_time(image_name):
    parts = image_name.split('_')
    gain_str = parts[-2].replace('pF', '').replace('p', '.')
    time_str = parts[-1].replace('.tif', '').replace('.tiff', '').replace('p', '.')

    # Convert to float
    gain = float(gain_str)
    time = float(time_str)

    return gain, time

def process_images_in_folder(input_path, fn_filter_cond, fn_filter_cond_additional):
    results = []
    for image_path in filter_files(input_path, ftype_filter, fn_filter_cond):
        image_name = os.path.basename(image_path)
        if fn_filter_cond_additional(image_name):
            try:
                avg_intensity, saturated_pixel = image_processing(image_path)
                gain, time = extract_gain_and_time(image_name) if '_offset_' in image_name.lower() else ('', '')
                creation_time = datetime.fromtimestamp(os.path.getctime(image_path))
                modification_time = datetime.fromtimestamp(os.path.getmtime(image_path))

                print(f"Processed {image_name}: Avg Intensity = {avg_intensity:.1f}, Gain = {gain}, Time = {time}, Pixels >= {intensity_threshold} = {saturated_pixel}")
                results.append([image_name, gain, time, creation_time, modification_time, avg_intensity, saturated_pixel])

            except ValueError as e:
                print(e)

    return results

# Format windows file path
input_path = format_windows_path(input_path)
output_path = format_windows_path(output_path)
output_excel = output_path + "/" + excel_name

# Process data based on the user's choice
if process_type == 'offset_ref' or process_type == 'all_separate_sheet':
    print('Processing OFFSET REFERENCE Images')
    print('----------------------------------')
    offset_ref_data = process_images_in_folder(input_path, fn_filter_cond,
        lambda fn: '_offset_' in fn.lower() and 
                   'OffRef_' in fn)
    print('----------------------------------')
else:
    offset_ref_data = []

if process_type == 'offset' or process_type == 'all_separate_sheet':
    print('Processing OFFSET Images')
    print('----------------------------------')
    offset_data = process_images_in_folder(input_path, fn_filter_cond,
                                           lambda fn: '_offset_' in fn.lower() and 
                                           'OffRef_' not in fn)
    print('----------------------------------')
else:
    offset_data = []

if process_type == 'data' or process_type == 'all_separate_sheet':
    print('Processing DATA Images')
    print('----------------------------------')
    data_data = process_images_in_folder(input_path, fn_filter_cond,
                                         lambda fn: '_offset_' not in fn.lower())
    print('----------------------------------')
else:
    data_data = []

if process_type == 'all_in_a_sheet':
    print('Processing All Images')
    print('----------------------------------')
    all_data = process_images_in_folder(input_path, fn_filter_cond,
                                        lambda fn: "" in fn.lower())
    print('----------------------------------')
else:
    all_data = []

# Save results to an Excel file with 3 sheets only if data exists
# Save results to an Excel file with sorted data in each sheet
with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
    if offset_ref_data:
        # Convert to DataFrame and sort by "Creation Timestamp"
        offset_ref_df = pd.DataFrame(
            offset_ref_data, 
            columns=["Image Name", "Gain", "Time", "Creation Timestamp", "Last Modified Timestamp", "Average Intensity", f"Pixels >= {intensity_threshold}"]
        ).sort_values(by="Creation Timestamp", ascending=True)
        offset_ref_df.to_excel(writer, sheet_name='OffsetRef', index=False)

    if offset_data:
        # Convert to DataFrame and sort by "Creation Timestamp"
        offset_df = pd.DataFrame(
            offset_data, 
            columns=["Image Name", "Gain", "Time", "Creation Timestamp", "Last Modified Timestamp", "Average Intensity", f"Pixels >= {intensity_threshold}"]
        ).sort_values(by="Creation Timestamp", ascending=True)
        offset_df.to_excel(writer, sheet_name='Offset', index=False)

    if data_data:
        # Convert to DataFrame and sort by "Creation Timestamp"
        data_df = pd.DataFrame(
            data_data, 
            columns=["Image Name", "Gain", "Time", "Creation Timestamp", "Last Modified Timestamp", "Average Intensity", f"Pixels >= {intensity_threshold}"]
        ).sort_values(by="Creation Timestamp", ascending=True)
        data_df.to_excel(writer, sheet_name='Data', index=False)

    if all_data:
        # Convert to DataFrame and sort by "Creation Timestamp"
        all_df = pd.DataFrame(
            all_data, 
            columns=["Image Name", "Gain", "Time", "Creation Timestamp", "Last Modified Timestamp", "Average Intensity", f"Pixels >= {intensity_threshold}"]
        ).sort_values(by="Creation Timestamp", ascending=True)
        all_df.to_excel(writer, sheet_name='All', index=False)

print(f"Results saved to {output_excel}")
