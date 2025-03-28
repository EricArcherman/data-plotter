use serde_cbor::from_slice;
use std::fs::{File, read};
use std::io::Write;
use walkdir::WalkDir;
use std::collections::HashMap;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Walk through all directories in the data folder
    for entry in WalkDir::new("omc-regs-fib-hyperkzg-benchmark-results/data")
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();

        println!("{}", path.display());
    }

    Ok(())
}

