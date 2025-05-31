import os
from ast import literal_eval

# Get the directory where this script is located
dir = os.path.dirname(os.path.abspath(__file__))

# result files
omc_file = os.path.join(dir, 'omc_results.txt')
r1cs_file = os.path.join(dir, 'r1cs_results.txt')

with open(omc_file, 'r') as f:
    omc_data = literal_eval(f.read())

with open(r1cs_file, 'r') as f:
    r1cs_data = literal_eval(f.read())

# Calculate and print ratios
print("Number\tOMC/R1CS Ratio")
print("-" * 25)

for omc_point, r1cs_point in zip(omc_data, r1cs_data):
    number = omc_point[0]
    omc_value = omc_point[1]
    r1cs_value = r1cs_point[1]
    ratio = omc_value / r1cs_value * 5/4.7
    print(f"{number}\t{ratio:.2f}")
