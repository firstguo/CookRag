export type SearchResult = {
  id: string;
  title_zh: string;
  score: number;
  like_count: number;
  final_score: number;
  snippet?: string | null;
};

export type SearchRequest = {
  query: string;
  topK?: number;
  rank?: {
    alpha?: number;
    beta?: number;
  };
};

export async function searchRecipes(request: SearchRequest) {
  const resp = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!resp.ok) {
    const error = await resp.text();
    throw new Error(`search failed: ${resp.status} - ${error}`);
  }
  return (await resp.json()) as { query: string; results: SearchResult[] };
}

export type RecipeDetail = {
  id: string;
  title_zh: string;
  ingredients: string[];
  tags: string[];
  cook_time_minutes?: number | null;
  content_zh: string;
  steps?: string[];
  like_count: number;
  liked_by_me: boolean;
};

export async function getRecipeById(id: string) {
  const resp = await fetch(`/api/recipes/${encodeURIComponent(id)}`);
  if (!resp.ok) {
    throw new Error(`recipe fetch failed: ${resp.status}`);
  }
  return (await resp.json()) as RecipeDetail;
}

// Auth types and functions
export type User = {
  id: string;
  nickname: string;
};

export type AuthResponse = {
  token: string;
  user: User;
};

export async function register(nickname: string, password: string) {
  const resp = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nickname, password }),
  });
  if (!resp.ok) {
    const error = await resp.text();
    throw new Error(`register failed: ${resp.status} - ${error}`);
  }
  return (await resp.json()) as { user: User };
}

export async function login(nickname: string, password: string) {
  const resp = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nickname, password }),
  });
  if (!resp.ok) {
    const error = await resp.text();
    throw new Error(`login failed: ${resp.status} - ${error}`);
  }
  return (await resp.json()) as AuthResponse;
}

export function setAuthToken(token: string) {
  localStorage.setItem("auth_token", token);
}

export function getAuthToken(): string | null {
  return localStorage.getItem("auth_token");
}

export function clearAuthToken() {
  localStorage.removeItem("auth_token");
}

export function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Like functions
export type LikeResponse = {
  liked_by_me: boolean;
  like_count: number;
};

export async function likeRecipe(recipeId: string): Promise<LikeResponse> {
  const resp = await fetch(`/api/recipes/${encodeURIComponent(recipeId)}/like`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!resp.ok) {
    const error = await resp.text();
    throw new Error(`like failed: ${resp.status} - ${error}`);
  }
  return (await resp.json()) as LikeResponse;
}

export async function unlikeRecipe(recipeId: string): Promise<LikeResponse> {
  const resp = await fetch(`/api/recipes/${encodeURIComponent(recipeId)}/like`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!resp.ok) {
    const error = await resp.text();
    throw new Error(`unlike failed: ${resp.status} - ${error}`);
  }
  return (await resp.json()) as LikeResponse;
}

