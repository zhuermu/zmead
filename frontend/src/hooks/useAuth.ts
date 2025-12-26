import { useState, useEffect } from "react";
import { User } from "@/types";
import api from "@/lib/api";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          setAuthState({ user: null, isLoading: false, error: null });
          return;
        }

        const response = await api.get("/auth/me");
        const data = response.data;

        // Convert snake_case to camelCase
        const user: User = {
          id: data.id,
          email: data.email,
          displayName: data.display_name,
          avatarUrl: data.avatar_url,
          oauthProvider: data.oauth_provider,
          giftedCredits: data.gifted_credits,
          purchasedCredits: data.purchased_credits,
          language: data.language,
          timezone: data.timezone,
          conversationalProvider: data.conversational_provider,
          conversationalModel: data.conversational_model,
          isApproved: data.is_approved,
          isSuperAdmin: data.is_super_admin,
          createdAt: data.created_at,
          lastLoginAt: data.last_login_at,
        };
        setAuthState({ user, isLoading: false, error: null });
      } catch (error) {
        console.error("Failed to fetch user:", error);
        // Don't clear tokens here, let the API interceptor handle it
        setAuthState({ user: null, isLoading: false, error: "Failed to fetch user" });
      }
    };

    fetchUser();
  }, []);

  return authState;
}
