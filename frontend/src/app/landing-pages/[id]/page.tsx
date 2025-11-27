"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  ArrowLeft,
  Edit,
  Trash2,
  ExternalLink,
  Monitor,
  Smartphone,
  Eye,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import api from "@/lib/api";

interface LandingPage {
  id: number;
  name: string;
  url: string;
  s3_key: string;
  productUrl: string;
  template: string;
  language: string;
  html_content?: string;
  status: "draft" | "published" | "archived";
  createdAt: string;
  updatedAt?: string;
  publishedAt?: string;
}

export default function LandingPageDetailPage() {
  const router = useRouter();
  const params = useParams();
  const landingPageId = params.id as string;

  const [landingPage, setLandingPage] = useState<LandingPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"desktop" | "mobile">("desktop");
  const [publishing, setPublishing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchLandingPage();
  }, [landingPageId]);

  const fetchLandingPage = async () => {
    try {
      setLoading(true);
      const response = await api.get<LandingPage>(`/landing-pages/${landingPageId}`);
      setLandingPage(response.data);
    } catch (error) {
      console.error("Failed to fetch landing page:", error);
      router.push("/landing-pages");
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!landingPage) return;

    try {
      setPublishing(true);
      await api.post(`/landing-pages/${landingPageId}/publish`);
      await fetchLandingPage();
    } catch (error) {
      console.error("Failed to publish landing page:", error);
      alert("Failed to publish landing page. Please try again.");
    } finally {
      setPublishing(false);
    }
  };

  const handleDelete = async () => {
    if (!landingPage) return;

    const confirmed = confirm(
      "Are you sure you want to delete this landing page? This action cannot be undone."
    );

    if (!confirmed) return;

    try {
      setDeleting(true);
      await api.delete(`/landing-pages/${landingPageId}?hard_delete=true`);
      router.push("/landing-pages");
    } catch (error) {
      console.error("Failed to delete landing page:", error);
      alert("Failed to delete landing page. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  const handleEdit = () => {
    router.push(`/landing-pages/${landingPageId}/edit`);
  };

  const handlePreviewInNewTab = () => {
    if (landingPage?.url) {
      window.open(landingPage.url, "_blank");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "published":
        return "bg-green-100 text-green-800";
      case "draft":
        return "bg-yellow-100 text-yellow-800";
      case "archived":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

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
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/landing-pages")}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">{landingPage.name}</h1>
              <Badge className={getStatusColor(landingPage.status)}>
                {landingPage.status}
              </Badge>
            </div>
            <p className="text-gray-600 mt-1">{landingPage.productUrl}</p>
          </div>
        </div>

        <div className="flex gap-2">
          {landingPage.status === "draft" && (
            <Button onClick={handlePublish} disabled={publishing}>
              <Upload className="w-4 h-4 mr-2" />
              {publishing ? "Publishing..." : "Publish"}
            </Button>
          )}
          {landingPage.status === "published" && (
            <Button variant="outline" onClick={handlePreviewInNewTab}>
              <ExternalLink className="w-4 h-4 mr-2" />
              Open Live Page
            </Button>
          )}
          <Button variant="outline" onClick={handleEdit}>
            <Edit className="w-4 h-4 mr-2" />
            Edit
          </Button>
          <Button
            variant="outline"
            onClick={handleDelete}
            disabled={deleting}
            className="text-red-600 hover:text-red-700"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="p-4">
          <div className="text-sm text-gray-600 mb-1">Template</div>
          <div className="font-semibold capitalize">{landingPage.template}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-600 mb-1">Language</div>
          <div className="font-semibold uppercase">{landingPage.language}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-600 mb-1">Created</div>
          <div className="font-semibold">{formatDate(landingPage.createdAt)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-600 mb-1">
            {landingPage.publishedAt ? "Published" : "Last Updated"}
          </div>
          <div className="font-semibold">
            {landingPage.publishedAt
              ? formatDate(landingPage.publishedAt)
              : landingPage.updatedAt
              ? formatDate(landingPage.updatedAt)
              : "Never"}
          </div>
        </Card>
      </div>

      {/* Preview Controls */}
      <Card className="p-4 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === "desktop" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("desktop")}
            >
              <Monitor className="w-4 h-4 mr-2" />
              Desktop
            </Button>
            <Button
              variant={viewMode === "mobile" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("mobile")}
            >
              <Smartphone className="w-4 h-4 mr-2" />
              Mobile
            </Button>
          </div>

          {landingPage.url && (
            <div className="text-sm text-gray-600">
              <span className="font-mono">{landingPage.url}</span>
            </div>
          )}
        </div>
      </Card>

      {/* Preview */}
      <Card className="p-4">
        <div className="flex justify-center">
          {landingPage.status === "published" && landingPage.url ? (
            <div
              className={`border rounded-lg overflow-hidden shadow-lg transition-all ${
                viewMode === "desktop" ? "w-full" : "w-[375px]"
              }`}
              style={{
                height: viewMode === "desktop" ? "800px" : "667px",
              }}
            >
              <iframe
                src={landingPage.url}
                className="w-full h-full"
                title="Landing Page Preview"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          ) : landingPage.html_content ? (
            <div
              className={`border rounded-lg overflow-hidden shadow-lg transition-all ${
                viewMode === "desktop" ? "w-full" : "w-[375px]"
              }`}
              style={{
                height: viewMode === "desktop" ? "800px" : "667px",
              }}
            >
              <iframe
                srcDoc={landingPage.html_content}
                className="w-full h-full"
                title="Landing Page Preview"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          ) : (
            <div className="text-center py-12">
              <Eye className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Preview Available</h3>
              <p className="text-gray-600 mb-4">
                This landing page doesn&apos;t have any content yet.
              </p>
              <Button onClick={handleEdit}>
                <Edit className="w-4 h-4 mr-2" />
                Add Content
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Conversion Metrics (Placeholder) */}
      {landingPage.status === "published" && (
        <Card className="p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">Conversion Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">0</div>
              <div className="text-sm text-gray-600 mt-1">Page Views</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">0</div>
              <div className="text-sm text-gray-600 mt-1">Conversions</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">0%</div>
              <div className="text-sm text-gray-600 mt-1">Conversion Rate</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">0s</div>
              <div className="text-sm text-gray-600 mt-1">Avg. Time on Page</div>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-4 text-center">
            Metrics tracking will be available once the landing page receives traffic
          </p>
        </Card>
      )}
    </div>
  );
}
