package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func get(t *testing.T, path string) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	newMux().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, path, nil))
	return rec
}

func TestHealthz(t *testing.T) {
	rec := get(t, "/healthz")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("content type = %q", ct)
	}
}

func TestVersionReportsBuildInfo(t *testing.T) {
	version, commit = "1.2.3", "abc123"
	defer func() { version, commit = "dev", "unknown" }()
	var body map[string]string
	if err := json.Unmarshal(get(t, "/version").Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["version"] != "1.2.3" || body["commit"] != "abc123" {
		t.Fatalf("got %v", body)
	}
}

func TestProducts(t *testing.T) {
	var items []product
	if err := json.Unmarshal(get(t, "/api/products").Body.Bytes(), &items); err != nil {
		t.Fatal(err)
	}
	if len(items) != 3 || items[0].Name == "" {
		t.Fatalf("unexpected catalog: %v", items)
	}
}

func TestOnlyGetIsAllowed(t *testing.T) {
	rec := httptest.NewRecorder()
	newMux().ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/api/products", nil))
	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("POST status = %d, want 405", rec.Code)
	}
}

func TestUnknownPath(t *testing.T) {
	if rec := get(t, "/admin"); rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}
