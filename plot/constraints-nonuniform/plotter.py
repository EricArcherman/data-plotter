import matplotlib.pyplot as plt
import matplotlib as mpl
import ast
import os
import numpy as np

# Set style for research paper
plt.style.use('seaborn-v0_8-paper')
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']
mpl.rcParams['axes.labelsize'] = 24
mpl.rcParams['axes.titlesize'] = 32
mpl.rcParams['xtick.labelsize'] = 18
mpl.rcParams['ytick.labelsize'] = 18
mpl.rcParams['legend.fontsize'] = 18

# Get the directory where this script is located
dir = os.path.dirname(os.path.abspath(__file__))

# Read data from files
data_files = ['372.txt', '629.txt', '22765.txt']
data_series = {}

for file_name in data_files:
    file_path = os.path.join(dir, file_name)
    with open(file_path, 'r') as f:
        data_series[file_name] = ast.literal_eval(f.read())

# Create the plot
fig, ax = plt.subplots(figsize=(8, 6))

# Plot each series with different colors and markers
colors = ['#2E4057', '#2E7D32', '#C62828']
markers = ['o', 's', '^']

for (file_name, data), color, marker in zip(data_series.items(), colors, markers):
    series_num = file_name.split(".")[0]  # Extract number from filename
    label = f'{series_num} init trace length'  # Add complexity notation
    x_vals, y_vals = zip(*data)
    
    # Plot the data points and connecting lines
    ax.plot(x_vals, y_vals, color=color, linewidth=2, label=label)
    ax.scatter(x_vals, y_vals, color=color, marker=marker, s=64, 
              edgecolor='black', linewidth=1.5, zorder=3)

# Set labels and title
ax.set_xlabel('Added Non-Uniform Constraints', fontsize=24, labelpad=10)
ax.set_ylabel('Time (s)', fontsize=24, labelpad=10)
ax.set_title('Non-Uniform Constraints Scaling', fontsize=32, pad=15)

# Add grid and legend
ax.grid(True, linestyle='--', alpha=0.7)
ax.legend(frameon=True, fancybox=False, edgecolor='black')

# Adjust layout
plt.tight_layout()

# Save the plot
output_file = os.path.join(dir, 'nonuniform_constraints_scaling.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()