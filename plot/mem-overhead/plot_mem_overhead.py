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
plt.figure(figsize=(10, 6))
plt.plot(x_values, y_values, 'o-', linewidth=2, markersize=8)

# Add labels and title
plt.xlabel('Trace Length')
plt.ylabel('Percent Memory Proof (%)')
plt.title('Memory Proof Overhead')

# Set y-axis limits
plt.ylim(40, 80)

# Add grid for better readability
plt.grid(True, linestyle='--', alpha=0.7)

# Save the plot
plt.tight_layout()
plt.savefig(os.path.join(dir, 'mem_overhead_plot.png'), dpi=300, bbox_inches='tight')
plt.close()