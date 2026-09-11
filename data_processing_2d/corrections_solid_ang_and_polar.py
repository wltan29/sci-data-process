"""Visualise 2D detector intensity corrections over a flat area detector.

Builds meshgrids of scattering angle (2theta) and azimuth (chi) for a synthetic
detector, computes the solid-angle correction (cos^3(2theta)) and a
polarisation correction, and shows each as a linked 3D surface plot and a 2D
image. Rotating one 3D subplot rotates them all.

Self-contained -- all parameters are the module-level constants below; nothing
is read from disk.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm

# Generate Data
size, num_points, max_angle = 2000, 201, 45
scale_factor = np.sqrt(2 * size**2) / max_angle
X, Y = np.meshgrid(np.linspace(-size, size, num_points),
                    np.linspace(-size, size, num_points))
TwoTheta = np.sqrt(X**2 + Y**2) / scale_factor
Chi = np.rad2deg(np.arctan2(Y, X))
Solid_Angle_Corr = np.cos(np.deg2rad(TwoTheta))**3
polar_coef = 0.9
Polar_Corr = (((1 - polar_coef) * np.cos(np.deg2rad(Chi))**2 +
               polar_coef * np.sin(np.deg2rad(Chi))**2) *
              np.cos(np.deg2rad(TwoTheta))**2 +
              (1 - polar_coef) * np.sin(np.deg2rad(Chi))**2 +
              polar_coef * np.cos(np.deg2rad(Chi))**2)

def plot_data(ax_surf, ax_im, data, title):
    surf = ax_surf.plot_surface(X, Y, data, cmap=cm.coolwarm)
    ax_surf.set(title=title, xlabel='X', ylabel='Y')
    fig_surf.colorbar(surf, ax=ax_surf, shrink=0.5)  # Ensure correct figure

    im = ax_im.imshow(data, cmap='coolwarm', origin='lower',
                      extent=[-size, size, -size, size])  # Fix axis range
    ax_im.set(title=title, xlabel='X', ylabel='Y')
    fig_im.colorbar(im, ax=ax_im, shrink=0.6)  # Ensure correct figure

# Create Figures
fig_surf, axs_surf = plt.subplots(2, 2, subplot_kw={'projection': '3d'}, figsize=(10, 10))
fig_im, axs_im = plt.subplots(2, 2, figsize=(10, 10))
data_list = [(TwoTheta, 'Two Theta'),
             (Chi, 'Chi'),
             (Solid_Angle_Corr, 'Solid Angle'),
             (Polar_Corr, 'Polarisation = ' + str(polar_coef))]

for ax_surf, ax_im, (data, title) in zip(axs_surf.flat, axs_im.flat, data_list):
    plot_data(ax_surf, ax_im, data, title)

# Function to synchronize the rotation of both subplots
# =====================================================
def on_move(event):
    if event.inaxes in axs_surf.flat:
        elev, azim = event.inaxes.elev, event.inaxes.azim
        for ax in axs_surf.flat:
            ax.view_init(elev=elev, azim=azim)
        fig_surf.canvas.draw_idle()

# Connect the event handler to the figure
fig_surf.canvas.mpl_connect('motion_notify_event', on_move)

fig_surf.tight_layout()
fig_im.tight_layout()
plt.show()
