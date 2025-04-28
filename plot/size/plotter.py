import matplotlib.pyplot as plt
import os
import matplotlib as mpl
from ast import literal_eval

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

# result files
omc_file = os.path.join(dir, 'omc_results.txt')
r1cs_file = os.path.join(dir, 'r1cs_results.txt')

with open(omc_file, 'r') as f:
    omc_data = literal_eval(f.read())

with open(r1cs_file, 'r') as f:
    r1cs_data = literal_eval(f.read())

fig, ax = plt.subplots(figsize=(6, 5))
omc_x = [point[0] for point in omc_data]
omc_y = [point[1] * 1024 for point in omc_data]
r1cs_x = [point[0] for point in r1cs_data] 
r1cs_y = [point[1] * 1024 for point in r1cs_data]

ax.plot(omc_x, omc_y, color='#2E4057', linewidth=2, label='Jolt')
ax.plot(r1cs_x, r1cs_y, color='#2E7D32', linewidth=2, label='LightningJolt')

ax.set_xlabel('Fibonacci Benchmark Number', fontsize=24, labelpad=10)
ax.set_ylabel('Proof Size (kb)', fontsize=24, labelpad=10)

title = 'Proof Size'
    
ax.set_title(f'{title}', fontsize=32, pad=15)
ax.legend(frameon=True, fancybox=False, edgecolor='black', fontsize=18)
ax.grid(True, linestyle='--', alpha=0.7)


plt.tight_layout()

output_file = os.path.join(dir, f'{dir.split("/")[-1]}_plot.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()
    
print(f"Generated graph: {output_file}")