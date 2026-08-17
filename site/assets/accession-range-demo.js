(function () {
  "use strict";

  const root = document.querySelector("[data-accession-demo]");
  if (!root) return;

  const form = root.querySelector("[data-accession-form]");
  const input = form.elements.accession;
  const status = root.querySelector("[data-edge-status]");
  const results = root.querySelector("[data-edge-results]");
  const languageButtons = Array.from(document.querySelectorAll("[data-language-choice]"));
  let currentPayload = null;
  let currentLanguage = "en";

  const messages = {
    en: {
      pageTitle: "Search genome datasets · BTED",
      ready: "Enter an accession to begin.",
      loading: "Searching for {accession}…",
      found: "Found {sources} source datasets and {records} transcript 3′-end records.",
      error: "No data were found for this accession. Check the accession and try again.",
      institution: "Lead institution",
      laboratory: "Laboratory / department",
      correspondingAuthor: "Corresponding author",
      culture: "Culture",
      sampling: "Sampling",
      sequencing: "Sequencing",
      replicates: "Biological replicates",
      submitter: "ENA submitting center",
      facility: "Sequencing facility",
      endpointSet: "Endpoint set",
      publication: "Publication",
      rawData: "Raw sequencing",
      details: "Dataset record",
      authorEndpoint: "author-called endpoints",
      curatedRecord: "literature-curated records",
      auditOnly: "metadata records",
    },
    zh: {
      pageTitle: "检索基因组数据集 · BTED",
      ready: "输入登录号开始检索。",
      loading: "正在检索 {accession}…",
      found: "已找到 {sources} 个来源数据集和 {records} 条转录本 3′ 端记录。",
      error: "未找到该登录号对应的数据，请检查后重试。",
      institution: "主要研究单位",
      laboratory: "实验室 / 院系",
      correspondingAuthor: "通讯作者",
      culture: "培养条件",
      sampling: "采样设计",
      sequencing: "测序信息",
      replicates: "生物学重复",
      submitter: "ENA 提交中心",
      facility: "测序机构",
      endpointSet: "端点数据",
      publication: "论文",
      rawData: "原始测序",
      details: "数据集详情",
      authorEndpoint: "个作者定义端点",
      curatedRecord: "条文献整理记录",
      auditOnly: "条元数据记录",
    },
  };

  function message(key, values = {}) {
    let output = messages[currentLanguage][key];
    Object.entries(values).forEach(([name, value]) => {
      output = output.replace(`{${name}}`, String(value));
    });
    return output;
  }

  function locale() {
    return currentLanguage === "zh" ? "zh-CN" : "en-US";
  }

  function formatNumber(value) {
    return Number(value).toLocaleString(locale());
  }

  function formatGenomeSize(value) {
    return `${(Number(value) / 1_000_000).toLocaleString(locale(), {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} Mb`;
  }

  function localized(object, key) {
    if (!object) return "—";
    if (currentLanguage === "zh" && object[`${key}_zh`]) return object[`${key}_zh`];
    return object[key] || "—";
  }

  function setText(selector, value) {
    root.querySelector(selector).textContent = value;
  }

  function evidenceLabel(value) {
    const labels = {
      author_called_endpoint: "authorEndpoint",
      curated_record: "curatedRecord",
      audit_only: "auditOnly",
    };
    return labels[value] ? message(labels[value]) : value.replaceAll("_", " ");
  }

  function addFact(list, label, value) {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value || "—";
    item.append(term, description);
    list.appendChild(item);
  }

  function actionLink(label, href, external = false) {
    const link = document.createElement("a");
    link.className = "study-link";
    link.href = href;
    link.textContent = label;
    if (external) {
      link.target = "_blank";
      link.rel = "noopener";
    }
    return link;
  }

  function renderStudyCards(tracks) {
    const list = root.querySelector("[data-edge-study-cards]");
    list.replaceChildren();
    tracks.forEach((track) => {
      const context = track.study_context || {};
      const card = document.createElement("article");
      card.className = "study-context-card";

      const header = document.createElement("header");
      const meta = document.createElement("div");
      meta.className = "study-card-meta";
      const role = document.createElement("span");
      role.className = "study-role";
      role.textContent = localized(context, "source_role");
      const identity = document.createElement("span");
      identity.textContent = `${track.source_id} · ${track.publication_year}`;
      meta.append(role, identity);
      const title = document.createElement("h3");
      title.textContent = track.paper_title || track.name;
      const relationship = document.createElement("p");
      relationship.textContent = localized(context, "data_relationship");
      header.append(meta, title, relationship);

      const institution = document.createElement("section");
      institution.className = "study-institution";
      const institutionLabel = document.createElement("span");
      institutionLabel.textContent = message("institution");
      const institutionName = document.createElement("strong");
      institutionName.textContent = context.lead_institution || "—";
      const laboratory = document.createElement("p");
      laboratory.textContent = context.lead_laboratory || "—";
      const location = document.createElement("small");
      location.textContent = `${localized(context, "country")} · ${message("correspondingAuthor")}: ${context.corresponding_author || "—"}`;
      institution.append(institutionLabel, institutionName, laboratory, location);

      const facts = document.createElement("dl");
      facts.className = "study-facts";
      addFact(facts, message("culture"), localized(context, "culture_condition"));
      addFact(facts, message("sampling"), localized(context, "sampling_scheme"));
      addFact(facts, message("sequencing"), `${context.sequencing_platform || "—"} · ${localized(context, "read_layout")}`);
      addFact(facts, message("replicates"), formatNumber(context.biological_replicates || 0));
      addFact(facts, message("submitter"), context.ena_submitting_center || "—");
      addFact(facts, message("facility"), localized(context, "sequencing_facility"));
      addFact(facts, message("endpointSet"), `${formatNumber(track.record_count)} ${evidenceLabel(track.evidence_class)}`);

      const footer = document.createElement("footer");
      footer.append(
        actionLink(`${message("publication")} · PMID ${track.pmid}`, track.publication_url, true),
        actionLink(`${message("rawData")} · ${track.raw_data_accession}`, track.raw_data_url, true),
        actionLink(message("details"), track.record_url || `records/${encodeURIComponent(track.source_id)}.html`),
      );

      card.append(header, institution, facts, footer);
      list.appendChild(card);
    });
  }

  function renderInterpretations(tracks) {
    const list = root.querySelector("[data-edge-interpretations]");
    list.replaceChildren();
    tracks.forEach((track) => {
      const item = document.createElement("li");
      const source = document.createElement("strong");
      source.textContent = `${track.source_id}: `;
      const note = document.createElement("span");
      note.textContent = currentLanguage === "zh"
        ? (track.interpretation_note_zh || track.interpretation_note)
        : track.interpretation_note;
      item.append(source, note);
      list.appendChild(item);
    });
  }

  function render(payload) {
    currentPayload = payload;
    setText("[data-edge-scientific-name]", payload.assembly.scientific_name || payload.assembly.display_name);
    setText("[data-edge-strain]", payload.assembly.strain || "");
    setText("[data-edge-assembly]", payload.assembly.accession);
    setText("[data-edge-reference]", payload.assembly.reference_name);
    setText("[data-edge-genome-size]", formatGenomeSize(payload.assembly.reference_length));
    setText("[data-edge-replicons]", formatNumber(payload.assembly.replicon_count || 1));
    setText("[data-edge-tracks]", formatNumber(payload.tracks.length));
    setText("[data-edge-records]", formatNumber(payload.record_count));
    setText("[data-edge-relationship]", currentLanguage === "zh"
      ? payload.assembly.source_relationship_note_zh
      : payload.assembly.source_relationship_note);
    renderStudyCards(payload.tracks);
    renderInterpretations(payload.tracks);

    root.querySelector("[data-edge-shared-raw]").href = payload.tracks[0].raw_data_url;
    root.querySelector("[data-edge-jbrowse]").href =
      `jbrowse/index.html?config=${encodeURIComponent(payload.jbrowse_config_url)}`;
    root.querySelector("[data-edge-assembly-page]").href =
      `assemblies/${encodeURIComponent(payload.assembly.accession)}.html`;
    root.querySelector("[data-edge-bed]").href =
      `downloads/assemblies/${encodeURIComponent(payload.assembly.accession)}/endpoints.bed`;
    root.querySelector("[data-edge-metadata]").href =
      `downloads/assemblies/${encodeURIComponent(payload.assembly.accession)}/metadata.json`;
    results.hidden = false;
  }

  function applyLanguage(language, persist = true) {
    currentLanguage = language === "zh" ? "zh" : "en";
    document.documentElement.lang = currentLanguage === "zh" ? "zh-CN" : "en";
    document.title = message("pageTitle");
    document.querySelectorAll("[data-lang-en][data-lang-zh]").forEach((element) => {
      element.textContent = currentLanguage === "zh" ? element.dataset.langZh : element.dataset.langEn;
    });
    document.querySelectorAll("[data-placeholder-en][data-placeholder-zh]").forEach((element) => {
      element.placeholder = currentLanguage === "zh" ? element.dataset.placeholderZh : element.dataset.placeholderEn;
    });
    languageButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.languageChoice === currentLanguage));
    });
    if (persist) window.localStorage.setItem("bted-language", currentLanguage);
    if (currentPayload) {
      render(currentPayload);
      status.textContent = message("found", {
        sources: formatNumber(currentPayload.tracks.length),
        records: formatNumber(currentPayload.record_count),
      });
    } else {
      status.textContent = message("ready");
    }
  }

  async function resolveAccession(accession) {
    status.className = "edge-query-status loading";
    status.textContent = message("loading", { accession });
    results.hidden = true;
    try {
      const response = await fetch(`api/assemblies/${encodeURIComponent(accession)}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const payload = await response.json();
      render(payload);
      status.className = "edge-query-status success";
      status.textContent = message("found", {
        sources: formatNumber(payload.tracks.length),
        records: formatNumber(payload.record_count),
      });
      const url = new URL(window.location.href);
      url.searchParams.set("accession", accession);
      url.searchParams.set("lang", currentLanguage);
      window.history.replaceState({}, "", url);
    } catch (error) {
      currentPayload = null;
      status.className = "edge-query-status error";
      status.textContent = message("error");
      console.error(error);
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const accession = input.value.trim();
    if (accession) resolveAccession(accession);
  });

  languageButtons.forEach((button) => {
    button.addEventListener("click", () => {
      applyLanguage(button.dataset.languageChoice);
      const url = new URL(window.location.href);
      url.searchParams.set("lang", currentLanguage);
      window.history.replaceState({}, "", url);
    });
  });

  const parameters = new URLSearchParams(window.location.search);
  const requestedLanguage = parameters.get("lang") || window.localStorage.getItem("bted-language") || "en";
  applyLanguage(requestedLanguage, false);
  input.value = parameters.get("accession") || root.dataset.defaultAccession;
  resolveAccession(input.value);
})();
