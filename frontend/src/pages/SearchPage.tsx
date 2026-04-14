import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { searchRecipes, containsChinese, getCurrentUser, setCurrentUser, clearAuthToken } from "../api";
import type { SearchResult, User } from "../api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(8);
  const [alpha, setAlpha] = useState(0.8);
  const [beta, setBeta] = useState(0.2);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  
  const [currentUser, setCurrentUserState] = useState<User | null>(getCurrentUser());

  const canSearch = useMemo(() => query.trim().length > 0 && !loading, [query, loading]);

  function handleLogout() {
    clearAuthToken();
    setCurrentUser(null);
    setCurrentUserState(null);
  }

  async function onSearch() {
    setLoading(true);
    setError(null);
    
    // Validate Chinese characters
    if (!containsChinese(query.trim())) {
      setError("查询必须包含中文字符");
      setLoading(false);
      return;
    }
    
    try {
      const resp = await searchRecipes({
        query: query.trim(),
        topK,
        rank: { alpha, beta },
      });
      setResults(resp.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 880, margin: "0 auto", padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>CookRag</h1>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {currentUser ? (
            <>
              <span>欢迎, {currentUser.nickname}</span>
              <button onClick={handleLogout} style={{ padding: "4px 12px" }}>退出</button>
            </>
          ) : (
            <>
              <Link to="/login" style={{ padding: "4px 12px" }}>登录</Link>
              <Link to="/register" style={{ padding: "4px 12px" }}>注册</Link>
            </>
          )}
        </div>
      </div>
      
      <p>输入任意语言的烹饪需求（菜谱数据仅中文），系统将返回匹配的中文菜谱。</p>

      <div style={{ display: "grid", gap: 12 }}>
        <label>
          Query (must contain Chinese characters)
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="例如：辣味麻婆豆腐"
            style={{ width: "100%", padding: 8 }}
          />
        </label>

        <label>
          topK
          <input
            type="number"
            value={topK}
            min={1}
            max={50}
            onChange={(e) => setTopK(Number(e.target.value))}
            style={{ width: 160, padding: 8 }}
          />
        </label>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label>
            Alpha (relevance weight)
            <input
              type="number"
              value={alpha}
              min={0}
              max={1}
              step={0.1}
              onChange={(e) => setAlpha(Number(e.target.value))}
              style={{ width: "100%", padding: 8 }}
            />
          </label>

          <label>
            Beta (like weight)
            <input
              type="number"
              value={beta}
              min={0}
              max={1}
              step={0.1}
              onChange={(e) => setBeta(Number(e.target.value))}
              style={{ width: "100%", padding: 8 }}
            />
          </label>
        </div>

        <button disabled={!canSearch} onClick={onSearch}>
          {loading ? "Searching..." : "Search"}
        </button>

        {error ? <div style={{ color: "crimson" }}>{error}</div> : null}

        <div>
          <h2>Results</h2>
          {results.length === 0 ? (
            <div>暂无结果</div>
          ) : (
            <ul>
              {results.map((r) => (
                <li key={r.id}>
                  <a href={`/recipes/${encodeURIComponent(r.id)}`}>{r.title_zh}</a>
                  <span style={{ marginLeft: 8, color: "#666" }}>
                    score: {r.score.toFixed(4)} | 
                    likes: {r.like_count} | 
                    final: {r.final_score.toFixed(4)}
                  </span>
                  {r.snippet && (
                    <div style={{ fontSize: "0.9em", color: "#888", marginTop: 4 }}>
                      {r.snippet}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

