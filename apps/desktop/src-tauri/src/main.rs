#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use futures_util::StreamExt;
mod attachment;
mod credentials;
use serde::{Deserialize, Serialize};
use std::{
    io::{BufRead, BufReader, Read, Write},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
};
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{Emitter, LogicalSize, Manager, PhysicalPosition};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

#[derive(Clone, Serialize, Deserialize)]
struct Connection {
    url: String,
    token: String,
}
struct Broker {
    child: Child,
    info: Connection,
    #[cfg(windows)]
    job: isize,
}
impl Drop for Broker {
    fn drop(&mut self) {
        // EOF requests graceful shutdown; the job handle guarantees descendant cleanup on crash.
        self.child.stdin.take();
        let _ = self.child.kill();
        let _ = self.child.wait();
        #[cfg(windows)]
        unsafe {
            if self.job != 0 {
                windows_sys::Win32::Foundation::CloseHandle(self.job as _);
            }
        }
    }
}
struct Supervisor {
    broker: Mutex<Option<ManagedBroker>>,
    root: PathBuf,
    data_root: PathBuf,
    isolated_background: bool,
}

enum ManagedBroker {
    Owned(Broker),
    Attached(attachment::Record),
    Detached,
}
impl ManagedBroker {
    fn info(&self) -> Result<Connection, String> {
        match self {
            Self::Owned(broker) => Ok(broker.info.clone()),
            Self::Attached(record) if attachment::alive(record) => Ok(Connection {
                url: record.url.clone(),
                token: record.token.clone(),
            }),
            Self::Attached(_) => {
                Err("Background runtime ended. Attach explicitly after restarting it.".into())
            }
            Self::Detached => Err("Dashboard detached. Attach a local background runtime.".into()),
        }
    }
}

const COMPACT: (f64, f64) = (148., 176.);

fn runtime_directory(root: &std::path::Path) -> Result<(PathBuf, bool), String> {
    // Debug-only acceptance root: cannot select arbitrary paths or start a model
    // broker. Production IPC never accepts a rendezvous path from the webview.
    #[cfg(debug_assertions)]
    {
        let args: Vec<String> = std::env::args().collect();
        if let Some(pair) = args.windows(2).find(|pair| {
            pair[0] == "--local-background-test-root" || pair[0] == "--model-hub-test-root"
        }) {
            let path = PathBuf::from(&pair[1])
                .canonicalize()
                .map_err(|_| "Acceptance data root must exist.")?;
            let scope = root
                .join(".cache")
                .canonicalize()
                .map_err(|_| "Acceptance workspace unavailable.")?;
            if !path.starts_with(&scope) || path == scope {
                return Err(
                    "Acceptance data must be inside this workspace's .cache directory.".into(),
                );
            }
            return Ok((path, pair[0] == "--local-background-test-root"));
        }
    }
    Ok((
        std::env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|| root.join("data"))
            .join("Immortility"),
        false,
    ))
}

#[derive(Serialize, Deserialize)]
struct Placement {
    monitor: Option<String>,
    right: bool,
    fraction: f64,
}
fn placement_file(app: &tauri::AppHandle) -> Option<PathBuf> {
    if let Some(state) = app.try_state::<Supervisor>() {
        if state.isolated_background {
            return Some(state.data_root.join("placement.json"));
        }
    }
    app.path()
        .app_config_dir()
        .ok()
        .map(|p| p.join("placement.json"))
}
fn save_placement(window: &tauri::WebviewWindow) {
    // Only the compact face owns the saved anchor; chat, overlay and command center do not.
    if window
        .outer_size()
        .map(|size| {
            let scale = window.scale_factor().unwrap_or(1.);
            size.width as f64 / scale > COMPACT.0 + 8.
                || size.height as f64 / scale > COMPACT.1 + 8.
        })
        .unwrap_or(true)
    {
        return;
    }
    let (Ok(Some(monitor)), Ok(position)) = (window.current_monitor(), window.outer_position())
    else {
        return;
    };
    let work = monitor.work_area();
    let placement = Placement {
        monitor: monitor.name().cloned(),
        right: position.x > work.position.x + work.size.width as i32 / 2,
        fraction: ((position.y - work.position.y) as f64 / work.size.height as f64).clamp(0., 1.),
    };
    if let Some(path) = placement_file(window.app_handle()) {
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if let Ok(json) = serde_json::to_vec(&placement) {
            let _ = std::fs::write(path, json);
        }
    }
}
fn restore_placement(window: &tauri::WebviewWindow) -> tauri::Result<()> {
    let placement = placement_file(window.app_handle())
        .and_then(|p| std::fs::read(p).ok())
        .and_then(|b| serde_json::from_slice::<Placement>(&b).ok());
    let monitors = window.available_monitors()?;
    let target = placement
        .as_ref()
        .and_then(|p| monitors.iter().find(|m| m.name() == p.monitor.as_ref()))
        .cloned()
        .or(window.primary_monitor()?);
    if let Some(monitor) = target {
        let work = monitor.work_area();
        let size = window.outer_size()?;
        let right = placement.as_ref().map(|p| p.right).unwrap_or(true);
        let fraction = placement
            .as_ref()
            .map(|p| p.fraction)
            .filter(|f| f.is_finite())
            .unwrap_or(0.2)
            .clamp(0., 1.);
        let x = if right {
            work.position.x + work.size.width as i32 - size.width as i32 - 8
        } else {
            work.position.x + 8
        };
        let y = (work.position.y + (work.size.height as f64 * fraction) as i32).clamp(
            work.position.y + 8,
            (work.position.y + work.size.height as i32 - size.height as i32 - 8)
                .max(work.position.y + 8),
        );
        window.set_position(PhysicalPosition::new(x, y))?;
    }
    Ok(())
}

