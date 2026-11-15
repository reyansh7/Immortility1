//! Private current-user DPAPI rendezvous. No token or arbitrary path crosses IPC.
use serde::Deserialize;
use std::{io::Read, path::Path};

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub schema_version: String,
    pub runtime: String,
    pub instance_id: String,
    pub url: String,
    pub token: String,
    pub pid: u32,
    pub created: u64,
    pub executable: String,
    pub project_root: String,
    pub data_root: String,
}

pub(crate) fn endpoint(url: &str) -> bool {
    url.strip_prefix("http://127.0.0.1:")
        .and_then(|port| port.parse::<u16>().ok())
        .is_some_and(|port| port > 0 && url == format!("http://127.0.0.1:{port}"))
}

fn same_path(a: &Path, b: &Path) -> bool {
    match (a.canonicalize(), b.canonicalize()) {
        (Ok(a), Ok(b)) => a == b,
        _ => false,
    }
}

#[cfg(windows)]
fn decrypt(input: &[u8]) -> Result<Vec<u8>, String> {
    use windows_sys::Win32::{Foundation::LocalFree, Security::Cryptography::*};
    let entropy = b"Immortility local headless connection v1";
    let source = CRYPT_INTEGER_BLOB {
        cbData: input.len() as u32,
        pbData: input.as_ptr() as _,
    };
    let extra = CRYPT_INTEGER_BLOB {
        cbData: entropy.len() as u32,
        pbData: entropy.as_ptr() as _,
    };
    let mut output: CRYPT_INTEGER_BLOB = unsafe { std::mem::zeroed() };
    unsafe {
        if CryptUnprotectData(
            &source,
            std::ptr::null_mut(),
            &extra,
            std::ptr::null(),
            std::ptr::null(),
            CRYPTPROTECT_UI_FORBIDDEN,
            &mut output,
        ) == 0
        {
            return Err("Protected background connection could not be verified.".into());
        }
        let result = if output.cbData > 0 && output.cbData <= 16000 {
            Ok(std::slice::from_raw_parts(output.pbData, output.cbData as usize).to_vec())
        } else {
            Err("Invalid protected connection size.".into())
        };
        for i in 0..output.cbData as usize {
            std::ptr::write_volatile(output.pbData.add(i), 0);
        }
        LocalFree(output.pbData as _);
        result
    }
}

#[cfg(not(windows))]
fn decrypt(_: &[u8]) -> Result<Vec<u8>, String> {
    Err("Windows DPAPI is required.".into())
}

#[cfg(windows)]
pub fn alive(record: &Record) -> bool {
    use windows_sys::Win32::{Foundation::*, System::Threading::*};
    unsafe {
        let process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, record.pid);
        if process.is_null() {
            return false;
        }
        let mut code = 0;
        let mut times: [FILETIME; 4] = std::mem::zeroed();
        let mut name = [0u16; 4096];
        let mut length = name.len() as u32;
        let result = GetExitCodeProcess(process, &mut code) != 0
            && code == 259
            && GetProcessTimes(
                process,
                &mut times[0],
                &mut times[1],
                &mut times[2],
                &mut times[3],
            ) != 0
            && ((times[0].dwHighDateTime as u64) << 32 | times[0].dwLowDateTime as u64)
                == record.created
            && QueryFullProcessImageNameW(process, 0, name.as_mut_ptr(), &mut length) != 0
            && same_path(
                Path::new(&String::from_utf16_lossy(&name[..length as usize])),
                Path::new(&record.executable),
            );
        CloseHandle(process);
        result
    }
}

#[cfg(not(windows))]
pub fn alive(_: &Record) -> bool {
    false
}

pub fn read(data_root: &Path, project_root: &Path) -> Result<Record, String> {
    let path = data_root.join("background-connection.dpapi");
    let mut encrypted = Vec::new();
    std::fs::File::open(path)
        .map_err(|_| "No published background runtime. Start it explicitly first.")?
        .take(32001)
        .read_to_end(&mut encrypted)
        .map_err(|_| "Cannot read protected connection.")?;
    if encrypted.is_empty() || encrypted.len() > 32000 {
        return Err("Invalid protected connection size.".into());
    }
    let mut plaintext = decrypt(&encrypted)?;
    let parsed = serde_json::from_slice::<Record>(&plaintext);
    for byte in &mut plaintext {
        unsafe {
            std::ptr::write_volatile(byte, 0);
        }
    }
    let record = parsed.map_err(|_| "Invalid background connection contract.")?;
    let cfg = std::fs::read_to_string(project_root.join(".venv/pyvenv.cfg"))
        .map_err(|_| "Reviewed Python environment unavailable.")?;
    let home = cfg
        .lines()
        .find_map(|line| line.strip_prefix("home = "))
        .ok_or("Reviewed Python home unavailable.")?;
    if record.schema_version != "1.0"
        || record.runtime != "local-read-workflows"
        || !endpoint(&record.url)
        || !(32..=128).contains(&record.token.len())
        || !record.token.bytes().all(|b| (33..127).contains(&b))
        || record.instance_id.len() != 36
        || record.pid == 0
        || record.created == 0
        || !same_path(Path::new(&record.project_root), project_root)
        || !same_path(Path::new(&record.data_root), data_root)
        || !same_path(
            Path::new(&record.executable),
            &Path::new(home).join("python.exe"),
        )
        || !alive(&record)
    {
        return Err("Background endpoint, runtime scope or process identity changed.".into());
    }
    Ok(record)
}

pub fn verified_health(body: &serde_json::Value, record: &Record) -> bool {
    body["instance_id"] == record.instance_id
        && body["runtime_mode"] == "local-background"
        && body["free_only"] == true
        && body["capture_enabled"] == false
        && body["code_execution_enabled"] == false
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn private_endpoint_is_literal_loopback_only() {
        assert!(endpoint("http://127.0.0.1:12345"));
        for url in [
            "http://localhost:12345",
            "https://127.0.0.1:12345",
            "http://127.0.0.1:0",
            "http://127.0.0.1:00123",
            "http://127.0.0.1:123/a",
            "http://127.0.0.1:123@evil.test",
        ] {
            assert!(!endpoint(url));
        }
    }
}
