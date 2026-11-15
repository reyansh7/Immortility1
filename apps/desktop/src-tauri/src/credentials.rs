//! Provider entry stays in a native dialog. Keys never cross a webview IPC response.

pub fn provider_label(provider: &str) -> Result<&'static str, String> {
    match provider {
        "openrouter" => Ok("OpenRouter"),
        "gemini" => Ok("Gemini"),
        "groq" => Ok("Groq"),
        "nvidia" => Ok("NVIDIA"),
        _ => Err("Unknown credential provider.".into()),
    }
}

pub fn erase<T: Default>(buffer: &mut [T]) {
    for value in buffer {
        unsafe { std::ptr::write_volatile(value, T::default()) };
    }
}

#[cfg(windows)]
pub fn prompt(provider: &str, parent: isize) -> Result<Option<Vec<u8>>, String> {
    use windows_sys::Win32::Security::Credentials::*;
    let label = provider_label(provider)?;
    let wide = |value: &str| value.encode_utf16().chain(Some(0)).collect::<Vec<u16>>();
    let target = wide(&format!("Immortility/{label}"));
    let title = wide(&format!("Immortility — {label} API key"));
    let message = wide(
        "Enter the API key in the password field. This stays on this PC. No provider is contacted.",
    );
    let mut username = [0u16; 64];
    for (slot, value) in username.iter_mut().zip("Immortility".encode_utf16()) {
        *slot = value;
    }
    let mut password = [0u16; 512];
    let mut save = 0;
    let info = CREDUI_INFOW {
        cbSize: std::mem::size_of::<CREDUI_INFOW>() as u32,
        hwndParent: parent as _,
        pszMessageText: message.as_ptr(),
        pszCaptionText: title.as_ptr(),
        hbmBanner: std::ptr::null_mut(),
    };
    let result = unsafe {
        CredUIPromptForCredentialsW(
            &info,
            target.as_ptr(),
            std::ptr::null(),
            0,
            username.as_mut_ptr(),
            username.len() as u32,
            password.as_mut_ptr(),
            password.len() as u32,
            &mut save,
            CREDUI_FLAGS_GENERIC_CREDENTIALS
                | CREDUI_FLAGS_DO_NOT_PERSIST
                | CREDUI_FLAGS_ALWAYS_SHOW_UI
                | CREDUI_FLAGS_KEEP_USERNAME,
        )
    };
    let length = password
        .iter()
        .position(|c| *c == 0)
        .unwrap_or(password.len());
    let key = if result == 1223 {
        Ok(None)
    } else if result != 0 {
        Err("Native credential entry failed.".into())
    } else if !(16..=500).contains(&length)
        || password[..length].iter().any(|c| !(33..=126).contains(c))
    {
        Err("The API key must contain 16–500 printable characters.".into())
    } else {
        Ok(Some(password[..length].iter().map(|c| *c as u8).collect()))
    };
    erase(&mut password);
    erase(&mut username);
    key
}

#[cfg(not(windows))]
pub fn prompt(provider: &str, _parent: isize) -> Result<Option<Vec<u8>>, String> {
    provider_label(provider)?;
    Err("Native credential entry requires Windows.".into())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn provider_and_secret_buffers_are_bounded() {
        assert!(provider_label("../../other").is_err());
        assert_eq!(provider_label("openrouter").unwrap(), "OpenRouter");
        let mut dummy = [7u16; 512];
        erase(&mut dummy);
        assert!(dummy.iter().all(|c| *c == 0));
    }
}
