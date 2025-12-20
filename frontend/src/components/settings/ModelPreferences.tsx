"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface ProviderModels {
  name: string;
  models: {
    [key: string]: string;
  };
}

interface ModelPreferences {
  // Conversational
  conversational_provider: string;
  conversational_model: string;
  // Image generation
  image_generation_provider: string;
  image_generation_model: string;
  // Video generation
  video_generation_provider: string;
  video_generation_model: string;
  // Available providers
  available_conversational_providers: {
    [key: string]: ProviderModels;
  };
  available_image_providers: {
    [key: string]: ProviderModels;
  };
  available_video_providers: {
    [key: string]: ProviderModels;
  };
}

type ModelCategory = "conversational" | "image" | "video";

export function ModelPreferences() {
  const [preferences, setPreferences] = useState<ModelPreferences | null>(null);
  const [activeCategory, setActiveCategory] = useState<ModelCategory>("conversational");
  
  // Conversational selections
  const [selectedConvProvider, setSelectedConvProvider] = useState<string>("gemini");
  const [selectedConvModel, setSelectedConvModel] = useState<string>("gemini-2.5-flash");
  
  // Image generation selections
  const [selectedImageProvider, setSelectedImageProvider] = useState<string>("gemini");
  const [selectedImageModel, setSelectedImageModel] = useState<string>("gemini-2.0-flash-exp");
  
  // Video generation selections
  const [selectedVideoProvider, setSelectedVideoProvider] = useState<string>("sagemaker");
  const [selectedVideoModel, setSelectedVideoModel] = useState<string>("wan2.2");
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setIsLoading(true);
      const response = await api.get("/users/me/model-preferences");
      const data = response.data;
      setPreferences(data);
      
      // Set conversational selections
      setSelectedConvProvider(data.conversational_provider);
      setSelectedConvModel(data.conversational_model);
      
      // Set image generation selections
      setSelectedImageProvider(data.image_generation_provider || "gemini");
      setSelectedImageModel(data.image_generation_model || "gemini-2.0-flash-exp");
      
      // Set video generation selections
      setSelectedVideoProvider(data.video_generation_provider || "sagemaker");
      setSelectedVideoModel(data.video_generation_model || "wan2.2");
    } catch (error) {
      console.error("Failed to load model preferences:", error);
      setMessage({ type: "error", text: "Failed to load model preferences" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setMessage(null);

      await api.put("/users/me/model-preferences", {
        conversational_provider: selectedConvProvider,
        conversational_model: selectedConvModel,
        image_generation_provider: selectedImageProvider,
        image_generation_model: selectedImageModel,
        video_generation_provider: selectedVideoProvider,
        video_generation_model: selectedVideoModel,
      });

      setMessage({ type: "success", text: "Model preferences updated successfully" });
      await loadPreferences();
    } catch (error: any) {
      console.error("Failed to save model preferences:", error);
      setMessage({
        type: "error",
        text: error.response?.data?.detail || "Failed to save model preferences",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleConvProviderChange = (provider: string) => {
    setSelectedConvProvider(provider);
    if (preferences?.available_conversational_providers[provider]) {
      const models = Object.keys(preferences.available_conversational_providers[provider].models);
      if (models.length > 0) {
        setSelectedConvModel(models[0]);
      }
    }
  };

  const handleImageProviderChange = (provider: string) => {
    setSelectedImageProvider(provider);
    if (preferences?.available_image_providers[provider]) {
      const models = Object.keys(preferences.available_image_providers[provider].models);
      if (models.length > 0) {
        setSelectedImageModel(models[0]);
      }
    }
  };

  const handleVideoProviderChange = (provider: string) => {
    setSelectedVideoProvider(provider);
    if (preferences?.available_video_providers[provider]) {
      const models = Object.keys(preferences.available_video_providers[provider].models);
      if (models.length > 0) {
        setSelectedVideoModel(models[0]);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!preferences) {
    return (
      <div className="text-center py-12 text-gray-500">
        Failed to load model preferences
      </div>
    );
  }

  const categories = [
    { id: "conversational" as ModelCategory, label: "Conversational AI", icon: "💬", description: "Chat and conversation models" },
    { id: "image" as ModelCategory, label: "Image Generation", icon: "🎨", description: "AI image creation models" },
    { id: "video" as ModelCategory, label: "Video Generation", icon: "🎬", description: "AI video creation models" },
  ];

  const renderProviderSelection = () => {
    let providers: { [key: string]: ProviderModels } = {};
    let selectedProvider = "";
    let onProviderChange: (provider: string) => void = () => {};

    switch (activeCategory) {
      case "conversational":
        providers = preferences.available_conversational_providers;
        selectedProvider = selectedConvProvider;
        onProviderChange = handleConvProviderChange;
        break;
      case "image":
        providers = preferences.available_image_providers;
        selectedProvider = selectedImageProvider;
        onProviderChange = handleImageProviderChange;
        break;
      case "video":
        providers = preferences.available_video_providers;
        selectedProvider = selectedVideoProvider;
        onProviderChange = handleVideoProviderChange;
        break;
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(providers).map(([providerId, provider]) => (
          <button
            key={providerId}
            onClick={() => onProviderChange(providerId)}
            className={`p-4 rounded-lg border-2 transition-all text-left ${
              selectedProvider === providerId
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900">{provider.name}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {Object.keys(provider.models).length} model{Object.keys(provider.models).length > 1 ? 's' : ''} available
                </p>
              </div>
              {selectedProvider === providerId && (
                <div className="text-blue-500">
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              )}
            </div>
          </button>
        ))}
      </div>
    );
  };

  const renderModelSelection = () => {
    let providers: { [key: string]: ProviderModels } = {};
    let selectedProvider = "";
    let selectedModel = "";
    let onModelChange: (model: string) => void = () => {};

    switch (activeCategory) {
      case "conversational":
        providers = preferences.available_conversational_providers;
        selectedProvider = selectedConvProvider;
        selectedModel = selectedConvModel;
        onModelChange = setSelectedConvModel;
        break;
      case "image":
        providers = preferences.available_image_providers;
        selectedProvider = selectedImageProvider;
        selectedModel = selectedImageModel;
        onModelChange = setSelectedImageModel;
        break;
      case "video":
        providers = preferences.available_video_providers;
        selectedProvider = selectedVideoProvider;
        selectedModel = selectedVideoModel;
        onModelChange = setSelectedVideoModel;
        break;
    }

    const availableModels = providers[selectedProvider]?.models || {};

    return (
      <div className="space-y-2">
        {Object.entries(availableModels).map(([modelId, modelName]) => (
          <button
            key={modelId}
            onClick={() => onModelChange(modelId)}
            className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
              selectedModel === modelId
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">{modelName}</h4>
                <p className="text-sm text-gray-500 mt-1 font-mono">{modelId}</p>
              </div>
              {selectedModel === modelId && (
                <div className="text-blue-500">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              )}
            </div>
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">AI Model Preferences</h2>
        <p className="text-gray-600 mt-1">
          Configure which AI models to use for different tasks
        </p>
      </div>

      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Category Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setActiveCategory(category.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeCategory === category.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <span className="mr-2">{category.icon}</span>
              {category.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Category Description */}
      <div className="bg-gray-50 rounded-lg p-4">
        <p className="text-sm text-gray-600">
          {categories.find(c => c.id === activeCategory)?.description}
        </p>
      </div>

      <div className="space-y-6">
        {/* Provider Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Select Provider
          </label>
          {renderProviderSelection()}
        </div>

        {/* Model Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Select Model
          </label>
          {renderModelSelection()}
        </div>

        {/* Current Selection Summary */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Current Configuration</h3>
              <div className="mt-2 text-sm text-blue-700 space-y-1">
                <p>💬 Conversational: <span className="font-medium">{selectedConvProvider}</span> / <span className="font-mono text-xs">{selectedConvModel}</span></p>
                <p>🎨 Image Generation: <span className="font-medium">{selectedImageProvider}</span> / <span className="font-mono text-xs">{selectedImageModel}</span></p>
                <p>🎬 Video Generation: <span className="font-medium">{selectedVideoProvider}</span> / <span className="font-mono text-xs">{selectedVideoModel}</span></p>
              </div>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end pt-4 border-t">
          <Button
            onClick={handleSave}
            disabled={isSaving}
            className="min-w-[120px]"
          >
            {isSaving ? (
              <>
                <span className="animate-spin mr-2">⏳</span>
                Saving...
              </>
            ) : (
              "Save All Changes"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
