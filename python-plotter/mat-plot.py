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

target_x = 70000
omc_idx = min(range(len(omc_x)), key=lambda i: abs(omc_x[i] - target_x))
r1cs_idx = min(range(len(r1cs_x)), key=lambda i: abs(r1cs_x[i] - target_x))

# Draw vertical line segment between points
ax.plot([target_x, target_x], [r1cs_y[r1cs_idx], omc_y[omc_idx]], 
        color='gray', linestyle='--', alpha=0.5, linewidth=1.5)

# Plot points and add labels
ax.plot(omc_x[omc_idx], omc_y[omc_idx], 'o', color='#2E4057', markersize=8)
ax.plot(r1cs_x[r1cs_idx], r1cs_y[r1cs_idx], 'o', color='#2E7D32', markersize=8)

# Add point labels with improved formatting
ax.annotate(f'Jolt: ({target_x}, {omc_y[omc_idx]:.2f}s)', 
            xy=(omc_x[omc_idx], omc_y[omc_idx]),
            xytext=(-90, 15), textcoords='offset points',
            fontsize=16, color='#2E4057',
            bbox=dict(facecolor='white', edgecolor='#2E4057', alpha=0.8))
ax.annotate(f'LightningJolt: ({target_x}, {r1cs_y[r1cs_idx]:.2f}s)', 
            xy=(r1cs_x[r1cs_idx], r1cs_y[r1cs_idx]),
            xytext=(-30, -25), textcoords='offset points',
            fontsize=16, color='#2E7D32',
            bbox=dict(facecolor='white', edgecolor='#2E7D32', alpha=0.8))

# Calculate and add speedup factor with enhanced visibility
speedup = omc_y[omc_idx] / r1cs_y[r1cs_idx]
mid_y = (omc_y[omc_idx] + r1cs_y[r1cs_idx]) / 2
ax.annotate(f'{speedup:.1f}× faster',
            xy=(target_x, mid_y),
            xytext=(-100, 0), textcoords='offset points',
            fontsize=54, color='#39FF14',  # Bright neon green
            bbox=dict(facecolor='white',  # Light green background
                      edgecolor='#39FF14',
                      linewidth=2,  # Thicker edges
                      alpha=0.9,
                      pad=15),
            fontweight='bold')

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
