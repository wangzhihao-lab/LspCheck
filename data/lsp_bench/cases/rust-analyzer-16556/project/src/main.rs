fn main() {
    let files = [1];

    let query = if files.is_empty() {
        return;
    } else if files.len() == 1 {
        1
    } else {
        17
    };
    print!("{query}");
}
