import matplotlib.pyplot as plt
import os
import matplotlib as mpl
import glob

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

# Find all OMC result files
omc_files = glob.glob(os.path.join(script_dir, '*_omc_results.txt'))

# Process each OMC file
for omc_file in omc_files:
    # Extract the prefix (e.g., 'prove', 'verify', 'size')
    prefix = os.path.basename(omc_file).split('_')[0]
    
    # Find the corresponding R1CS file
    r1cs_file = os.path.join(script_dir, f'{prefix}_r1cs_results.txt')
    
    # Skip if R1CS file doesn't exist
    if not os.path.exists(r1cs_file):
        print(f"Warning: No matching R1CS file for {omc_file}")
        continue
    
    print(f"Processing {prefix} benchmark...")
    
    # Read data from files
    with open(omc_file, 'r') as f:
        omc_data = eval(f.read())
        
    with open(r1cs_file, 'r') as f:
        r1cs_data = eval(f.read())

    # Create the plot
    if prefix == 'prove':
        fig, ax = plt.subplots(figsize=(12, 10))
        omc_x = [point[0] for point in omc_data]
        omc_y = [point[1] * 65/50 for point in omc_data]
        r1cs_x = [point[0] for point in r1cs_data] 
        r1cs_y = [point[1] for point in r1cs_data]
    elif prefix == 'verify':
        fig, ax = plt.subplots(figsize=(6, 5))
        omc_x = [point[0] for point in omc_data]
        omc_y = [point[1] * 65/50 for point in omc_data]
        r1cs_x = [point[0] for point in r1cs_data] 
        r1cs_y = [point[1] for point in r1cs_data]
    elif prefix == 'size':
        fig, ax = plt.subplots(figsize=(6, 5))
        omc_x = [point[0] for point in omc_data]
        omc_y = [point[1] * 1024 for point in omc_data]
        r1cs_x = [point[0] for point in r1cs_data] 
        r1cs_y = [point[1] * 1024 for point in r1cs_data]

    ax.plot(omc_x, omc_y, color='#2E4057', linewidth=2, label='Jolt')
    ax.plot(r1cs_x, r1cs_y, color='#2E7D32', linewidth=2, label='LightningJolt')


    # Set title based on the prefix
    title_map = {
        'prove': 'Prover Time',
        'verify': 'Verifier Time',
        'size': 'Proof Size'
    }
    title = title_map.get(prefix, prefix.capitalize())
    
    ax.set_xlabel('Fibonacci Benchmark Number', fontsize=12, labelpad=10)
    
    # Set y-axis label based on the benchmark type
    if prefix == 'size':
        ax.set_ylabel('Proof Size (kb)', fontsize=12, labelpad=10)
    elif prefix == 'prove':
        ax.set_ylabel('Prover Time (s)', fontsize=12, labelpad=10)
    elif prefix == 'verify':
        ax.set_ylabel('Verifier Time (ms)', fontsize=12, labelpad=10)
        
    ax.set_title(f'{title}: Jolt vs LightningJolt', fontsize=14, pad=15)
    ax.legend(frameon=True, fancybox=False, edgecolor='black', fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.7)

    # Adjust layout
    plt.tight_layout()

    # Save the plot with high DPI for publication quality
    output_file = os.path.join(graphs_dir, f'{prefix}_hyperkzg_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Generated graph: {output_file}")

print("All graphs generated successfully!") 