import matplotlib.pyplot as plt
import matplotlib as mpl
import ast
import os

# Set style for research paper
plt.style.use('seaborn-v0_8-paper')
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']
mpl.rcParams['axes.labelsize'] = 24
mpl.rcParams['axes.titlesize'] = 32
mpl.rcParams['xtick.labelsize'] = 18
mpl.rcParams['ytick.labelsize'] = 18
mpl.rcParams['legend.fontsize'] = 18

# Read and parse the data
dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(dir, 'mem_overhead.txt'), 'r') as f:
    data = ast.literal_eval(f.read())

# Extract x and y values
x_values = [item[0] for item in data]
y_values = [item[1] for item in data]

# Create the plot
fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(x_values, y_values, 'o-', color='#2E4057', linewidth=2, markersize=8)

# Add labels and title
ax.set_xlabel('Trace Length', fontsize=24, labelpad=10)
ax.set_ylabel('Percent Memory Proof (%)', fontsize=24, labelpad=10)
ax.set_title('Memory Proof Overhead', fontsize=32, pad=15)

# Set y-axis limits
ax.set_ylim(40, 80)

# Add grid for better readability
ax.grid(True, linestyle='--', alpha=0.7)

# Save the plot
plt.tight_layout()
plt.savefig(os.path.join(dir, 'mem_overhead_plot.png'), dpi=300, bbox_inches='tight')
plt.close()