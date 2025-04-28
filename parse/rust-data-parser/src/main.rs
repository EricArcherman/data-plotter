use walkdir::WalkDir;

use serde_cbor::Value;
use std::fs::File;
use std::io::BufReader;

fn decode_cbor(path: &str) -> Result<Vec<(i32, f64)>, Box<dyn std::error::Error>> {
    let mut number_path: Vec<(i32,String)> = Vec::new(); 

    // Walk through all directories in the given folder
    for entry in WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();

        if path.to_str().unwrap().split("/").last().unwrap().starts_with("measurement") {
            // Get the parent directory name which contains the number
            let dir_name = path.parent().unwrap().file_name().unwrap().to_str().unwrap();
            // Extract the number from "Xth fibonacci number"
            let number = dir_name.split("th").next().unwrap().parse::<i32>().unwrap();

            number_path.push((number, path.to_str().unwrap().to_string()));
        }
    }
    number_path.sort_by_key(|&(num, _)| num);

    
    // fibonacci number and benchmark time vector
    let mut number_time: Vec<(i32, f64)> = Vec::new();

    // Decode the .cbor files
    for pair in number_path {
        let file = File::open(pair.1)?;
        let reader = BufReader::new(file);
        let value: Value = serde_cbor::from_reader(reader)?;
        
        if let Value::Map(map) = value {
            if let Some(Value::Map(estimates)) = map.get(&Value::Text("estimates".to_string())) {
                if let Some(Value::Map(median)) = estimates.get(&Value::Text("median".to_string())) {
                    if let Some(Value::Float(point_estimate)) = median.get(&Value::Text("point_estimate".to_string())) {
                        number_time.push((pair.0, *point_estimate));
                    }
                }
            }
        }
    }

    Ok(number_time)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let paths = ["../regs-r1cs-fib-hyperkzg-benchmark-results/data", "../regs-omc-fib-hyperkzg-benchmark-results/data"];
    let output_files = ["../python-plotter/r1cs-results.txt", "../python-plotter/omc-results.txt"];

    for (path, output_file) in paths.iter().zip(output_files.iter()) {
        match decode_cbor(path) {
            Ok(fib_time) => {
                let mut content = String::new();
                content.push_str("[");
                for (i, (number, time)) in fib_time.iter().enumerate() {
                    if i > 0 {
                        content.push_str(", ");
                    }
                    content.push_str(&format!("({}, {})", number, time));
                }
                content.push_str("]");
                std::fs::write(output_file, content)?;
                println!("Results written to {}", output_file);
            },
            Err(e) => eprintln!("Error: {}", e),
        }
    }
    Ok(())
}