"use strict";

const studio = {
  token: "",
  header: "X-ReelSyntax-CSRF",
  locale: "en",
  strings: {},
  locales: [],
  aspects: [],
  formats: [],
  projects: [],
  current: null,
  detail: null,
  busy: false
};

const KNOWN_STATUS = ["pass", "review", "fail", "blocked", "completed", "awaiting_approval", "paused", "in_progress", "initialized", "awaiting_edit", "timeline"];

function t(key, params) {
  let text = Object.prototype.hasOwnProperty.call(studio.strings, key) ? studio.strings[key] : key;
  if (params) {
    for (const name of Object.keys(params)) {
      text = text.split("{" + name + "}").join(String(params[name]));
    }
  }
  return text;
}

function hasString(key) {
  return Object.prototype.hasOwnProperty.call(studio.strings, key);
}

function el(tag, options, children) {
  const node = document.createElement(tag);
  const opts = options || {};
  for (const key of Object.keys(opts)) {
    const value = opts[key];
    if (value === undefined || value === null || value === false) {
      continue;
    }
    if (key === "text") {
      node.textContent = String(value);
    } else if (key === "className") {
      node.className = value;
    } else if (key === "on") {
      for (const eventName of Object.keys(value)) {
        node.addEventListener(eventName, value[eventName]);
      }
    } else if (value === true) {
      node.setAttribute(key, "");
    } else {
      node.setAttribute(key, String(value));
    }
  }
  for (const child of children || []) {
    if (child === null || child === undefined || child === false) {
      continue;
    }
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function setStatus(message, isError) {
  const box = document.getElementById("status");
  box.textContent = message;
  box.classList.toggle("is-error", Boolean(isError));
}

function showError(error) {
  setStatus(t("ui.status.error", { message: error && error.message ? error.message : String(error) }), true);
}

async function api(path, body) {
  const init = { method: "GET", credentials: "same-origin", cache: "no-store", headers: { "Accept": "application/json" } };
  if (body !== undefined) {
    init.method = "POST";
    init.headers["Content-Type"] = "application/json";
    init.headers[studio.header] = studio.token;
    init.body = JSON.stringify(body);
  }
  const response = await fetch(path, init);
  let payload = null;
  try {
    payload = await response.json();
  } catch (error) {
    payload = null;
  }
  if (!response.ok || !payload || payload.ok !== true) {
    throw new Error(payload && payload.error ? payload.error : "HTTP " + response.status);
  }
  return payload.result;
}

function mediaUrl(project, path) {
  return "/api/media?project=" + encodeURIComponent(project) + "&path=" + encodeURIComponent(path);
}

function setBusy(flag) {
  studio.busy = flag;
  document.body.setAttribute("aria-busy", flag ? "true" : "false");
  for (const control of document.querySelectorAll("main button, main input, main select, main textarea")) {
    control.disabled = flag;
  }
}

async function runAction(task) {
  if (studio.busy) {
    return;
  }
  setBusy(true);
  setStatus(t("ui.status.working"), false);
  try {
    await task();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
}

function statusBadge(status) {
  const value = status ? String(status) : "—";
  const cls = KNOWN_STATUS.indexOf(value) >= 0 ? "badge " + value : "badge";
  return el("span", { className: cls, text: value });
}

function applyStrings() {
  for (const node of document.querySelectorAll("[data-i18n]")) {
    const key = node.getAttribute("data-i18n");
    if (hasString(key)) {
      node.textContent = t(key);
    }
  }
  for (const node of document.querySelectorAll("[data-i18n-aria-label]")) {
    const key = node.getAttribute("data-i18n-aria-label");
    if (hasString(key)) {
      node.setAttribute("aria-label", t(key));
    }
  }
  document.title = t("ui.title");
  document.documentElement.lang = studio.locale;
}

async function loadSession(lang) {
  const query = lang ? "?lang=" + encodeURIComponent(lang) : "";
  const session = await api("/api/session" + query);
  studio.token = session.csrf_token || studio.token;
  studio.header = session.csrf_header || studio.header;
  studio.locale = session.locale;
  studio.strings = session.strings || {};
  studio.locales = session.locales || [];
  studio.aspects = session.aspects || [];
  applyStrings();
  renderLanguageSelect();
  renderMakeSelects();
}

function renderLanguageSelect() {
  const select = document.getElementById("lang-select");
  select.replaceChildren();
  for (const entry of studio.locales) {
    select.append(el("option", { value: entry.code, selected: entry.code === studio.locale, text: entry.name + " (" + entry.code + ")" }));
  }
  select.value = studio.locale;
}

function fillSelect(select, options, selected) {
  select.replaceChildren();
  for (const option of options) {
    select.append(el("option", { value: option.value, text: option.label }));
  }
  if (selected !== undefined) {
    select.value = selected;
  }
}

function localizedTitle(fmt) {
  const title = fmt.title;
  if (title && typeof title === "object") {
    return title[studio.locale] || title.en || fmt.id;
  }
  return title || fmt.id;
}

function renderMakeSelects() {
  const aspect = document.getElementById("make-aspect");
  const previousAspect = aspect.value;
  fillSelect(aspect, [{ value: "", label: t("ui.make.default_option") }].concat(studio.aspects.map((a) => ({ value: a, label: a }))), previousAspect);
  const lang = document.getElementById("make-lang");
  const previousLang = lang.value;
  fillSelect(lang, [{ value: "", label: t("ui.make.default_option") }].concat(studio.locales.map((l) => ({ value: l.code, label: l.name }))), previousLang);
  renderFormatSelect();
}

function renderFormatSelect() {
  const select = document.getElementById("make-format");
  const previous = select.value;
  const options = [{ value: "", label: t("ui.make.format_auto") }];
  for (const fmt of studio.formats) {
    options.push({ value: fmt.id, label: localizedTitle(fmt) + " (" + fmt.id + ")" });
  }
  fillSelect(select, options, previous);
}

function showView(name, focusHeading) {
  for (const view of document.querySelectorAll(".view")) {
    view.hidden = view.id !== "view-" + name;
  }
  for (const tab of document.querySelectorAll(".tab")) {
    if (tab.getAttribute("data-view") === name) {
      tab.setAttribute("aria-current", "page");
    } else {
      tab.removeAttribute("aria-current");
    }
  }
  if (focusHeading) {
    const heading = document.querySelector("#view-" + name + " h2");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus();
    }
  }
}

async function loadProjects() {
  const result = await api("/api/projects");
  studio.projects = result.projects || [];
  renderProjectList();
}

function renderProjectList() {
  const list = document.getElementById("project-list");
  list.replaceChildren();
  if (!studio.projects.length) {
    list.append(el("li", { className: "muted", text: t("ui.projects.empty") }));
    return;
  }
  for (const project of studio.projects) {
    const label = project.id || project.name;
    const button = el("button", {
      type: "button",
      "aria-current": studio.current === project.path ? "true" : "false",
      on: { click: () => runAction(() => openProject(project.path, true)) }
    }, [
      el("span", { text: label }),
      el("span", { className: "sub", text: project.path + " · " + (project.format_id || "reel.json") }),
      el("span", {}, [statusBadge(project.status)])
    ]);
    list.append(el("li", {}, [button]));
  }
}

async function openProject(path, focusTitle) {
  const detail = await api("/api/project?project=" + encodeURIComponent(path));
  studio.current = path;
  studio.detail = detail;
  renderProjectList();
  renderDetail(detail, focusTitle);
  setStatus(t("ui.status.ready"), false);
}

function section(id, titleKey) {
  return el("section", { className: "section", "aria-labelledby": id }, [el("h3", { id: id, text: t(titleKey) })]);
}

function renderDetail(d, focusTitle) {
  const box = document.getElementById("project-detail");
  box.replaceChildren();
  const title = el("h2", { tabindex: "-1", text: (d.timeline && d.timeline.id) || d.id || d.name });
  box.append(title);
  const meta = el("div", { className: "meta" }, [
    el("code", { text: d.path }),
    el("span", { text: t("ui.project.status", { status: d.status || "—" }) }),
    d.format_id ? el("span", { text: t("ui.project.format", { format: d.format_id }) }) : null
  ]);
  if (d.workflow) {
    meta.append(el("span", { text: [d.workflow.aspect, d.workflow.duration_sec ? d.workflow.duration_sec + " s" : "", d.workflow.video_lang].filter(Boolean).join(" · ") }));
  }
  if (d.timeline) {
    meta.append(el("span", { text: d.timeline.width + "×" + d.timeline.height + " · " + d.timeline.fps + " fps · " + d.timeline.frames + " f" }));
  }
  box.append(meta);
  if (d.prompt && d.prompt.text) {
    const promptSection = section("prompt-h", "ui.project.prompt");
    promptSection.append(el("p", { text: d.prompt.text }));
    box.append(promptSection);
  }
  box.append(renderSteps(d));
  box.append(renderScenes(d));
  box.append(renderSnapshots(d));
  box.append(renderVideos(d));
  box.append(renderQc(d));
  if (focusTitle) {
    title.focus();
  }
}

function stepAction(project, stepId, action, instruction) {
  return runAction(async () => {
    const body = { project: project, step_id: stepId, action: action };
    if (instruction) {
      body.instruction = instruction;
    }
    const result = await api("/api/step", body);
    await loadProjects();
    await openProject(project, false);
    setStatus(t("ui.project.status", { status: result.status }), false);
  });
}

function stepLabel(id) {
  return hasString("make.step." + id) ? t("make.step." + id) : id;
}

function renderSteps(d) {
  const box = section("steps-h", "ui.project.steps");
  if (!d.workflow) {
    box.append(el("p", { className: "muted", text: t("ui.project.no_state") }));
    return box;
  }
  const list = el("ol", { className: "steps" });
  for (const step of d.workflow.steps) {
    let stateKey = "ui.step.queued";
    let badgeClass = "badge";
    if (step.pending) {
      stateKey = "ui.step.pending";
      badgeClass = "badge awaiting_approval";
    } else if (step.approved) {
      stateKey = "ui.step.approved";
      badgeClass = "badge completed";
    } else if (step.completed) {
      stateKey = "ui.step.done";
      badgeClass = "badge completed";
    }
    const item = el("li", { className: step.pending ? "step is-pending" : "step", "aria-current": step.current ? "step" : false });
    item.append(el("div", { className: "step-head" }, [
      el("span", { className: "step-title", text: stepLabel(step.id) }),
      el("code", { text: step.id }),
      el("span", { className: badgeClass, text: t(stateKey) }),
      el("span", { className: "muted", text: [step.type, step.profile].filter(Boolean).join(" · ") }),
      step.gate ? el("span", { className: "muted", text: t("ui.step.gate") }) : null
    ]));
    const out = step.output || {};
    const facts = [];
    if (out.artifact) {
      facts.push(out.artifact);
    }
    if (out.frames) {
      facts.push(out.frames + " f");
    }
    if (out.simulated) {
      facts.push("simulated");
    }
    if (out.previews) {
      facts.push(out.previews.length + " png");
    }
    if (facts.length) {
      item.append(el("p", { className: "hint mono", text: facts.join(" · ") }));
    }
    const actions = el("div", { className: "step-actions" });
    if (step.pending) {
      actions.append(el("button", { type: "button", className: "primary", text: t("gate.action.approve"), on: { click: () => stepAction(d.path, step.id, "approve") } }));
      actions.append(el("button", { type: "button", text: t("gate.action.back"), on: { click: () => stepAction(d.path, step.id, "back") } }));
    } else if (step.completed) {
      actions.append(el("button", { type: "button", text: t("ui.step.redo"), on: { click: () => stepAction(d.path, step.id, "back") } }));
    } else if (step.current && !d.workflow.pending_gate && d.workflow.status !== "completed") {
      actions.append(el("button", { type: "button", className: "primary", text: t("ui.step.run"), on: { click: () => stepAction(d.path, step.id, "run") } }));
    }
    if (actions.childNodes.length) {
      item.append(actions);
    }
    if (step.pending || step.completed) {
      const fieldId = "edit-" + step.id;
      const textarea = el("textarea", { id: fieldId, rows: "2", maxlength: "600" });
      const form = el("form", {
        className: "form",
        on: {
          submit: (event) => {
            event.preventDefault();
            const text = textarea.value.trim();
            if (!text) {
              textarea.focus();
              return;
            }
            stepAction(d.path, step.id, "edit", text);
          }
        }
      }, [
        el("label", { className: "hint", for: fieldId, text: t("ui.step.edit_label") }),
        textarea,
        el("div", { className: "actions" }, [el("button", { type: "submit", text: t("ui.step.edit_submit") })])
      ]);
      item.append(form);
    }
    list.append(item);
  }
  box.append(list);
  return box;
}

function isHexColor(value) {
  if (typeof value !== "string" || value.length !== 7 || value[0] !== "#") {
    return false;
  }
  for (const ch of value.slice(1).toLowerCase()) {
    if ("0123456789abcdef".indexOf(ch) < 0) {
      return false;
    }
  }
  return true;
}

function renderScenes(d) {
  const box = section("scenes-h", "ui.project.scenes");
  if (!d.timeline || !d.timeline.scenes.length) {
    box.append(el("p", { className: "muted", text: t("ui.project.no_scenes") }));
    return box;
  }
  const head = el("tr", {}, ["ui.scene.id", "ui.scene.recipe", "ui.scene.frames", "ui.scene.heading", "ui.scene.subheading", "ui.scene.colors"].map((key) => el("th", { scope: "col", text: t(key) })));
  const body = el("tbody");
  for (const scene of d.timeline.scenes) {
    const colors = el("td");
    for (const color of scene.colors) {
      if (isHexColor(color)) {
        const swatch = el("span", { className: "swatch", title: color, "aria-hidden": "true" });
        swatch.style.backgroundColor = color;
        colors.append(swatch);
      }
    }
    colors.append(el("span", { className: "mono", text: scene.colors.join(" ") }));
    body.append(el("tr", {}, [
      el("th", { scope: "row" }, [el("code", { text: scene.id }), scene.locked ? el("span", { className: "badge warn", text: t("ui.scene.locked") }) : null]),
      el("td", { text: scene.recipe + " · " + scene.engine }),
      el("td", { className: "mono", text: scene.frame_range[0] + "–" + scene.frame_range[1] }),
      el("td", { text: scene.heading }),
      el("td", { text: scene.subheading }),
      colors
    ]));
  }
  box.append(el("div", { className: "table-wrap" }, [el("table", {}, [el("thead", {}, [head]), body])]));
  box.append(renderReviseForm(d));
  return box;
}

function renderReviseForm(d) {
  const sceneSelect = el("select", { id: "revise-scene" });
  sceneSelect.append(el("option", { value: "", text: t("ui.revise.all_scenes") }));
  for (const scene of d.timeline.scenes) {
    sceneSelect.append(el("option", { value: scene.id, disabled: scene.locked, text: scene.id + (scene.heading ? " — " + scene.heading : "") }));
  }
  const instruction = el("textarea", { id: "revise-instruction", rows: "3", maxlength: "600", "aria-describedby": "revise-hint" });
  const render = el("input", { id: "revise-render", type: "checkbox" });
  const form = el("form", {
    className: "form",
    on: {
      submit: (event) => {
        event.preventDefault();
        const text = instruction.value.trim();
        if (!text) {
          instruction.focus();
          return;
        }
        runAction(async () => {
          const body = { project: d.path, instruction: text, render: render.checked };
          if (sceneSelect.value) {
            body.scene = sceneSelect.value;
          }
          const result = await api("/api/revise", body);
          await openProject(d.path, false);
          setStatus(t("ui.status.done") + " " + (result.changed_scenes || []).join(", "), false);
        });
      }
    }
  }, [
    el("h4", { text: t("ui.revise.title") }),
    el("label", { className: "field", for: "revise-scene" }, [el("span", { text: t("ui.revise.scene_label") })]),
    sceneSelect,
    el("label", { className: "field", for: "revise-instruction" }, [el("span", { text: t("ui.revise.instruction_label") })]),
    instruction,
    el("p", { id: "revise-hint", className: "hint", text: t("ui.revise.hint") }),
    el("label", { className: "check", for: "revise-render" }, [render, el("span", { text: t("ui.revise.render") })]),
    el("div", { className: "actions" }, [el("button", { type: "submit", className: "primary", text: t("ui.revise.submit") })])
  ]);
  return form;
}

function baseName(path) {
  const name = path.split("/").pop();
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(0, dot) : name;
}

function renderSnapshots(d) {
  const box = section("snapshots-h", "ui.project.snapshots");
  if (!d.snapshots.length) {
    box.append(el("p", { className: "muted", text: t("ui.project.no_snapshots") }));
    return box;
  }
  const grid = el("div", { className: "thumbs" });
  for (const path of d.snapshots) {
    const scene = baseName(path);
    grid.append(el("figure", {}, [
      el("img", { src: mediaUrl(d.path, path), alt: t("ui.project.snapshot_alt", { scene: scene }), loading: "lazy", decoding: "async" }),
      el("figcaption", { text: scene })
    ]));
  }
  box.append(grid);
  return box;
}

function renderVideos(d) {
  const box = section("videos-h", "ui.project.videos");
  if (!d.videos.length) {
    box.append(el("p", { className: "muted", text: t("ui.project.no_videos") }));
    return box;
  }
  const grid = el("div", { className: "videos" });
  for (const video of d.videos) {
    const megabytes = (video.bytes / 1048576).toFixed(1);
    grid.append(el("figure", {}, [
      el("video", { src: mediaUrl(d.path, video.path), controls: true, preload: "metadata", playsinline: true, "aria-label": video.path }),
      el("figcaption", { text: video.path + " · " + megabytes + " MiB" })
    ]));
  }
  box.append(grid);
  return box;
}

function renderQc(d) {
  const box = section("qc-h", "ui.project.qc");
  if (!d.qc.length) {
    box.append(el("p", { className: "muted", text: t("ui.project.no_qc") }));
    return box;
  }
  for (const report of d.qc) {
    const statusKey = "qc.status." + report.technical_status;
    box.append(el("h4", {}, [report.profile + " ", statusBadge(report.technical_status)]));
    if (hasString(statusKey)) {
      box.append(el("p", { className: "hint", text: t(statusKey) }));
    }
    const head = el("tr", {}, ["ui.qc.check", "ui.qc.result", "ui.qc.observed"].map((key) => el("th", { scope: "col", text: t(key) })));
    const body = el("tbody");
    for (const check of report.checks) {
      body.append(el("tr", {}, [
        el("th", { scope: "row" }, [el("code", { text: check.id })]),
        el("td", {}, [statusBadge(check.status)]),
        el("td", { className: "mono", text: check.observed })
      ]));
    }
    box.append(el("div", { className: "table-wrap" }, [el("table", {}, [el("thead", {}, [head]), body])]));
  }
  return box;
}

async function loadFormats() {
  const result = await api("/api/formats");
  studio.formats = result.formats || [];
  renderFormats();
  renderFormatSelect();
}

function chips(values) {
  return el("div", { className: "chips" }, (values || []).map((value) => el("span", { className: "badge", text: value })));
}

function renderFormats() {
  const grid = document.getElementById("format-grid");
  grid.replaceChildren();
  if (!studio.formats.length) {
    grid.append(el("p", { className: "muted", text: t("ui.formats.empty") }));
    return;
  }
  for (const fmt of studio.formats) {
    const duration = fmt.duration_sec ? t("ui.format.duration_range", { min: fmt.duration_sec.min, max: fmt.duration_sec.max }) : "—";
    const steps = (fmt.steps || []).map((s) => stepLabel(s.id) + (s.gate ? " ✓" : ""));
    const rows = [
      ["ui.format.category", el("span", { text: fmt.category })],
      ["ui.format.aspect", chips(fmt.aspect)],
      ["ui.format.duration", el("span", { text: duration })],
      ["ui.format.needs", chips(fmt.needs)],
      ["ui.format.engines", chips(fmt.engines)],
      ["ui.format.languages", chips(fmt.languages)],
      ["ui.format.steps", el("span", { text: steps.join(" → ") })]
    ];
    const list = el("dl");
    for (const row of rows) {
      list.append(el("dt", { text: t(row[0]) }));
      list.append(el("dd", {}, [row[1]]));
    }
    grid.append(el("article", { className: "panel format-card", "aria-labelledby": "fmt-" + fmt.id }, [
      el("h3", { id: "fmt-" + fmt.id, text: localizedTitle(fmt) }),
      el("p", { className: "muted mono", text: fmt.id + " · v" + fmt.version }),
      list,
      el("button", {
        type: "button",
        className: "primary",
        text: t("ui.format.use"),
        on: {
          click: () => {
            renderFormatSelect();
            document.getElementById("make-format").value = fmt.id;
            showView("new", false);
            document.getElementById("make-prompt").focus();
          }
        }
      })
    ]));
  }
}

function readInt(id) {
  const raw = document.getElementById(id).value.trim();
  if (!raw) {
    return undefined;
  }
  const value = Number(raw);
  return Number.isInteger(value) ? value : raw;
}

function renderBudget(result) {
  const box = document.getElementById("make-result");
  box.replaceChildren();
  const budget = result.budget || {};
  const list = el("dl");
  const entries = [
    ["format_id", result.format_id],
    ["provider", result.provider],
    ["scenes", budget.scenes],
    ["frames", budget.frames],
    ["fps", budget.fps],
    ["duration_sec", budget.duration_sec],
    ["draft_resolution", (budget.draft_resolution || []).join("×")],
    ["production_resolution", (budget.production_resolution || []).join("×")],
    ["estimated_draft_sec", budget.estimated_draft_sec],
    ["estimated_hero_sec", budget.estimated_hero_sec],
    ["estimated_cache_mib", budget.estimated_cache_mib],
    ["engines_required", (budget.engines_required || []).join(", ")],
    ["approval_gates", (budget.approval_gates || []).map(stepLabel).join(" → ")]
  ];
  for (const entry of entries) {
    list.append(el("dt", {}, [el("code", { text: entry[0] })]));
    list.append(el("dd", { text: entry[1] === undefined ? "—" : String(entry[1]) }));
  }
  box.append(el("h3", { tabindex: "-1", text: t("ui.make.budget_title") }), list);
  box.firstChild.focus();
}

function submitMake(event) {
  event.preventDefault();
  const submitter = event.submitter;
  const create = Boolean(submitter && submitter.getAttribute("data-mode") === "create");
  const promptField = document.getElementById("make-prompt");
  const prompt = promptField.value.trim();
  if (!prompt) {
    promptField.setAttribute("aria-invalid", "true");
    promptField.focus();
    return;
  }
  promptField.removeAttribute("aria-invalid");
  const body = { prompt: prompt, dry_run: !create };
  const formatId = document.getElementById("make-format").value;
  const aspect = document.getElementById("make-aspect").value;
  const lang = document.getElementById("make-lang").value;
  const name = document.getElementById("make-name").value.trim();
  const duration = readInt("make-duration");
  const seed = readInt("make-seed");
  if (formatId) {
    body.format_id = formatId;
  }
  if (aspect) {
    body.aspect = aspect;
  }
  if (lang) {
    body.lang = lang;
  }
  if (duration !== undefined) {
    body.duration = duration;
  }
  if (seed !== undefined) {
    body.seed = seed;
  }
  if (create && name) {
    body.name = name;
  }
  runAction(async () => {
    const result = await api("/api/make", body);
    if (!create) {
      renderBudget(result);
      setStatus(t("ui.status.done"), false);
      return;
    }
    document.getElementById("make-result").replaceChildren();
    await loadProjects();
    showView("projects", false);
    await openProject(result.project, true);
    setStatus(t("ui.make.created", { project: result.project }), false);
  });
}

function wireTabs() {
  const tabs = Array.from(document.querySelectorAll(".tab"));
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => showView(tab.getAttribute("data-view"), true));
    tab.addEventListener("keydown", (event) => {
      let next = -1;
      if (event.key === "ArrowRight") {
        next = (index + 1) % tabs.length;
      } else if (event.key === "ArrowLeft") {
        next = (index - 1 + tabs.length) % tabs.length;
      } else if (event.key === "Home") {
        next = 0;
      } else if (event.key === "End") {
        next = tabs.length - 1;
      }
      if (next >= 0) {
        event.preventDefault();
        tabs[next].focus();
      }
    });
  });
}

async function changeLanguage(code) {
  await loadSession(code);
  renderProjectList();
  renderFormats();
  if (studio.detail) {
    renderDetail(studio.detail, false);
  }
  setStatus(t("ui.status.ready"), false);
}

async function init() {
  const meta = document.querySelector("meta[name=\"reelsyntax-csrf\"]");
  if (meta) {
    studio.token = meta.getAttribute("content") || "";
  }
  setStatus("…", false);
  await loadSession(document.documentElement.lang);
  setStatus(t("ui.status.loading"), false);
  wireTabs();
  document.getElementById("refresh-projects").addEventListener("click", () => runAction(async () => {
    await loadProjects();
    if (studio.current) {
      await openProject(studio.current, false);
    }
    setStatus(t("ui.status.ready"), false);
  }));
  document.getElementById("lang-select").addEventListener("change", (event) => {
    changeLanguage(event.target.value).catch(showError);
  });
  document.getElementById("make-form").addEventListener("submit", submitMake);
  await Promise.all([loadProjects(), loadFormats()]);
  setStatus(t("ui.status.ready"), false);
}

document.addEventListener("DOMContentLoaded", () => {
  init().catch(showError);
});
