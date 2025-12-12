"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  ArrowLeft,
  Save,
  Eye,
  Undo,
  Redo,
  Type,
  Image as ImageIcon,
  Palette,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import api from "@/lib/api";

interface LandingPage {
  id: number;
  name: string;
  url: string;
  productUrl: string;
  template: string;
  language: string;
  draft_content?: string;  // 草稿内容：编辑器操作的版本
  html_content?: string;   // 已发布内容：线上版本
  has_unpublished_changes?: boolean;  // 是否有未发布的更改
  ga_measurement_id?: string;  // GA4 Measurement ID
  status: string;
}

interface EditorState {
  html: string;
  timestamp: number;
}

export default function LandingPageEditPage() {
  const router = useRouter();
  const params = useParams();
  const landingPageId = params.id as string;

  const [landingPage, setLandingPage] = useState<LandingPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [htmlContent, setHtmlContent] = useState("");
  const [selectedElement, setSelectedElement] = useState<HTMLElement | null>(null);
  const [themeColor, setThemeColor] = useState("#3b82f6");
  const [gaMeasurementId, setGaMeasurementId] = useState("");
  
  // Undo/Redo state
  const [history, setHistory] = useState<EditorState[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const maxHistorySize = 20;

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchLandingPage();
  }, [landingPageId]);

  useEffect(() => {
    if (htmlContent && history.length === 0) {
      // Initialize history with current content
      addToHistory(htmlContent);
    }
  }, [htmlContent]);

  const fetchLandingPage = async () => {
    try {
      setLoading(true);
      const response = await api.get<LandingPage>(`/landing-pages/${landingPageId}`);
      setLandingPage(response.data);
      // 编辑器始终操作 draft_content（草稿版本）
      setHtmlContent(response.data.draft_content || response.data.html_content || getDefaultTemplate());
      // 加载 GA4 Measurement ID
      setGaMeasurementId(response.data.ga_measurement_id || "");
    } catch (error) {
      console.error("Failed to fetch landing page:", error);
      router.push("/landing-pages");
    } finally {
      setLoading(false);
    }
  };

  const getDefaultTemplate = () => {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Landing Page</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .hero { text-align: center; padding: 80px 20px; background: linear-gradient(135deg, ${themeColor} 0%, #1e40af 100%); color: white; }
    .hero h1 { font-size: 48px; margin-bottom: 20px; }
    .hero p { font-size: 20px; margin-bottom: 30px; }
    .cta-button { display: inline-block; padding: 15px 40px; background: white; color: ${themeColor}; text-decoration: none; border-radius: 8px; font-weight: bold; }
    .features { padding: 60px 20px; }
    .features h2 { text-align: center; font-size: 36px; margin-bottom: 40px; }
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }
    .feature { text-align: center; padding: 30px; }
    .feature img { width: 100px; height: 100px; margin-bottom: 20px; }
    .feature h3 { font-size: 24px; margin-bottom: 10px; }
  </style>
</head>
<body>
  <div class="hero" data-editable="section">
    <div class="container">
      <h1 data-editable="text">Welcome to Our Product</h1>
      <p data-editable="text">Transform your business with our innovative solution</p>
      <a href="#" class="cta-button" data-editable="text">Get Started</a>
    </div>
  </div>
  
  <div class="features" data-editable="section">
    <div class="container">
      <h2 data-editable="text">Key Features</h2>
      <div class="feature-grid">
        <div class="feature">
          <img src="https://via.placeholder.com/100" alt="Feature 1" data-editable="image">
          <h3 data-editable="text">Feature One</h3>
          <p data-editable="text">Description of your first amazing feature</p>
        </div>
        <div class="feature">
          <img src="https://via.placeholder.com/100" alt="Feature 2" data-editable="image">
          <h3 data-editable="text">Feature Two</h3>
          <p data-editable="text">Description of your second amazing feature</p>
        </div>
        <div class="feature">
          <img src="https://via.placeholder.com/100" alt="Feature 3" data-editable="image">
          <h3 data-editable="text">Feature Three</h3>
          <p data-editable="text">Description of your third amazing feature</p>
        </div>
      </div>
    </div>
  </div>
</body>
</html>`;
  };

  const addToHistory = (html: string) => {
    const newState: EditorState = {
      html,
      timestamp: Date.now(),
    };

    // Remove any states after current index
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(newState);

    // Keep only last 20 states
    if (newHistory.length > maxHistorySize) {
      newHistory.shift();
    }

    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setHtmlContent(history[newIndex].html);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      setHistoryIndex(newIndex);
      setHtmlContent(history[newIndex].html);
    }
  };

  const handleSave = async () => {
    if (!landingPage) return;

    // Validate GA Measurement ID format if provided
    if (gaMeasurementId && !/^G-[A-Z0-9]+$/.test(gaMeasurementId)) {
      alert("Invalid GA4 Measurement ID format. It should start with 'G-' followed by alphanumeric characters (e.g., G-XXXXXXXXXX)");
      return;
    }

    try {
      setSaving(true);
      await api.put(`/landing-pages/${landingPageId}`, {
        html_content: htmlContent,
        ga_measurement_id: gaMeasurementId || null,
      });
      alert("Landing page saved successfully!");
    } catch (error) {
      console.error("Failed to save landing page:", error);
      alert("Failed to save landing page. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = () => {
    const previewWindow = window.open("", "_blank");
    if (previewWindow) {
      previewWindow.document.write(htmlContent);
      previewWindow.document.close();
    }
  };

  const handleThemeColorChange = (color: string) => {
    setThemeColor(color);
    const updatedHtml = htmlContent.replace(
      /background: linear-gradient\(135deg, #[0-9a-fA-F]{6}/g,
      `background: linear-gradient(135deg, ${color}`
    ).replace(
      /color: #[0-9a-fA-F]{6};/g,
      `color: ${color};`
    );
    setHtmlContent(updatedHtml);
    addToHistory(updatedHtml);
  };

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      // Get presigned URL for landing page asset (uploads to public bucket)
      const uploadResponse = await api.post(`/landing-pages/${landingPageId}/assets/upload-url`, {
        filename: file.name,
        content_type: file.type,
        size: file.size,
      });

      const { upload_url: uploadUrl, public_url: cdnUrl } = uploadResponse.data;

      // Upload to GCS
      await fetch(uploadUrl, {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type,
        },
      });

      // Update selected image element
      if (selectedElement && selectedElement.tagName === "IMG") {
        const iframe = iframeRef.current;
        if (iframe && iframe.contentDocument) {
          // Update src in the iframe DOM
          (selectedElement as HTMLImageElement).src = cdnUrl;
          // Get updated HTML
          const updatedHtml = "<!DOCTYPE html>\n" + iframe.contentDocument.documentElement.outerHTML;
          setHtmlContent(updatedHtml);
          addToHistory(updatedHtml);
        }
      }
    } catch (error) {
      console.error("Failed to upload image:", error);
      alert("Failed to upload image. Please try again.");
    }

    // Reset file input
    event.target.value = "";
  };

  const setupIframeInteraction = () => {
    const iframe = iframeRef.current;
    if (!iframe || !iframe.contentDocument) return;

    const doc = iframe.contentDocument;

    // Make all text elements and images editable
    const editableSelectors = "h1, h2, h3, h4, h5, h6, p, span, a, li, button, img, [data-editable]";
    const editableElements = doc.querySelectorAll(editableSelectors);

    editableElements.forEach((element) => {
      const el = element as HTMLElement;

      // Skip elements that are just containers (have child elements that are also editable)
      if (el.tagName !== "IMG" && el.children.length > 0) {
        const hasEditableChildren = el.querySelector(editableSelectors);
        if (hasEditableChildren) return;
      }

      el.style.cursor = "pointer";
      el.style.outline = "2px dashed transparent";
      el.style.transition = "outline 0.2s";

      el.addEventListener("mouseenter", () => {
        el.style.outline = "2px dashed #3b82f6";
      });

      el.addEventListener("mouseleave", () => {
        if (el !== selectedElement) {
          el.style.outline = "2px dashed transparent";
        }
      });

      el.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        setSelectedElement(el);
        el.style.outline = "2px solid #3b82f6";

        // Handle image editing
        if (el.tagName === "IMG") {
          fileInputRef.current?.click();
          return;
        }

        // Handle text editing
        const currentText = el.textContent || "";
        const newText = prompt("Edit text:", currentText);
        if (newText !== null && newText !== currentText) {
          el.textContent = newText;
          const updatedHtml = "<!DOCTYPE html>\n" + doc.documentElement.outerHTML;
          setHtmlContent(updatedHtml);
          addToHistory(updatedHtml);
        }
      });
    });
  };

  useEffect(() => {
    if (iframeRef.current && htmlContent) {
      const iframe = iframeRef.current;
      const doc = iframe.contentDocument;
      if (doc) {
        doc.open();
        doc.write(htmlContent);
        doc.close();

        // Setup interaction after a small delay to ensure DOM is ready
        setTimeout(() => {
          setupIframeInteraction();
        }, 100);
      }
    }
  }, [htmlContent]);

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!landingPage) {
    return null;
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/landing-pages/${landingPageId}`)}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <h1 className="text-xl font-bold">Edit: {landingPage.name}</h1>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleUndo}
              disabled={historyIndex <= 0}
              title="Undo (Ctrl+Z)"
            >
              <Undo className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRedo}
              disabled={historyIndex >= history.length - 1}
              title="Redo (Ctrl+Y)"
            >
              <Redo className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handlePreview}>
              <Eye className="w-4 h-4 mr-2" />
              Preview
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              <Save className="w-4 h-4 mr-2" />
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-64 border-r bg-gray-50 p-4 overflow-y-auto">
          <h2 className="font-semibold mb-4">Editor Tools</h2>

          {/* Text Editing */}
          <Card className="p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Type className="w-4 h-4" />
              <h3 className="font-semibold text-sm">Text</h3>
            </div>
            <p className="text-xs text-gray-600">
              Click on any text element to edit. Supports bold, italic, and color.
            </p>
          </Card>

          {/* Image Upload */}
          <Card className="p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <ImageIcon className="w-4 h-4" />
              <h3 className="font-semibold text-sm">Images</h3>
            </div>
            <p className="text-xs text-gray-600 mb-2">
              Click on any image to replace it with a new one.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
          </Card>

          {/* Theme Color */}
          <Card className="p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Palette className="w-4 h-4" />
              <h3 className="font-semibold text-sm">Theme Color</h3>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={themeColor}
                onChange={(e) => handleThemeColorChange(e.target.value)}
                className="w-12 h-12 rounded cursor-pointer"
              />
              <Input
                type="text"
                value={themeColor}
                onChange={(e) => handleThemeColorChange(e.target.value)}
                className="flex-1 text-sm"
                placeholder="#3b82f6"
              />
            </div>
          </Card>

          {/* Analytics Settings */}
          <Card className="p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4" />
              <h3 className="font-semibold text-sm">Analytics</h3>
            </div>
            <p className="text-xs text-gray-600 mb-3">
              Connect Google Analytics 4 to track page views and conversions.
            </p>
            <div className="space-y-2">
              <label className="text-xs font-medium text-gray-700">
                GA4 Measurement ID
              </label>
              <Input
                type="text"
                value={gaMeasurementId}
                onChange={(e) => setGaMeasurementId(e.target.value.toUpperCase())}
                placeholder="G-XXXXXXXXXX"
                className="text-sm"
              />
              <p className="text-xs text-gray-500">
                Find this in Google Analytics → Admin → Data Streams
              </p>
            </div>
            {gaMeasurementId && (
              <div className="mt-3 p-2 bg-green-50 rounded text-xs text-green-700">
                GA4 tracking will be added when you publish.
              </div>
            )}
          </Card>

          {/* History Info */}
          <Card className="p-4">
            <h3 className="font-semibold text-sm mb-2">History</h3>
            <p className="text-xs text-gray-600">
              {historyIndex + 1} / {history.length} states
            </p>
            <p className="text-xs text-gray-500 mt-1">
              (Max {maxHistorySize} undo steps)
            </p>
          </Card>
        </div>

        {/* Editor Canvas */}
        <div className="flex-1 bg-gray-100 p-6 overflow-auto">
          <div className="max-w-6xl mx-auto">
            <Card className="overflow-hidden shadow-lg">
              <iframe
                ref={iframeRef}
                className="w-full"
                style={{ height: "800px", border: "none" }}
                title="Landing Page Editor"
                sandbox="allow-scripts allow-same-origin"
              />
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
