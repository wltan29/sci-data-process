"""Fit sample height vs cryostat temperature from photodiode/STG-X scans.

Developed for one specific calibration: for every ``.asc`` file (converted from
EPICS ``.mda``) in ``input_folder``, fit a Gaussian + flat background to
photodiode current vs STG-X, take the peak centre as the correct sample height,
and average the cryostat temperature over the scan. Writes an Excel workbook
whose first sheet summarises height vs temperature, with one raw-data sheet per
scan, and saves a fit-quality PNG per scan under ``Plots/``.

Edit ``input_folder`` below. No beamline hardware required.
"""

import csv
import os
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from datetime import datetime
import warnings
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')  # Ignore warnings for curve fitting

# Gaussian function with flat background (constant background)
def gaussian_with_flat_background(x, a, x0, sigma, c):
    return a * np.exp(-(x - x0) ** 2 / (2 * sigma ** 2)) + c

# Function to format scan time into an Excel-friendly format (DD-MM-YYYY HH:MM:SS)
def format_scan_time(scan_time_str):
    try:
        scan_time = datetime.strptime(scan_time_str.split('.')[0], '%b %d, %Y %H:%M:%S')
        return scan_time.strftime('%d-%m-%Y %H:%M:%S')
    except ValueError:
        return scan_time_str

# Read the ASC file and extract the scan values, header, and scan time
def extract_scan_values(file_path):
    scan_values = []
    header = []
    scan_time = None

    with open(file_path, 'r') as file:
        lines = file.readlines()

        for line in lines:
            if line.startswith("# Scan time ="):
                raw_scan_time = line.split('=')[1].strip()
                scan_time = format_scan_time(raw_scan_time)
                break

        start_reading_header = False
        for line in lines:
            line = line.strip()
            if line.startswith("# Column Descriptions:"):
                start_reading_header = True
                continue
            if start_reading_header:
                if line.startswith("#") and line.strip() != "# Column Descriptions:":
                    if ']' in line:
                        header.append(line.split(']')[1].strip())
                if line.startswith("# 1-D Scan Values"):
                    break

        start_reading_data = False
        for line in lines:
            line = line.strip()
            if line.startswith("# 1-D Scan Values"):
                start_reading_data = True
                continue
            if start_reading_data:
                if line:
                    scan_values.append(tuple(map(float, line.split(','))))

    return header, scan_values, scan_time

# Perform Gaussian fitting with flat background
def perform_gaussian_fitting_with_flat_background(x_data, y_data):
    initial_guess = [-(max(y_data) - min(y_data)), np.mean(x_data), np.std(x_data), max(y_data)]
    try:
        popt, _ = curve_fit(gaussian_with_flat_background, x_data, y_data, p0=initial_guess)
        return popt
    except RuntimeError:
        print("Error: Gaussian fit failed")
        return None

# Function to plot raw data and Gaussian fit with dynamic axis labels from headers
def plot_gaussian_fit(x_data, y_data, params, file_name, scan_time, avg_temp, plots_folder, x_label, y_label):
    plt.figure(figsize=(8, 6))

    # Plot raw data
    plt.scatter(x_data, y_data, color='blue', label='Raw Data')

    # Plot Gaussian fit if parameters are available
    if params is not None:
        a, x0, sigma, c = params
        fitted_y = gaussian_with_flat_background(x_data, *params)
        plt.plot(x_data, fitted_y, color='red', label=f'Gaussian Fit\nPeak position (x0) = {x0:.2f} mm')

    # Set the title to include the scan time, average temperature, and peak position
    plt.title(f'Gaussian Fit for {file_name}\n'
              f'Scan Time: {scan_time}, Avg Temp: {avg_temp:.2f} K, Peak Position: {x0:.2f} mm')

    # Label x and y axes using the provided x_label and y_label
    plt.xlabel(x_label)
    plt.ylabel(y_label)

    # Show legend
    plt.legend()

    # Ensure the 'Plots' folder exists
    if not os.path.exists(plots_folder):
        os.makedirs(plots_folder)

    # Save the plot as a PNG file in the 'Plots' folder
    plot_path = os.path.join(plots_folder, f'{file_name}_gaussian_fit.png')
    plt.savefig(plot_path)
    plt.close()

# Folder containing the ASC files
input_folder = r'path/to/asc_folder'
plots_folder = os.path.join(input_folder, 'Plots')  # Subfolder for plots
plots_option = True # True if want the plots saved, False otherwise.

asc_files = [f for f in os.listdir(input_folder) if f.endswith('.asc')]

fitted_params_list = []

output_file_path = os.path.join(input_folder, 'converted_data_with_flat_background.xlsx')
with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
    for asc_file in asc_files:
        input_file_path = os.path.join(input_folder, asc_file)

        header, values, scan_time = extract_scan_values(input_file_path)
        
        df = pd.DataFrame(values, columns=header)
        
        # Header is ['', 'SR10BM01STG01:X, STG01_X, LINEAR, mm, , ,', 'SR10BM01PVGLUE:AMP03_MON, AMP1 Current Reading, uA', 'SR10BM01TCIOC02:CRY:KELVINA_MONITOR, Temp Channel A Kelvin, Degrees'] 
        x_column = header[1]
        y_column = header[2]
        temp_column = header[3]
        
        if x_column in df.columns and y_column in df.columns:
            x_data = df[x_column].values
            y_data = df[y_column].values
            
            params = perform_gaussian_fitting_with_flat_background(x_data, y_data)
            
            if params is not None:
                a, x0, sigma, c = params
                if temp_column in df.columns:
                    avg_temp = df[temp_column].mean()
                    std_temp = df[temp_column].std()
                else:
                    avg_temp = np.nan
                    std_temp = np.nan
                
                fitted_params_list.append({
                    'File': asc_file,
                    'Scan Time': scan_time,
                    'Average Temperature': avg_temp,
                    'Std Temperature': std_temp,
                    'Peak position (x0)': x0,
                    'Standard deviation (sigma)': sigma,
                    'Amplitude (a)': a,
                    'Constant background (c)': c                   
                })
                
                if plots_option == True:

                    # Plot raw data and fitted curve using dynamic labels
                    x_label = x_column
                    y_label = y_column
                    plot_gaussian_fit(x_data, y_data, params, asc_file, scan_time, avg_temp, plots_folder, x_label, y_label)

            else:
                print(f'Gaussian fitting failed for {asc_file}')

    fitted_params_df = pd.DataFrame(fitted_params_list)
    fitted_params_df.to_excel(writer, sheet_name='Fitted_Parameters', index=False)

    for asc_file in asc_files:
        input_file_path = os.path.join(input_folder, asc_file)

        header, values, scan_time = extract_scan_values(input_file_path)
        
        df = pd.DataFrame(values, columns=header)
        sheet_name = os.path.splitext(asc_file)[0]
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f'Data, fitted parameters, and plots have been exported to {output_file_path}.')