fn spawn_broker(root: &std::path::Path, data_root: &std::path::Path) -> Result<Broker, String> {
    let python = root.join(".venv/Scripts/python.exe");
    if !python.is_file() {
        return Err("Broker dependencies missing. Run scripts/bootstrap-dev.ps1.".into());
    }
    let mut command = Command::new(python);
    #[cfg(debug_assertions)]
    let model_hub_fixture = std::env::args().any(|arg| arg == "--model-hub-test-root");
    #[cfg(not(debug_assertions))]
    let model_hub_fixture = false;
    if model_hub_fixture {
        #[cfg(debug_assertions)]
        {
            let scoped = data_root
                .canonicalize()
                .map_err(|_| "Acceptance root unavailable.")?;
            let cache = root
                .join(".cache")
                .canonicalize()
                .map_err(|_| "Acceptance workspace unavailable.")?;
            if !scoped.starts_with(&cache) || scoped == cache {
                return Err("Acceptance root must stay inside workspace .cache.".into());
            }
            command
                .arg(root.join("scripts/native-model-hub-broker.py"))
                .arg("--data-dir")
                .arg(scoped);
        }
    } else {
        command.args(["-m", "immortility_broker"]);
    }
    command
        .current_dir(root)
        .env("PYTHONPATH", root.join("services/broker/src"))
        .env("PYTHONUTF8", "1")
        .env("DATA_DIR", data_root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    #[cfg(debug_assertions)]
    if model_hub_fixture {
        // Scratch fixture has no vault/environment credentials; never applies to production.
        let diagnostic = std::fs::File::create(data_root.join("broker-startup.stderr.txt"))
            .map_err(|_| "Acceptance diagnostic unavailable.")?;
        command.stderr(Stdio::from(diagnostic));
    }
    let mut child = command
        .spawn()
        .map_err(|_| "Could not start broker Python.".to_string())?;
    #[cfg(windows)]
    let job = unsafe {
        use windows_sys::Win32::System::{JobObjects::*, Threading::*};
        let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
        let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        let process = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, 0, child.id());
        let ok = !handle.is_null()
            && !process.is_null()
            && SetInformationJobObject(
                handle,
                JobObjectExtendedLimitInformation,
                &limits as *const _ as _,
                std::mem::size_of_val(&limits) as u32,
            ) != 0
            && AssignProcessToJobObject(handle, process) != 0;
        if !process.is_null() {
            windows_sys::Win32::Foundation::CloseHandle(process);
        }
        if !ok {
            let _ = child.kill();
            if !handle.is_null() {
                windows_sys::Win32::Foundation::CloseHandle(handle);
            }
            return Err("Cannot establish Windows process cleanup boundary.".into());
        }
        handle as isize
    };
    let stdout = child.stdout.take().ok_or("Broker stdout unavailable.")?;
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let mut line = String::new();
        let result = BufReader::new(stdout)
            .take(16001)
            .read_line(&mut line)
            .map(|_| line);
        let _ = tx.send(result);
    });
    let info = rx
        .recv_timeout(std::time::Duration::from_secs(12))
        .ok()
        .and_then(Result::ok)
        .and_then(|line| serde_json::from_str::<Connection>(&line).ok());
    let Some(info) = info else {
        let _ = child.kill();
        let _ = child.wait();
        #[cfg(windows)]
        unsafe {
            windows_sys::Win32::Foundation::CloseHandle(job as _);
        }
        return Err("Broker did not start. Check .env settings and run scripts/doctor.ps1.".into());
    };
    if !attachment::endpoint(&info.url)
        || !(32..=128).contains(&info.token.len())
        || !info.token.bytes().all(|byte| (33..127).contains(&byte))
    {
        let _ = child.kill();
        let _ = child.wait();
        #[cfg(windows)]
        unsafe {
            windows_sys::Win32::Foundation::CloseHandle(job as _);
        }
        return Err("Invalid broker handshake.".into());
    }
    Ok(Broker {
        child,
        info,
        #[cfg(windows)]
        job,
    })
}

fn ensure_broker(state: &Supervisor) -> Result<Connection, String> {
    let mut guard = state.broker.lock().map_err(|_| "Supervisor unavailable.")?;
    if let Some(ManagedBroker::Owned(broker)) = guard.as_mut() {
        if broker
            .child
            .try_wait()
            .map_err(|_| "Cannot inspect broker.")?
            .is_some()
        {
            *guard = None;
        }
    }
    if guard.is_none() {
        if attachment::read(&state.data_root, &state.root).is_ok() {
            *guard = Some(ManagedBroker::Detached);
            return Err("A local background runtime owns this data. Attach explicitly.".into());
        }
        *guard = Some(ManagedBroker::Owned(spawn_broker(
            &state.root,
            &state.data_root,
        )?));
    }
    guard.as_ref().ok_or("Broker unavailable.")?.info()
}

