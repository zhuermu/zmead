"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRouter } from "next/navigation";

interface CreditConfig {
  id: number;
  gemini_flash_input_rate: number;
  gemini_flash_output_rate: number;
  gemini_pro_input_rate: number;
  gemini_pro_output_rate: number;
  image_generation_rate: number;
  video_generation_rate: number;
  landing_page_rate: number;
  competitor_analysis_rate: number;
  optimization_suggestion_rate: number;
  registration_bonus: number;
  packages: Record<string, any>;
  updated_at: string | null;
  updated_by: string | null;
}

interface ConfigChangeLog {
  id: number;
  config_id: number;
  field_name: string;
  old_value: string | null;
  new_value: string;
  changed_by: string;
  changed_at: string;
  notes: string | null;
}

export default function AdminConfigPage() {
  const router = useRouter();
  const [config, setConfig] = useState<CreditConfig | null>(null);
  const [changeHistory, setChangeHistory] = useState<ConfigChangeLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [editedConfig, setEditedConfig] = useState<Partial<CreditConfig>>({});

  // Field labels for display
  const fieldLabels: Record<string, string> = {
    gemini_flash_input_rate: "Gemini Flash Input Rate (per 1K tokens)",
    gemini_flash_output_rate: "Gemini Flash Output Rate (per 1K tokens)",
    gemini_pro_input_rate: "Gemini Pro Input Rate (per 1K tokens)",
    gemini_pro_output_rate: "Gemini Pro Output Rate (per 1K tokens)",
    image_generation_rate: "Image Generation Rate (per image)",
    video_generation_rate: "Video Generation Rate (per video)",
    landing_page_rate: "Landing Page Generation Rate",
    competitor_analysis_rate: "Competitor Analysis Rate",
    optimization_suggestion_rate: "Optimization Suggestion Rate",
    registration_bonus: "Registration Bonus Credits",
  };

  useEffect(() => {
    fetchConfig();
    fetchChangeHistory();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch("/api/v1/credits/config", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch config");
      }

      const data = await response.json();
      setConfig(data);
      setEditedConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load config");
    } finally {
      setLoading(false);
    }
  };

  const fetchChangeHistory = async () => {
    try {
      const response = await fetch("/api/v1/credits/config/history?limit=50", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch change history");
      }

      const data = await response.json();
      setChangeHistory(data);
    } catch (err) {
      console.error("Failed to load change history:", err);
    }
  };

  const handleFieldChange = (field: string, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue >= 0) {
      setEditedConfig((prev) => ({
        ...prev,
        [field]: numValue,
      }));
    }
  };

  const getFieldValue = (field: string): number => {
    const value = editedConfig[field as keyof CreditConfig];
    return typeof value === "number" ? value : 0;
  };

  const getCurrentValue = (field: string): number => {
    const value = config?.[field as keyof CreditConfig];
    return typeof value === "number" ? value : 0;
  };

  const handleSave = async () => {
    if (!config || !editedConfig) return;

    setSaving(true);
    setError(null);

    try {
      // Build query params for changed fields
      const params = new URLSearchParams();
      Object.entries(editedConfig).forEach(([key, value]) => {
        if (
          key !== "id" &&
          key !== "packages" &&
          key !== "updated_at" &&
          key !== "updated_by" &&
          value !== null &&
          value !== undefined &&
          value !== config[key as keyof CreditConfig]
        ) {
          params.append(key, value.toString());
        }
      });

      const response = await fetch(`/api/v1/credits/config?${params}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to update config");
      }

      const updatedConfig = await response.json();
      setConfig(updatedConfig);
      setEditedConfig(updatedConfig);
      setShowConfirmation(false);

      // Refresh change history
      await fetchChangeHistory();

      alert("Configuration updated successfully!");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = () => {
    if (!config || !editedConfig) return false;

    return Object.keys(fieldLabels).some(
      (key) =>
        editedConfig[key as keyof CreditConfig] !==
        config[key as keyof CreditConfig]
    );
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading configuration...</div>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-red-500">Failed to load configuration</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Credit Configuration</h1>
        <p className="text-gray-600">
          Manage credit rates and pricing for AI operations
        </p>
        {config.updated_at && (
          <p className="text-sm text-gray-500 mt-2">
            Last updated: {new Date(config.updated_at).toLocaleString()} by{" "}
            {config.updated_by}
          </p>
        )}
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-6 mb-6">
        {/* AI Model Rates */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">AI Model Rates</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              "gemini_flash_input_rate",
              "gemini_flash_output_rate",
              "gemini_pro_input_rate",
              "gemini_pro_output_rate",
            ].map((field) => (
              <div key={field}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {fieldLabels[field]}
                </label>
                <Input
                  type="number"
                  step="0.0001"
                  min="0"
                  value={getFieldValue(field)}
                  onChange={(e) => handleFieldChange(field, e.target.value)}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Current: {getCurrentValue(field)} credits
                </p>
              </div>
            ))}
          </div>
        </Card>

        {/* Operation Rates */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Operation Rates</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              "image_generation_rate",
              "video_generation_rate",
              "landing_page_rate",
              "competitor_analysis_rate",
              "optimization_suggestion_rate",
            ].map((field) => (
              <div key={field}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {fieldLabels[field]}
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={getFieldValue(field)}
                  onChange={(e) => handleFieldChange(field, e.target.value)}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Current: {getCurrentValue(field)} credits
                </p>
              </div>
            ))}
          </div>
        </Card>

        {/* Registration Bonus */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">User Settings</h2>
          <div className="max-w-md">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {fieldLabels.registration_bonus}
            </label>
            <Input
              type="number"
              step="1"
              min="0"
              value={getFieldValue("registration_bonus")}
              onChange={(e) =>
                handleFieldChange("registration_bonus", e.target.value)
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Current: {getCurrentValue("registration_bonus")} credits
            </p>
          </div>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4 mb-8">
        <Button
          onClick={() => setShowConfirmation(true)}
          disabled={!hasChanges() || saving}
          className="px-6"
        >
          {saving ? "Saving..." : "Save Changes"}
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            setEditedConfig(config);
            setError(null);
          }}
          disabled={!hasChanges() || saving}
        >
          Reset
        </Button>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Confirm Changes</h3>
            <p className="text-gray-600 mb-4">
              Are you sure you want to update the credit configuration? These
              changes will apply to all new operations immediately.
            </p>
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
              <p className="text-sm text-yellow-800">
                ⚠️ Note: Changes are non-retroactive and will not affect
                historical transactions.
              </p>
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowConfirmation(false)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : "Confirm"}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Change History */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Change History</h2>
        {changeHistory.length === 0 ? (
          <p className="text-gray-500">No changes recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-3 text-sm font-medium text-gray-700">
                    Date & Time
                  </th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-gray-700">
                    Field
                  </th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-gray-700">
                    Old Value
                  </th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-gray-700">
                    New Value
                  </th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-gray-700">
                    Changed By
                  </th>
                </tr>
              </thead>
              <tbody>
                {changeHistory.map((log) => (
                  <tr key={log.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 px-3 text-sm">
                      {new Date(log.changed_at).toLocaleString()}
                    </td>
                    <td className="py-2 px-3 text-sm">
                      {fieldLabels[log.field_name] || log.field_name}
                    </td>
                    <td className="py-2 px-3 text-sm text-gray-600">
                      {log.old_value || "—"}
                    </td>
                    <td className="py-2 px-3 text-sm font-medium">
                      {log.new_value}
                    </td>
                    <td className="py-2 px-3 text-sm text-gray-600">
                      {log.changed_by}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
