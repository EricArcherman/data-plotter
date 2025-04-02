import matplotlib.pyplot as plt
import os
import matplotlib as mpl

# Set style for research paper
plt.style.use('seaborn-v0_8-paper')
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']
mpl.rcParams['axes.labelsize'] = 16
mpl.rcParams['axes.titlesize'] = 16
mpl.rcParams['xtick.labelsize'] = 14
mpl.rcParams['ytick.labelsize'] = 14

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
graphs_dir = os.path.join(script_dir, 'graphs')

# Ensure graphs directory exists
os.makedirs(graphs_dir, exist_ok=True)

# Read data from files
with open(os.path.join(script_dir, 'omc-results.txt'), 'r') as f:
    omc_data = eval(f.read())
    
with open(os.path.join(script_dir, 'r1cs-results.txt'), 'r') as f:
    r1cs_data = eval(f.read())

# Split data into x and y coordinates
omc_x = [point[0] for point in omc_data]
omc_y = [point[1]/1e9 * 5/3.25 for point in omc_data] # Convert to billions

r1cs_x = [point[0] for point in r1cs_data] 
r1cs_y = [point[1]/1e9 for point in r1cs_data] # Convert to billions

# Create the plot
fig, ax = plt.subplots(figsize=(12, 10))
ax.plot(omc_x, omc_y, color='#2E4057', linewidth=2, label='Jolt')
ax.plot(r1cs_x, r1cs_y, color='#2E7D32', linewidth=2, label='LightningJolt')

ax.set_xlabel('Fibonacci Benchmark Number', fontsize=12, labelpad=10)
ax.set_ylabel('Prover Time (s)', fontsize=12, labelpad=10)
ax.set_title('Prover Time: Jolt vs LightningJolt', fontsize=14, pad=15)
ax.legend(frameon=True, fancybox=False, edgecolor='black', fontsize=10)
ax.grid(True, linestyle='--', alpha=0.7)

# Adjust layout
plt.tight_layout()

# Save the plot with high DPI for publication quality
output_file = os.path.join(graphs_dir, 'prove_hyperkzg_comparison.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()

print(f"Generated graph: {output_file}")