#[tauri::command]
async fn attach_background(state: tauri::State<'_, Supervisor>) -> Result<(), String> {
    if matches!(
        *state.broker.lock().map_err(|_| "Supervisor unavailable.")?,
        Some(ManagedBroker::Owned(_))
    ) {
        return Err("A desktop broker already owns this data. Quit the desktop, start the background runtime, then reopen and attach.".into());
    }
    let directory = state.data_root.clone();
    let root = state.root.clone();
    let record = tauri::async_runtime::spawn_blocking(move || attachment::read(&directory, &root))
        .await
        .map_err(|_| "Background verification worker failed.".to_string())??;
    let response = local_client(5)?
        .get(format!("{}/health/ready", record.url))
        .bearer_auth(&record.token)
        .send()
        .await
        .map_err(|_| "Background runtime did not answer.".to_string())?;
    if !response.status().is_success() {
        return Err("Background authentication failed.".into());
    }
    let body: serde_json::Value = response
        .json()
        .await
        .map_err(|_| "Invalid background readiness response.")?;
    if !attachment::verified_health(&body, &record) {
        return Err("Background runtime identity or policy changed.".into());
    }
    let mut guard = state.broker.lock().map_err(|_| "Supervisor unavailable.")?;
    if matches!(*guard, Some(ManagedBroker::Owned(_))) {
        return Err("Desktop broker started during attachment; retry after closing it.".into());
    }
    *guard = Some(ManagedBroker::Attached(record));
    Ok(())
}

#[tauri::command]
fn detach_background(state: tauri::State<'_, Supervisor>) -> Result<(), String> {
    let mut guard = state.broker.lock().map_err(|_| "Supervisor unavailable.")?;
    if matches!(*guard, Some(ManagedBroker::Owned(_))) {
        return Err("This dashboard owns a desktop broker; use Quit to stop it.".into());
    }
    *guard = Some(ManagedBroker::Detached);
    Ok(())
}

#[tauri::command]
async fn connection(app: tauri::AppHandle) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        ensure_broker(&app.state::<Supervisor>()).map(|_| ())
    })
    .await
    .map_err(|_| "Supervisor worker failed.".to_string())?
}

