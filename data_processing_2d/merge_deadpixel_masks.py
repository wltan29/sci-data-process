'''
Author:     Liam Tan
Created:    2024.11.04
Modified:   2024.11.07

This code merge all dead pixels in a 16-bit 2D TIF dead pixels/data image in a folder into a new TIF image
This code assume the input images only have two values for intensity, 65535 for dead pixels, 0 for non-dead pixels. This follows the convention for XRpad's PxlMask

This merged TIF image can't be used directly with the XIS software to make the PxlMask file. Initially thought it's because of image type (I;16B instead of I;16)
but it was found not to be the case. Instead, the image needs to be converted into a mask file on Dioptas (Above Threshold 65534), followed by conversion into a 16-bit TIF image
on ImageJ, then only it works. Unsure what is the reason.
'''


import os
import numpy as np
from PIL import Image
from glob import glob
from scidata.io_utils import format_windows_path

# Define INPUT parameters here
image_dir = r"path/to/mask_folder"
merged_mask_deadpixel_name = r"03454_g5_PxlMask_20241111.tif"

# Find all TIF files in the directory
image_dir = format_windows_path(image_dir)
image_path_list = glob(os.path.join(image_dir, '*.tif'))

# Initialize the mask_sum array with zeros with the array size matching image array size.
img_array_size = np.array(Image.open(image_path_list[1]), dtype=np.uint16)
mask_sum = np.zeros_like(img_array_size, dtype=np.float64)

# Sum the Boolean mask for saturated pixels for each image.
print("-------------------------------------------")
for i, image_path in enumerate(image_path_list):
    print(f"Image {i+1} = {os.path.basename(image_path).replace('.tif','')}")
    
    img_array = np.array(Image.open(image_path), dtype=np.uint16)
    img_array_sat_bool = img_array >= 1 # Saturated pixels have 65535 counts.
    
    print(f'-- Dead pixels : {np.sum(img_array_sat_bool)}')
    
    mask_sum += img_array_sat_bool

# Make the pixels saturated at least once True.
mask_sum_bool = mask_sum > 0 # Pixels dead at least once
mask_sum_merge = mask_sum_bool * 65535 # Follow dead pixel value of XRpad.

# Print dead pixel statistics
print("-------------------------------------------")
print(f'Summed dead pixel mask (Bool) image - sum : {np.sum(mask_sum)}')
print(f'Summed dead pixel mask (Bool) image - max : {np.max(mask_sum)}')
print(f'Summed dead pixel mask (Bool) image - mumber of pixels with max intensity of {np.max(mask_sum)} : {np.sum(mask_sum == np.max(mask_sum))}')
print(f'Number of pixels dead at least once : {np.sum(mask_sum_bool)}')
print("-------------------------------------------")

# Save merged dead pixel image
mask_deadpixel_array = mask_sum_merge.astype(np.uint16)  # Ensuring 16-bit precision for the dead pixel array
mask_deadpixel = Image.fromarray(mask_deadpixel_array, mode='I;16')  # Convert the array back to an image in I;16B (16-bit big endian unsigned integer pixels) which XIS may accept but it actually doesn't.
mask_deadpixel.save(os.path.join(image_dir, merged_mask_deadpixel_name))
print(f"Merged dead pixel mask: {merged_mask_deadpixel_name}")
print(f'-- Dead pixels : {np.sum(mask_sum_bool)}')
print(f"{merged_mask_deadpixel_name} saved successfully")
print("-------------------------------------------")