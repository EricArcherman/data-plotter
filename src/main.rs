use walkdir::WalkDir;

use serde_cbor::Value;
use std::fs::File;
use std::io::BufReader;

fn decode_cbor(path: &str) -> Result<Vec<(i32, f64)>, Box<dyn std::error::Error>> {
    let mut number_path: Vec<(i32,String)> = Vec::new(); 

    // Walk through all directories in the data folder
    for entry in WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();

        if path.to_str().unwrap().split("/").last().unwrap().starts_with("measurement") {
            let number = path.to_str().unwrap().split("/").nth(2).unwrap().split("th").nth(0).unwrap().parse::<i32>().unwrap();

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

fn main() {
    let path = "omc-regs-fib-hyperkzg-benchmark-results/data";

    match decode_cbor(path) {
        Ok(fib_time) => println!("{:?}", fib_time),
        Err(e) => eprintln!("Error: {}", e),
    }
}