#[derive(Deserialize, Clone, Copy)]
#[serde(rename_all = "snake_case")]
enum Operation {
    Health,
    Sessions,
    CreateSession,
    SessionTasks,
    CreateTask,
    Task,
    TaskTrace,
    TaskUsage,
    ListCapabilities,
    CreateWorkflow,
    GetWorkflow,
    StartObservation,
    ObservationResult,
    ShutdownBackground,
    Cancel,
    Stop,
    VoiceStatus,
    VoiceDevices,
    VoicePrepare,
    VoiceRecord,
    VoiceFinish,
    VoiceCancel,
    VoiceSpeak,
    VoiceOptions,
    VoicePreview,
    VoiceDeleteProfile,
    MigrateCredentials,
    SetDelegation,
    SetLocalTools,
    ListTools,
    CallTool,
    SetWorkspace,
    ResolveApproval,
    SetWebResearch,
    SetMcp,
    SetStandardMcp,
    SetArtifacts,
    ModelCatalog,
    SetModelMode,
    ListMcp,
    CallMcp,
    MemorySearch,
    MemoryDelete,
    Rollback,
}
fn valid_id(id: Option<String>) -> Result<String, String> {
    let value = id.ok_or("Missing identifier.")?;
    if value.len() != 36 || !value.chars().all(|c| c.is_ascii_hexdigit() || c == '-') {
        return Err("Invalid identifier.".into());
    }
    Ok(value)
}
fn endpoint(operation: Operation, id: Option<String>) -> Result<(reqwest::Method, String), String> {
    use reqwest::Method;
    Ok(match operation {
        Operation::Health => (Method::GET, "/health/ready".into()),
        Operation::Sessions => (Method::GET, "/v1/sessions".into()),
        Operation::CreateSession => (Method::POST, "/v1/sessions".into()),
        Operation::CreateTask => (Method::POST, "/v1/tasks".into()),
        Operation::SessionTasks => (Method::GET, format!("/v1/sessions/{}/tasks", valid_id(id)?)),
        Operation::Task => (Method::GET, format!("/v1/tasks/{}", valid_id(id)?)),
        Operation::TaskTrace => (Method::GET, format!("/v1/tasks/{}/trace", valid_id(id)?)),
        Operation::TaskUsage => (Method::GET, format!("/v1/tasks/{}/usage", valid_id(id)?)),
        Operation::ListCapabilities => (Method::GET, "/v1/capabilities".into()),
        Operation::CreateWorkflow => (Method::POST, "/v1/workflows".into()),
        Operation::GetWorkflow => (Method::GET, format!("/v1/workflows/{}", valid_id(id)?)),
        Operation::StartObservation => (Method::POST, "/v1/observations".into()),
        Operation::ShutdownBackground => (Method::POST, "/v1/runtime/shutdown".into()),
        Operation::ObservationResult => {
            (Method::GET, format!("/v1/observations/{}", valid_id(id)?))
        }
        Operation::Cancel => (Method::POST, format!("/v1/tasks/{}/cancel", valid_id(id)?)),
        Operation::Stop => (Method::POST, "/v1/stop".into()),
        Operation::VoiceStatus => (Method::GET, "/v1/voice/status".into()),
        Operation::VoiceDevices => (Method::GET, "/v1/voice/devices".into()),
        Operation::VoicePrepare => (Method::POST, "/v1/voice/prepare".into()),
        Operation::VoiceRecord => (Method::POST, "/v1/voice/record".into()),
        Operation::VoiceFinish => (Method::POST, "/v1/voice/finish".into()),
        Operation::VoiceCancel => (Method::POST, "/v1/voice/cancel".into()),
        Operation::VoiceSpeak => (Method::POST, format!("/v1/voice/speak/{}", valid_id(id)?)),
        Operation::VoiceOptions => (Method::POST, "/v1/voice/options".into()),
        Operation::VoicePreview => (Method::POST, "/v1/voice/preview".into()),
        Operation::VoiceDeleteProfile => (Method::POST, "/v1/voice/profile/delete".into()),
        Operation::MigrateCredentials => (Method::POST, "/v1/settings/migrate-credentials".into()),
        Operation::SetDelegation => (Method::POST, "/v1/settings/delegation".into()),
        Operation::SetLocalTools => (Method::POST, "/v1/settings/local-tools".into()),
        Operation::ListTools => (Method::GET, "/v1/tools".into()),
        Operation::CallTool => (Method::POST, "/v1/tools/call".into()),
        Operation::SetWorkspace => (Method::POST, "/v1/settings/workspace".into()),
        Operation::ResolveApproval => (
            Method::POST,
            format!("/v1/tasks/{}/approval", valid_id(id)?),
        ),
        Operation::SetWebResearch => (Method::POST, "/v1/settings/web-research".into()),
        Operation::SetMcp => (Method::POST, "/v1/settings/mcp".into()),
        Operation::SetStandardMcp => (Method::POST, "/v1/settings/standard-mcp".into()),
        Operation::SetArtifacts => (Method::POST, "/v1/settings/artifacts".into()),
        Operation::ModelCatalog => (Method::GET, "/v1/models".into()),
        Operation::SetModelMode => (Method::POST, "/v1/settings/model-mode".into()),
        Operation::ListMcp => (Method::GET, "/v1/mcp/tools".into()),
        Operation::CallMcp => (Method::POST, "/v1/mcp/call".into()),
        Operation::MemorySearch => (Method::POST, "/v1/memory/search".into()),
        Operation::MemoryDelete => (Method::POST, "/v1/memory/delete".into()),
        Operation::Rollback => (
            Method::POST,
            format!("/v1/tasks/{}/rollback", valid_id(id)?),
        ),
    })
}
fn local_client(seconds: u64) -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(std::time::Duration::from_secs(seconds))
        .build()
        .map_err(|_| "Local HTTP client unavailable.".into())
}

#[tauri::command]
async fn configure_provider(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, Supervisor>,
    provider: String,
) -> Result<bool, String> {
    credentials::provider_label(&provider)?;
    let info = ensure_broker(&state)?;
    #[cfg(windows)]
    let parent = window.hwnd().map_err(|_| "Native window unavailable.")?.0 as isize;
    #[cfg(not(windows))]
    let parent = {
        let _ = window;
        0
    };
    let chosen = provider.clone();
    let secret = tauri::async_runtime::spawn_blocking(move || credentials::prompt(&chosen, parent))
        .await
        .map_err(|_| "Native entry worker failed.".to_string())??;
    let Some(mut secret) = secret else {
        return Ok(false);
    };
    #[derive(Serialize)]
    struct NativeKey<'a> {
        provider: &'a str,
        api_key: &'a str,
    }
    let request = local_client(8)?
        .post(format!("{}/v1/settings/provider-key", info.url))
        .bearer_auth(info.token)
        .json(&NativeKey {
            provider: &provider,
            api_key: std::str::from_utf8(&secret).map_err(|_| "Invalid credential.")?,
        });
    credentials::erase(&mut secret);
    let response = request
        .send()
        .await
        .map_err(|_| "Local credential save failed.".to_string())?;
    if !response.status().is_success() {
        return Err("Credential store rejected the key.".into());
    }
    Ok(true)
}

