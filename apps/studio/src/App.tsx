import { useCallback, useEffect, useRef, useState } from "react";
import { useModals } from "./hooks/useModals";
import {
  sidecar,
  type CollectionItem,
  type EnvironmentSummary,
  type ExecuteRequestInput,
  type ExecuteResponse,
  type HealthResponse,
  type ParsedCurl,
  type StoredCollection,
} from "./lib/sidecar";
import {
  isDirty,
  newRequestTab,
  parseHeadersText,
  signatureOf,
  tabFromSaved,
  type RequestTab,
} from "./state/types";
import { Sidebar } from "./components/Sidebar";
import { RequestTabBar } from "./components/RequestTabBar";
import { UrlBar } from "./components/UrlBar";
import { RequestPanel } from "./components/RequestPanel";
import { ResponsePanel, type ConsoleEntry } from "./components/ResponsePanel";
import { StatusBar } from "./components/StatusBar";
import { SavePopover } from "./components/SavePopover";
import { EnvManagerModal } from "./components/EnvManagerModal";
import { CodegenModal } from "./components/CodegenModal";
import { CurlImportModal } from "./components/CurlImportModal";
import { TestGenModal } from "./components/TestGenModal";
import { DiffModal } from "./components/DiffModal";
import { GraphQLModal } from "./components/GraphQLModal";
import { GrpcModal } from "./components/GrpcModal";
import { ImportModal } from "./components/ImportModal";
import { KafkaModal } from "./components/KafkaModal";
import { LoadTestModal } from "./components/LoadTestModal";
import { MockServerModal } from "./components/MockServerModal";
import { ProxyRecorderModal } from "./components/ProxyRecorderModal";
import { ServiceMapModal } from "./components/ServiceMapModal";
import { SwaggerBrowserModal } from "./components/SwaggerBrowserModal";
import { OpenAPIImportModal } from "./components/OpenAPIImportModal";
import { SettingsModal } from "./components/SettingsModal";
import { WebSocketModal } from "./components/WebSocketModal";
import { HistoryPanel, type HistoryEntry } from "./components/HistoryPanel";
import { SoapModal } from "./components/SoapModal";
import { CommandPalette, useDefaultActions } from "./components/CommandPalette";
import { GlobalSearch } from "./components/GlobalSearch";
import { ContextMenu, buildSidebarActions, type ContextMenuAction } from "./components/ContextMenu";
import { JwtInspectorModal } from "./components/JwtInspectorModal";
import { BatchRunnerModal } from "./components/BatchRunnerModal";
import { MonitorsModal } from "./components/MonitorsModal";
import { SecurityScannerModal } from "./components/SecurityScannerModal";
import { CollectionVarsModal } from "./components/CollectionVarsModal";
import { SecretsVaultModal } from "./components/SecretsVaultModal";
import { WebhooksModal } from "./components/WebhooksModal";
import { MultiEnvModal } from "./components/MultiEnvModal";
import { FlowEditorModal } from "./components/FlowEditorModal";
import { PerformanceDashboardModal } from "./components/PerformanceDashboardModal";
import { AgentExplorerModal } from "./components/AgentExplorerModal";
import { OWASPScannerModal } from "./components/OWASPScannerModal";
import { RequestDiffModal } from "./components/RequestDiffModal";
import { BodyDiffModal } from "./components/BodyDiffModal";
import { CollectionStatsModal } from "./components/CollectionStatsModal";
import { ComparisonTableModal } from "./components/ComparisonTableModal";
import { SSEModal } from "./components/SSEModal";
import { ChangelogModal } from "./components/ChangelogModal";
import { PipelineModal } from "./components/PipelineModal";
import { DocGeneratorModal } from "./components/DocGeneratorModal";
import { DependencyGraphModal } from "./components/DependencyGraphModal";
import { NetworkConsole, type NetworkEntry, type NetworkEntryType } from "./components/NetworkConsole";
import { ActivityBar, type AppMode } from "./components/ActivityBar";
import { ToastContainer, type Toast } from "./components/Toast";
import { EventToastContainer } from "./components/EventToast";
import { ReleaseCenterModal } from "./components/ReleaseCenterModal";
import { SpinPanel } from "./components/SpinPanel";

const APP_VERSION = "0.0.1";
const ACTIVE_ENV_KEY = "theridion.activeEnvironmentId";
const DRAFT_TABS_KEY = "theridion.draft-tabs";

type SidecarStatus =
  | { state: "checking" }
  | { state: "ok"; info: HealthResponse }
  | { state: "down"; error: string };

