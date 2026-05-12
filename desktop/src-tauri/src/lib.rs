use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

fn python_candidates() -> Vec<&'static str> {
    if cfg!(target_os = "windows") {
        vec!["py", "python"]
    } else {
        vec!["python3", "python"]
    }
}

fn repo_src_path() -> String {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .and_then(|desktop| desktop.parent())
        .map(|repo| repo.join("src"))
        .unwrap_or_else(|| manifest_dir.join(".." ).join(".." ).join("src"))
        .to_string_lossy()
        .to_string()
}

fn run_python(script: &str, stdin_payload: Option<&str>) -> Result<String, String> {
    let pythonpath = repo_src_path();
    let mut last_error = String::from("Python was not found.");

    for executable in python_candidates() {
        let mut command = Command::new(executable);
        if executable == "py" {
            command.arg("-3");
        }
        command
            .arg("-c")
            .arg(script)
            .env("PYTHONPATH", &pythonpath)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        if stdin_payload.is_some() {
            command.stdin(Stdio::piped());
        }

        let mut child = match command.spawn() {
            Ok(child) => child,
            Err(error) => {
                last_error = format!("{executable}: {error}");
                continue;
            }
        };

        if let Some(payload) = stdin_payload {
            if let Some(mut stdin) = child.stdin.take() {
                if let Err(error) = stdin.write_all(payload.as_bytes()) {
                    return Err(format!("Failed to pass data to Python: {error}"));
                }
            }
        }

        let output = child
            .wait_with_output()
            .map_err(|error| format!("Failed to wait for Python process: {error}"))?;

        if output.status.success() {
            return String::from_utf8(output.stdout).map_err(|error| format!("Python returned invalid UTF-8: {error}"));
        }

        last_error = String::from_utf8_lossy(&output.stderr).trim().to_string();
        if last_error.is_empty() {
            last_error = format!("Python exited with status {}", output.status);
        }
    }

    Err(last_error)
}

#[tauri::command]
fn list_printers() -> Result<Vec<String>, String> {
    let script = r#"
import json
from zebra_label_tool.printing import get_printers
print(json.dumps(get_printers()))
"#;
    let stdout = run_python(script, None)?;
    serde_json::from_str(stdout.trim()).map_err(|error| format!("Could not parse printer list: {error}"))
}

#[tauri::command]
fn print_zpl(printer: String, zpl: String) -> Result<(), String> {
    let payload = serde_json::json!({ "printer": printer, "zpl": zpl }).to_string();
    let script = r#"
import json
import sys
from zebra_label_tool.printing import send_zpl_to_printer
payload = json.load(sys.stdin)
send_zpl_to_printer(payload["printer"], payload["zpl"])
print("OK")
"#;
    run_python(script, Some(&payload)).map(|_| ())
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![list_printers, print_zpl])
        .run(tauri::generate_context!())
        .expect("error while running Zebra Label Tool desktop client");
}
