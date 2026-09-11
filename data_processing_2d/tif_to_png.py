"""Convert detector TIFFs in a folder to display-ready PNGs.

For each matching 16-bit TIFF: masks saturated pixels, clips intensities to a
configurable percentile range, downsamples, log-normalises, and saves a PNG
(``inferno`` colour map). Saturated-pixel counts are annotated onto the image,
saturated pixels are set to the low percentile value (default 5th percentile)
for visualisation, and the PNG modification time is nudged just after the TIFF's
for tidy file sorting. Set ``plot_prompt = True`` for a per-image TIFF/PNG/histogram
figure.

Edit the ``# Input`` block below. No beamline hardware required.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from scidata.io_utils import filter_files, format_windows_path
from scipy.ndimage import zoom
from datetime import datetime, timedelta

# Input
input_path = r"path/to/tif_folder"
output_path = input_path


ftype_filter = (".tif") # file type
fn_filter_cond = "STD945mm_GlassSlide_Shadowing_0126123"  # Set image_name filter here (e.g., '1002'). Use empty string if processing all images in the folder.

# Mask conditions: mask = tiff_img_arr < mask_vmax
mask_vmax = 65535

intensity_percentile_threshold = [5, 99] # Default values
# intensity_percentile_threshold = [25, 99.9]

plot_prompt = False # For viewing 2D images and the historgram of pixel intensity
image_origin = "upper" # Options: "upper", "lower"
cmap = "inferno"

# File path and image names processing
input_path = format_windows_path(input_path)
print("----------------------------------")
print(f"Processing folder path: {input_path}")

# Modify creation time of PNG file so that it's later than the TIFF creation time for better file sorting
def modify_modified_time(file_path, new_time):
    try:
        os.utime(file_path, (os.path.getatime(file_path), new_time.timestamp()))  # Keep access time, update modified time
    except Exception as e:
        print(f"Failed to update modified time for {file_path}: {e}")
    
def postprocess_detector_image_in_folder(input_path,
                                         output_path,
                                         plot_prompt,
                                         resize_factor=1./4):
    
    image_path_list = filter_files(input_path, ftype_filter, fn_filter_cond)
    j = len(image_path_list)
    
    if j == 0:
        print(f"WARNING: No images with the name '{fn_filter_cond}'")
    
    for i, image_path in enumerate(image_path_list):
        image_name = os.path.basename(image_path)
        output_image_path = output_path + "/" + image_name.replace('.tif', '') + ".png"
                
        print("----------------------------------")
        print(f"Processing image {i+1} out of {j} : {image_name}")
                
        # Open the image
        tiff_img = Image.open(image_path)
        tiff_img_arr = np.array(tiff_img)
        
        # Intensity analysis of raw data
        # print("--Intensity statistics--")
        # print("Raw TIFF image")
        tiff_vmin = tiff_img_arr.min()
        tiff_vmax = tiff_img_arr.max()
        print(f"[+] Raw Intensities >> Min: {tiff_vmin:.0f}, Max: {tiff_vmax:.0f}")
        
        # Determine the number of saturated pixels
        mask_saturated_pixel = tiff_img_arr >= mask_vmax
        mask_none_saturated_pixels = tiff_img_arr < mask_vmax

        saturated_pixel_count = np.sum(mask_saturated_pixel)
        if saturated_pixel_count > 0:
            print(f"[+] Saturated Pixels (Intensity >= {mask_vmax}): {saturated_pixel_count}")
            print(f"[+] Masked Intensities >> Min: {np.min(tiff_img_arr[mask_none_saturated_pixels]):.0f}, Max: {np.max(tiff_img_arr[mask_none_saturated_pixels]):.0f}")
        
        tiff_img_arr_percentile_low = np.percentile(tiff_img_arr[mask_none_saturated_pixels], intensity_percentile_threshold[0])
        tiff_img_arr_percentile_high = np.percentile(tiff_img_arr[mask_none_saturated_pixels], intensity_percentile_threshold[1])
        print(f"[+] Clipped Intensities >> Min: {tiff_img_arr_percentile_low:.0f}, Max: {tiff_img_arr_percentile_high:.0f}")
        
        tiff_vmax_clipped = tiff_img_arr_percentile_high   
        if tiff_img_arr_percentile_low == 0:
            print(f"tiff_vmin_clipped is 0, setting it as 1")
            tiff_vmin_clipped = max((tiff_img_arr_percentile_low), 1) # Avoid doing np.log on zero intensity.
            print(f"[+] Clipped Intensities >> Min: {tiff_vmin_clipped:.0f}, Max: {tiff_vmax_clipped:.0f}")
        else:
            tiff_vmin_clipped = tiff_img_arr_percentile_low
         
        # Create another np.array with clipped intensities, and set saturated pixels as low percentile value for visualisation
        tiff_img_arr_clipped = np.where(tiff_img_arr <= tiff_vmin_clipped, tiff_vmin_clipped, tiff_img_arr)
        tiff_img_arr_clipped = np.where(tiff_img_arr_clipped >= tiff_vmax_clipped, tiff_vmax_clipped, tiff_img_arr_clipped)
        tiff_img_arr_clipped[mask_saturated_pixel] = tiff_vmin_clipped 

        # Resize np.array only after the intensity analysis
        tiff_img_arr_resized = zoom(tiff_img_arr_clipped, resize_factor, order=1)  # order = 1 for bilinear interpolation
              
        # PNG saving
        # Log Normalize the image array manually
        normalized_array = np.log(tiff_img_arr_resized)

        # Save the normalized PNG image to the specified output path       
        plt.imsave(output_image_path, normalized_array, origin=image_origin, cmap="inferno")
       
        # Append a message on PNG image if there are saturated pixels
        if saturated_pixel_count > 0:
            png_image = Image.open(output_image_path)
            
            draw = ImageDraw.Draw(png_image)
            text = f"Saturated Pixels: {saturated_pixel_count}"
            position = (10, 10)  # (x, y) position           
            font = ImageFont.load_default(30) # Define font (use a default PIL font) with size 30
                
            # Add a semi-transparent background for readability
            text_bg = (255, 255, 0, 255)  # RGBA (yellow)
            text_size = draw.textbbox(position, text, font=font)  # Get text bounding box
            draw.rectangle(text_size, fill=text_bg)

            # Draw text
            draw.text(position, text, fill="red", font=font)

            # Save the image
            png_image.save(output_image_path)

        # Read creation time of TIFF image and modify the creation time of PNG to be one second later.
        tiff_modified_timestamp = os.path.getmtime(image_path) # Returns modified timestamp
        tiff_modified_time = datetime.fromtimestamp(tiff_modified_timestamp)  # Convert to datetime object
        png_modfied_time = tiff_modified_time + timedelta(seconds = 2) # Add 2 second
        # print(png_modfied_time)
        
        modify_modified_time(output_image_path, png_modfied_time)
        
        # Plot ori TIFF on LogNorm Display, Logged PNG and histogram
        if plot_prompt == True:
            # Create side-by-side plots
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))

            # Plot the original image with LogNorm scaling
            norm = LogNorm(vmin=tiff_vmin_clipped, vmax=tiff_vmax_clipped)
            axes[0].imshow(tiff_img_arr, origin=image_origin, cmap=cmap, norm=norm)
            axes[0].set_title("Original TIFF Image (LogNorm Display)")
            axes[0].axis('off')
            fig.colorbar(axes[0].imshow(tiff_img_arr, origin=image_origin, cmap=cmap, norm=norm),
                        ax=axes[0], orientation='vertical', label='Intensity')

            # Plot the normalized image
            axes[1].imshow(normalized_array, origin=image_origin, cmap=cmap)
            axes[1].set_title("Logged PNG Image to save")
            axes[1].axis('off')
            fig.colorbar(axes[1].imshow(normalized_array, origin=image_origin, cmap=cmap),
                        ax=axes[1], orientation='vertical', label='Normalized Intensity')
                
            # Plot the histogram of pixel intensities
            # axes[2].hist(tiff_img_arr[mask_none_saturated_pixels].flatten(), bins=200, color='blue', edgecolor='black')
            axes[2].hist(tiff_img_arr.flatten(), bins=200, color='blue', edgecolor='black')
            #axes[2].hist(tiff_img_arr_noSat.flatten(), bins=200, color='blue', edgecolor='black')
            axes[2].set_title("Histogram of Original Pixel Intensity")
            axes[2].set_xlabel('Intensity Value')
            axes[2].set_ylabel('Pixel Count')
            axes[2].grid(True, linestyle='--', alpha=0.7)
            axes[2].set_yscale('log')  # Use log scale for better visualization of pixel count distribution

            plt.tight_layout()
            plt.show()



# Main work flow
postprocess_detector_image_in_folder(input_path, output_path, plot_prompt = plot_prompt)
print("----------------------------------")
print("Finished processing all images")