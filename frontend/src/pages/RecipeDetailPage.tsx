import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";

import { getRecipeById, type RecipeDetail, likeRecipe, unlikeRecipe, getAuthToken, getCurrentUser } from "../api";

export default function RecipeDetailPage() {
  const params = useParams();
  const recipeId = params.id ? decodeURIComponent(params.id) : null;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [likeLoading, setLikeLoading] = useState(false);
  const [currentUser] = useState(getCurrentUser());

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
      setError("请先登录以点赞");
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
      <Link to="/">返回</Link>

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
              {likeLoading ? "..." : recipe.liked_by_me ? "❤️ 取消点赞" : "🤍 点赞"} ({recipe.like_count})
            </button>
          </div>

          {recipe.cook_time_minutes ? <div>烹饪时间: {recipe.cook_time_minutes} 分钟</div> : null}

          {recipe.tags && recipe.tags.length > 0 && (
            <div style={{ margin: "12px 0" }}>
              <strong>标签:</strong>{" "}
              {recipe.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    margin: "2px 4px",
                    background: "#e0e0e0",
                    borderRadius: "4px",
                    fontSize: "0.9em",
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          <h2>食材</h2>
          <ul>
            {recipe.ingredients?.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>

          <h2>内容</h2>
          <pre style={{ whiteSpace: "pre-wrap", background: "#f7f7f7", padding: 12, borderRadius: 8 }}>
            {recipe.content_zh}
          </pre>

          {recipe.steps && recipe.steps.length > 0 ? (
            <>
              <h2>步骤</h2>
              <ol>
                {recipe.steps.map((s, idx) => (
                  <li key={`${idx}-${s}`}>{s}</li>
                ))}
              </ol>
            </>
          ) : null}

          {recipe.meta && (
            <div style={{ marginTop: 24, padding: 12, background: "#f0f0f0", borderRadius: 8 }}>
              <h3>元数据</h3>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.9em" }}>
                {JSON.stringify(recipe.meta, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