#[tauri::command]
async fn broker_request(
    state: tauri::State<'_, Supervisor>,
    operation: Operation,
    id: Option<String>,
    payload: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let (method, path) = endpoint(operation, id)?;
    let info = ensure_broker(&state)?;
    let seconds = match operation {
        Operation::ObservationResult => 85,
        Operation::ResolveApproval | Operation::CallMcp => 30,
        _ => 8,
    };
    let mut request = local_client(seconds)?
        .request(method, format!("{}{}", info.url, path))
        .bearer_auth(info.token);
    if let Some(body) = payload {
        request = request.json(&body);
    }
    let response = request
        .send()
        .await
        .map_err(|error| format!("Local broker request failed: {}", error.without_url()))?;
    let success = response.status().is_success();
    let value: serde_json::Value = response
        .json()
        .await
        .map_err(|_| "Invalid local broker response.".to_string())?;
    if !success {
        return Err(value["error"]["message"]
            .as_str()
            .unwrap_or("Local request rejected.")
            .into());
    }
    Ok(value)
}

#[tauri::command]
async fn stream_task(
    state: tauri::State<'_, Supervisor>,
    task_id: String,
    after: u64,
    channel: tauri::ipc::Channel<serde_json::Value>,
) -> Result<(), String> {
    let id = valid_id(Some(task_id))?;
    let info = ensure_broker(&state)?;
    let response = local_client(100)?
        .get(format!(
            "{}/v1/tasks/{}/events?after={}",
            info.url, id, after
        ))
        .bearer_auth(info.token)
        .send()
        .await
        .map_err(|_| "Event stream disconnected.".to_string())?;
    if !response.status().is_success() {
        return Err("Event stream rejected.".into());
    }
    let mut chunks = response.bytes_stream();
    let mut buffer = Vec::new();
    while let Some(chunk) = chunks.next().await {
        buffer.extend_from_slice(&chunk.map_err(|_| "Event stream interrupted.".to_string())?);
        if buffer.len() > 256000 {
            return Err("Event frame limit exceeded.".into());
        }
        while let Some(end) = buffer.windows(2).position(|w| w == b"\n\n") {
            let frame = String::from_utf8(buffer.drain(..end + 2).collect())
                .map_err(|_| "Invalid event encoding.".to_string())?;
            for line in frame.lines() {
                if let Some(data) = line.strip_prefix("data: ") {
                    let value = serde_json::from_str(data)
                        .map_err(|_| "Invalid event data.".to_string())?;
                    channel
                        .send(value)
                        .map_err(|_| "Event subscriber closed.".to_string())?;
                }
            }
        }
    }
    Ok(())
}

fn stop_all(app: &tauri::AppHandle) {
    let state = app.state::<Supervisor>();
    if let Ok(guard) = state.broker.lock() {
        if let Some(broker) = guard.as_ref().and_then(|broker| broker.info().ok()) {
            let address = broker.url.trim_start_matches("http://");
            if let Ok(address) = address.parse::<std::net::SocketAddr>() {
                if let Ok(mut stream) = std::net::TcpStream::connect_timeout(
                    &address,
                    std::time::Duration::from_millis(200),
                ) {
                    let _ = stream.set_write_timeout(Some(std::time::Duration::from_millis(200)));
                    let _=write!(stream,"POST /v1/stop HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer {}\r\nContent-Length: 2\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{{}}",broker.token);
                }
            }
        }
    }
    let _ = app.emit("global-stop", ());
}

fn snap(window: &tauri::WebviewWindow) -> Result<(), String> {
    let monitor = window
        .current_monitor()
        .map_err(|_| "Monitor unavailable.")?
        .ok_or("No monitor.")?;
    let position = window
        .outer_position()
        .map_err(|_| "Position unavailable.")?;
    let size = window.outer_size().map_err(|_| "Size unavailable.")?;
    let work = monitor.work_area();
    let origin = &work.position;
    let screen = &work.size;
    let right = origin.x + screen.width as i32 - size.width as i32 - 8;
    let x = if position.x - origin.x < right - position.x {
        origin.x + 8
    } else {
        right
    };
    let y = position.y.clamp(
        origin.y + 8,
        (origin.y + screen.height as i32 - size.height as i32 - 8).max(origin.y + 8),
    );
    window
        .set_position(PhysicalPosition::new(x, y))
        .map_err(|_| "Could not snap window.".to_string())?;
    save_placement(window);
    Ok(())
}

fn may_snap_after_drag(button_down: bool, position_stable: bool) -> bool {
    !button_down && position_stable
}

fn primary_mouse_down() -> bool {
    #[cfg(windows)]
    unsafe {
        use windows_sys::Win32::UI::{
            Input::KeyboardAndMouse::{GetAsyncKeyState, VK_LBUTTON, VK_RBUTTON},
            WindowsAndMessaging::{GetSystemMetrics, SM_SWAPBUTTON},
        };
        let key = if GetSystemMetrics(SM_SWAPBUTTON) != 0 {
            VK_RBUTTON
        } else {
            VK_LBUTTON
        };
        GetAsyncKeyState(key as i32) < 0
    }
    #[cfg(not(windows))]
    {
        false
    }
}

fn command_size(work_width: f64, work_height: f64) -> (f64, f64) {
    (
        (work_width - 48.).clamp(640., 1600.).min(work_width),
        (work_height - 40.).clamp(480., 980.).min(work_height),
    )
}

fn leave_workspace(window: &tauri::WebviewWindow) -> tauri::Result<()> {
    if window.is_maximized()? {
        window.unmaximize()?;
    }
    window.set_min_size(None::<tauri::Size>)?;
    window.set_resizable(false)?;
    window.set_skip_taskbar(true)
}

