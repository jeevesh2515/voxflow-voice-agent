"use client";

import { useState, useEffect, useRef } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  Download,
  AlertCircle,
  CheckCircle2,
  X,
  Boxes,
  Users,
  ShoppingCart,
  Truck,
  Package,
  Layers,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export type EntityType = "products" | "stock" | "suppliers" | "orders" | "shipments";

interface CsvImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialEntity?: EntityType;
  onSuccess?: () => void;
}

const ENTITY_CONFIG: Record<
  EntityType,
  { label: string; icon: any; color: string; desc: string }
> = {
  products: {
    label: "Products & SKUs",
    icon: Package,
    color: "#00ffcc",
    desc: "SKUs, names, pack sizes, categories, and retail MRPs",
  },
  stock: {
    label: "Warehouse Stock",
    icon: Boxes,
    color: "#00f0ff",
    desc: "Bin inventory quantities and warehouse distribution",
  },
  suppliers: {
    label: "Suppliers & Contacts",
    icon: Users,
    color: "#ff2d78",
    desc: "Contact book, verified phone numbers, and PIN codes",
  },
  orders: {
    label: "Purchase Orders",
    icon: ShoppingCart,
    color: "#ffb800",
    desc: "Customer & vendor PO numbers, line items, and dispatch notes",
  },
  shipments: {
    label: "Shipments & Logistics",
    icon: Truck,
    color: "#a855f7",
    desc: "Logistics carriers, tracking IDs, and delivery ETAs",
  },
};

