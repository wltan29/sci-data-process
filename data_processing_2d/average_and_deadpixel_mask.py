'''
Author:     Liam Tan
Created:    2024.10.31

This code has two functions: Average 2D images and Merging Dead Pixels for a group of images with the same basename
Average 2D images
   Only images taken with repetitively on the same sample will be averaged. Individual image will not be processed.
   Avreaged images will be saved with '_avg' appended to the end of the name.
   Bugs remain: Doens't work when collecting single images with the same name ends with '_' followed by 4 integers.
   Bugs remain: When using DrivePV, it averages 3 loop, 3 position, 1 images/position when it shouldn't. This is due to file name structure and it can't be fixed.
Merging Dead Pixels
   It will create a mask file that capture pixels that saturated at least once in an image group (repeated collection with same parameter)
   Saturated pixel has a value of 1, the rest are 0. Value for saturated pixels can be changed to any number.
   Potential improvement: Add filename filtering to select specific data to process instead of processing all data in a folder.

Only need to change parameters in the INPUT section.
'''


import os
import numpy as np
from PIL import Image
from glob import glob
from scidata.io_utils import filter_files, format_windows_path


# Define INPUT parameters here
input_path = r"path/to/tif_folder"
output_path = r"path/to/output"
ftype_filter = (".tif")
fn_filter_cond = "_long_"
average_images_prompt = True # True if averaging images, False if not.
merge_dead_pixel_prompt = True # True if merging dead pixels, False if not.
saturate_threshold = 65535 # Value for saturated pixel is 65535.


input_path = format_windows_path(input_path)
output_path = format_windows_path(output_path)

def check_if_integer(name):
    # Check if name is integer, return True if it is and False if it isn't
    try:
        int(name)
        return True
    except ValueError:
        return False

def create_output_pathectory(output_path):
    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)


def group_images(image_files):
    # Dictionary to store grouped images based on base name
    image_groups = {}
    for image_path in image_files:
        base_name = os.path.basename(image_path).replace('.tif', '')
        
        # Do not process offset and gain files, and also if the filename doesn't end of '_' followed by 4 integers.
        if (('_offset_' not in image_path) and
            ('_gain_' not in image_path) and
            check_if_integer(base_name.split('_')[-1]) and
            len(base_name.split('_')[-1]) == 4):
            base_name = base_name[:-5]  # Remove last 5 characters excluding the tif extension
            image_groups.setdefault(base_name, []).append(image_path)
    return image_groups

def process_image_names(image_groups):
    # Remove image groups that shouldn't be averaged
    keys = list(image_groups.keys())
    for key in keys:
        do_average_check = [False, False]  # The first check is based on filename, the second is based on number of values for each key
        name_component_dic = {}
        
        # Name processing
        name_split = key.split('_')
        for j, name_component in enumerate(reversed(name_split), 1):
            if check_if_integer(name_component):
                label = f'{name_component}'  # This is an integer
            elif 'p' in name_component and len(name_component) >= 5:
                name_component_split = name_component.split('p')
                if check_if_integer(name_component_split[-1]) and len(name_component_split[-1]) == 3:
                    label = f'{name_component} --> DrivePV'
                else:
                    label = f'{name_component} --> X Integer'
            else:
                label = f'{name_component} --> X Integer'
            name_component_dic[f'-{j}'] = label

        # Update do_average_checks based on name components
        if (check_if_integer(name_component_dic.get('-1', '')) and
                len(name_component_dic['-1']) == 4):
            do_average_check[0] = True
        if 'DrivePV' in name_component_dic.get('-1', ''):
            do_average_check[0] = True
        if len(image_groups[key]) > 1:  # Only average if there is more than one value for this image group key
            do_average_check[1] = True
        
        # Remove group if it doesn't pass checks
        if not all(do_average_check):
            print(f'**Removed \'{key}\' x {len(image_groups[key])} images from the image_groups dictionary**\n')
            del image_groups[key]

def process_images(image_groups, output_path, average_images_prompt, merge_dead_pixel_prompt, saturate_threshold):
    print('----------------------------------')
    print('Processing images')  
    print('----------------------------------')  
          
    for base_name, files in image_groups.items():
        print(f"Merging {base_name}")
        img_arrays = [np.array(Image.open(file), dtype=np.uint16) for file in files]  # Load images and accumulate them for averaging
        
        if average_images_prompt == True:
            print('----------------------------------') 
            print('Averaging images')  
            avg_img_array = np.mean(img_arrays, axis=0).astype(np.uint16)  # Calculate the average image, ensuring 16-bit precision
            avg_img = Image.fromarray(avg_img_array, mode='I;16')  # Convert the array back to an image
            avg_image_name = f"{base_name}_avg.tif"
            avg_img.save(os.path.join(output_path, avg_image_name))
            print(f"-- {avg_image_name} saved successfully")

        if merge_dead_pixel_prompt == True:
            print('----------------------------------') 
            print('Merging dead pixels')          
            # Initialize the average array with zeros
            mask_sum = np.zeros_like(img_arrays[0], dtype=np.float64)

            print(f'Total number of images: {len(img_arrays)}')
            
            # Create a Boolean mask that captures pixels that are saturated in individual images
            for i, img in enumerate(img_arrays):
                mask = img >= saturate_threshold  # Create a mask for pixels exceeding the threshold
                print(f'-- Dead pixels in image {i + 1}: {np.sum(mask)}')
                mask_sum += mask  # Element-wise addition, each True is 1, each False is 0
                
            print('**Merged dead pixels statistics**')
            for i in range(len(img_arrays), 0, -1):
                print(f'-- Pixels dead in {i} images: {np.sum(mask_sum == i)}')
            
            mask_sum_bool = mask_sum > 0
            print(f'Pixels dead at least once: {np.sum(mask_sum_bool)}')
            
            mask_sum_merge = mask_sum_bool * 65535 # Follow dead pixel value of XRpad.
            
            mask_deadpixel_array = mask_sum_merge.astype(np.uint16)  # Ensuring 16-bit precision for the dead pixel array
            mask_deadpixel = Image.fromarray(mask_deadpixel_array, mode='I;16')  # Convert the array back to an image
            mask_deadpixel_name = f"{base_name}_deadpixels_{np.sum(mask_sum_bool)}.tif"
            mask_deadpixel.save(os.path.join(output_path, mask_deadpixel_name))
            print(f"{mask_deadpixel_name} saved successfully")
            print('----------------------------------')  


# Main processing flow
create_output_pathectory(output_path)
image_files = filter_files(input_path, ftype_filter, fn_filter_cond)
image_groups = group_images(image_files)  # Store grouped images in a dictionary based on base name
process_image_names(image_groups)  # Remove image groups that shouldn't be averaged

# Print out image_group list of key after name processing
print('Processing following image groups')  
print('----------------------------------')  
for key, group in image_groups.items():
    print(f'{key} : {len(group)} images')
print('----------------------------------')

# Processs image depending on the average images and merge dead pixel prompts
process_images(image_groups, output_path, average_images_prompt, merge_dead_pixel_prompt, saturate_threshold)