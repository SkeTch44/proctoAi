// src/pages/AdminPages/CodingProblemManager.jsx
// Admin: list, create, edit, archive coding problems.
import React, { useEffect, useMemo, useState } from "react";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

const DIFFICULTIES = ["easy", "medium", "hard", "expert"];
const LANGS = ["python", "javascript", "cpp", "c", "java"];

const empty = () => ({
  title: "",
  description: "",
  difficulty: "medium",
  constraints: "",
  tags: "",
  time_limit_ms: 2000,
  memory_limit_kb: 256000,
  starter_code: { python: "" },
  test_cases: [{ input: "", expected: "", is_sample: true, weight: 1.0 }],
});

export default function CodingProblemManager() {
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null); // null | {id?, ...form}
  const [saving, setSaving] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/coding/problems`, {
        headers: getAuthHeader(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProblems(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const startCreate = () => setEditing(empty());

  const startEdit = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/coding/admin/problems/${id}`, {
        headers: getAuthHeader(),
      });
      if (!res.ok) throw new Error("Failed to load problem");
      const p = await res.json();
      setEditing({
        id: p.id,
        title: p.title,
        description: p.description,
        difficulty: p.difficulty,
        constraints: p.constraints || "",
        tags: (p.tags || []).join(", "),
        time_limit_ms: p.time_limit_ms,
        memory_limit_kb: p.memory_limit_kb,
        starter_code: p.starter_code && Object.keys(p.starter_code).length ? p.starter_code : { python: "" },
        test_cases:
          p.test_cases && p.test_cases.length
            ? p.test_cases
            : [{ input: "", expected: "", is_sample: true, weight: 1.0 }],
      });
    } catch (e) {
      alert(e.message);
    }
  };

  const archive = async (id) => {
    if (!window.confirm("Archive this problem? Students won't see it anymore.")) return;
    const res = await fetch(`${API_BASE}/api/v1/coding/admin/problems/${id}`, {
      method: "DELETE",
      headers: getAuthHeader(),
    });
    if (res.ok) refresh();
    else alert("Archive failed");
  };

  const save = async () => {
    if (!editing.title.trim() || !editing.description.trim()) {
      alert("Title and description required");
      return;
    }
    setSaving(true);
    try {
      const body = {
        title: editing.title,
        description: editing.description,
        difficulty: editing.difficulty,
        constraints: editing.constraints,
        tags: editing.tags.split(",").map((t) => t.trim()).filter(Boolean),
        time_limit_ms: parseInt(editing.time_limit_ms),
        memory_limit_kb: parseInt(editing.memory_limit_kb),
        starter_code: editing.starter_code,
        test_cases: editing.test_cases.map((tc) => ({
          input: tc.input,
          expected: tc.expected,
          is_sample: !!tc.is_sample,
          weight: parseFloat(tc.weight) || 1.0,
        })),
      };

      const url = editing.id
        ? `${API_BASE}/api/v1/coding/admin/problems/${editing.id}`
        : `${API_BASE}/api/v1/coding/admin/problems`;
      const method = editing.id ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Save failed");

      setEditing(null);
      refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Coding Problems</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Create and manage DSA problems for the coding room.
          </p>
        </div>
        <button
          onClick={startCreate}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow"
        >
          + New Problem
        </button>
      </div>

      {loading && <div className="text-gray-400">Loading...</div>}
      {error && (
        <div className="p-4 rounded-xl bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-200">
          {error}
        </div>
      )}

      <div className="grid gap-3">
        {problems.map((p) => (
          <div
            key={p.id}
            className="bg-white dark:bg-[#171A1D] border border-gray-200 dark:border-[#374151] rounded-2xl p-4 shadow flex justify-between items-center"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">#{p.id}</span>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  {p.title}
                </h3>
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                  {p.difficulty}
                </span>
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {(p.tags || []).map((t) => (
                  <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                    {t}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => startEdit(p.id)}
                className="px-3 py-1.5 text-xs font-bold rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Edit
              </button>
              <button
                onClick={() => archive(p.id)}
                className="px-3 py-1.5 text-xs font-bold rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200"
              >
                Archive
              </button>
            </div>
          </div>
        ))}
        {!loading && problems.length === 0 && (
          <div className="text-center py-10 text-gray-500 dark:text-gray-400">
            No problems yet. Create your first one.
          </div>
        )}
      </div>

      {editing && (
        <Editor
          form={editing}
          setForm={setEditing}
          onSave={save}
          onCancel={() => setEditing(null)}
          saving={saving}
        />
      )}
    </div>
  );
}

function Editor({ form, setForm, onSave, onCancel, saving }) {
  const langs = useMemo(() => Object.keys(form.starter_code || {}), [form.starter_code]);

  const updateLangCode = (lang, value) => {
    setForm({ ...form, starter_code: { ...form.starter_code, [lang]: value } });
  };
  const addLang = (l) => {
    if (!form.starter_code[l]) {
      setForm({ ...form, starter_code: { ...form.starter_code, [l]: "" } });
    }
  };

  const updateTC = (i, key, value) => {
    const next = [...form.test_cases];
    next[i] = { ...next[i], [key]: value };
    setForm({ ...form, test_cases: next });
  };
  const addTC = () => {
    setForm({
      ...form,
      test_cases: [
        ...form.test_cases,
        { input: "", expected: "", is_sample: false, weight: 1.0 },
      ],
    });
  };
  const removeTC = (i) => {
    if (form.test_cases.length === 1) return;
    setForm({ ...form, test_cases: form.test_cases.filter((_, idx) => idx !== i) });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white dark:bg-[#1A1D21] rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            {form.id ? "Edit Problem" : "Create New Problem"}
          </h2>

          <Field label="Title">
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
            />
          </Field>

          <div className="grid grid-cols-3 gap-3">
            <Field label="Difficulty">
              <select
                value={form.difficulty}
                onChange={(e) => setForm({ ...form, difficulty: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
              >
                {DIFFICULTIES.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </Field>
            <Field label="Time (ms)">
              <input
                type="number"
                value={form.time_limit_ms}
                onChange={(e) => setForm({ ...form, time_limit_ms: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
              />
            </Field>
            <Field label="Memory (KB)">
              <input
                type="number"
                value={form.memory_limit_kb}
                onChange={(e) => setForm({ ...form, memory_limit_kb: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
              />
            </Field>
          </div>

          <Field label="Tags (comma-separated)">
            <input
              type="text"
              value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.target.value })}
              placeholder="array, hash-table"
              className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
            />
          </Field>

          <Field label="Description (Markdown / plain text)">
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={6}
              className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100 font-mono text-sm"
            />
          </Field>

          <Field label="Constraints">
            <input
              type="text"
              value={form.constraints}
              onChange={(e) => setForm({ ...form, constraints: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100"
            />
          </Field>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-bold text-gray-700 dark:text-gray-200">Starter Code</label>
              <select
                onChange={(e) => { if (e.target.value) addLang(e.target.value); e.target.value = ""; }}
                className="px-2 py-1 text-xs rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115]"
              >
                <option value="">+ Add language...</option>
                {LANGS.filter((l) => !langs.includes(l)).map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              {langs.map((l) => (
                <div key={l}>
                  <div className="text-xs text-gray-500 mb-1">{l}</div>
                  <textarea
                    value={form.starter_code[l] || ""}
                    onChange={(e) => updateLangCode(l, e.target.value)}
                    rows={5}
                    className="w-full px-3 py-2 rounded-lg border dark:border-gray-700 bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100 font-mono text-xs"
                  />
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-bold text-gray-700 dark:text-gray-200">Test Cases</label>
              <button onClick={addTC} className="px-3 py-1 text-xs rounded-lg bg-gray-200 dark:bg-gray-700">+ Add</button>
            </div>
            <div className="space-y-3">
              {form.test_cases.map((tc, i) => (
                <div key={i} className="border dark:border-gray-700 rounded-lg p-3 bg-gray-50 dark:bg-[#0f1115]">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Input</div>
                      <textarea
                        value={tc.input}
                        onChange={(e) => updateTC(i, "input", e.target.value)}
                        rows={3}
                        className="w-full px-2 py-1 rounded border dark:border-gray-700 bg-white dark:bg-[#1a1d21] font-mono text-xs"
                      />
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Expected</div>
                      <textarea
                        value={tc.expected}
                        onChange={(e) => updateTC(i, "expected", e.target.value)}
                        rows={3}
                        className="w-full px-2 py-1 rounded border dark:border-gray-700 bg-white dark:bg-[#1a1d21] font-mono text-xs"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <label className="flex items-center gap-1 text-xs">
                      <input
                        type="checkbox"
                        checked={!!tc.is_sample}
                        onChange={(e) => updateTC(i, "is_sample", e.target.checked)}
                      />
                      Visible to student
                    </label>
                    <label className="flex items-center gap-1 text-xs">
                      Weight:
                      <input
                        type="number"
                        step="0.1"
                        value={tc.weight}
                        onChange={(e) => updateTC(i, "weight", e.target.value)}
                        className="w-16 px-1 py-0.5 rounded border dark:border-gray-700 bg-white dark:bg-[#1a1d21]"
                      />
                    </label>
                    <button
                      onClick={() => removeTC(i)}
                      className="ml-auto text-xs text-red-500 hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t dark:border-gray-700 px-6 py-4 flex justify-end gap-3 bg-gray-50 dark:bg-[#0f1115] rounded-b-2xl">
          <button
            onClick={onCancel}
            className="px-5 py-2 rounded-xl bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-bold"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving}
            className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold disabled:opacity-50"
          >
            {saving ? "Saving..." : form.id ? "Save Changes" : "Create Problem"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-bold text-gray-700 dark:text-gray-200 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}
