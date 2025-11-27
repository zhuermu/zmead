"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import api from "@/lib/api";

interface LandingPage {
  id: number;
  name: string;
  url: string;
  productUrl: string;
  template: string;
  language: string;
  status: "draft" | "published" | "archived";
  createdAt: string;
  publishedAt?: string;
}

interface LandingPageListResponse {
  landing_pages: LandingPage[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export default function LandingPagesPage() {
  const router = useRouter();
  const [landingPages, setLandingPages] = useState<LandingPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [templateFilter, setTemplateFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    fetchLandingPages();
  }, [page, statusFilter, templateFilter]);

  const fetchLandingPages = async () => {
    try {
      setLoading(true);
      const params: Record<string, string | number> = {
        page,
        page_size: 12,
      };

      if (statusFilter !== "all") {
        params.status = statusFilter;
      }

      if (templateFilter !== "all") {
        params.template = templateFilter;
      }

      const response = await api.get<LandingPageListResponse>("/landing-pages", {
        params,
      });

      setLandingPages(response.data.landing_pages);
      setTotal(response.data.total);
      setHasMore(response.data.has_more);
    } catch (error) {
      console.error("Failed to fetch landing pages:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredPages = landingPages.filter((page) =>
    page.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Landing Pages</h1>
          <p className="text-gray-600 mt-1">
            Manage your landing pages and track performance
          </p>
        </div>
        <Button onClick={() => router.push("/landing-pages/new")}>
          <Plus className="w-4 h-4 mr-2" />
          Create Landing Page
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Search landing pages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select
          value={statusFilter}
          onValueChange={setStatusFilter}
        >
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </Select>

        <Select
          value={templateFilter}
          onValueChange={setTemplateFilter}
        >
          <option value="all">All Templates</option>
          <option value="modern">Modern</option>
          <option value="classic">Classic</option>
          <option value="minimal">Minimal</option>
        </Select>
      </div>

      {/* Results count */}
      <div className="mb-4 text-sm text-gray-600">
        Showing {filteredPages.length} of {total} landing pages
      </div>

      {/* Landing Pages Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="p-6 animate-pulse">
              <div className="h-40 bg-gray-200 rounded mb-4"></div>
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-2/3"></div>
            </Card>
          ))}
        </div>
      ) : filteredPages.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-gray-400 mb-4">
            <Filter className="w-12 h-12 mx-auto" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No landing pages found</h3>
          <p className="text-gray-600 mb-4">
            {searchQuery || statusFilter !== "all" || templateFilter !== "all"
              ? "Try adjusting your filters"
              : "Create your first landing page to get started"}
          </p>
          {!searchQuery && statusFilter === "all" && templateFilter === "all" && (
            <Button onClick={() => router.push("/landing-pages/new")}>
              <Plus className="w-4 h-4 mr-2" />
              Create Landing Page
            </Button>
          )}
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPages.map((landingPage) => (
              <Card
                key={landingPage.id}
                className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/landing-pages/${landingPage.id}`)}
              >
                {/* Thumbnail */}
                <div className="h-40 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
                  <div className="text-center p-4">
                    <div className="text-4xl mb-2">🌐</div>
                    <div className="text-xs text-gray-600 font-mono truncate max-w-full">
                      {landingPage.url || "Not published"}
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-lg truncate flex-1">
                      {landingPage.name}
                    </h3>
                    <Badge className={getStatusColor(landingPage.status)}>
                      {landingPage.status}
                    </Badge>
                  </div>

                  <p className="text-sm text-gray-600 mb-3 truncate">
                    {landingPage.productUrl}
                  </p>

                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span className="capitalize">{landingPage.template}</span>
                    <span>{formatDate(landingPage.createdAt)}</span>
                  </div>

                  {landingPage.publishedAt && (
                    <div className="mt-2 text-xs text-green-600">
                      Published {formatDate(landingPage.publishedAt)}
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {(page > 1 || hasMore) && (
            <div className="flex justify-center gap-2 mt-8">
              <Button
                variant="outline"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="flex items-center px-4 text-sm text-gray-600">
                Page {page}
              </span>
              <Button
                variant="outline"
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
