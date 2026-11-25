use std::{fs::File, io::{BufReader, Read}};

fn main() {
    if let Ok(file) = File::open("bug.txt") {
        let mut reader = BufReader::new(file);
        let mut mod_info = String::new();
        reader.read_to_string();
    }
}
