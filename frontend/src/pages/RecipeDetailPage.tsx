import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getRecipeById, type RecipeDetail, likeRecipe, unlikeRecipe, getAuthToken } from "../api";

export default function RecipeDetailPage() {
  const params = useParams();
  const recipeId = params.id ? decodeURIComponent(params.id) : null;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [likeLoading, setLikeLoading] = useState(false);

  useEffect(() => {
    if (!recipeId) return;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const r = await getRecipeById(recipeId);
        setRecipe(r);
      } catch (e) {
        setError(e instanceof Error ? e.message : "load failed");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [recipeId]);

  async function handleLike() {
    if (!recipeId || !recipe) return;
    
    const token = getAuthToken();
    if (!token) {
      setError("Please login to like recipes");
      return;
    }

    setLikeLoading(true);
    try {
      if (recipe.liked_by_me) {
        const result = await unlikeRecipe(recipeId);
        setRecipe({
          ...recipe,
          liked_by_me: result.liked_by_me,
          like_count: result.like_count,
        });
      } else {
        const result = await likeRecipe(recipeId);
        setRecipe({
          ...recipe,
          liked_by_me: result.liked_by_me,
          like_count: result.like_count,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "like operation failed");
    } finally {
      setLikeLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 880, margin: "0 auto", padding: 16 }}>
      <a href="/">Back</a>

      {loading ? <div>Loading...</div> : null}
      {error ? <div style={{ color: "crimson" }}>{error}</div> : null}

      {recipe ? (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h1>{recipe.title_zh}</h1>
            <button
              onClick={handleLike}
              disabled={likeLoading}
              style={{
                padding: "8px 16px",
                fontSize: "16px",
                cursor: likeLoading ? "not-allowed" : "pointer",
                background: recipe.liked_by_me ? "#ff4444" : "#4CAF50",
                color: "white",
                border: "none",
                borderRadius: "4px",
              }}
            >
              {likeLoading ? "..." : recipe.liked_by_me ? "❤️ Unlike" : "🤍 Like"} ({recipe.like_count})
            </button>
          </div>

          {recipe.cook_time_minutes ? <div>Cook time: {recipe.cook_time_minutes} min</div> : null}

          <h2>Ingredients</h2>
          <ul>
            {recipe.ingredients?.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>

          <h2>Content</h2>
          <pre style={{ whiteSpace: "pre-wrap", background: "#f7f7f7", padding: 12, borderRadius: 8 }}>
            {recipe.content_zh}
          </pre>

          {recipe.steps && recipe.steps.length > 0 ? (
            <>
              <h2>Steps</h2>
              <ol>
                {recipe.steps.map((s, idx) => (
                  <li key={`${idx}-${s}`}>{s}</li>
                ))}
              </ol>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