#[tauri::command]
fn window_action(window: tauri::WebviewWindow, action: String) -> Result<(), String> {
    let error = |_| "Window action unavailable.".to_string();
    match action.as_str() {
        "drag" => {
            window.start_dragging().map_err(error)?;
            let moved = window.clone();
            std::thread::spawn(move || {
                let mut previous = None;
                for _ in 0..300 {
                    std::thread::sleep(std::time::Duration::from_millis(100));
                    let current = moved.outer_position().ok();
                    if may_snap_after_drag(
                        primary_mouse_down(),
                        current.is_some() && current == previous,
                    ) {
                        let _ = snap(&moved);
                        break;
                    }
                    previous = current;
                }
            });
            Ok(())
        }
        "snap" => snap(&window),
        "nudge_up" | "nudge_down" => {
            let monitor = window
                .current_monitor()
                .map_err(error)?
                .ok_or("Monitor unavailable.")?;
            let position = window.outer_position().map_err(error)?;
            let size = window.outer_size().map_err(error)?;
            let work = monitor.work_area();
            let step = (24. * window.scale_factor().map_err(error)?) as i32;
            let delta = if action == "nudge_up" { -step } else { step };
            let y = (position.y + delta).clamp(
                work.position.y + 8,
                (work.position.y + work.size.height as i32 - size.height as i32 - 8)
                    .max(work.position.y + 8),
            );
            window
                .set_position(PhysicalPosition::new(position.x, y))
                .map_err(error)?;
            save_placement(&window);
            Ok(())
        }
        "expand" | "collapse" => {
            leave_workspace(&window).map_err(error)?;
            let height = window
                .current_monitor()
                .map_err(error)?
                .map(|m| (m.work_area().size.height as f64 / m.scale_factor() - 16.).min(760.))
                .unwrap_or(730.);
            window
                .set_size(if action == "expand" {
                    LogicalSize::new(440., height)
                } else {
                    LogicalSize::new(COMPACT.0, COMPACT.1)
                })
                .map_err(error)?;
            if action == "collapse" {
                restore_placement(&window).map_err(error)
            } else {
                snap(&window)
            }
        }
        "command" => {
            let monitor = window
                .current_monitor()
                .map_err(error)?
                .ok_or("Monitor unavailable.")?;
            let scale = monitor.scale_factor();
            let work = monitor.work_area();
            let (width, height) = command_size(
                work.size.width as f64 / scale,
                work.size.height as f64 / scale,
            );
            window.set_always_on_top(false).map_err(error)?;
            window.set_skip_taskbar(false).map_err(error)?;
            window.set_resizable(true).map_err(error)?;
            window
                .set_min_size(Some(LogicalSize::new(width.min(900.), height.min(600.))))
                .map_err(error)?;
            window
                .set_size(LogicalSize::new(width, height))
                .map_err(error)?;
            let x = work.position.x + ((work.size.width as f64 - width * scale) / 2.) as i32;
            let y = work.position.y + ((work.size.height as f64 - height * scale) / 2.) as i32;
            window
                .set_position(PhysicalPosition::new(x, y))
                .map_err(error)?;
            window.set_focus().map_err(error)
        }
        "overlay" => {
            leave_workspace(&window).map_err(error)?;
            let monitor = window
                .current_monitor()
                .map_err(error)?
                .ok_or("Monitor unavailable.")?;
            let scale = monitor.scale_factor();
            let work = monitor.work_area();
            window
                .set_size(LogicalSize::new(340., 136.))
                .map_err(error)?;
            let x = work.position.x + work.size.width as i32 - (352. * scale) as i32;
            window
                .set_position(PhysicalPosition::new(
                    x,
                    work.position.y + (12. * scale) as i32,
                ))
                .map_err(error)?;
            window.set_always_on_top(true).map_err(error)
        }
        "minimize" => window.minimize().map_err(error),
        "maximize" => {
            if window.is_maximized().map_err(error)? {
                window.unmaximize().map_err(error)
            } else {
                window.maximize().map_err(error)
            }
        }
        "drag_free" => window.start_dragging().map_err(error),
        "context_menu" => {
            let app = window.app_handle();
            let chat = MenuItem::with_id(app, "ctx-chat", "Open quick chat", true, None::<&str>)
                .map_err(error)?;
            let command = MenuItem::with_id(
                app,
                "ctx-command",
                "Open command center",
                true,
                None::<&str>,
            )
            .map_err(error)?;
            let stop = MenuItem::with_id(app, "ctx-stop", "Stop active task", true, None::<&str>)
                .map_err(error)?;
            let quit = MenuItem::with_id(app, "ctx-quit", "Quit Immortility", true, None::<&str>)
                .map_err(error)?;
            let menu = Menu::with_items(app, &[&chat, &command, &stop, &quit]).map_err(error)?;
            window.popup_menu(&menu).map_err(error)
        }
        "pin" => window.set_always_on_top(true).map_err(error),
        "unpin" => window.set_always_on_top(false).map_err(error),
        "hide" => window.hide().map_err(error),
        "quit" => {
            window.app_handle().exit(0);
            Ok(())
        }
        _ => Err("Unknown window action.".into()),
    }
}

