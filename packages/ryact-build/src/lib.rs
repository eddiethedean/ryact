//! PyO3 bridge to the Rolldown bundler (Rust).

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use rolldown::{
  BundlerBuilder, BundlerOptions, InputItem, LogLevel, OutputFormat, Platform, RawMinifyOptions,
  SourceMapType,
};
use rolldown_utils::indexmap::FxIndexMap;

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
  m.add_function(wrap_pyfunction!(bundle_roll, m)?)?;
  Ok(())
}

#[pyfunction]
#[pyo3(signature = (entry, out_dir, cwd, format, minify, verbose, defines=None))]
fn bundle_roll(
  py: Python<'_>,
  entry: String,
  out_dir: String,
  cwd: String,
  format: String,
  minify: bool,
  verbose: bool,
  defines: Option<HashMap<String, String>>,
) -> PyResult<()> {
  let cwd_path = PathBuf::from(&cwd);
  let entry_path = PathBuf::from(&entry);
  let import = entry_import_path(&entry_path, &cwd_path).map_err(PyValueError::new_err)?;
  let entry_name = entry_path
    .file_stem()
    .and_then(|s| s.to_str())
    .map(str::to_string);

  let output_format = parse_format(&format)?;
  let define_map = defines.map(|d| d.into_iter().collect::<FxIndexMap<String, String>>());

  let opts = BundlerOptions {
    input: Some(vec![InputItem { name: entry_name, import }]),
    cwd: Some(cwd_path.clone()),
    dir: Some(out_dir),
    format: Some(output_format),
    platform: Some(Platform::Browser),
    sourcemap: Some(SourceMapType::File),
    minify: Some(RawMinifyOptions::Bool(minify)),
    log_level: Some(if verbose {
      LogLevel::Debug
    } else {
      LogLevel::Warn
    }),
    define: define_map,
    ..BundlerOptions::default()
  };

  if verbose {
    eprintln!("ryact-build (rolldown): options = {opts:#?}");
  }

  py.allow_threads(|| {
    tokio::runtime::Builder::new_multi_thread()
      .enable_all()
      .build()
      .map_err(|e| PyRuntimeError::new_err(format!("tokio runtime: {e}")))?
      .block_on(async move {
        let mut bundler = BundlerBuilder::default()
          .with_options(opts)
          .build()
          .map_err(|e| PyRuntimeError::new_err(format!("{e:#}")))?;
        bundler
          .write()
          .await
          .map_err(|e| PyRuntimeError::new_err(format!("{e:#}")))?;
        bundler
          .close()
          .await
          .map_err(|e| PyRuntimeError::new_err(format!("{e:#}")))?;
        Ok::<(), PyErr>(())
      })
  })
}

fn parse_format(s: &str) -> PyResult<OutputFormat> {
  match s {
    "esm" => Ok(OutputFormat::Esm),
    "cjs" => Ok(OutputFormat::Cjs),
    "iife" => Ok(OutputFormat::Iife),
    _ => Err(PyValueError::new_err(format!(
      "format must be esm, cjs, or iife; got {s:?}"
    ))),
  }
}

fn entry_import_path(entry: &Path, cwd: &Path) -> Result<String, String> {
  let abs_entry = if entry.is_absolute() {
    entry.to_path_buf()
  } else {
    cwd.join(entry)
  };
  let abs_entry = abs_entry
    .canonicalize()
    .map_err(|e| format!("entry path {}: {e}", abs_entry.display()))?;
  let abs_cwd = cwd
    .canonicalize()
    .map_err(|e| format!("cwd {}: {e}", cwd.display()))?;
  let rel = abs_entry.strip_prefix(&abs_cwd).map_err(|_| {
    format!(
      "entry {} is not under cwd {}",
      abs_entry.display(),
      abs_cwd.display()
    )
  })?;
  Ok(rel.to_string_lossy().replace('\\', "/"))
}
