"""Fit a 3rd-order polynomial to sample-height calibration points.

Reads the first two columns of a CSV as (x, y), fits ``numpy.polyfit`` degree 3,
and plots the points with the fitted curve and its equation in the legend. Edit
``file_path`` / ``output_path`` below.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# File path to the CSV file
file_path = r'path/to/alldatapoints.csv'

# Read the CSV file into a pandas DataFrame
df = pd.read_csv(file_path)

# Extract the first two columns
x_data = df[df.columns[0]]  # First column as x-axis
y_data = df[df.columns[1]]  # Second column as y-axis

# Perform a third-order polynomial fit
coeffs = np.polyfit(x_data, y_data, 3)

# Generate a polynomial function using the fitted coefficients
poly_func = np.poly1d(coeffs)

# Generate data for the fitted curve
x_fit = np.linspace(min(x_data), max(x_data), 100)
y_fit = poly_func(x_fit)

# Plot the original data and the fitted curve
plt.figure(figsize=(10, 7))
plt.scatter(x_data, y_data, label='Fitted Peak Position', color='blue', marker='o')  # Original data points
plt.plot(x_fit, y_fit, label=f'3rd Order Poly Fit: $y = {coeffs[0]:.3e}x^3 + {coeffs[1]:.3e}x^2 + {coeffs[2]:.3e}x + {coeffs[3]:.3e}$', color='red')  # Fitted curve

# Label the axes with column headers
plt.xlabel(df.columns[0])
plt.ylabel(df.columns[1])

# Add a title and legend
plt.legend()
#plt.title('Third-Order Polynomial Fit')

# Display the polynomial coefficients in scientific notation with 3 significant figures on the plot
#plt.text(0.05, 0.95, 
#         f'Coefficients:\n{coeffs[0]:.3e} (x^3)\n{coeffs[1]:.3e} (x^2)\n{coeffs[2]:.3e} (x)\n{coeffs[3]:.3e}', 
#         transform=plt.gca().transAxes, fontsize=10, verticalalignment='top')

# Save the plot as an image file (e.g., PNG format)
output_path = r'path/to/poly_fit_plot.png'
plt.savefig(output_path, format='png')

# Show the plot
plt.show()