fn report_extension(artifact_id: &str) -> Result<&'static str, String> {
    match artifact_id {
        "report.pdf" => Ok(".pdf"),
        "report.md" => Ok(".md"),
        _ => Err("Unsupported published report type.".into()),
    }
}

#[cfg(windows)]
fn verify_report_copy(body: &serde_json::Value, bytes: &[u8]) -> Result<(), String> {
    use sha2::{Digest, Sha256};
    if bytes.is_empty()
        || bytes.len() > 8_000_000
        || body["size"].as_u64() != Some(bytes.len() as u64)
        || body["sha256"].as_str() != Some(format!("{:x}", Sha256::digest(bytes)).as_str())
    {
        return Err("Report copy changed after verification.".into());
    }
    Ok(())
}

#[tauri::command]
async fn open_artifact(
    state: tauri::State<'_, Supervisor>,
    task_id: String,
    artifact_id: String,
) -> Result<(), String> {
    let task_id = valid_id(Some(task_id))?;
    let extension = report_extension(&artifact_id)?;
    let connection = ensure_broker(&state)?;
    let response = local_client(5)?
        .post(format!(
            "{}/v1/tasks/{}/artifacts/{}/copy",
            connection.url, task_id, artifact_id
        ))
        .bearer_auth(connection.token)
        .json(&serde_json::json!({}))
        .send()
        .await
        .map_err(|_| "Report copy request failed.")?;
    if !response.status().is_success() {
        return Err("Report verification or copy was refused.".into());
    }
    let body: serde_json::Value = response
        .json()
        .await
        .map_err(|_| "Invalid report copy response.")?;
    let copy_id = valid_id(Some(
        body["copy_id"]
            .as_str()
            .ok_or("Missing report copy identity.")?
            .to_string(),
    ))?;
    if body["open_allowed"] != true || body["extension"] != extension {
        return Err("Report opening was not authorized.".into());
    }
    let expected_folder = state
        .data_root
        .canonicalize()
        .map_err(|_| "Runtime scope unavailable.")?
        .join("artifacts")
        .join(task_id)
        .join("copies");
    let folder = expected_folder
        .canonicalize()
        .map_err(|_| "Report folder is unavailable.")?;
    if folder != expected_folder {
        return Err("Report copy folder changed identity.".into());
    }
    let file = folder
        .join(format!("{}{}", copy_id, extension))
        .canonicalize()
        .map_err(|_| "Report copy is unavailable.")?;
    if file.parent() != Some(folder.as_path())
        || !file.is_file()
        || std::fs::metadata(&file)
            .map_err(|_| "Report metadata unavailable.")?
            .len()
            > 8_000_000
    {
        return Err("Report copy escaped its scope.".into());
    }
    #[cfg(windows)]
    {
        use std::io::Read;
        use std::os::windows::ffi::OsStrExt;
        use std::os::windows::fs::OpenOptionsExt;
        use windows_sys::Win32::UI::{Shell::ShellExecuteW, WindowsAndMessaging::SW_SHOWNORMAL};
        // Keep the exact verified file closed to writes/renames until Windows
        // accepts the explicit user opening action. Reads remain permitted.
        let handle = std::fs::OpenOptions::new()
            .read(true)
            .share_mode(1)
            .open(&file)
            .map_err(|_| "Report readback failed.")?;
        let mut bytes = Vec::new();
        (&handle)
            .take(8_000_001)
            .read_to_end(&mut bytes)
            .map_err(|_| "Report readback failed.")?;
        verify_report_copy(&body, &bytes)?;
        let filename: Vec<u16> = file.as_os_str().encode_wide().chain(Some(0)).collect();
        let verb: Vec<u16> = "open".encode_utf16().chain(Some(0)).collect();
        let result = unsafe {
            ShellExecuteW(
                std::ptr::null_mut(),
                verb.as_ptr(),
                filename.as_ptr(),
                std::ptr::null(),
                std::ptr::null(),
                SW_SHOWNORMAL,
            )
        };
        if result as isize <= 32 {
            return Err(
                "Windows could not open the report. Configure a PDF or Markdown viewer.".into(),
            );
        }
        Ok(())
    }
    #[cfg(not(windows))]
    {
        Err("Native report opening is Windows-only.".into())
    }
}

