"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import api from "@/lib/api";

export default function NewLandingPagePage() {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    product_url: "",
    template: "modern",
    language: "en",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || !formData.product_url) {
      alert("Please fill in all required fields");
      return;
    }

    try {
      setCreating(true);
      const response = await api.post("/landing-pages", formData);
      const landingPageId = response.data.id;
      router.push(`/landing-pages/${landingPageId}/edit`);
    } catch (error) {
      console.error("Failed to create landing page:", error);
      alert("Failed to create landing page. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push("/landing-pages")}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Create Landing Page</h1>
          <p className="text-gray-600 mt-1">
            Set up your new landing page with basic information
          </p>
        </div>
      </div>

      {/* Form */}
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Landing Page Name <span className="text-red-500">*</span>
            </label>
            <Input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              placeholder="e.g., Summer Sale 2024"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              A descriptive name for your landing page
            </p>
          </div>

          {/* Product URL */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Product URL <span className="text-red-500">*</span>
            </label>
            <Input
              type="url"
              value={formData.product_url}
              onChange={(e) =>
                setFormData({ ...formData, product_url: e.target.value })
              }
              placeholder="https://example.com/product"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              The URL of the product or service you&apos;re promoting
            </p>
          </div>

          {/* Template */}
          <div>
            <label className="block text-sm font-medium mb-2">Template</label>
            <Select
              value={formData.template}
              onValueChange={(value) =>
                setFormData({ ...formData, template: value })
              }
            >
              <option value="modern">Modern</option>
              <option value="classic">Classic</option>
              <option value="minimal">Minimal</option>
            </Select>
            <p className="text-xs text-gray-500 mt-1">
              Choose a template style for your landing page
            </p>
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium mb-2">Language</label>
            <Select
              value={formData.language}
              onValueChange={(value) =>
                setFormData({ ...formData, language: value })
              }
            >
              <option value="en">English</option>
              <option value="zh">中文</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
            </Select>
            <p className="text-xs text-gray-500 mt-1">
              The primary language for your landing page content
            </p>
          </div>

          {/* Template Preview */}
          <div className="border rounded-lg p-4 bg-gray-50">
            <h3 className="font-semibold mb-2">Template Preview</h3>
            <div className="aspect-video bg-gradient-to-br from-blue-50 to-indigo-100 rounded flex items-center justify-center">
              <div className="text-center">
                <div className="text-4xl mb-2">🌐</div>
                <p className="text-sm text-gray-600 capitalize">
                  {formData.template} Template
                </p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/landing-pages")}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={creating} className="flex-1">
              <Plus className="w-4 h-4 mr-2" />
              {creating ? "Creating..." : "Create & Edit"}
            </Button>
          </div>
        </form>
      </Card>

      {/* Info */}
      <Card className="p-4 mt-6 bg-blue-50 border-blue-200">
        <h3 className="font-semibold text-sm mb-2 text-blue-900">
          What happens next?
        </h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Your landing page will be created in draft status</li>
          <li>• You&apos;ll be taken to the visual editor to customize content</li>
          <li>• You can edit text, images, and theme colors</li>
          <li>• Publish when ready to make it live</li>
        </ul>
      </Card>
    </div>
  );
}
