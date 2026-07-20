/*
 * Public runtime configuration for the static OSS/CDN build.
 *
 * `scripts/write_runtime_config.py` replaces this file during a release. It
 * deliberately starts with an empty API origin: a production static bundle must
 * never silently call a visitor's localhost when deployment configuration is
 * missing.
 */
window.__VOLTA_RUNTIME_CONFIG__ = Object.freeze({
  apiBaseUrl: "",
  appOrigin: "",
  csrfCookieName: "volta_csrf",
  csrfHeaderName: "X-CSRF-Token",
  release: "unconfigured"
});