export default function App() {
  const [sidecarStatus, setSidecarStatus] = useState<SidecarStatus>({ state: "checking" });

  const [collections, setCollections] = useState<StoredCollection[]>([]);
  const [collectionsLoading, setCollectionsLoading] = useState(false);

  const [tabs, setTabs] = useState<RequestTab[]>(() => {
    if (typeof window !== "undefined") {
      const saved = window.localStorage.getItem(DRAFT_TABS_KEY);
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as RequestTab[];
          if (Array.isArray(parsed) && parsed.length > 0) {
            // Restore tabs but clear transient state.
            return parsed.map((t) => ({
              ...newRequestTab(),
              ...t,
              busy: false,
              response: null,
              error: null,
              assertionResults: null,
              pinned: t.pinned ?? false,
            }));
          }
        } catch { /* ignore corrupt data */ }
      }
    }
    return [newRequestTab()];
  });
  const [activeId, setActiveId] = useState<string>(tabs[0].id);
  const [savePopoverOpen, setSavePopoverOpen] = useState(false);

  const [environments, setEnvironments] = useState<EnvironmentSummary[]>([]);
  const [activeEnvId, setActiveEnvId] = useState<string | null>(() =>
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACTIVE_ENV_KEY)
      : null,
  );
  const modals = useModals();
  const [previousResponse, setPreviousResponse] = useState<import("./lib/sidecar").ExecuteResponse | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);
  const [globalSearchOpen, setGlobalSearchOpen] = useState(false);
  const [requestCount, setRequestCount] = useState(0);
  const [lastStatus, setLastStatus] = useState<number | null>(null);
  const [consoleEntries, setConsoleEntries] = useState<ConsoleEntry[]>([]);
  const [ctxMenu, setCtxMenu] = useState<{ open: boolean; x: number; y: number; actions: ContextMenuAction[] }>({ open: false, x: 0, y: 0, actions: [] });
  const [networkOpen, setNetworkOpen] = useState(false);
  const [networkEntries, setNetworkEntries] = useState<NetworkEntry[]>([]);
  const [networkRecording, setNetworkRecording] = useState(true);
  const [networkPreserveLog, setNetworkPreserveLog] = useState(false);
  const [appMode, setAppMode] = useState<AppMode>("requests");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [shortcutOverlayOpen, setShortcutOverlayOpen] = useState(false);
  const [inlineNewName, setInlineNewName] = useState<{type: "collection" | "folder"; parentId?: string; collectionId?: string} | null>(null);
  const [splitRatio, setSplitRatio] = useState(0.5);
  const splitDragging = useState(false);
  const [networkHeight, setNetworkHeight] = useState(300);
  const [statsCollectionId, setStatsCollectionId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const networkDragging = useRef(false);

  function addToast(type: Toast["type"], message: string) {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev.slice(-2), { id, type, message }]);
  }

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // ---- sidecar health polling ---------------------------------------------
  useEffect(() => {
    let alive = true;
    const tick = () =>
      sidecar
        .health()
        .then((info) => alive && setSidecarStatus({ state: "ok", info }))
        .catch((e: unknown) =>
          alive &&
          setSidecarStatus({
            state: "down",
            error: e instanceof Error ? e.message : String(e),
          }),
        );
    tick();
    const id = setInterval(tick, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  // ---- load collections on mount and after sidecar comes back -------------
  const refreshCollections = useCallback(async () => {
    setCollectionsLoading(true);
    try {
      const summaries = await sidecar.listCollections();
      const full = await Promise.all(
        summaries.map((s) => sidecar.getCollection(s.id)),
      );
      // Sort newest-first by name for now; later we'll persist ordering.
      full.sort((a, b) => a.name.localeCompare(b.name));
      setCollections(full);
    } catch (e) {
      console.error("failed to load collections", e);
    } finally {
      setCollectionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (sidecarStatus.state === "ok") {
      void refreshCollections();
      void refreshEnvironments();
    }
  }, [sidecarStatus.state, refreshCollections]);

  const refreshEnvironments = useCallback(async () => {
    try {
      const list = await sidecar.listEnvironments();
      setEnvironments(list);
      // If the persisted active env no longer exists, clear it.
      setActiveEnvId((curr) =>
        curr && list.some((e) => e.id === curr) ? curr : null,
      );
    } catch (e) {
      console.error("failed to load environments", e);
    }
  }, []);

  // Persist the active environment so it survives reloads.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (activeEnvId) {
      window.localStorage.setItem(ACTIVE_ENV_KEY, activeEnvId);
    } else {
      window.localStorage.removeItem(ACTIVE_ENV_KEY);
    }
  }, [activeEnvId]);

  // ---- auto-save draft tabs to localStorage every 5 seconds --------------
  useEffect(() => {
    const timer = setTimeout(() => {
      if (typeof window !== "undefined") {
        // Save tab state (excluding transient response data to keep it small).
        const draft = tabs.map((t) => ({
          id: t.id,
          savedAs: t.savedAs,
          name: t.name,
          method: t.method,
          url: t.url,
          headersRaw: t.headersRaw,
          body: t.body,
          auth: t.auth,
          assertions: t.assertions,
          preRequestScript: t.preRequestScript,
          postResponseScript: t.postResponseScript,
          notes: t.notes,
          cleanSignature: t.cleanSignature,
          lastRunAt: t.lastRunAt,
          pinned: t.pinned,
        }));
        window.localStorage.setItem(DRAFT_TABS_KEY, JSON.stringify(draft));
      }
    }, 5000);
    return () => clearTimeout(timer);
  }, [tabs]);

  // ---- tab helpers --------------------------------------------------------
  const active = tabs.find((t) => t.id === activeId) ?? tabs[0];

  function patchActive(patch: Partial<RequestTab>) {
    setTabs((curr) =>
      curr.map((t) => (t.id === activeId ? { ...t, ...patch } : t)),
    );
  }

  function newTab(seed?: Partial<RequestTab>) {
    const t = newRequestTab(seed);
    setTabs((curr) => [...curr, t]);
    setActiveId(t.id);
  }

  function closeTab(id: string) {
    // Don't close pinned tabs.
    const tab = tabs.find((t) => t.id === id);
    if (tab?.pinned) return;
    setTabs((curr) => {
      const idx = curr.findIndex((t) => t.id === id);
      const next = curr.filter((t) => t.id !== id);
      const ensured = next.length > 0 ? next : [newRequestTab()];
      if (id === activeId) {
        const fallback = ensured[Math.max(0, idx - 1)] ?? ensured[0];
        setActiveId(fallback.id);
      }
      return ensured;
    });
  }

  function duplicateTab(id: string) {
    const src = tabs.find((t) => t.id === id);
    if (!src) return;
    const dup = newRequestTab({
      name: `${src.name} (copy)`,
      method: src.method,
      url: src.url,
      headersRaw: src.headersRaw,
      body: src.body,
      auth: src.auth,
      assertions: src.assertions,
      preRequestScript: src.preRequestScript,
      postResponseScript: src.postResponseScript,
    });
    setTabs((curr) => [...curr, dup]);
    setActiveId(dup.id);
  }

  function pinTab(id: string) {
    setTabs((curr) =>
      curr.map((t) => (t.id === id ? { ...t, pinned: !t.pinned } : t)),
    );
  }

  function closeOtherTabs(id: string) {
    setTabs((curr) => {
      const keep = curr.filter((t) => t.id === id || t.pinned);
      return keep.length > 0 ? keep : [newRequestTab()];
    });
    setActiveId(id);
  }

  function closeTabsToRight(id: string) {
    setTabs((curr) => {
      const idx = curr.findIndex((t) => t.id === id);
      if (idx === -1) return curr;
      const keep = curr.filter((t, i) => i <= idx || t.pinned);
      return keep.length > 0 ? keep : [newRequestTab()];
    });
  }

  function copyTabUrl(id: string) {
    const tab = tabs.find((t) => t.id === id);
    if (tab?.url) void navigator.clipboard.writeText(tab.url);
  }

  function openSaved(collectionId: string, item: CollectionItem) {
    // Sidebar can also fire onOpen for folders (when, e.g., the user
    // clicks the row); ignore those — only requests open in tabs.
    if (item.is_folder) return;
    const existing = tabs.find(
      (t) =>
        t.savedAs?.collectionId === collectionId &&
        t.savedAs?.requestId === item.id,
    );
    if (existing) {
      setActiveId(existing.id);
      return;
    }
    const tab = tabFromSaved(collectionId, item);
    setTabs((curr) => [...curr, tab]);
    setActiveId(tab.id);
  }

  // ---- send + save --------------------------------------------------------
  function cancelRequest() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      patchActive({ busy: false, error: "Request cancelled" });
      addToast("info", "Request cancelled");
    }
  }

  async function send() {
    if (!active.url || active.busy) return;
    const controller = new AbortController();
    abortControllerRef.current = controller;
    patchActive({ busy: true, error: null });
    setConsoleEntries([]);
    try {
      const cc = active.certConfig;
      const input: ExecuteRequestInput = {
        method: active.method,
        url: active.url,
        headers: parseHeadersText(active.headersRaw),
        body: active.body.length > 0 ? active.body : null,
        auth: active.auth.type !== "none" ? active.auth : null,
        environment_id: activeEnvId,
        collection_id: active.savedAs?.collectionId ?? null,
        client_cert: cc.client_cert_path || null,
        client_key: cc.client_key_path || null,
        ca_bundle_path: cc.ca_bundle_path || null,
        verify_ssl: cc.verify_ssl,
      };
      let response: ExecuteResponse;
      let retryAttempts: import("./state/types").RetryAttemptInfo[] | null = null;
      if (active.retryConfig.enabled) {
        const retryResult = await sidecar.executeWithRetry(input, active.retryConfig);
        response = retryResult.final_response;
        retryAttempts = retryResult.attempts;
      } else {
        response = await sidecar.execute(input);
      }
      setPreviousResponse(active.response);
      patchActive({ busy: false, response, error: null, lastRunAt: Date.now(), retryAttempts });
      setRequestCount((c) => c + 1);
      setLastStatus(response.status);
      // Capture network entry for the Network Console.
      if (networkRecording) {
        const entryType: NetworkEntryType = detectNetworkType(active.url, active.body, active.method);
        const networkEntry: NetworkEntry = {
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          method: active.method,
          url: response.resolved_url ?? response.final_url ?? active.url,
          status: response.status,
          statusText: response.status_text ?? "",
          type: entryType,
          requestHeaders: parseHeadersText(active.headersRaw),
          responseHeaders: response.headers,
          requestBody: active.body.length > 0 ? active.body : null,
          responseBody: response.body,
          cookies: response.cookies ?? {},
          size: response.body_size_bytes,
          elapsed_ms: response.elapsed_ms,
          timing: response.timing ? {
            dns_ms: response.timing.dns_ms,
            connect_ms: response.timing.connect_ms,
            tls_ms: response.timing.tls_ms,
            ttfb_ms: response.timing.transfer_ms, // map transfer to ttfb as approximation
            download_ms: 0,
          } : undefined,
        };
        setNetworkEntries((prev) => [...prev, networkEntry]);
      }
      // Evaluate assertions if any exist.
      if (active.assertions.length > 0) {
        try {
          const evalResult = await sidecar.evaluateAssertions({
            assertions: active.assertions,
            response: {
              status: response.status,
              headers: response.headers,
              body: response.body,
              elapsed_ms: response.elapsed_ms,
            },
          });
          patchActive({ assertionResults: evalResult.results });
        } catch {
          // Non-critical — don't fail the request over assertion errors.
        }
      } else {
        patchActive({ assertionResults: null });
      }
      // Store last response info for sidebar hover preview.
      if (active.savedAs?.requestId) {
        try {
          const stored = JSON.parse(localStorage.getItem("theridion.last-responses") ?? "{}");
          stored[active.savedAs.requestId] = {
            status: response.status,
            elapsed_ms: response.elapsed_ms,
            preview: response.body.slice(0, 200),
            timestamp: Date.now(),
          };
          localStorage.setItem("theridion.last-responses", JSON.stringify(stored));
        } catch { /* non-critical */ }
      }
      const histEntry: HistoryEntry = {
        id: crypto.randomUUID(),
        method: active.method,
        url: active.url,
        status: response.status,
        elapsed_ms: response.elapsed_ms,
        timestamp: Date.now(),
      };
      setHistory((prev) => [histEntry, ...prev].slice(0, 100));
      // Persist to backend (fire-and-forget)
      sidecar.recordHistory({
        method: active.method,
        url: active.url,
        status: response.status,
        elapsed_ms: response.elapsed_ms,
        timestamp: histEntry.timestamp,
        request_body: active.body ?? undefined,
        response_body: response.body.slice(0, 10000),
        request_headers: parseHeadersText(active.headersRaw) ?? undefined,
        response_headers: response.headers,
      }).catch(() => { /* non-critical */ });
    } catch (e: unknown) {
      patchActive({
        busy: false,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  /**
   * Persist the active tab. If `target` is given, save to that collection
   * with that name (used by the popover). Otherwise: if the tab is already
   * bound to a saved request, save in place; if not, open the popover so
   * the user can pick.
   */
  async function save(target?: { collectionId: string; name: string }) {
    if (!active.url) return;
    if (sidecarStatus.state !== "ok") return;

    if (!target && !active.savedAs) {
      setSavePopoverOpen(true);
      return;
    }

    const collectionId = target?.collectionId ?? active.savedAs!.collectionId;
    const name =
      target?.name ??
      (active.name && active.name !== "Untitled"
        ? active.name
        : deriveNameFromUrl(active.url));

    const updated = await sidecar.saveRequest(collectionId, {
      id: active.savedAs?.requestId,
      name,
      method: active.method,
      url: active.url,
      headers: parseHeadersText(active.headersRaw),
      body: active.body.length > 0 ? active.body : null,
      auth: active.auth.type !== "none" ? active.auth : null,
      assertions: active.assertions,
      pre_request_script: active.preRequestScript || null,
      post_response_script: active.postResponseScript || null,
      notes: active.notes || null,
    });

    // Find the saved record we just wrote. If we passed an id, look it up;
    // otherwise it's the newly-appended last item.
    const matched =
      (active.savedAs?.requestId &&
        updated.items.find((r) => r.id === active.savedAs!.requestId)) ||
      updated.items[updated.items.length - 1];

    patchActive({
      name: matched.name,
      savedAs: { collectionId, requestId: matched.id },
      cleanSignature: signatureOf({
        name: matched.name,
        method: active.method,
        url: active.url,
        headersRaw: active.headersRaw,
        body: active.body,
        auth: active.auth,
        assertions: active.assertions,
        preRequestScript: active.preRequestScript,
        postResponseScript: active.postResponseScript,
        notes: active.notes,
      }),
    });

    await refreshCollections();
    addToast("success", "Request saved");
  }

  // ---- cURL import / export -----------------------------------------------
  function importCurl(parsed: ParsedCurl) {
    newTab({
      method: parsed.method,
      url: parsed.url,
      headersRaw: Object.entries(parsed.headers)
        .map(([k, v]) => `${k}: ${v}`)
        .join("\n"),
      body: parsed.body ?? "",
      auth: parsed.auth ?? { type: "none" },
    });
  }

  async function copyAsCurl() {
    try {
      const result = await sidecar.generateCurl({
        method: active.method,
        url: active.url,
        headers: parseHeadersText(active.headersRaw),
        body: active.body.length > 0 ? active.body : null,
        auth: active.auth.type !== "none" ? active.auth : null,
      });
      await navigator.clipboard.writeText(result.curl);
      addToast("success", "Copied to clipboard");
    } catch (e) {
      console.error("failed to copy as cURL", e);
      addToast("error", "Failed to copy as cURL");
    }
  }

  // ---- HAR export -----------------------------------------------------------
  async function exportHar() {
    if (networkEntries.length === 0) return;
    try {
      const entries = networkEntries.map((e) => ({
        method: e.method,
        url: e.url,
        status: e.status,
        request_headers: e.requestHeaders,
        response_headers: e.responseHeaders,
        request_body: e.requestBody,
        response_body: e.responseBody,
        elapsed_ms: e.elapsed_ms,
        timestamp: e.timestamp,
      }));
      const result = await sidecar.exportHarFromEntries(entries);
      const blob = new Blob([result.har_json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `theridion-export-${Date.now()}.har`;
      a.click();
      URL.revokeObjectURL(url);
      addToast("success", `Exported ${networkEntries.length} entries as HAR`);
    } catch (e) {
      addToast("error", `HAR export failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  // ---- Postman export -------------------------------------------------------
  async function exportPostman(collectionId: string) {
    try {
      const result = await sidecar.exportPostman(collectionId);
      const blob = new Blob([result.postman_json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const col = collections.find((c) => c.id === collectionId);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${col?.name ?? "collection"}.postman_collection.json`;
      a.click();
      URL.revokeObjectURL(url);
      addToast("success", "Exported as Postman collection");
    } catch (e) {
      addToast("error", `Postman export failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  // ---- collection ops -----------------------------------------------------
  function newCollection() {
    setInlineNewName({ type: "collection" });
  }

  async function commitNewCollection(name: string) {
    setInlineNewName(null);
    await sidecar.createCollection(name);
    await refreshCollections();
  }

  /** Used by the save popover. Returns the freshly-created collection so
   * the popover can immediately bind the save to it. */
  async function newCollectionFromPopover(name: string) {
    const created = await sidecar.createCollection(name);
    await refreshCollections();
    return created;
  }

  async function deleteCollection(id: string) {
    await sidecar.deleteCollection(id);
    await refreshCollections();
    // Detach any open tabs that pointed at this collection.
    setTabs((curr) =>
      curr.map((t) =>
        t.savedAs?.collectionId === id ? { ...t, savedAs: null } : t,
      ),
    );
  }

  async function deleteRequest(collectionId: string, requestId: string) {
    await sidecar.deleteRequest(collectionId, requestId);
    await refreshCollections();
    setTabs((curr) =>
      curr.map((t) =>
        t.savedAs?.collectionId === collectionId &&
        t.savedAs?.requestId === requestId
          ? { ...t, savedAs: null }
          : t,
      ),
    );
  }

  function newFolder(collectionId: string, parentFolderId: string | null) {
    setInlineNewName({ type: "folder", collectionId, parentId: parentFolderId ?? undefined });
  }

  async function commitNewFolder(name: string) {
    if (!inlineNewName || inlineNewName.type !== "folder" || !inlineNewName.collectionId) return;
    const collectionId = inlineNewName.collectionId;
    const parentFolderId = inlineNewName.parentId ?? null;
    setInlineNewName(null);
    await sidecar.createFolder(collectionId, {
      name,
      parent_folder_id: parentFolderId,
    });
    await refreshCollections();
  }

  async function renameCollection(id: string, name: string) {
    await sidecar.renameCollection(id, name);
    await refreshCollections();
  }

  async function renameItem(collectionId: string, itemId: string, name: string) {
    await sidecar.renameItem(collectionId, itemId, name);
    await refreshCollections();
    // Update name in any open tab pointing at this request.
    setTabs((curr) =>
      curr.map((t) =>
        t.savedAs?.collectionId === collectionId && t.savedAs?.requestId === itemId
          ? { ...t, name }
          : t,
      ),
    );
  }

  async function deleteFolder(collectionId: string, folderId: string) {
    await sidecar.deleteFolder(collectionId, folderId);
    await refreshCollections();
    // Detach any open tabs whose saved request lived under that folder —
    // we don't track folder ancestry on the tab, but we do detach all tabs
    // bound to this collection's items that no longer exist after the
    // delete. That refresh happens in refreshCollections; we conservatively
    // null out tabs that lost their backing request.
  }

  // ---- breadcrumb helper -------------------------------------------------
  const activeBreadcrumb = (() => {
    if (!active.savedAs) return null;
    const col = collections.find((c) => c.id === active.savedAs!.collectionId);
    if (!col) return null;
    const path: string[] = [col.name];
    function walk(items: CollectionItem[], target: string): boolean {
      for (const item of items) {
        if (item.id === target) return true;
        if (item.is_folder && item.items) {
          if (walk(item.items, target)) {
            path.push(item.name);
            return true;
          }
        }
      }
      return false;
    }
    walk(col.items, active.savedAs!.requestId);
    return path;
  })();

  // ---- draggable split handler -------------------------------------------
  const handleSplitMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    splitDragging[1](true);
    const container = (e.target as HTMLElement).parentElement;
    if (!container) return;
    const startX = e.clientX;
    const startRatio = splitRatio;
    const containerWidth = container.getBoundingClientRect().width;
    const minPx = 300;

    function onMove(ev: MouseEvent) {
      const dx = ev.clientX - startX;
      let newRatio = startRatio + dx / containerWidth;
      // Enforce min widths
      if (newRatio * containerWidth < minPx) newRatio = minPx / containerWidth;
      if ((1 - newRatio) * containerWidth < minPx) newRatio = 1 - minPx / containerWidth;
      setSplitRatio(newRatio);
    }
    function onUp() {
      splitDragging[1](false);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [splitRatio, splitDragging]);

  const handleNetworkDragMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    networkDragging.current = true;
    const startY = e.clientY;
    const startH = networkHeight;

    function onMove(ev: MouseEvent) {
      const dy = startY - ev.clientY;
      const newH = Math.min(600, Math.max(150, startH + dy));
      setNetworkHeight(newH);
    }
    function onUp() {
      networkDragging.current = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [networkHeight]);

  // Responsive auto-collapse sidebar when window is narrow
  useEffect(() => {
    const check = () => {
      if (window.innerWidth < 1200 && !sidebarCollapsed) setSidebarCollapsed(true);
    };
    window.addEventListener("resize", check);
    check();
    return () => window.removeEventListener("resize", check);
  }, [sidebarCollapsed]);

  const isFirstRun = collections.length === 0 && !active.response;

  // ---- command palette actions ----------------------------------------------
  const cmdActions = useDefaultActions({
    newTab: (seed) => newTab(seed as Partial<RequestTab> | undefined),
    importCurl: () => modals.open("curlImport"),
    openGraphQL: () => modals.open("graphql"),
    openWebSocket: () => modals.open("webSocket"),
    openKafka: () => modals.open("kafka"),
    openSoap: () => modals.open("soap"),
    manageEnvs: () => modals.open("envManager"),
    openCodegen: () => modals.open("codegen"),
    openGrpc: () => modals.open("grpc"),
    openMock: () => modals.open("mock"),
    openLoadTest: () => modals.open("loadTest"),
    openSettings: () => modals.open("settings"),
    importCollection: () => modals.open("import"),
    openServiceMap: () => modals.open("serviceMap"),
    openProxy: () => modals.open("proxy"),
    openSwagger: () => modals.open("swagger"),
    openOpenapiImport: () => modals.open("openapiImport"),
    openJwt: () => modals.open("jwt"),
    openBatch: () => modals.open("batch"),
    openMonitors: () => modals.open("monitors"),
    openSecurity: () => modals.open("security"),
    openCollVars: () => modals.open("collVars"),
    openSecrets: () => modals.open("secrets"),
    openWebhooks: () => modals.open("webhooks"),
    openMultiEnv: () => modals.open("multiEnv"),
    openFlowEditor: () => modals.open("flowEditor"),
    openPerfDash: () => modals.open("perfDash"),
    openAgentExplorer: () => modals.open("agentExplorer"),
    openOwaspScanner: () => modals.open("owaspScanner"),
    openRequestDiff: () => modals.open("requestDiff"),
    openBodyDiff: () => modals.open("bodyDiff"),
    openEnvComparison: () => modals.open("envComparison"),
    openSSE: () => modals.open("sse"),
    openChangelog: () => modals.open("changelog"),
    openPipeline: () => modals.open("pipeline"),
    openDocGenerator: () => modals.open("docGenerator"),
    openDepGraph: () => modals.open("depGraph"),
    openReleaseCenter: () => modals.open("releaseCenter"),
    collections,
    onOpenRequest: openSaved,
    environments,
    activeEnvId,
    onSelectEnv: (id) => {
      setActiveEnvId(id);
      addToast("info", id ? `Switched to: ${environments.find((e) => e.id === id)?.name}` : "Switched to: No environment");
    },
  });

  // ---- keyboard shortcuts -------------------------------------------------
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const cmd = e.metaKey || e.ctrlKey;
      if (cmd && e.shiftKey && e.key === "f") {
        e.preventDefault();
        setGlobalSearchOpen((o) => !o);
      } else if (cmd && e.key === "k") {
        e.preventDefault();
        setCmdPaletteOpen((o) => !o);
      } else if (cmd && e.key === ",") {
        e.preventDefault();
        modals.open("settings");
      } else if (cmd && e.key === "s") {
        e.preventDefault();
        // Cmd+Shift+S = always show picker (Save As); Cmd+S alone = save in
        // place when bound, otherwise open picker.
        if (e.shiftKey) {
          setSavePopoverOpen(true);
        } else {
          void save();
        }
      } else if (cmd && e.key === "t") {
        e.preventDefault();
        newTab();
      } else if (cmd && e.key === "w") {
        e.preventDefault();
        closeTab(activeId);
      } else if (cmd && e.shiftKey && e.key === "C") {
        e.preventDefault();
        if (active.response?.body) {
          void navigator.clipboard.writeText(active.response.body);
          addToast("success", "Response body copied");
        }
      } else if (cmd && e.shiftKey && e.key === "N") {
        e.preventDefault();
        setNetworkOpen((o) => !o);
      } else if (cmd && e.key === "e") {
        e.preventDefault();
        // Cycle through environments.
        if (environments.length === 0) return;
        const currentIdx = environments.findIndex((env) => env.id === activeEnvId);
        const nextIdx = (currentIdx + 1) % (environments.length + 1);
        if (nextIdx === environments.length) {
          // Wrap to "no environment".
          setActiveEnvId(null);
          addToast("info", "Switched to: No environment");
        } else {
          setActiveEnvId(environments[nextIdx].id);
          addToast("info", `Switched to: ${environments[nextIdx].name}`);
        }
      } else if (e.altKey && !cmd && e.key >= "1" && e.key <= "7") {
        e.preventDefault();
        const tabMap: Record<string, string> = { "1": "params", "2": "headers", "3": "body", "4": "auth", "5": "tests", "6": "scripts", "7": "notes" };
        const tabId = tabMap[e.key];
        if (tabId) {
          // Dispatch custom event for RequestPanel to pick up
          window.dispatchEvent(new CustomEvent("theridion:switch-request-tab", { detail: tabId }));
        }
      } else if (cmd && e.key === "Enter") {
        e.preventDefault();
        void send();
      } else if (cmd && e.key === "d") {
        e.preventDefault();
        duplicateTab(activeId);
      } else if (cmd && e.shiftKey && e.key === "H") {
        e.preventDefault();
        setHistoryOpen((o) => !o);
      } else if (cmd && e.key === "i") {
        e.preventDefault();
        modals.open("import");
      } else if (e.key === "?" && !cmd && !e.altKey) {
        // Don't trigger if user is typing in an input/textarea/contenteditable.
        const tag = (e.target as HTMLElement).tagName;
        const editable = (e.target as HTMLElement).isContentEditable;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || editable) return;
        e.preventDefault();
        setShortcutOverlayOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, activeId, collections, sidecarStatus.state]);

  return (
    <div className={`grid h-full ${sidebarCollapsed ? "grid-cols-[48px_64px_1fr]" : "grid-cols-[48px_260px_1fr]"} ${networkOpen && appMode === "requests" ? `grid-rows-[1fr_${networkHeight}px_auto]` : "grid-rows-[1fr_auto]"} relative bg-neutral-950 bg-mesh-gradient text-neutral-100 transition-[grid-template-columns] duration-200 ease-in-out`} style={networkOpen && appMode === "requests" ? { gridTemplateRows: `1fr ${networkHeight}px auto` } : undefined}>
      {/* Subtle accent radial glow -- top-right corner */}
      <div className="pointer-events-none absolute right-0 top-0 h-[500px] w-[500px] rounded-full bg-[radial-gradient(circle,rgb(var(--accent-500)/0.04)_0%,transparent_70%)]" aria-hidden />
      <div className="row-span-1 overflow-hidden">
        <ActivityBar
          mode={appMode}
          onModeChange={setAppMode}
          networkEntryCount={networkEntries.length}
        />
      </div>

      {appMode === "requests" && (<>
      <div className="row-span-1 overflow-hidden">
        <Sidebar
          collections={collections}
          loading={collectionsLoading}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
          onOpen={openSaved}
          onNewCollection={newCollection}
          onGenerateTests={() => modals.open("testGen")}
          onNewFolder={newFolder}
          onDeleteCollection={deleteCollection}
          onDeleteRequest={deleteRequest}
          onDeleteFolder={deleteFolder}
          onRenameCollection={renameCollection}
          onRenameItem={renameItem}
          onImport={() => modals.open("import")}
          onRunCollection={() => modals.open("batch")}
          onFileImport={async (content, filename) => {
            try {
              await sidecar.universalImport(content, filename);
              await refreshCollections();
              addToast("success", `Imported ${filename}`);
            } catch (e) {
              addToast("error", `Import failed: ${e instanceof Error ? e.message : String(e)}`);
            }
          }}
          inlineNewName={inlineNewName}
          onInlineNewCommit={(name) => {
            if (inlineNewName?.type === "collection") void commitNewCollection(name);
            else if (inlineNewName?.type === "folder") void commitNewFolder(name);
          }}
          onInlineNewCancel={() => setInlineNewName(null)}
          onRefresh={refreshCollections}
          onReorder={async (collectionId, parentFolderId, itemIds) => {
            try {
              await sidecar.reorderItems(collectionId, parentFolderId, itemIds);
              await refreshCollections();
            } catch (e) {
              console.error("reorder failed", e);
            }
          }}
          onExportCurl={async (collectionId) => {
            try {
              const result = await sidecar.exportCurl(collectionId);
              await navigator.clipboard.writeText(result.commands.join("\n\n"));
              addToast("success", `Exported ${result.count} cURL command${result.count !== 1 ? "s" : ""}`);
            } catch (e) {
              console.error("export curl failed", e);
            }
          }}
          onExportPostman={(collectionId) => void exportPostman(collectionId)}
          onViewStats={(collectionId) => {
            setStatsCollectionId(collectionId);
            modals.open("collectionStats");
          }}
          onMoveToFolder={async (collectionId, itemId, targetFolderId) => {
            try {
              await sidecar.moveItem(collectionId, itemId, targetFolderId);
              await refreshCollections();
            } catch (e) {
              console.error("move failed", e);
            }
          }}
          onContextMenu={(e, collectionId, item) => {
            e.preventDefault();
            setCtxMenu({
              open: true,
              x: e.clientX,
              y: e.clientY,
              actions: buildSidebarActions({
                onOpenInNewTab: !item.is_folder ? () => {
                  const tab = tabFromSaved(collectionId, item);
                  setTabs(curr => [...curr, tab]);
                  setActiveId(tab.id);
                } : undefined,
                onRename: () => {
                  // Handled by inline rename in Sidebar
                  void renameItem(collectionId, item.id, item.name);
                },
                onDuplicate: () => {
                  void sidecar.duplicateRequest(collectionId, item.id).then(() => refreshCollections());
                },
                onDelete: () => {
                  void deleteRequest(collectionId, item.id);
                },
                onCopyAsCurl: item.url ? () => {
                  void sidecar.generateCurl({
                    method: item.method ?? "GET",
                    url: item.url ?? "",
                    headers: item.headers,
                    body: item.body,
                  }).then((r) => navigator.clipboard.writeText(r.curl));
                } : undefined,
              }),
            });
          }}
        />
      </div>

      <main className="flex min-h-0 flex-col overflow-hidden">
        <RequestTabBar
          tabs={tabs}
          activeId={activeId}
          onSelect={setActiveId}
          onClose={closeTab}
          onNew={() => newTab()}
          onImportCurl={() => modals.open("curlImport")}
          onOpenGraphQL={() => modals.open("graphql")}
          onOpenWebSocket={() => modals.open("webSocket")}
          onOpenKafka={() => modals.open("kafka")}
          onOpenGrpc={() => modals.open("grpc")}
          onOpenMock={() => modals.open("mock")}
          onOpenLoadTest={() => modals.open("loadTest")}
          onOpenSwagger={() => modals.open("swagger")}
          onToggleHistory={() => setHistoryOpen((o) => !o)}
          historyOpen={historyOpen}
          historyCount={history.length}
          onOpenSoap={() => modals.open("soap")}
          environments={environments}
          activeEnvId={activeEnvId}
          onSelectEnv={setActiveEnvId}
          onManageEnv={() => modals.open("envManager")}
          onOpenAgentExplorer={() => modals.open("agentExplorer")}
          onDuplicateTab={duplicateTab}
          onPinTab={pinTab}
          onCloseOtherTabs={closeOtherTabs}
          onCloseTabsToRight={closeTabsToRight}
          onCopyUrl={copyTabUrl}
          onCopyAsCurl={copyAsCurl}
        />
        <div className="relative">
          <UrlBar
            method={active.method}
            url={active.url}
            busy={active.busy}
            canSend={active.url.length > 0 && !active.busy}
            dirty={isDirty(active)}
            onMethodChange={(method) => patchActive({ method })}
            onUrlChange={(url) => patchActive({ url })}
            onSend={send}
            onCancel={cancelRequest}
            onSave={() => save()}
            onSaveAs={() => setSavePopoverOpen(true)}
            onCopyAsCurl={copyAsCurl}
            onCopyShareable={() => {
              const lines: string[] = [];
              lines.push(`${active.method} ${active.url}`);
              for (const line of active.headersRaw.split("\n").filter((l) => l.trim() && !l.startsWith("#"))) {
                lines.push(line.trim());
              }
              if (active.body) {
                lines.push("");
                lines.push(active.body);
              }
              void navigator.clipboard.writeText(lines.join("\n"));
              addToast("success", "Copied shareable text");
            }}
            activeEnvId={activeEnvId}
            environments={environments}
            onEnvChange={(envId) => {
              setActiveEnvId(envId);
              if (envId) window.localStorage.setItem(ACTIVE_ENV_KEY, envId);
              else window.localStorage.removeItem(ACTIVE_ENV_KEY);
            }}
            lastStatus={lastStatus}
          />
          <SavePopover
            open={savePopoverOpen}
            collections={collections}
            defaultName={
              active.name && active.name !== "Untitled"
                ? active.name
                : deriveNameFromUrl(active.url)
            }
            onClose={() => setSavePopoverOpen(false)}
            onSave={(t) => save(t)}
            onCreateCollection={newCollectionFromPopover}
          />
        </div>
        <div className={`flex min-h-0 flex-1 ${historyOpen ? "" : ""}`}>
          <div className="min-h-0 overflow-hidden border-r border-neutral-800" style={{ width: historyOpen ? `calc(${splitRatio * 100}% - 120px)` : `${splitRatio * 100}%` }}>
            <RequestPanel
              url={active.url}
              headersRaw={active.headersRaw}
              body={active.body}
              auth={active.auth}
              assertions={active.assertions}
              assertionResults={active.assertionResults}
              onUrlChange={(url) => patchActive({ url })}
              onHeadersChange={(headersRaw) => patchActive({ headersRaw })}
              onBodyChange={(body) => patchActive({ body })}
              onAuthChange={(auth) => patchActive({ auth })}
              certConfig={active.certConfig}
              onCertConfigChange={(certConfig) => patchActive({ certConfig })}
              onAssertionsChange={(assertions) => patchActive({ assertions, assertionResults: null })}
              preRequestScript={active.preRequestScript}
              onPreRequestScriptChange={(preRequestScript) => patchActive({ preRequestScript })}
              postResponseScript={active.postResponseScript}
              onPostResponseScriptChange={(postResponseScript) => patchActive({ postResponseScript })}
              notes={active.notes}
              onNotesChange={(notes) => patchActive({ notes })}
              savedAs={active.savedAs}
              method={active.method}
              onMethodChange={(method) => patchActive({ method })}
              response={active.response}
              retryConfig={active.retryConfig}
              onRetryConfigChange={(retryConfig) => patchActive({ retryConfig })}
              retryAttempts={active.retryAttempts}
              breadcrumb={activeBreadcrumb}
              onReEvaluate={active.response && active.assertions.length > 0 ? async () => {
                try {
                  const evalResult = await sidecar.evaluateAssertions({
                    assertions: active.assertions,
                    response: {
                      status: active.response!.status,
                      headers: active.response!.headers,
                      body: active.response!.body,
                      elapsed_ms: active.response!.elapsed_ms,
                    },
                  });
                  patchActive({ assertionResults: evalResult.results });
                  addToast("info", "Assertions re-evaluated");
                } catch {
                  addToast("error", "Failed to re-evaluate assertions");
                }
              } : undefined}
            />
          </div>
          {/* Draggable split divider */}
          <div
            className="group relative w-1 shrink-0 cursor-col-resize"
            onMouseDown={handleSplitMouseDown}
          >
            <div className={`absolute inset-y-0 left-1/2 w-px -translate-x-1/2 transition-colors ${splitDragging[0] ? "bg-cobweb-500/60" : "bg-neutral-800 group-hover:bg-cobweb-500/40"}`} />
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <ResponsePanel
              busy={active.busy}
              response={active.response}
              error={active.error}
              onDiff={() => modals.open("diff")}
              onCodegen={() => modals.open("codegen")}
              consoleEntries={consoleEntries}
              isFirstRun={isFirstRun}
              onImportCollection={() => modals.open("import")}
              onOpenSwagger={() => modals.open("swagger")}
              onOpenAgentExplorer={() => modals.open("agentExplorer")}
              onNewCollection={newCollection}
              onAddAssertion={(assertion) => {
                patchActive({ assertions: [...active.assertions, assertion], assertionResults: null });
              }}
            />
          </div>
          {historyOpen && (
            <div className="min-h-0 overflow-hidden border-l border-neutral-800 bg-neutral-925">
              <HistoryPanel
                entries={history}
                onSelect={(entry) => {
                  newTab({ method: entry.method, url: entry.url });
                }}
                onReplay={(entry) => {
                  newTab({ method: entry.method, url: entry.url });
                }}
                onClear={() => setHistory([])}
              />
            </div>
          )}
        </div>
      </main>
      </>)}

      {appMode === "flows" && (
        <div className="col-span-2 flex items-center justify-center text-neutral-500">
          <div className="text-center">
            <p className="text-lg font-medium text-neutral-400">Flow Editor</p>
            <p className="mt-1 text-sm">Coming soon</p>
          </div>
        </div>
      )}

      {appMode === "traffic" && (
        <div className="col-span-2 overflow-hidden">
          <NetworkConsole
            entries={networkEntries}
            recording={networkRecording}
            onToggleRecording={() => setNetworkRecording((r) => !r)}
            onClear={() => setNetworkEntries([])}
            preserveLog={networkPreserveLog}
            onTogglePreserveLog={() => setNetworkPreserveLog((p) => !p)}
            onExportHar={exportHar}
          />
        </div>
      )}

      {appMode === "monitors" && (
        <div className="col-span-2 flex items-center justify-center text-neutral-500">
          <div className="text-center">
            <p className="text-lg font-medium text-neutral-400">API Monitors</p>
            <p className="mt-1 text-sm">Coming soon</p>
          </div>
        </div>
      )}

      {appMode === "spin" && (
        <div className="col-span-2 overflow-hidden">
          <SpinPanel />
        </div>
      )}

      {networkOpen && appMode === "requests" && (
        <div className="col-span-3 overflow-hidden relative">
          {/* Drag handle for resizing Network Console */}
          <div
            className="absolute inset-x-0 top-0 z-10 h-1 cursor-row-resize group"
            onMouseDown={handleNetworkDragMouseDown}
          >
            <div className="mx-auto h-px w-16 bg-neutral-700 transition-colors group-hover:bg-neutral-500 mt-[1px]" />
          </div>
          <NetworkConsole
            entries={networkEntries}
            recording={networkRecording}
            onToggleRecording={() => setNetworkRecording((r) => !r)}
            onClear={() => setNetworkEntries([])}
            preserveLog={networkPreserveLog}
            onTogglePreserveLog={() => setNetworkPreserveLog((p) => !p)}
            onExportHar={exportHar}
          />
        </div>
      )}

      <div className="col-span-3">
        <StatusBar
          sidecarStatus={sidecarStatus}
          appVersion={APP_VERSION}
          onOpenSettings={() => modals.open("settings")}
          requestCount={requestCount}
          lastStatus={lastStatus}
          networkOpen={networkOpen}
          networkEntryCount={networkEntries.length}
          onToggleNetwork={() => setNetworkOpen((o) => !o)}
          activeEnvId={activeEnvId}
          environments={environments}
          onManageEnv={() => modals.open("envManager")}
          onToggleHistory={() => setHistoryOpen((o) => !o)}
          onOpenDiagnostics={() => modals.open("settings")}
        />
      </div>

      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Cross-module event toasts (Silk, Hub, Runner → theridion://event) */}
      <EventToastContainer />

      <EnvManagerModal
        open={modals.isOpen("envManager")}
        onClose={modals.close}
        onChanged={refreshEnvironments}
      />
      <CurlImportModal
        open={modals.isOpen("curlImport")}
        onClose={modals.close}
        onImport={importCurl}
      />
      <GraphQLModal open={modals.isOpen("graphql")} onClose={modals.close} activeEnvId={activeEnvId} />
      <WebSocketModal open={modals.isOpen("webSocket")} onClose={modals.close} />
      <KafkaModal open={modals.isOpen("kafka")} onClose={modals.close} />
      <CodegenModal
        open={modals.isOpen("codegen")}
        onClose={modals.close}
        method={active.method}
        url={active.url}
        headers={parseHeadersText(active.headersRaw)}
        body={active.body || null}
      />
      <DiffModal
        open={modals.isOpen("diff")}
        onClose={modals.close}
        currentResponse={active.response}
        previousResponse={previousResponse}
      />
      <GrpcModal open={modals.isOpen("grpc")} onClose={modals.close} />
      <MockServerModal open={modals.isOpen("mock")} onClose={modals.close} />
      <LoadTestModal
        open={modals.isOpen("loadTest")}
        onClose={modals.close}
        method={active.method}
        url={active.url}
        headers={parseHeadersText(active.headersRaw)}
        body={active.body || null}
      />
      <SettingsModal open={modals.isOpen("settings")} onClose={modals.close} />
      <ReleaseCenterModal
        open={modals.isOpen("releaseCenter")}
        collections={collections}
        onClose={modals.close}
        onRefreshCollections={refreshCollections}
        onToast={addToast}
      />
      <ImportModal open={modals.isOpen("import")} onClose={modals.close} onImported={refreshCollections} />
      <ServiceMapModal open={modals.isOpen("serviceMap")} onClose={modals.close} />
      <ProxyRecorderModal open={modals.isOpen("proxy")} onClose={modals.close} />
      <SwaggerBrowserModal
        open={modals.isOpen("swagger")}
        onClose={modals.close}
        onTryEndpoint={(method, url, headers, body) => {
          newTab({
            method: method as import("./state/types").Method,
            url,
            headersRaw: Object.entries(headers).map(([k, v]) => `${k}: ${v}`).join("\n"),
            body: body || "",
          });
        }}
      />
      <OpenAPIImportModal open={modals.isOpen("openapiImport")} onClose={modals.close} onImported={refreshCollections} />
      <SoapModal open={modals.isOpen("soap")} onClose={modals.close} />
      <TestGenModal
        open={modals.isOpen("testGen")}
        onClose={modals.close}
        onCreated={() => {
          void refreshCollections();
        }}
      />
      <CommandPalette
        open={cmdPaletteOpen}
        onClose={() => setCmdPaletteOpen(false)}
        actions={cmdActions}
      />
      <GlobalSearch
        open={globalSearchOpen}
        onClose={() => setGlobalSearchOpen(false)}
        collections={collections}
        environments={environments}
        onOpenRequest={openSaved}
        onManageEnvs={() => modals.open("envManager")}
        onSelectEnv={(id) => {
          setActiveEnvId(id);
          addToast("info", id ? `Switched to: ${environments.find((e) => e.id === id)?.name}` : "No environment");
        }}
        onNewTab={() => newTab()}
        onOpenCommandPalette={() => setCmdPaletteOpen(true)}
        onOpenSettings={() => modals.open("settings")}
      />
      <ContextMenu
        open={ctxMenu.open}
        x={ctxMenu.x}
        y={ctxMenu.y}
        actions={ctxMenu.actions}
        onClose={() => setCtxMenu((c) => ({ ...c, open: false }))}
      />
      <JwtInspectorModal open={modals.isOpen("jwt")} onClose={modals.close} />
      <BatchRunnerModal open={modals.isOpen("batch")} onClose={modals.close} />
      <MonitorsModal open={modals.isOpen("monitors")} onClose={modals.close} />
      <SecurityScannerModal open={modals.isOpen("security")} onClose={modals.close} />
      <CollectionVarsModal open={modals.isOpen("collVars")} onClose={modals.close} />
      <SecretsVaultModal open={modals.isOpen("secrets")} onClose={modals.close} />
      <WebhooksModal open={modals.isOpen("webhooks")} onClose={modals.close} />
      <MultiEnvModal open={modals.isOpen("multiEnv")} onClose={modals.close} />
      <FlowEditorModal open={modals.isOpen("flowEditor")} onClose={modals.close} />
      <PerformanceDashboardModal open={modals.isOpen("perfDash")} onClose={modals.close} />
      <AgentExplorerModal open={modals.isOpen("agentExplorer")} onClose={modals.close} onCollectionCreated={refreshCollections} />
      <OWASPScannerModal open={modals.isOpen("owaspScanner")} onClose={modals.close} />
      <RequestDiffModal open={modals.isOpen("requestDiff")} onClose={modals.close} />
      <BodyDiffModal open={modals.isOpen("bodyDiff")} onClose={modals.close} />
      <CollectionStatsModal
        open={modals.isOpen("collectionStats")}
        onClose={() => { modals.close(); setStatsCollectionId(null); }}
        collection={statsCollectionId ? collections.find((c) => c.id === statsCollectionId) ?? null : null}
      />
      <ComparisonTableModal
        open={modals.isOpen("envComparison")}
        onClose={modals.close}
        collections={collections}
        environments={environments}
      />
      <SSEModal open={modals.isOpen("sse")} onClose={modals.close} />
      <ChangelogModal open={modals.isOpen("changelog")} onClose={modals.close} />
      <PipelineModal open={modals.isOpen("pipeline")} onClose={modals.close} collections={collections} />
      <DocGeneratorModal open={modals.isOpen("docGenerator")} onClose={modals.close} />
      <DependencyGraphModal
        open={modals.isOpen("depGraph")}
        onClose={modals.close}
        collectionId={active.savedAs?.collectionId ?? collections[0]?.id ?? null}
        onOpenRequest={(reqId) => {
          const cId = active.savedAs?.collectionId ?? collections[0]?.id;
          if (!cId) return;
          const coll = collections.find((c) => c.id === cId);
          if (!coll) return;
          // Find the request in collection items (flat search)
          function findItem(items: CollectionItem[]): CollectionItem | undefined {
            for (const it of items) {
              if (it.id === reqId) return it;
              if (it.is_folder && it.items) {
                const found = findItem(it.items);
                if (found) return found;
              }
            }
            return undefined;
          }
          const item = findItem(coll.items);
          if (item) openSaved(cId, item);
        }}
      />

      {/* Keyboard shortcut overlay */}
      {shortcutOverlayOpen && (
        <ShortcutOverlay onClose={() => setShortcutOverlayOpen(false)} />
      )}
    </div>
  );
}

const SHORTCUT_SECTIONS: { title: string; items: { action: string; shortcut: string }[] }[] = [
  {
    title: "Request",
    items: [
      { action: "Send request", shortcut: "\u2318\u23CE" },
      { action: "Save", shortcut: "\u2318S" },
      { action: "Save As", shortcut: "\u2318\u21E7S" },
      { action: "Copy response body", shortcut: "\u2318\u21E7C" },
    ],
  },
  {
    title: "Tabs",
    items: [
      { action: "New tab", shortcut: "\u2318T" },
      { action: "Close tab", shortcut: "\u2318W" },
      { action: "Duplicate tab", shortcut: "\u2318D" },
    ],
  },
  {
    title: "Navigation",
    items: [
      { action: "Command palette", shortcut: "\u2318K" },
      { action: "Global search", shortcut: "\u2318\u21E7F" },
      { action: "Settings", shortcut: "\u2318," },
      { action: "Network console", shortcut: "\u2318\u21E7N" },
      { action: "History panel", shortcut: "\u2318\u21E7H" },
      { action: "Import", shortcut: "\u2318I" },
      { action: "Switch environment", shortcut: "Ctrl+E" },
    ],
  },
  {
    title: "Request Panel",
    items: [
      { action: "Params tab", shortcut: "Alt+1" },
      { action: "Headers tab", shortcut: "Alt+2" },
      { action: "Body tab", shortcut: "Alt+3" },
      { action: "Auth tab", shortcut: "Alt+4" },
      { action: "Tests tab", shortcut: "Alt+5" },
      { action: "Pre-request tab", shortcut: "Alt+6" },
      { action: "Notes tab", shortcut: "Alt+7" },
    ],
  },
  {
    title: "Tools",
    items: [
      { action: "Search in response", shortcut: "Ctrl+F" },
      { action: "This overlay", shortcut: "?" },
    ],
  },
];

function ShortcutOverlay({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" || e.key === "?") {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-lg rounded-xl border border-glass bg-neutral-900/95 p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-100">Keyboard Shortcuts</h2>
          <span className="text-[11px] text-neutral-500">Press Esc or ? to close</span>
        </div>
        <div className="grid grid-cols-2 gap-6">
          {SHORTCUT_SECTIONS.map((section) => (
            <div key={section.title}>
              <h3 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-neutral-500">{section.title}</h3>
              <div className="space-y-1.5">
                {section.items.map((item) => (
                  <div key={item.action} className="flex items-center justify-between text-xs">
                    <span className="text-neutral-300">{item.action}</span>
                    <kbd className="rounded border border-glass bg-neutral-800 px-1.5 py-0.5 font-mono text-[10px] text-neutral-400">
                      {item.shortcut}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function detectNetworkType(url: string, body: string, _method: string): NetworkEntryType {
  const lUrl = url.toLowerCase();
  const lBody = body.toLowerCase();
  if (lUrl.includes("soap") || lBody.includes("<soap:") || lBody.includes("<soapenv:") || lBody.includes("schemas.xmlsoap.org")) return "soap";
  if (lUrl.includes("graphql") || (lBody.includes('"query"') && lBody.includes("{"))) return "graphql";
  if (lUrl.includes("grpc") || lUrl.includes("twirp")) return "grpc";
  if (lUrl.startsWith("ws://") || lUrl.startsWith("wss://")) return "ws";
  return "xhr";
}

function deriveNameFromUrl(url: string): string {
  try {
    const u = new URL(url);
    const last = u.pathname.split("/").filter(Boolean).pop();
    if (last) return last;
    return u.host;
  } catch {
    return url.slice(0, 40);
  }
}