export default function CsvImportModal({
  isOpen,
  onClose,
  initialEntity = "products",
  onSuccess,
}: CsvImportModalProps) {
  const { activeTenantId } = useTenant();
  const [selectedEntity, setSelectedEntity] = useState<EntityType>(initialEntity);
  const [file, setFile] = useState<File | null>(null);
  const [rawText, setRawText] = useState("");
  const [useRawInput, setUseRawInput] = useState(false);
  const [mode, setMode] = useState<"upsert" | "strict">("upsert");
  const [isDragging, setIsDragging] = useState(false);

  // Validation & import state
  const [validating, setValidating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    total_rows: number;
    valid_rows: number;
    error_count: number;
    errors: Array<{ row_number: number; column: string; message: string; raw_value?: string }>;
    preview: Array<Record<string, any>>;
    headers: string[];
    is_valid: boolean;
  } | null>(null);
  const [importSuccess, setImportSuccess] = useState<{
    inserted: number;
    updated: number;
    total: number;
    message: string;
  } | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialEntity) {
      setSelectedEntity(initialEntity);
    }
  }, [initialEntity, isOpen]);

  // Reset state when modal opens or entity changes
  const resetUploadState = () => {
    setFile(null);
    setRawText("");
    setValidationResult(null);
    setImportSuccess(null);
    setApiError(null);
  };

  const handleEntityChange = (entity: EntityType) => {
    setSelectedEntity(entity);
    resetUploadState();
  };

  const handleFileSelect = (selectedFile: File) => {
    if (!selectedFile.name.endsWith(".csv") && selectedFile.type !== "text/csv") {
      setApiError("Please select a valid CSV file (.csv)");
      return;
    }
    setFile(selectedFile);
    setApiError(null);
    setImportSuccess(null);

    // Read content for instant validation preview
    const reader = new FileReader();
    reader.onload = async (e) => {
      const text = e.target?.result as string;
      if (text) {
        setRawText(text);
        await runValidation(text);
      }
    };
    reader.readAsText(selectedFile);
  };

  const runValidation = async (textToValidate: string) => {
    if (!textToValidate.trim()) {
      setValidationResult(null);
      return;
    }
    setValidating(true);
    setApiError(null);
    try {
      const res = await api.validateCsvImport(selectedEntity, textToValidate, activeTenantId);
      setValidationResult(res);
    } catch (err: any) {
      setApiError(err.message || "Failed to validate CSV");
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!validationResult || !validationResult.is_valid) return;
    setImporting(true);
    setApiError(null);
    try {
      let res;
      if (file && !useRawInput) {
        res = await api.importCsvFile(selectedEntity, file, mode, activeTenantId);
      } else {
        res = await api.importCsvText(selectedEntity, rawText, mode, activeTenantId);
      }

      if (res.success) {
        setImportSuccess({
          inserted: res.inserted,
          updated: res.updated,
          total: res.total_processed,
          message: res.message,
        });
        if (onSuccess) {
          onSuccess();
        }
      } else {
        setApiError(res.message || "Import failed");
      }
    } catch (err: any) {
      setApiError(err.message || "Server error occurred during import");
    } finally {
      setImporting(false);
    }
  };

  if (!isOpen) return null;

  const currentConfig = ENTITY_CONFIG[selectedEntity];
  const IconComponent = currentConfig.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 backdrop-blur-md bg-black/75 animate-fade-in">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl bg-[#0e0a1a] border border-[#302840] shadow-[0_25px_60px_rgba(0,0,0,0.85)] overflow-hidden">
        {/* Ambient Top Glow */}
        <div
          className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-40 blur-[100px] opacity-30 pointer-events-none"
          style={{ backgroundColor: currentConfig.color }}
        />

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#302840]/60 bg-[#140f24]/80 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            <div
              className="p-2.5 rounded-xl border border-white/10 shadow-lg"
              style={{ backgroundColor: `${currentConfig.color}15`, color: currentConfig.color }}
            >
              <IconComponent size={20} />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#f0ecf8] flex items-center gap-2">
                Bulk Company Data Ingestion
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#00ffcc]">
                  CSV Engine
                </span>
              </h2>
              <p className="text-xs text-[#a098b0]">
                Populate your voice agent's real-time knowledge base with transactional guarantees
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[#a098b0] hover:text-white hover:bg-white/5 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Entity Selector Tabs */}
        <div className="px-6 pt-3 pb-2 border-b border-[#302840]/40 bg-[#0a0712]/60 overflow-x-auto">
          <div className="flex items-center gap-2 min-w-max">
            {(Object.keys(ENTITY_CONFIG) as EntityType[]).map((key) => {
              const cfg = ENTITY_CONFIG[key];
              const TabIcon = cfg.icon;
              const isSelected = selectedEntity === key;
              return (
                <button
                  key={key}
                  onClick={() => handleEntityChange(key)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isSelected
                      ? "bg-[#251e38] text-white border border-white/20 shadow-md"
                      : "text-[#8a809e] hover:text-[#e0d8f0] hover:bg-white/5"
                  }`}
                >
                  <TabIcon size={14} style={{ color: isSelected ? cfg.color : undefined }} />
                  {cfg.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar">
          {/* Template Bar */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3.5 rounded-xl bg-[#140f24] border border-[#302840]/60 gap-3">
            <div className="flex items-center gap-3">
              <FileSpreadsheet size={18} className="text-[#00ffcc]" />
              <div>
                <div className="text-xs font-semibold text-[#f0ecf8]">
                  {currentConfig.label} Template
                </div>
                <div className="text-[11px] text-[#a098b0]">{currentConfig.desc}</div>
              </div>
            </div>
            <a
              href={api.getCsvTemplateUrl(selectedEntity)}
              download={`${selectedEntity}_template.csv`}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#00ffcc]/10 hover:bg-[#00ffcc]/20 border border-[#00ffcc]/30 text-[#00ffcc] text-xs font-medium transition-colors"
            >
              <Download size={13} />
              Download CSV Template
            </a>
          </div>

          {/* Import Success State */}
          {importSuccess && (
            <div className="p-4 rounded-xl bg-[#00ffcc]/10 border border-[#00ffcc]/40 text-[#00ffcc] flex items-start gap-3 animate-fade-in">
              <CheckCircle2 size={20} className="shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="text-xs font-bold uppercase tracking-wider">
                  Ingestion Completed Successfully
                </h4>
                <p className="text-xs text-[#e0fcf5] mt-1">{importSuccess.message}</p>
                <div className="flex items-center gap-4 mt-2.5 text-xs font-mono">
                  <span className="px-2 py-0.5 rounded bg-[#00ffcc]/20">
                    Inserted: {importSuccess.inserted}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#00f0ff]/20 text-[#00f0ff]">
                    Updated: {importSuccess.updated}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-white/10 text-white">
                    Total: {importSuccess.total}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* API / Server Error Alert */}
          {apiError && (
            <div className="p-4 rounded-xl bg-[#ff2d78]/10 border border-[#ff2d78]/40 text-[#ff2d78] flex items-start gap-3 animate-shake">
              <AlertCircle size={20} className="shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="text-xs font-bold uppercase tracking-wider">Ingestion Error</h4>
                <p className="text-xs text-[#ffd6e6] mt-1 whitespace-pre-wrap">{apiError}</p>
              </div>
            </div>
          )}

          {/* Upload Method Switcher */}
          {!importSuccess && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-label uppercase tracking-wider text-[#a098b0]">
                  {useRawInput ? "Paste CSV Content" : "Upload CSV File"}
                </label>
                <button
                  type="button"
                  onClick={() => setUseRawInput(!useRawInput)}
                  className="text-[11px] text-[#00ffcc] hover:underline flex items-center gap-1 font-mono"
                >
                  <Layers size={11} />
                  {useRawInput ? "Switch to Drag & Drop Upload" : "Switch to Raw CSV Editor"}
                </button>
              </div>

              {!useRawInput ? (
                /* Drag and Drop Zone */
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDragging(false);
                    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                      handleFileSelect(e.dataTransfer.files[0]);
                    }
                  }}
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
                    isDragging
                      ? "border-[#00ffcc] bg-[#00ffcc]/10 shadow-[0_0_25px_rgba(0,255,204,0.2)]"
                      : file
                      ? "border-[#00ffcc]/50 bg-[#140f24]/90"
                      : "border-[#302840] hover:border-[#504068] bg-[#0a0712]/50 hover:bg-[#140f24]/50"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,text/csv"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileSelect(e.target.files[0]);
                      }
                    }}
                  />

                  <div className="p-3.5 rounded-full bg-[#1e1a2e] border border-white/10 mb-3 text-[#00ffcc]">
                    <UploadCloud size={24} />
                  </div>

                  {file ? (
                    <div className="text-center">
                      <div className="text-xs font-semibold text-[#f0ecf8]">{file.name}</div>
                      <div className="text-[11px] font-mono text-[#a098b0] mt-0.5">
                        {(file.size / 1024).toFixed(1)} KB · Click or drag another file to replace
                      </div>
                    </div>
                  ) : (
                    <div className="text-center">
                      <div className="text-xs font-medium text-[#f0ecf8]">
                        Drag and drop your <span className="text-[#00ffcc]">.csv</span> file here,
                        or <span className="text-[#00ffcc] underline">browse</span>
                      </div>
                      <div className="text-[11px] text-[#a098b0] mt-1">
                        Max file size: 5 MB · UTF-8 encoding
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Raw CSV Editor */
                <div className="space-y-2">
                  <textarea
                    value={rawText}
                    onChange={(e) => {
                      setRawText(e.target.value);
                      runValidation(e.target.value);
                    }}
                    placeholder="sku,name,category,pack_size,mrp_inr&#10;SKU-001,Premium Earl Grey,Tea,50 bags,4.50"
                    rows={6}
                    className="w-full p-3 rounded-xl bg-[#0a0712] border border-[#302840] font-mono text-xs text-[#f0ecf8] placeholder-[#504068] focus:outline-none focus:border-[#00ffcc]/50 resize-y"
                  />
                  <div className="flex justify-between items-center text-[11px] text-[#a098b0]">
                    <span>Lines: {rawText.split("\n").filter((l) => l.trim()).length}</span>
                    <button
                      type="button"
                      onClick={() => runValidation(rawText)}
                      className="text-[#00ffcc] hover:underline"
                    >
                      Re-validate Text
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Validation Status & Live Preview */}
          {validating && (
            <div className="flex items-center justify-center p-4 gap-2 text-xs text-[#00ffcc]">
              <RefreshCw size={14} className="animate-spin" />
              Validating schema compliance & headers...
            </div>
          )}

          {validationResult && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-label uppercase tracking-wider text-[#a098b0]">
                    Pre-Import Validation
                  </span>
                  {validationResult.is_valid ? (
                    <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded-full bg-[#00ffcc]/15 text-[#00ffcc] border border-[#00ffcc]/30">
                      ✓ Ready ({validationResult.valid_rows} Valid Rows)
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded-full bg-[#ff2d78]/15 text-[#ff2d78] border border-[#ff2d78]/30">
                      ✕ {validationResult.error_count} Error(s) Found
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-mono text-[#a098b0]">
                  Columns: {validationResult.headers.join(", ")}
                </span>
              </div>

              {/* Validation Errors List */}
              {validationResult.errors.length > 0 && (
                <div className="p-3.5 rounded-xl bg-[#ff2d78]/10 border border-[#ff2d78]/30 space-y-1.5 max-h-36 overflow-y-auto custom-scrollbar">
                  <div className="text-xs font-semibold text-[#ff2d78]">
                    Please fix the following issues before importing:
                  </div>
                  {validationResult.errors.map((err, i) => (
                    <div key={i} className="text-[11px] text-[#ffd6e6] flex items-start gap-1.5">
                      <span className="font-mono text-[#ff2d78] font-bold">
                        {err.row_number > 0 ? `Row ${err.row_number}:` : "File:"}
                      </span>
                      <span>
                        <strong className="text-white">[{err.column}]</strong> {err.message}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Data Preview Table */}
              {validationResult.preview.length > 0 && (
                <div className="border border-[#302840]/60 rounded-xl overflow-hidden bg-[#0a0712]/80">
                  <div className="px-3.5 py-2 bg-[#140f24] text-[11px] font-mono uppercase tracking-wider text-[#a098b0] border-b border-[#302840]/60 flex justify-between">
                    <span>Sample Data Preview (First 10 Rows)</span>
                    <span>Total: {validationResult.total_rows} rows</span>
                  </div>
                  <div className="overflow-x-auto max-h-48 custom-scrollbar">
                    <table className="w-full text-left text-xs border-collapse font-mono">
                      <thead>
                        <tr className="border-b border-[#302840]/40 text-[#a098b0] bg-[#140f24]/50">
                          <th className="p-2 w-10 text-center">#</th>
                          {validationResult.headers.map((h, i) => (
                            <th key={i} className="p-2 font-semibold">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {validationResult.preview.map((row, rowIdx) => (
                          <tr
                            key={rowIdx}
                            className="border-b border-[#302840]/20 hover:bg-white/5 text-[#e0d8f0]"
                          >
                            <td className="p-2 text-center text-[#504068]">{rowIdx + 1}</td>
                            {validationResult.headers.map((h, colIdx) => (
                              <td key={colIdx} className="p-2 truncate max-w-[180px]">
                                {row[h] || <span className="text-[#504068]">-</span>}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Ingestion Mode Selector */}
          {!importSuccess && validationResult?.is_valid && (
            <div className="p-3.5 rounded-xl bg-[#140f24] border border-[#302840]/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold text-[#f0ecf8]">Conflict Resolution Mode</div>
                <div className="text-[11px] text-[#a098b0]">
                  How to handle existing primary keys (SKU / Order / Supplier ID)
                </div>
              </div>
              <div className="flex items-center gap-2">
                <label
                  onClick={() => setMode("upsert")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                    mode === "upsert"
                      ? "bg-[#00ffcc]/20 border border-[#00ffcc]/40 text-[#00ffcc]"
                      : "bg-[#1e1a2e] text-[#a098b0] border border-transparent"
                  }`}
                >
                  <input
                    type="radio"
                    name="import_mode"
                    checked={mode === "upsert"}
                    onChange={() => setMode("upsert")}
                    className="hidden"
                  />
                  <span>Idempotent Upsert</span>
                </label>
                <label
                  onClick={() => setMode("strict")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                    mode === "strict"
                      ? "bg-[#ff2d78]/20 border border-[#ff2d78]/40 text-[#ff2d78]"
                      : "bg-[#1e1a2e] text-[#a098b0] border border-transparent"
                  }`}
                >
                  <input
                    type="radio"
                    name="import_mode"
                    checked={mode === "strict"}
                    onChange={() => setMode("strict")}
                    className="hidden"
                  />
                  <span>Strict Fail</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-[#302840]/60 bg-[#140f24]/90">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-[#a098b0] hover:text-white hover:bg-white/5 transition-colors"
          >
            {importSuccess ? "Close Window" : "Cancel"}
          </button>

          {!importSuccess && (
            <button
              type="button"
              disabled={!validationResult?.is_valid || importing || validating}
              onClick={handleImport}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-lg ${
                validationResult?.is_valid && !importing && !validating
                  ? "bg-[#00ffcc] text-[#0a0a12] hover:bg-[#00ffcc]/90 shadow-[0_0_20px_rgba(0,255,204,0.3)] cursor-pointer"
                  : "bg-[#251e38] text-[#605078] cursor-not-allowed"
              }`}
            >
              {importing ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  Importing Transactionally...
                </>
              ) : (
                <>
                  <span>Import {validationResult?.valid_rows || 0} Records</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