fn main() {
    // Developer preview: no arbitrary executable paths or commands accepted from the webview.
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("repository root")
        .to_path_buf();
    let (data_root, isolated_background) =
        runtime_directory(&root).expect("Invalid runtime data scope");
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
            let _ = app.emit("toggle-chat", ());
        }))
        .manage(Supervisor {
            broker: Mutex::new(if isolated_background {
                Some(ManagedBroker::Detached)
            } else {
                None
            }),
            root,
            data_root,
            isolated_background,
        })
        .on_menu_event(|app, event| match event.id.as_ref() {
            "ctx-chat" => {
                let _ = app.emit("companion-mode", "chat");
            }
            "ctx-command" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                }
                let _ = app.emit("companion-mode", "command");
            }
            "ctx-stop" => stop_all(app),
            "ctx-quit" => app.exit(0),
            _ => {}
        })
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, shortcut, event| {
                    if event.state() != ShortcutState::Pressed {
                        return;
                    }
                    if shortcut.to_string().to_lowercase().contains("escape") {
                        stop_all(app);
                    } else {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                        let _ = app.emit("toggle-chat", ());
                    }
                })
                .build(),
        )
        .setup(|app| {
            let window = app
                .get_webview_window("main")
                .ok_or("Main window missing")?;
            restore_placement(&window)?;
            let open = MenuItem::with_id(app, "open", "Open companion", true, None::<&str>)?;
            let command =
                MenuItem::with_id(app, "command", "Open command center", true, None::<&str>)?;
            let stop = MenuItem::with_id(app, "stop", "Stop all tasks", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit Immortility", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &command, &stop, &quit])?;
            let icon = app
                .default_window_icon()
                .ok_or("Window icon missing")?
                .clone();
            TrayIconBuilder::new()
                .icon(icon)
                .tooltip("Immortility")
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                        let _ = app.emit("toggle-chat", ());
                    }
                    "command" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                        }
                        let _ = app.emit("companion-mode", "command");
                    }
                    "stop" => stop_all(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;
            // Conflicts are visible; startup continues with tray controls available.
            for shortcut in ["Ctrl+Shift+Space", "Ctrl+Shift+Escape"] {
                if app.global_shortcut().register(shortcut).is_err() {
                    let _ = app.emit("shortcut-unavailable", shortcut);
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            connection,
            window_action,
            broker_request,
            stream_task,
            configure_provider,
            attach_background,
            detach_background,
            open_artifact
        ])
        .build(tauri::generate_context!())
        .expect("Immortility desktop initialization failed")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Ok(mut guard) = app.state::<Supervisor>().broker.lock() {
                    *guard = None;
                }
            }
        });
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn model_modes_use_fixed_local_routes() {
        let catalog = endpoint(Operation::ModelCatalog, None).unwrap();
        assert_eq!(catalog.0, reqwest::Method::GET);
        assert_eq!(catalog.1, "/v1/models");
        let selection = endpoint(Operation::SetModelMode, None).unwrap();
        assert_eq!(selection.0, reqwest::Method::POST);
        assert_eq!(selection.1, "/v1/settings/model-mode");
        for name in [
            "provider_http",
            "set_provider_price",
            "provider_key",
            "local_model_download",
        ] {
            assert!(serde_json::from_value::<Operation>(serde_json::json!(name)).is_err());
        }
    }
    #[test]
    fn report_opening_rejects_unpublished_or_executable_names() {
        assert_eq!(report_extension("report.md").unwrap(), ".md");
        assert_eq!(report_extension("report.pdf").unwrap(), ".pdf");
        for name in [
            "report.docx",
            "report.pdf.exe",
            "../report.pdf",
            "C:\\report.md",
            "receipt.json",
            "report.PDF",
        ] {
            assert!(report_extension(name).is_err());
        }
    }
    #[cfg(windows)]
    #[test]
    fn report_opening_checks_hash_and_size_before_launch() {
        use sha2::{Digest, Sha256};
        let bytes = b"verified fixture";
        let mut body = serde_json::json!({"size": bytes.len(), "sha256": format!("{:x}", Sha256::digest(bytes))});
        assert!(verify_report_copy(&body, bytes).is_ok());
        assert!(verify_report_copy(&body, b"tampered fixture").is_err());
        body["size"] = serde_json::json!(0);
        assert!(verify_report_copy(&body, bytes).is_err());
    }
    #[test]
    fn pausing_a_held_drag_never_snaps_the_window() {
        assert!(!may_snap_after_drag(true, true));
        assert!(!may_snap_after_drag(true, false));
        assert!(!may_snap_after_drag(false, false));
        assert!(may_snap_after_drag(false, true));
    }
    #[test]
    fn command_center_fits_inside_the_work_area() {
        assert_eq!(command_size(2560., 1400.), (1600., 980.));
        assert_eq!(command_size(1280., 680.), (1232., 640.));
        let (width, height) = command_size(600., 400.);
        assert!(width <= 600. && height <= 400.);
    }
    #[test]
    fn native_bridge_denies_non_chat_operations() {
        for operation in [
            "inference",
            "terminal",
            "file_write",
            "capture",
            "http",
            "save_provider_key",
            "approve_observation",
            "select_window",
            "click",
        ] {
            assert!(serde_json::from_value::<Operation>(serde_json::json!(operation)).is_err());
        }
    }
    #[test]
    fn resource_ids_cannot_escape_the_local_task_routes() {
        for id in [
            "../../inference",
            "http://evil.test",
            "\\\\server\\share",
            "",
        ] {
            assert!(endpoint(Operation::Cancel, Some(id.into())).is_err());
        }
        let result = endpoint(
            Operation::Cancel,
            Some("f0153ff9-a672-41b1-b490-0cea79542195".into()),
        )
        .unwrap();
        assert_eq!(
            result.1,
            "/v1/tasks/f0153ff9-a672-41b1-b490-0cea79542195/cancel"
        );
    }
}
